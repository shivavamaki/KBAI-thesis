import json
from pathlib import Path
import pandas as pd

DEFAULT_SYSTEM_PROMPT = Path("prompts/system_prompt.md").read_text(encoding="utf-8") if Path("prompts/system_prompt.md").exists() else """
You classify prescription medication errors.
Use only provided knowledge excerpts and prescription data.
If evidence is insufficient, set has_medication_error to false.
Return JSON only.
""".strip()

# Columns that identify the group — strip from per-row records to avoid duplication
_GROUP_COLS = {"case_id", "ID", "id", "order_id"}

# Known drug-name column variants (checked in order)
_DRUG_COLS = ("drug_name", "Drug", "drug", "DRUG", "medication", "Medication")


def build_case_prompt(case_id: str, case_df: pd.DataFrame) -> str:
    """Build user prompt. Works with any column layout (local CSV or Colab JSON)."""
    records = []
    for _, row in case_df.iterrows():
        record = {
            k: v for k, v in row.items()
            if k not in _GROUP_COLS
            and pd.notna(v)
            and str(v).strip() not in ("", "-", "None", "nan")
        }
        if record:
            records.append(record)

    return (
        f"Order ID: {case_id}\n"
        f"Prescription: {json.dumps(records, ensure_ascii=False, separators=(',', ':'))}\n"
        f"Classify medication errors. Return JSON only."
    )


def extract_drug_names(case_df: pd.DataFrame) -> list:
    """Return de-duplicated drug names from whichever column exists in the dataframe."""
    for col in _DRUG_COLS:
        if col in case_df.columns:
            seen, result = set(), []
            for val in case_df[col]:
                s = str(val).strip()
                if s and s not in ("", "-", "None", "nan") and s not in seen:
                    seen.add(s)
                    result.append(s)
            if result:
                return result
    return []
