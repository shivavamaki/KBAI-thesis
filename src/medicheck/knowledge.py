from pathlib import Path
from typing import List, Dict, Any
from openai import OpenAI
from .io import load_json, save_json

def build_knowledge_base(
    api_key: str,
    knowledge_files: List[str],
    vector_store_name: str,
    cache_path: str = "outputs/knowledge_cache.json",
    recreate: bool = False,
) -> Dict[str, Any]:
    """Upload knowledge files, attach to vector store, and poll until indexing completes."""
    client = OpenAI(api_key=api_key)
    cache = load_json(cache_path)

    if recreate or "vector_store" not in cache:
        vector_store = client.vector_stores.create(name=vector_store_name)
        cache["vector_store"] = {"id": vector_store.id, "name": vector_store_name}
        cache["files"] = {}
        save_json(cache_path, cache)

    vector_store_id = cache["vector_store"]["id"]
    uploaded_file_ids = []

    for file_path in knowledge_files:
        p = Path(file_path)
        if not p.exists():
            raise FileNotFoundError(f"Knowledge file not found: {file_path}")

        cache_key = str(p.resolve())
        if not recreate and cache.get("files", {}).get(cache_key):
            uploaded_file_ids.append(cache["files"][cache_key]["id"])
            continue

        with p.open("rb") as f:
            uploaded = client.files.create(file=f, purpose="assistants")

        cache.setdefault("files", {})[cache_key] = {"id": uploaded.id, "filename": p.name}
        uploaded_file_ids.append(uploaded.id)
        save_json(cache_path, cache)

    if uploaded_file_ids:
        file_batch = client.vector_stores.file_batches.create_and_poll(
            vector_store_id=vector_store_id,
            file_ids=uploaded_file_ids,
        )

        cache["last_file_batch"] = {
            "id": file_batch.id,
            "status": file_batch.status,
            "file_counts": getattr(file_batch, "file_counts", None).model_dump() if getattr(file_batch, "file_counts", None) else None,
        }
        save_json(cache_path, cache)

        if getattr(file_batch, "status", None) != "completed":
            raise RuntimeError(f"Vector store ingestion not completed: {file_batch}")

    vector_store = client.vector_stores.retrieve(vector_store_id)
    cache["vector_store_status"] = {
        "status": vector_store.status,
        "file_counts": getattr(vector_store, "file_counts", None).model_dump() if getattr(vector_store, "file_counts", None) else None,
    }
    save_json(cache_path, cache)
    return cache
