import pandas as pd
from medicheck.prompting import build_case_prompt

def test_build_case_prompt_contains_case_and_drug():
    df = pd.DataFrame([{
        "case_id": "CASE-1",
        "patient_age": 65,
        "drug_name": "paracetamol",
        "dose": "500 mg",
        "route": "PO",
        "frequency": "q6h"
    }])
    prompt = build_case_prompt("CASE-1", df)
    assert "CASE-1" in prompt
    assert "paracetamol" in prompt
