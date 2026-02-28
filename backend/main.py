from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from mangum import Mangum
import httpx

import config
from schemas import AnalyzeRequest, AnalyzeResponse, AnalyzeUrlRequest, VaultRequest, VaultReceipt
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

# Serve the web dashboard at /dashboard
app.mount(
    "/dashboard",
    StaticFiles(directory="static", html=True),
    name="dashboard",
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


@app.post("/analyze_url", response_model=AnalyzeResponse)
async def analyze_url(req: AnalyzeUrlRequest):
    if not req.url or not req.url.strip():
        raise HTTPException(status_code=400, detail="URL is required.")

    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            resp = await client.get(req.url, follow_redirects=True)
            resp.raise_for_status()
    except httpx.HTTPError as e:
        raise HTTPException(
            status_code=400,
            detail=f"Failed to fetch URL: {e}",
        )

    html_text = resp.text

    # Very simple extraction: strip tags and collapse whitespace.
    import re as _re

    text = _re.sub(r"<script[\\s\\S]*?</script>", " ", html_text, flags=_re.I)
    text = _re.sub(r"<style[\\s\\S]*?</style>", " ", text, flags=_re.I)
    text = _re.sub(r"<[^>]+>", " ", text)
    text = _re.sub(r"\\s+", " ", text).strip()

    if len(text) < 50:
        raise HTTPException(
            status_code=400,
            detail="Fetched page did not contain enough text to analyze.",
        )

    sections = parse_text(text)
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
