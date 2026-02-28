import hashlib
import json
import logging
import httpx
import anthropic

import config
from services.parser import Section

logger = logging.getLogger(__name__)

MAX_SECTIONS_FOR_LLM = 12
MAX_SECTION_BODY_CHARS = 1500
MAX_PROMPT_CHARS = 10_000
LLM_MAX_TOKENS = 2048

_cache: dict[str, dict] = {}

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
- Keep ALL strings concise — summaries under 3 sentences, explanations under 2 sentences, excerpts under 30 words.
- If the document is not a legal document, still do your best and note it in the summary.
- For risks, focus on clauses that are unusual, one-sided, or could surprise a typical consumer. Limit to the top 5 most important risks.
- Severity guide: high = could cause significant financial/legal harm; medium = worth knowing about; low = standard but notable.
"""


def _build_user_prompt(sections: list[Section], doc_type: str | None, persona: str | None) -> str:
    parts = []

    if doc_type:
        parts.append(f"Document type: {doc_type}")
    if persona:
        parts.append(f"User persona: {persona} — tailor the persona_notes for this person.")

    parts.append("\n--- DOCUMENT SECTIONS ---\n")

    total_chars = 0
    sections_to_use = sections[:MAX_SECTIONS_FOR_LLM]

    for s in sections_to_use:
        label_str = ", ".join(s.labels) if s.labels else "unclassified"
        header = f"[Section {s.index}: {s.title}] (labels: {label_str})"
        body = s.body[:MAX_SECTION_BODY_CHARS]

        chunk = header + "\n" + body + "\n"
        if total_chars + len(chunk) > MAX_PROMPT_CHARS:
            break
        parts.append(chunk)
        total_chars += len(chunk)

    return "\n".join(parts)


def _cache_key(sections: list[Section], doc_type: str | None, persona: str | None) -> str:
    content = "|".join(f"{s.title}:{s.body[:200]}" for s in sections[:MAX_SECTIONS_FOR_LLM])
    raw = f"{doc_type}:{persona}:{content}"
    return hashlib.md5(raw.encode()).hexdigest()


def _repair_truncated_json(text: str) -> str:
    in_string = False
    escape = False
    stack: list[str] = []

    for ch in text:
        if escape:
            escape = False
            continue
        if ch == "\\":
            if in_string:
                escape = True
            continue
        if ch == '"':
            in_string = not in_string
            continue
        if in_string:
            continue
        if ch in ("{", "["):
            stack.append(ch)
        elif ch == "}" and stack and stack[-1] == "{":
            stack.pop()
        elif ch == "]" and stack and stack[-1] == "[":
            stack.pop()

    if in_string:
        text += '"'

    while stack:
        opener = stack.pop()
        text += "]" if opener == "[" else "}"

    return text


def _parse_llm_json(raw: str, truncated: bool = False) -> dict:
    text = raw.strip()
    if text.startswith("```"):
        lines = text.splitlines()
        lines = [l for l in lines if not l.strip().startswith("```")]
        text = "\n".join(lines)

    start = text.find("{")
    if start != -1:
        text = text[start:]

    for attempt_text in [text, _repair_truncated_json(text)] if truncated else [text]:
        end = attempt_text.rfind("}") + 1
        if end > 0:
            try:
                return json.loads(attempt_text[:end])
            except json.JSONDecodeError:
                pass
        try:
            return json.loads(attempt_text)
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
    titles = [s.title for s in sections]
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

    key = _cache_key(sections, doc_type, persona)
    if key in _cache:
        logger.info("Cache hit — skipping MiniMax API call.")
        return _cache[key]

    try:
        client = anthropic.AsyncAnthropic(
            api_key=config.MINIMAX_API_KEY,
            base_url=config.MINIMAX_BASE_URL,
            timeout=httpx.Timeout(120.0, connect=10.0),
        )

        user_prompt = _build_user_prompt(sections, doc_type, persona)
        logger.info("Prompt size: %d chars (%d sections)", len(user_prompt), min(len(sections), MAX_SECTIONS_FOR_LLM))

        message = await client.messages.create(
            model=config.MINIMAX_MODEL,
            max_tokens=LLM_MAX_TOKENS,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_prompt}],
        )

        raw_text = ""
        for block in message.content:
            if hasattr(block, "text"):
                raw_text += block.text

        truncated = getattr(message, "stop_reason", None) == "max_tokens"
        if truncated:
            logger.warning("LLM response was truncated (hit max_tokens), attempting repair.")

        logger.info("MiniMax API call succeeded, response length: %d", len(raw_text))
        result = _parse_llm_json(raw_text, truncated=truncated)

        _cache[key] = result
        if len(_cache) > 50:
            oldest_key = next(iter(_cache))
            del _cache[oldest_key]

        return result

    except anthropic.APIStatusError as e:
        logger.error("MiniMax API error (status %s): %s", e.status_code, e.message)
        return _generate_fallback(sections, doc_type, persona)
    except httpx.TimeoutException:
        logger.error("MiniMax API call timed out — falling back to heuristic analysis.")
        return _generate_fallback(sections, doc_type, persona)
    except Exception as e:
        logger.error("MiniMax API call failed: %s — falling back to heuristic analysis.", e)
        return _generate_fallback(sections, doc_type, persona)
