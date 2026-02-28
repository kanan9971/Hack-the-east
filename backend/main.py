from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from mangum import Mangum

import config
from schemas import AnalyzeRequest, AnalyzeResponse, VaultRequest, VaultReceipt
from services.parser import parse_text
from services.classifier import classify_sections
from services.analyzer import analyze_contract
from services.risk_flagger import flag_risks
from services.vault import create_vault_receipt

app = FastAPI(title="ContractLens API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/analyze", response_model=AnalyzeResponse)
async def analyze(req: AnalyzeRequest):
    if not req.text or len(req.text.strip()) < 50:
        raise HTTPException(status_code=400, detail="Text too short to analyze.")

    sections = parse_text(req.text)
    classified = classify_sections(sections)
    llm_result = await analyze_contract(classified, req.doc_type, req.persona)
    risks = flag_risks(classified, llm_result)

    return AnalyzeResponse(
        summary=llm_result.get("summary", ""),
        key_points=llm_result.get("key_points", []),
        risks=risks,
        sections=[
            {"title": s.title, "body": s.body, "labels": s.labels}
            for s in classified
        ],
        entities=llm_result.get("entities", {}),
        persona_notes=llm_result.get("persona_notes"),
    )


@app.post("/vault", response_model=VaultReceipt)
async def vault_analysis(req: VaultRequest):
    if not req.analysis:
        raise HTTPException(status_code=400, detail="No analysis data provided.")
    receipt = create_vault_receipt(req.analysis)
    return VaultReceipt(**receipt)


handler = Mangum(app)
