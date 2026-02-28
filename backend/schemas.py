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


class UserContext(BaseModel):
    persona: str | None = None
    primary_concerns: list[str] = []
    document_context: str | None = None
    experience_level: str | None = None
    deal_breakers: list[str] = []


class ForYouInsights(BaseModel):
    top_risks_for_you: list[str]
    action_items: list[str]
    deal_breaker_checks: list[str]
    tailored_summary: str


class InsightsRequest(BaseModel):
    analysis: AnalyzeResponse
    user_context: UserContext


class InsightsResponse(BaseModel):
    insights: ForYouInsights
class VaultRequest(BaseModel):
    analysis: dict


class VaultReceipt(BaseModel):
    vault_id: str
    content_hash: str
    timestamp: str
    vault_address: str
    network: str
    algorithm: str
    status: str
    expires: str | None = None
    message: str
