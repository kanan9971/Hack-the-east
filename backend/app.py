import json
import logging
import uuid
from typing import Any

import anthropic

try:
    import boto3
    from botocore.config import Config as BotoConfig
except Exception:
    boto3 = None  # type: ignore[assignment]
    BotoConfig = None  # type: ignore[assignment,misc]

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from mangum import Mangum

import config
from schemas import (
    AgentRequest,
    AgentResponse,
    AnalyzeRequest,
    AnalyzeResponse,
)
from services.analyzer import (
    analyze_contract,
    compare_documents_for_hk,
    draft_negotiation_email_for_hk,
    hk_pdpo_compliance_check,
)
from services.classifier import classify_sections
from services.parser import parse_text
from services.risk_flagger import flag_risks

logger = logging.getLogger(__name__)

app = FastAPI(title="ContractLens API", version="1.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=config.ALLOWED_ORIGINS,
    allow_credentials=config.ALLOW_CREDENTIALS,
    allow_methods=["*"],
    allow_headers=["*"],
)

ADVISOR_SYSTEM_PROMPT = (
    "You are ContractLens Advisor, an agentic AI assistant for Hong Kong users "
    "reviewing Terms of Service, privacy policies, and contracts.\n\n"
    "You have access to tools. Use them when the user's question would benefit from "
    "structured analysis. Always reason step-by-step, call the appropriate tool(s), "
    "then synthesise a clear, practical answer.\n\n"
    "Priorities:\n"
    "1) Highlight user risk in plain language with HK context (students, fintech, freelancers).\n"
    "2) Use check_hk_pdpo for personal-data / PDPO compliance questions.\n"
    "3) Use compare_documents when the user asks to compare two services or ToS.\n"
    "4) Use draft_email_template to produce negotiation-ready language.\n\n"
    "Safety:\n"
    "- Never request unnecessary personal data.\n"
    "- Keep output concise, actionable, and clearly labelled as informational (not legal advice).\n"
    "- Recommend professional legal counsel for high-stakes decisions.\n"
    "- If you don't have enough context to call a tool, answer from general knowledge and note the limitation."
)

ANTHROPIC_TOOLS: list[dict[str, Any]] = [
    {
        "name": "compare_documents",
        "description": "Compare the risk posture of two Terms of Service or policy documents. Returns a breakdown by risk category with a winner and HK-specific notes.",
        "input_schema": {
            "type": "object",
            "properties": {
                "primary_text": {"type": "string", "description": "Full text of the main document."},
                "comparison_text": {"type": "string", "description": "Full text of the document to compare against."},
                "primary_name": {"type": "string", "description": "Label for the main document."},
                "comparison_name": {"type": "string", "description": "Label for the comparison document."},
                "persona": {"type": "string", "description": "Optional user persona such as student or freelancer."},
            },
            "required": ["primary_text", "comparison_text"],
        },
    },
    {
        "name": "draft_email_template",
        "description": "Draft a negotiation email asking a company to revise a specific Terms clause. Tailored for HK users.",
        "input_schema": {
            "type": "object",
            "properties": {
                "clause_text": {"type": "string", "description": "The exact clause text the user wants changed."},
                "ask": {"type": "string", "description": "What the user is requesting."},
                "tone": {"type": "string", "enum": ["polite", "friendly", "firm"], "description": "Desired email tone."},
                "context": {"type": "string", "description": "Optional context about the user's situation."},
            },
            "required": ["clause_text", "ask"],
        },
    },
    {
        "name": "check_hk_pdpo",
        "description": "Run a quick Hong Kong Personal Data (Privacy) Ordinance (PDPO) compliance screen against DPP1-DPP6.",
        "input_schema": {
            "type": "object",
            "properties": {
                "text": {"type": "string", "description": "The terms or privacy policy text to evaluate."},
                "use_case": {"type": "string", "description": "Optional use-case context."},
            },
            "required": ["text"],
        },
    },
]

BEDROCK_TOOLS: list[dict[str, Any]] = [
    {
        "toolSpec": {
            "name": tool["name"],
            "description": tool["description"],
            "inputSchema": {"json": tool["input_schema"]},
        }
    }
    for tool in ANTHROPIC_TOOLS
]

MAX_TOOL_ROUNDS = 5


def _execute_tool(name: str, tool_input: dict[str, Any]) -> dict[str, Any]:
    if name == "compare_documents":
        return compare_documents_for_hk(
            primary_text=str(tool_input.get("primary_text", "")),
            comparison_text=str(tool_input.get("comparison_text", "")),
            primary_name=str(tool_input.get("primary_name", "Current ToS")),
            comparison_name=str(tool_input.get("comparison_name", "Comparison ToS")),
            persona=tool_input.get("persona"),
        )
    elif name == "draft_email_template":
        return draft_negotiation_email_for_hk(
            clause_text=str(tool_input.get("clause_text", "")),
            ask=str(tool_input.get("ask", "Please revise this clause.")),
            tone=str(tool_input.get("tone", "polite")),
            context=tool_input.get("context"),
        )
    elif name == "check_hk_pdpo":
        return hk_pdpo_compliance_check(
            text=str(tool_input.get("text", "")),
            use_case=tool_input.get("use_case"),
        )
    return {"error": f"Unknown tool '{name}'"}


def _can_use_bedrock() -> bool:
    # Bedrock can use explicit keys from .env or the default AWS credential chain.
    return bool(boto3 and config.AWS_REGION and config.BEDROCK_MODEL_ID)


# ---------------------------------------------------------------------------
# Bedrock Converse path (used when full AWS credentials are available)
# ---------------------------------------------------------------------------

def _get_bedrock_client():
    kwargs: dict[str, Any] = {"region_name": config.AWS_REGION}
    if config.AWS_ACCESS_KEY_ID and config.AWS_SECRET_ACCESS_KEY:
        kwargs["aws_access_key_id"] = config.AWS_ACCESS_KEY_ID
        kwargs["aws_secret_access_key"] = config.AWS_SECRET_ACCESS_KEY
    if config.AWS_SESSION_TOKEN:
        kwargs["aws_session_token"] = config.AWS_SESSION_TOKEN
    if BotoConfig:
        kwargs["config"] = BotoConfig(retries={"max_attempts": 3, "mode": "standard"})
    return boto3.client("bedrock-runtime", **kwargs)


def _converse_with_tools(client: Any, messages: list[dict], model_id: str) -> str:
    for _ in range(MAX_TOOL_ROUNDS):
        response = client.converse(
            modelId=model_id,
            messages=messages,
            system=[{"text": ADVISOR_SYSTEM_PROMPT}],
            toolConfig={"tools": BEDROCK_TOOLS},
            inferenceConfig={"maxTokens": 4096, "temperature": 0.3},
        )

        stop_reason = response["stopReason"]
        assistant_content = response["output"]["message"]["content"]
        messages.append({"role": "assistant", "content": assistant_content})

        if stop_reason in ("end_turn", "max_tokens"):
            return "\n".join(b["text"] for b in assistant_content if "text" in b) or "No response."

        if stop_reason == "tool_use":
            tool_results: list[dict[str, Any]] = []
            for block in assistant_content:
                if "toolUse" not in block:
                    continue
                tu = block["toolUse"]
                try:
                    result = _execute_tool(tu["name"], tu.get("input", {}))
                    tool_results.append({
                        "toolResult": {
                            "toolUseId": tu["toolUseId"],
                            "content": [{"json": result}],
                            "status": "success",
                        }
                    })
                except Exception as exc:
                    tool_results.append({
                        "toolResult": {
                            "toolUseId": tu["toolUseId"],
                            "content": [{"text": f"Tool error: {exc}"}],
                            "status": "error",
                        }
                    })
            messages.append({"role": "user", "content": tool_results})
            continue

        return "\n".join(b["text"] for b in assistant_content if "text" in b) or "No response."

    return "Reached maximum reasoning steps. Please try a more specific question."


# ---------------------------------------------------------------------------
# MiniMax / Anthropic SDK path (fallback when no Bedrock credentials)
# ---------------------------------------------------------------------------

def _anthropic_chat_with_tools(messages: list[dict[str, Any]]) -> str:
    client = anthropic.Anthropic(
        api_key=config.MINIMAX_API_KEY,
        base_url=config.MINIMAX_BASE_URL,
    )

    for _ in range(MAX_TOOL_ROUNDS):
        response = client.messages.create(
            model=config.MINIMAX_MODEL,
            max_tokens=config.MAX_TOKENS,
            system=ADVISOR_SYSTEM_PROMPT,
            messages=messages,
            tools=ANTHROPIC_TOOLS,
        )

        assistant_content = response.content
        messages.append({"role": "assistant", "content": _serialize_anthropic_content(assistant_content)})

        if response.stop_reason == "end_turn" or response.stop_reason == "max_tokens":
            return "\n".join(
                block.text for block in assistant_content if hasattr(block, "text")
            ) or "No response."

        if response.stop_reason == "tool_use":
            tool_results: list[dict[str, Any]] = []
            for block in assistant_content:
                if block.type != "tool_use":
                    continue
                try:
                    result = _execute_tool(block.name, block.input)
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": json.dumps(result),
                    })
                except Exception as exc:
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": f"Tool error: {exc}",
                        "is_error": True,
                    })
            messages.append({"role": "user", "content": tool_results})
            continue

        return "\n".join(
            block.text for block in assistant_content if hasattr(block, "text")
        ) or "No response."

    return "Reached maximum reasoning steps. Please try a more specific question."


def _serialize_anthropic_content(content: Any) -> list[dict[str, Any]]:
    serialized = []
    for block in content:
        if hasattr(block, "text"):
            serialized.append({"type": "text", "text": block.text})
        elif block.type == "tool_use":
            serialized.append({
                "type": "tool_use",
                "id": block.id,
                "name": block.name,
                "input": block.input,
            })
    return serialized


# ---------------------------------------------------------------------------
# Session store (in-memory, keyed by session_id)
# ---------------------------------------------------------------------------

_session_histories: dict[str, list[dict]] = {}


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/analyze", response_model=AnalyzeResponse)
async def analyze(req: AnalyzeRequest):
    if not req.text or len(req.text.strip()) < 50:
        raise HTTPException(status_code=400, detail="Text too short to analyze.")

    sections = parse_text(req.text)
    classified = classify_sections(sections)
    # Summary/key points analysis is intentionally routed through MiniMax.
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


@app.post("/agent", response_model=AgentResponse)
async def ask_agent(req: AgentRequest):
    if not req.query or len(req.query.strip()) < 5:
        raise HTTPException(status_code=400, detail="Query is too short.")

    session_id = req.session_id or str(uuid.uuid4())
    if _can_use_bedrock():
        messages = _session_histories.get(session_id, [])
        messages.append({"role": "user", "content": [{"text": req.query}]})
        try:
            client = _get_bedrock_client()
            answer = _converse_with_tools(client, messages, config.BEDROCK_MODEL_ID)
        except HTTPException:
            raise
        except Exception as exc:
            logger.exception("Bedrock Converse call failed")
            raise HTTPException(status_code=502, detail=f"Bedrock error: {exc}") from exc
        _session_histories[session_id] = messages[-20:]
    else:
        if not config.MINIMAX_API_KEY:
            raise HTTPException(
                status_code=503,
                detail=(
                    "No LLM credentials configured. "
                    "Set MINIMAX_API_KEY for summaries and configure AWS Bedrock for advisor chat."
                ),
            )
        messages = _session_histories.get(session_id, [])
        messages.append({"role": "user", "content": req.query})
        try:
            answer = _anthropic_chat_with_tools(messages)
        except Exception as exc:
            logger.exception("MiniMax advisor call failed")
            raise HTTPException(status_code=502, detail=f"LLM error: {exc}") from exc
        _session_histories[session_id] = messages[-20:]

    if not answer:
        answer = "I could not generate a response. Please try again with more context."

    return AgentResponse(session_id=session_id, response=answer)


handler = Mangum(app)
