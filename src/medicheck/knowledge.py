import json
import os
import tempfile
from pathlib import Path
from typing import List, Dict, Any

from dotenv import set_key, find_dotenv
from openai import OpenAI
from .io import load_json, save_json


def _save_vector_store_id_to_env(vector_store_id: str) -> None:
    """Persist VECTOR_STORE_ID into .env so inference never needs to rebuild."""
    env_path = find_dotenv(usecwd=True)
    if not env_path:
        env_path = Path(".env")
        env_path.touch()
        env_path = str(env_path)
    set_key(env_path, "VECTOR_STORE_ID", vector_store_id)
    print(f"Saved VECTOR_STORE_ID={vector_store_id} → {env_path}")


# Inventory/cost fields in the hospital formulary that carry zero clinical value
_FORMULARY_SKIP = {
    "Seq", "Code", "StoreBin", "Quantity", "UOM",
    "ItemCost", "Amount", "Count", "Vendor", "Unnamed: 10", "Manufacturing",
    "Generic Drug",   # Thai-script duplicate of Generic (ENG)
}
# Truncate long narrative fields so each entry stays under ~600 chars
_FORMULARY_TRUNCATE = {
    "Indications": 200,
    "Dosage (mg/kg/day)": 150,
    "Contraindications": 250,
}


def _format_formulary(obj: dict) -> str:
    """Compact single-block text for a BKN formulary drug entry."""
    name  = obj.get("Generic (ENG)") or obj.get("Itemname") or "Unknown"
    brand = obj.get("Itemname", "")
    group = obj.get(" Drug Group") or obj.get("Drug Group", "")
    allergen = str(obj.get("Allergen", "")).strip()

    header = f"Drug: {name}"
    if brand and brand.lower() != str(name).lower():
        header += f" ({brand})"
    if group:
        header += f" | Group: {group}"

    parts = [header]

    if allergen and allergen not in ("nan", "NaN", ""):
        # Strip leading drug-group prefix if duplicated (e.g. "Antiasthmatic & COPD,budesonide")
        if group and allergen.startswith(group + ","):
            allergen = allergen[len(group) + 1:].strip()
        parts.append(f"Allergen: {allergen}")

    for field, limit in _FORMULARY_TRUNCATE.items():
        val = str(obj.get(field, "")).strip()
        if val and val not in ("nan", "NaN", "-"):
            truncated = val[:limit] + ("..." if len(val) > limit else "")
            label = "Dosage" if "Dosage" in field else field
            parts.append(f"{label}: {truncated}")

    return "\n".join(parts)


def _format_knowledge(obj: dict) -> str:
    """Compact readable text for taxonomy/allergy KB entries."""
    parts = []

    title = obj.get("title") or obj.get("label") or ""
    if title:
        parts.append(f"[{title}]")

    # Allergy-rule specific header
    allergen_class = obj.get("allergen_class", "")
    allergen_examples = obj.get("allergen_examples", [])
    risk = obj.get("risk_level", "")
    if allergen_class:
        ex = ", ".join(allergen_examples[:4]) if allergen_examples else ""
        line = f"Allergen class: {allergen_class}"
        if ex:
            line += f" (e.g. {ex})"
        if risk:
            line += f" — Risk: {risk}"
        parts.append(line)

    text = obj.get("text", "")
    if text:
        parts.append(text)

    criteria = obj.get("criteria", [])
    if criteria:
        parts.append("Detection criteria: " + "; ".join(criteria))

    action = obj.get("action", "")
    if action:
        parts.append(f"Action: {action}")

    return "\n".join(parts)


def _is_formulary(src_path: str, first_obj: dict) -> bool:
    """Detect if this JSONL is a drug formulary (has Itemname + Allergen fields)."""
    return "Itemname" in first_obj and "Allergen" in first_obj


def _jsonl_to_txt(src_path: str) -> str:
    """Convert .jsonl to lean plain text for OpenAI upload.

    - Formulary files: strips 12 inventory fields, truncates narrative fields.
    - Knowledge/taxonomy files: formats as readable sections, drops metadata noise.
    Typical savings: ~80% fewer chars per formulary entry, ~35% for knowledge entries.
    """
    base = Path(src_path).stem
    tmp_path = os.path.join(tempfile.gettempdir(), f"{base}.txt")

    with open(src_path, "r", encoding="utf-8") as in_f:
        raw_lines = [l.strip() for l in in_f if l.strip()]

    if not raw_lines:
        Path(tmp_path).write_text("", encoding="utf-8")
        return tmp_path

    try:
        first_obj = json.loads(raw_lines[0])
        formulary = _is_formulary(src_path, first_obj)
    except json.JSONDecodeError:
        formulary = False

    formatter = _format_formulary if formulary else _format_knowledge

    with open(tmp_path, "w", encoding="utf-8") as out_f:
        for lineno, line in enumerate(raw_lines, 1):
            try:
                obj = json.loads(line)
                out_f.write(formatter(obj) + "\n\n")
            except json.JSONDecodeError as e:
                print(f"Warning: skipping invalid JSON on line {lineno} in {src_path}: {e}")

    return tmp_path


def build_knowledge_base(
    api_key: str,
    knowledge_files: List[str],
    vector_store_name: str,
    cache_path: str = "outputs/knowledge_cache.json",
    force_new_vector_store: bool = False,
) -> Dict[str, Any]:
    """Upload knowledge files to an OpenAI vector store and poll until indexing completes.

    - .jsonl files are converted to .txt before upload (OpenAI does not index .jsonl directly).
    - Cache keys are filename-based so the cache is portable across machines/drives.
    - If the cached vector store no longer exists on OpenAI it is recreated automatically.
    """
    client = OpenAI(api_key=api_key)
    cache = load_json(cache_path)

    raw_files_cache = cache.get("files", {})
    files_cache: Dict[str, str] = raw_files_cache if isinstance(raw_files_cache, dict) else {}

    vector_store_id = None if force_new_vector_store else cache.get("vector_store", {}).get("id")

    # Verify the cached vector store still exists (it expires after inactivity)
    if vector_store_id:
        try:
            client.vector_stores.retrieve(vector_store_id)
            print(f"Reusing vector store: {vector_store_id}")
        except Exception:
            print(f"Vector store {vector_store_id} no longer exists — will create a new one.")
            vector_store_id = None
            files_cache = {}

    # Stage 1: resolve upload paths, converting .jsonl → .txt
    files_to_upload: List[tuple] = []  # (upload_path, cache_key)
    temp_files: List[str] = []

    for filepath in knowledge_files:
        p = Path(filepath)
        if not p.exists():
            raise FileNotFoundError(f"Knowledge file not found: {filepath}")

        if p.suffix.lower() == ".jsonl":
            print(f"Converting {p.name} → .txt for upload ...")
            tmp_path = _jsonl_to_txt(str(p))
            cache_key = p.stem + ".txt"
            temp_files.append(tmp_path)
            files_to_upload.append((tmp_path, cache_key))
        else:
            files_to_upload.append((str(p), p.name))

    # Stage 2: upload files (skip cached entries unless forcing rebuild)
    uploaded_file_ids: List[str] = []

    for upload_path, cache_key in files_to_upload:
        if cache_key in files_cache and not force_new_vector_store:
            file_id = files_cache[cache_key]
            print(f"Reusing cached file: {cache_key} -> {file_id}")
        else:
            print(f"Uploading: {cache_key} ...")
            with open(upload_path, "rb") as f:
                uploaded = client.files.create(file=(cache_key, f.read()), purpose="assistants")
            file_id = uploaded.id
            files_cache[cache_key] = file_id
            print(f"Uploaded: {cache_key} -> {file_id}")
        uploaded_file_ids.append(file_id)

    # Stage 3: create or reuse vector store
    if not vector_store_id:
        print(f"Creating vector store '{vector_store_name}' ...")
        vs = client.vector_stores.create(name=vector_store_name)
        vector_store_id = vs.id
        print(f"Created vector store: {vector_store_id}")

    # Stage 4: attach files and poll until indexing completes
    print("Attaching files and waiting for indexing ...")
    batch = client.vector_stores.file_batches.create_and_poll(
        vector_store_id=vector_store_id,
        file_ids=uploaded_file_ids,
    )
    print(f"Batch status: {batch.status}")
    if getattr(batch, "file_counts", None):
        print(f"File counts: {batch.file_counts}")

    if batch.status != "completed":
        raise RuntimeError(f"Vector store ingestion did not complete: status={batch.status}")

    updated_cache = {
        "vector_store": {"id": vector_store_id, "name": vector_store_name},
        "files": files_cache,
        "last_batch": {
            "id": batch.id,
            "status": batch.status,
            "file_counts": batch.file_counts.model_dump() if getattr(batch, "file_counts", None) else None,
        },
    }
    save_json(cache_path, updated_cache)

    for tmp in temp_files:
        try:
            os.remove(tmp)
        except OSError:
            pass

    _save_vector_store_id_to_env(vector_store_id)

    print(f"\nDONE. vector_store_id: {vector_store_id}")
    print(f"Cache saved to: {cache_path}")

    return {
        "vector_store_id": vector_store_id,
        "cache_path": cache_path,
        "batch_status": batch.status,
    }
