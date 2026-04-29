from pathlib import Path
import pandas as pd

DEFAULT_SYSTEM_PROMPT = Path("prompts/system_prompt.md").read_text(encoding="utf-8") if Path("prompts/system_prompt.md").exists() else """
You classify prescription medication errors.
Use only provided knowledge excerpts and prescription data.
If evidence is insufficient, set has_medication_error to false.
Return JSON only.
""".strip()

def build_case_prompt(case_id: str, case_df: pd.DataFrame) -> str:
    first = case_df.iloc[0].to_dict()
    patient_fields = [
        "patient_age", "weight_kg", "height_cm", "bmi", "bsa",
        "sbp", "dbp", "allergy_text", "diagnosis_icd"
    ]

    lines = [f"Order/case ID: {case_id}", "", "Patient data:"]
    for field in patient_fields:
        if field in first and pd.notna(first[field]):
            lines.append(f"- {field}: {first[field]}")

    lines.append("")
    lines.append("Medication orders:")
    med_fields = ["drug_name", "dose", "route", "frequency", "duration", "status"]
    for idx, row in case_df.iterrows():
        med = []
        for field in med_fields:
            if field in row and pd.notna(row[field]):
                med.append(f"{field}={row[field]}")
        lines.append(f"{idx + 1}. " + "; ".join(med))

    lines.append("")
    lines.append("Classify medication errors using the required JSON schema.")
    return "\n".join(lines)
