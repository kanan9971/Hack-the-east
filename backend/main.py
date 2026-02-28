import logging
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from mangum import Mangum
import httpx

import config

logger = logging.getLogger(__name__)
from schemas import (
    AnalyzeRequest, AnalyzeResponse, AnalyzeUrlRequest, VaultRequest, VaultReceipt,
    InsightsRequest, InsightsResponse, AgentChatRequest, AgentChatResponse,
)
from services.parser import parse_text
from services.classifier import classify_sections
from services.analyzer import analyze_contract
from services.insights import generate_insights
from services.risk_flagger import flag_risks
from services.vault import create_vault_receipt
from services.agent import agent_chat

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


@app.on_event("startup")
def startup_config():
    """Log which API keys are set (never log values)."""
    minimax_ok = bool(config.MINIMAX_API_KEY and config.MINIMAX_API_KEY.strip())
    bedrock_configured = bool(config.AWS_REGION and config.BEDROCK_MODEL_ID)

    if minimax_ok:
        logger.info("MINIMAX_API_KEY is set — document analysis and insights will use the LLM.")
    else:
        logger.warning(
            "MINIMAX_API_KEY is not set — analysis/insights will use heuristic fallbacks. "
            "Set it in .env for full AI features (see .env.example)."
        )
    if bedrock_configured:
        logger.info(
            "AWS_REGION and BEDROCK_MODEL_ID are set — Student Privacy Agent will use Bedrock "
            "(credentials from .env or AWS default chain)."
        )
    else:
        logger.info(
            "AWS Bedrock not configured — Student Privacy Agent will use built-in fallback replies. "
            "Optional: set AWS_REGION, BEDROCK_MODEL_ID (and AWS_* if not using IAM) in .env."
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


@app.post("/insights", response_model=InsightsResponse)
async def get_insights(req: InsightsRequest):
    insights = await generate_insights(req.analysis, req.user_context)
    return InsightsResponse(insights=insights)


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

    text = _re.sub(r"<script[\s\S]*?</script>", " ", html_text, flags=_re.I)
    text = _re.sub(r"<style[\s\S]*?</style>", " ", text, flags=_re.I)
    text = _re.sub(r"<[^>]+>", " ", text)
    text = _re.sub(r"\s+", " ", text).strip()

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


@app.post("/agent/chat", response_model=AgentChatResponse)
async def chat_with_agent(req: AgentChatRequest):
    if not req.message or not req.message.strip():
        raise HTTPException(status_code=400, detail="Message cannot be empty.")
    result = await agent_chat(req.session_id, req.message, req.page_text)
    return AgentChatResponse(**result)


handler = Mangum(app)
