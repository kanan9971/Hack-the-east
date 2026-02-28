from pydantic import BaseModel


class AnalyzeRequest(BaseModel):
    text: str
    doc_type: str | None = None
    persona: str | None = None


class RiskFlag(BaseModel):
    category: str
    severity: str
    clause_excerpt: str
    explanation: str


class SectionOut(BaseModel):
    title: str
    body: str
    labels: list[str]


class AnalyzeResponse(BaseModel):
    summary: str
    key_points: list[str]
    risks: list[RiskFlag]
    sections: list[SectionOut]
    entities: dict
    persona_notes: list[str] | None = None
