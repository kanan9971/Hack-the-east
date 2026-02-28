import json
import logging
import httpx
import anthropic

import config
from schemas import AnalyzeResponse, UserContext, ForYouInsights

logger = logging.getLogger(__name__)

INSIGHTS_SYSTEM_PROMPT = """You are ContractLens, an expert legal document analyst. You receive:
1. A completed analysis of a legal document (summary, risks, key points, sections)
2. User context (persona, concerns, document context, experience level, deal-breakers)

Your job is to produce a JSON object with personalized "For You" insights — nothing else, just the raw JSON:

{
  "top_risks_for_you": ["2-4 risks from the analysis, ranked by relevance to this user's persona and concerns. Each item: 1 sentence explaining why this risk matters to them specifically."],
  "action_items": ["2-4 concrete actions the user should take (e.g., 'Set a calendar reminder before the auto-renewal window', 'Ask for clarification on the IP assignment clause'). Be specific and actionable."],
  "deal_breaker_checks": ["For each deal-breaker the user listed: whether this document contains it, and a brief verdict. E.g., 'Non-compete: Present — 12-month restriction. Consider negotiating.' or 'Unlimited liability: Not found.'"],
  "tailored_summary": "2-3 sentences summarizing what this document means for this specific user. Reference their persona, concerns, and context. Be direct and practical."
}

Rules:
- Output ONLY valid JSON, no markdown fences, no explanation outside the JSON.
- Prioritize risks that match the user's primary_concerns.
- If experience_level is 'first_contract', explain terms more clearly and suggest they consider legal review.
- If deal_breakers is empty, set deal_breaker_checks to [].
- Keep all strings concise — under 2 sentences each.
"""


def _build_insights_prompt(analysis: AnalyzeResponse, ctx: UserContext) -> str:
    parts = ["--- USER CONTEXT ---"]
    if ctx.persona:
        parts.append(f"Persona: {ctx.persona}")
    if ctx.primary_concerns:
        parts.append(f"Primary concerns: {', '.join(ctx.primary_concerns)}")
    if ctx.document_context:
        parts.append(f"Document context: {ctx.document_context}")
    if ctx.experience_level:
        parts.append(f"Experience level: {ctx.experience_level}")
    if ctx.deal_breakers:
        parts.append(f"Deal-breakers to check: {', '.join(ctx.deal_breakers)}")

    parts.append("\n--- DOCUMENT ANALYSIS ---")
    parts.append(f"Summary: {analysis.summary}")
    parts.append("\nKey points:")
    for p in analysis.key_points[:7]:
        parts.append(f"  - {p}")
    parts.append("\nRisks:")
    for r in analysis.risks[:10]:
        parts.append(f"  - [{r.severity}] {r.category}: {r.explanation}")
    parts.append("\nSections (titles):")
    for s in analysis.sections[:15]:
        parts.append(f"  - {s.title}")

    return "\n".join(parts)


def _parse_insights_json(raw: str) -> dict:
    text = raw.strip()
    if text.startswith("```"):
        lines = text.splitlines()
        lines = [l for l in lines if not l.strip().startswith("```")]
        text = "\n".join(lines)
    start = text.find("{")
    if start != -1:
        text = text[start:]
    end = text.rfind("}") + 1
    if end > 0:
        try:
            return json.loads(text[:end])
        except json.JSONDecodeError:
            pass
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        logger.error("Failed to parse insights JSON: %s", text[:500])
    return {}


def _generate_fallback_insights(analysis: AnalyzeResponse, ctx: UserContext) -> ForYouInsights:
    top_risks = []
    for r in analysis.risks[:3]:
        top_risks.append(f"{r.category}: {r.explanation}")
    if not top_risks:
        top_risks = ["Review the key points and sections for any clauses that concern you."]

    action_items = [
        "Read the full document before signing.",
        "Set a reminder for any auto-renewal or termination deadlines.",
    ]
    if ctx.experience_level == "first_contract":
        action_items.append("Consider having a lawyer review if this is a high-stakes agreement.")

    deal_breaker_checks = []
    for db in ctx.deal_breakers[:5]:
        found = any(db.lower() in r.category.lower() for r in analysis.risks)
        deal_breaker_checks.append(f"{db}: {'Present — review carefully.' if found else 'Not explicitly flagged.'}")

    persona = ctx.persona or "user"
    tailored = f"As a {persona}, this document covers the usual legal terms. "
    if ctx.primary_concerns:
        tailored += f"Given your concerns about {', '.join(ctx.primary_concerns[:2])}, pay extra attention to the risks above. "
    tailored += "Review the action items before proceeding."

    return ForYouInsights(
        top_risks_for_you=top_risks,
        action_items=action_items,
        deal_breaker_checks=deal_breaker_checks,
        tailored_summary=tailored,
    )


async def generate_insights(analysis: AnalyzeResponse, user_context: UserContext) -> ForYouInsights:
    if not config.MINIMAX_API_KEY:
        logger.warning("No MINIMAX_API_KEY set — using heuristic fallback for insights.")
        return _generate_fallback_insights(analysis, user_context)

    try:
        client = anthropic.AsyncAnthropic(
            api_key=config.MINIMAX_API_KEY,
            base_url=config.MINIMAX_BASE_URL,
            timeout=httpx.Timeout(90.0, connect=10.0),
        )

        user_prompt = _build_insights_prompt(analysis, user_context)

        message = await client.messages.create(
            model=config.MINIMAX_MODEL,
            max_tokens=2048,
            system=INSIGHTS_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_prompt}],
        )

        raw_text = ""
        for block in message.content:
            if hasattr(block, "text"):
                raw_text += block.text

        parsed = _parse_insights_json(raw_text)
        if parsed:
            return ForYouInsights(
                top_risks_for_you=parsed.get("top_risks_for_you", []),
                action_items=parsed.get("action_items", []),
                deal_breaker_checks=parsed.get("deal_breaker_checks", []),
                tailored_summary=parsed.get("tailored_summary", analysis.summary),
            )

    except anthropic.APIStatusError as e:
        logger.error("MiniMax API error (status %s): %s", e.status_code, e.message)
    except httpx.TimeoutException:
        logger.error("MiniMax insights call timed out.")
    except Exception as e:
        logger.error("MiniMax insights call failed: %s", e)

    return _generate_fallback_insights(analysis, user_context)
