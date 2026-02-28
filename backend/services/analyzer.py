import json
import logging
import re
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


def summarize_analysis_for_advisor(
    llm_result: dict,
    risks: list[dict],
    include_sections: bool = False,
) -> dict:
    response = {
        "summary": llm_result.get("summary", ""),
        "key_points": llm_result.get("key_points", []),
        "risks": risks,
        "entities": llm_result.get("entities", {}),
        "persona_notes": llm_result.get("persona_notes"),
    }
    if include_sections:
        response["sections"] = llm_result.get("sections", [])
    return response


def compare_documents_for_hk(
    primary_text: str,
    comparison_text: str,
    primary_name: str = "Current ToS",
    comparison_name: str = "Comparison ToS",
    persona: str | None = None,
) -> dict:
    if not primary_text.strip() or not comparison_text.strip():
        return {
            "result": "comparison_failed",
            "reason": "Both primary_text and comparison_text are required.",
        }

    risk_terms = {
        "auto_renew": [r"auto.?renew", r"renewal", r"subscription"],
        "data_sharing": [r"share.*data", r"third.?party", r"sell.*data"],
        "liability": [r"liability", r"indemnif", r"disclaim"],
        "termination": [r"terminate", r"suspend", r"without notice"],
        "fees": [r"fee", r"charge", r"penalt", r"refund"],
    }

    def _score(text: str) -> tuple[int, dict]:
        lowered = text.lower()
        detail = {}
        score = 0
        for category, patterns in risk_terms.items():
            hits = sum(
                1
                for p in patterns
                if re.search(p, lowered, flags=re.IGNORECASE | re.MULTILINE)
            )
            detail[category] = hits
            score += hits
        return score, detail

    primary_score, primary_detail = _score(primary_text)
    comparison_score, comparison_detail = _score(comparison_text)
    better = primary_name if primary_score < comparison_score else comparison_name
    if primary_score == comparison_score:
        better = "roughly equal"

    hk_note = (
        "For Hong Kong users (students/freelancers/fintech consumers), prioritize "
        "clear data-use limits, cancellation rights, and liability caps."
    )
    persona_note = (
        f"Persona note for {persona}: focus on exit rights and hidden fee language."
        if persona
        else None
    )

    return {
        "result": "comparison_complete",
        "winner": better,
        "summary": (
            f"{primary_name} score={primary_score}, {comparison_name} score={comparison_score}. "
            f"Lower is generally safer."
        ),
        "primary_breakdown": primary_detail,
        "comparison_breakdown": comparison_detail,
        "hk_note": hk_note,
        "persona_note": persona_note,
    }


def draft_negotiation_email_for_hk(
    clause_text: str,
    ask: str,
    tone: str = "polite",
    context: str | None = None,
) -> dict:
    if not clause_text.strip():
        return {
            "result": "draft_failed",
            "reason": "clause_text is required.",
        }

    intro = "I hope you are well."
    if tone.lower() == "firm":
        intro = "I am writing to request an urgent revision."
    elif tone.lower() == "friendly":
        intro = "Thanks for sharing the terms."

    context_line = f"Context: {context}\n\n" if context else ""
    email = (
        "Subject: Request to revise a Terms clause\n\n"
        "Dear Support/Legal Team,\n\n"
        f"{intro} {context_line}"
        "I reviewed the Terms and would like to discuss the following clause:\n"
        f"\"{clause_text.strip()}\"\n\n"
        f"My request: {ask.strip()}\n\n"
        "As a Hong Kong user, I would appreciate wording that is clearer on cancellation, "
        "fees, and personal-data usage in line with reasonable expectations under local privacy principles.\n\n"
        "Please let me know if we can agree on revised wording.\n\n"
        "Best regards,\n"
        "[Your Name]"
    )

    return {
        "result": "draft_complete",
        "tone": tone,
        "email": email,
    }


def hk_pdpo_compliance_check(text: str, use_case: str | None = None) -> dict:
    if not text.strip():
        return {"result": "check_failed", "reason": "text is required."}

    checks = [
        (
            "DPP1 Collection",
            ["purpose", "necessary", "collect"],
            "State why data is collected and limit to what is necessary.",
        ),
        (
            "DPP2 Accuracy/Retention",
            ["retain", "retention", "accurate"],
            "Explain retention period and data accuracy handling.",
        ),
        (
            "DPP3 Use",
            ["use", "consent", "third party", "marketing"],
            "Limit secondary use unless prescribed consent is obtained.",
        ),
        (
            "DPP4 Security",
            ["security", "encrypt", "access control", "breach"],
            "Include reasonable security safeguards for personal data.",
        ),
        (
            "DPP5 Openness",
            ["privacy policy", "contact", "access request"],
            "Provide transparent policy and contact channel for data requests.",
        ),
        (
            "DPP6 Access/Correction",
            ["access", "correct", "amend", "delete"],
            "Allow users to access and correct personal data.",
        ),
    ]

    lowered = text.lower()
    findings = []
    for principle, keywords, guidance in checks:
        hit = any(k in lowered for k in keywords)
        findings.append(
            {
                "principle": principle,
                "status": "covered" if hit else "potential_gap",
                "guidance": guidance,
            }
        )

    gaps = [f["principle"] for f in findings if f["status"] == "potential_gap"]
    return {
        "result": "check_complete",
        "use_case": use_case or "general",
        "framework": "Hong Kong PDPO (DPP1-DPP6) quick screen",
        "findings": findings,
        "summary": (
            "Potential PDPO gaps detected in: " + ", ".join(gaps)
            if gaps
            else "No obvious PDPO keyword-level gaps found. Manual legal review still recommended."
        ),
    }
