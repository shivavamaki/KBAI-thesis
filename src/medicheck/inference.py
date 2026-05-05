import json
import time
import traceback
from typing import Dict, Any
import pandas as pd
from openai import OpenAI, APIConnectionError, APITimeoutError, RateLimitError, APIError
from pydantic import ValidationError
from .config import get_settings
from .io import load_json, append_jsonl, save_json
from .prompting import DEFAULT_SYSTEM_PROMPT, build_case_prompt, extract_drug_names
from .schemas import ClassificationResult


def _resolve_vector_store_id(cache_path: str) -> str:
    """Return vector store ID from env (preferred) or cache file (fallback)."""
    settings = get_settings()
    if settings.vector_store_id:
        print(f"Using vector store from env: {settings.vector_store_id}")
        return settings.vector_store_id

    cache = load_json(cache_path)
    vs_id = cache.get("vector_store", {}).get("id", "")
    if vs_id:
        print(f"Using vector store from cache: {vs_id}")
        return vs_id

    raise ValueError(
        "Vector store ID not found. "
        "Set VECTOR_STORE_ID in .env or run build_knowledge.py first."
    )


def _retrieve_kb_snippets(
    client: OpenAI,
    vector_store_id: str,
    query: str,
    max_results: int = 5,
) -> str:
    """Search vector store and return concatenated text snippets."""
    result = client.vector_stores.search(
        vector_store_id=vector_store_id,
        query=query,
        max_num_results=max_results,
    )
    snippets = []
    for item in getattr(result, "data", []):
        parts = [
            getattr(c, "text", None)
            for c in getattr(item, "content", [])
            if getattr(c, "text", None)
        ]
        joined = "\n".join(parts).strip()
        if joined:
            snippets.append(joined)
    return "\n\n---\n\n".join(snippets)


def _get_json_schema() -> Dict[str, Any]:
    return {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "order_id": {"type": "string"},
            "has_medication_error": {"type": "boolean"},
            "error_categories": {"type": "array", "items": {"type": "string"}},
            "error_details": {
                "type": "array",
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "required": ["category", "implicated_drugs", "rationale"],
                    "properties": {
                        "category": {"type": "string"},
                        "implicated_drugs": {"type": "array", "items": {"type": "string"}},
                        "rationale": {"type": "string"},
                    },
                },
            },
            "ncc_merp_severity_category": {"type": "string"},
            "overall_recommendation": {"type": "string"},
            "evidence_quotes": {"type": "array", "items": {"type": "string"}},
        },
        "required": [
            "order_id",
            "has_medication_error",
            "error_categories",
            "error_details",
            "ncc_merp_severity_category",
            "overall_recommendation",
            "evidence_quotes",
        ],
    }


def classify_case(
    client: OpenAI,
    model: str,
    vector_store_id: str,
    case_id: str,
    case_df: pd.DataFrame,
    max_retries: int = 3,
    max_kb_results: int = 5,
) -> Dict[str, Any]:
    user_prompt = build_case_prompt(case_id, case_df)
    drugs = extract_drug_names(case_df)
    kb_query = f"medication error classification {' '.join(drugs[:5])}".strip()

    for attempt in range(1, max_retries + 1):
        try:
            kb_snippets = _retrieve_kb_snippets(client, vector_store_id, kb_query, max_kb_results)
            if not kb_snippets.strip():
                raise ValueError("No knowledge snippets retrieved from vector store.")

            combined_input = f"KNOWLEDGE BASE:\n{kb_snippets}\n\nCASE:\n{user_prompt}"

            response = client.responses.create(
                model=model,
                instructions=DEFAULT_SYSTEM_PROMPT,
                input=combined_input,
                text={
                    "format": {
                        "type": "json_schema",
                        "name": "medicheck_output",
                        "strict": True,
                        "schema": _get_json_schema(),
                    }
                },
                temperature=0,
            )

            raw_text = getattr(response, "output_text", None)
            if not raw_text or not raw_text.strip():
                raise ValueError("Model returned empty output.")

            data = json.loads(raw_text)
            parsed = ClassificationResult.model_validate(data)
            return parsed.model_dump()

        except (APIConnectionError, APITimeoutError, RateLimitError, APIError) as e:
            if attempt == max_retries:
                raise
            time.sleep(2 ** attempt)
        except (json.JSONDecodeError, ValidationError, ValueError):
            if attempt == max_retries:
                raise
            time.sleep(1)


def run_inference(
    api_key: str,
    input_path: str,
    output_path: str,
    cache_path: str = "outputs/knowledge_cache.json",
    model: str = "gpt-4.1-mini",
    group_column: str = "case_id",
    max_cases: int | None = None,
    max_kb_results: int = 5,
) -> Dict[str, Any]:
    vector_store_id = _resolve_vector_store_id(cache_path)
    client = OpenAI(api_key=api_key)
    if input_path.lower().endswith(".json"):
        import json as _json
        with open(input_path, "r", encoding="utf-8") as f:
            df = pd.DataFrame(_json.load(f))
    else:
        df = pd.read_csv(input_path)
    results = {}
    failed = []

    grouped = list(df.groupby(group_column, dropna=False))
    if max_cases:
        grouped = grouped[:max_cases]

    for case_id, case_df in grouped:
        case_id = str(case_id)
        try:
            result = classify_case(
                client, model, vector_store_id, case_id, case_df,
                max_kb_results=max_kb_results,
            )
            results[case_id] = result
            append_jsonl(output_path, [result])
        except Exception as e:
            failed.append({
                "case_id": case_id,
                "error": str(e),
                "traceback": traceback.format_exc(),
            })

    save_json("outputs/failed_cases.json", {"failed": failed})
    return {"completed": len(results), "failed": len(failed), "results": results}
