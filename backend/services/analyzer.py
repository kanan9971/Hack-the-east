import json
import logging
import anthropic

import config
from services.parser import Section

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are ContractLens, an expert legal document analyst. You receive the text of a legal document that has been split into classified sections.

Your job is to produce a JSON object with the following fields — nothing else, just the raw JSON:

{
  "summary": "A 2-3 sentence plain-English summary of what this document says and what the user agrees to.",
  "key_points": ["3-7 short bullet points covering the most important terms."],
  "risks": [
    {
      "category": "one of: data_sharing, ip_assignment, dispute_resolution, auto_renew, liability, non_compete, fees, data_use, termination, confidentiality, other",
      "severity": "high | medium | low",
      "clause_excerpt": "A short quote from the document.",
      "explanation": "Plain-English explanation of why this is risky."
    }
  ],
  "entities": {
    "parties": ["List of named parties/companies"],
    "dates": ["Any important dates mentioned"],
    "amounts": ["Any fees, penalties, or dollar amounts"],
    "obligations": ["Key things each party must do"]
  },
  "persona_notes": ["If a persona is provided, 2-4 tailored notes for that persona. Otherwise null."]
}

Rules:
- Output ONLY valid JSON, no markdown fences, no explanation outside the JSON.
- If the document is not a legal document, still do your best and note it in the summary.
- For risks, focus on clauses that are unusual, one-sided, or could surprise a typical consumer.
- Severity guide: high = could cause significant financial/legal harm; medium = worth knowing about; low = standard but notable.
"""


def _build_user_prompt(sections: list[Section], doc_type: str | None, persona: str | None) -> str:
    parts = []

    if doc_type:
        parts.append(f"Document type: {doc_type}")
    if persona:
        parts.append(f"User persona: {persona} — tailor the persona_notes for this person.")

    parts.append("\n--- DOCUMENT SECTIONS ---\n")

    for s in sections:
        label_str = ", ".join(s.labels) if s.labels else "unclassified"
        parts.append(f"[Section {s.index}: {s.title}] (labels: {label_str})")
        body = s.body[:3000] if len(s.body) > 3000 else s.body
        parts.append(body)
        parts.append("")

    return "\n".join(parts)


def _parse_llm_json(raw: str) -> dict:
    text = raw.strip()
    if text.startswith("```"):
        lines = text.splitlines()
        lines = [l for l in lines if not l.strip().startswith("```")]
        text = "\n".join(lines)

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        start = text.find("{")
        end = text.rfind("}") + 1
        if start != -1 and end > start:
            try:
                return json.loads(text[start:end])
            except json.JSONDecodeError:
                pass

    logger.error("Failed to parse LLM response as JSON: %s", text[:500])
    return {
        "summary": "Analysis could not be completed — the AI response was malformed.",
        "key_points": [],
        "risks": [],
        "entities": {"parties": [], "dates": [], "amounts": [], "obligations": []},
        "persona_notes": None,
    }


def _generate_fallback(sections: list[Section], doc_type: str | None, persona: str | None) -> dict:
    """Heuristic-only fallback when the LLM API is unavailable."""
    titles = [s.title for s in sections]
    all_text = " ".join(s.body for s in sections)[:500]

    summary = (
        f"This {doc_type or 'legal document'} contains {len(sections)} sections "
        f"covering topics such as {', '.join(titles[:4])}. "
        "Review the risk flags below for clauses that deserve extra attention."
    )

    key_points = []
    for s in sections[:7]:
        snippet = s.body[:120].replace("\n", " ").strip()
        key_points.append(f"{s.title}: {snippet}...")

    persona_notes = None
    if persona:
        persona_notes = [
            f"As a {persona}, pay close attention to any clauses about data sharing and liability.",
            f"Check the termination section — make sure you can exit without penalties relevant to a {persona}.",
            f"Look for auto-renewal terms; set a calendar reminder before the renewal window closes.",
        ]

    return {
        "summary": summary,
        "key_points": key_points,
        "risks": [],
        "entities": {"parties": [], "dates": [], "amounts": [], "obligations": []},
        "persona_notes": persona_notes,
    }


async def analyze_contract(
    sections: list[Section],
    doc_type: str | None = None,
    persona: str | None = None,
) -> dict:
    if not config.MINIMAX_API_KEY:
        logger.warning("No MINIMAX_API_KEY set — using heuristic fallback.")
        return _generate_fallback(sections, doc_type, persona)

    try:
        client = anthropic.Anthropic(
            api_key=config.MINIMAX_API_KEY,
            base_url=config.MINIMAX_BASE_URL,
        )

        user_prompt = _build_user_prompt(sections, doc_type, persona)

        message = client.messages.create(
            model=config.MINIMAX_MODEL,
            max_tokens=config.MAX_TOKENS,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_prompt}],
        )

        raw_text = ""
        for block in message.content:
            if hasattr(block, "text"):
                raw_text += block.text

        return _parse_llm_json(raw_text)

    except Exception as e:
        logger.error("MiniMax API call failed: %s — falling back to heuristic analysis.", e)
        return _generate_fallback(sections, doc_type, persona)
