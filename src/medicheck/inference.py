import json
import time
import traceback
from typing import Dict, Any
import pandas as pd
from openai import OpenAI, APIConnectionError, APITimeoutError, RateLimitError, APIError
from pydantic import ValidationError
from .io import load_json, append_jsonl, save_json
from .prompting import DEFAULT_SYSTEM_PROMPT, build_case_prompt
from .schemas import ClassificationResult

def extract_text_from_response(response) -> str:
    output_text = getattr(response, "output_text", None)
    if isinstance(output_text, str) and output_text.strip():
        return output_text.strip()

    preview = response.model_dump() if hasattr(response, "model_dump") else str(response)
    raise ValueError(f"Model returned empty text output. Response preview: {str(preview)[:3000]}")

def classify_case(
    client: OpenAI,
    model: str,
    vector_store_id: str,
    case_id: str,
    case_df: pd.DataFrame,
    max_retries: int = 3,
) -> Dict[str, Any]:
    user_prompt = build_case_prompt(case_id, case_df)

    for attempt in range(1, max_retries + 1):
        try:
            response = client.responses.create(
                model=model,
                instructions=DEFAULT_SYSTEM_PROMPT,
                input=user_prompt,
                tools=[{
                    "type": "file_search",
                    "vector_store_ids": [vector_store_id],
                }],
                temperature=0,
            )
            text = extract_text_from_response(response)
            data = json.loads(text)
            parsed = ClassificationResult.model_validate(data)
            return parsed.model_dump()
        except (APIConnectionError, APITimeoutError, RateLimitError, APIError) as e:
            if attempt == max_retries:
                raise
            time.sleep(2 * attempt)
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
) -> Dict[str, Any]:
    cache = load_json(cache_path)
    vector_store_id = cache.get("vector_store", {}).get("id")
    if not vector_store_id:
        raise ValueError("Vector store id not found. Run build_knowledge first.")

    client = OpenAI(api_key=api_key)
    df = pd.read_csv(input_path)
    results = {}
    failed = []

    grouped = list(df.groupby(group_column, dropna=False))
    if max_cases:
        grouped = grouped[:max_cases]

    for case_id, case_df in grouped:
        case_id = str(case_id)
        try:
            result = classify_case(client, model, vector_store_id, case_id, case_df)
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
