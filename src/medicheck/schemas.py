from typing import List
from pydantic import BaseModel, Field

class ErrorDetail(BaseModel):
    category: str
    implicated_drugs: List[str] = Field(default_factory=list)
    rationale: str = ""

class ClassificationResult(BaseModel):
    order_id: str
    has_medication_error: bool
    error_categories: List[str] = Field(default_factory=list)
    error_details: List[ErrorDetail] = Field(default_factory=list)
    ncc_merp_severity_category: str = "A"
    overall_recommendation: str = ""
    evidence_quotes: List[str] = Field(default_factory=list)
