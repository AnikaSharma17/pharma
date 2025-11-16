from pydantic import BaseModel, Field
from typing import List, Optional

class MoleculeOpportunity(BaseModel):
    """Schema for a single molecule repurposing opportunity."""
    molecule_name: str = Field(description="The generic molecule name analyzed.")
    current_status: str = Field(description="Molecule's current regulatory status (e.g., 'Approved for COPD').")
    repurpose_opportunity: str = Field(description="The new disease/market target for repurposing (e.g., 'Asthma in India').")
    unmet_need_score: float = Field(description="Quantitative score (0-10) indicating patient need in the target market.")
    key_patent_expiry: Optional[str] = Field(description="The earliest relevant patent expiry date (YYYY-MM-DD).")
    evidence_summary: str = Field(description="A brief summary of clinical/internal evidence supporting the opportunity.")

class FinalReport(BaseModel):
    """The final structured output schema for the executive report."""
    report_title: str = Field(description="A concise, executive title for the innovation brief.")
    executive_summary: str = Field(description="A one-paragraph summary of the top findings and recommendation.")
    opportunities: List[MoleculeOpportunity] = Field(description="A list of 1-3 molecule repurposing opportunities identified.")
    disclaimer: str = Field(default="This report is AI-generated and requires human validation of all regulatory and IP data.", description="Standard legal disclaimer.")
    query: str = Field(description="The original research query posed by the user.")
    target_geography: str = Field(description="The geographic focus area for the report (e.g., 'India', 'Global').")
    