import re
from schemas import RiskFlag
from services.parser import Section

HEURISTIC_RULES: list[dict] = [
    {
        "label": "dispute_resolution",
        "pattern": re.compile(r"(binding\s+arbitration|waive.{0,20}(jury|class\s+action))", re.I),
        "category": "dispute_resolution",
        "severity": "high",
        "explanation": "This clause may require binding arbitration and waive your right to a jury trial or class action lawsuit.",
    },
    {
        "label": "ip_assignment",
        "pattern": re.compile(r"(perpetual|irrevocable|worldwide|unlimited).{0,30}(license|assignment|right)", re.I),
        "category": "ip_assignment",
        "severity": "high",
        "explanation": "Broad, irrevocable IP assignment could mean you lose ownership of your work or content permanently.",
    },
    {
        "label": "data_sharing",
        "pattern": re.compile(r"(sell|share|monetize).{0,30}(personal|data|information).{0,30}(third.?part|advertis|partner)", re.I),
        "category": "data_sharing",
        "severity": "high",
        "explanation": "Your personal data may be sold or shared with third parties for advertising or other commercial purposes.",
    },
    {
        "label": "auto_renew",
        "pattern": re.compile(r"auto.{0,5}renew.{0,60}(no.{0,10}(refund|cancel)|non.?refund)", re.I),
        "category": "auto_renew",
        "severity": "high",
        "explanation": "Auto-renewal with no cancellation window or refund policy could lock you into recurring charges.",
    },
    {
        "label": "liability",
        "pattern": re.compile(r"(unlimited\s+liabilit|you\s+(shall\s+)?indemnif|hold\s+harmless)", re.I),
        "category": "liability",
        "severity": "high",
        "explanation": "You may be taking on unlimited liability or must indemnify the other party for their losses.",
    },
    {
        "label": "non_compete",
        "pattern": re.compile(r"non.?compet.{0,40}(\d+\s*(year|month))", re.I),
        "category": "non_compete",
        "severity": "medium",
        "explanation": "A non-compete clause restricts where you can work or what business you can pursue after this agreement.",
    },
    {
        "label": "termination",
        "pattern": re.compile(r"terminat.{0,30}(without\s+(cause|reason|notice)|at\s+(its?\s+)?sole\s+discretion)", re.I),
        "category": "termination",
        "severity": "medium",
        "explanation": "The other party can terminate this agreement at will, without cause or prior notice to you.",
    },
    {
        "label": "liability",
        "pattern": re.compile(r"(as.?is|no\s+warrant|disclaim.{0,20}all\s+warrant)", re.I),
        "category": "liability",
        "severity": "low",
        "explanation": "The service is provided 'as-is' with no warranties — standard but means you have limited legal recourse if something goes wrong.",
    },
]


def _find_excerpt(text: str, pattern: re.Pattern, max_len: int = 200) -> str:
    match = pattern.search(text)
    if not match:
        return ""
    start = max(0, match.start() - 40)
    end = min(len(text), match.end() + 40)
    excerpt = text[start:end].strip()
    if len(excerpt) > max_len:
        excerpt = excerpt[:max_len] + "..."
    return excerpt


def flag_risks(sections: list[Section], llm_result: dict) -> list[RiskFlag]:
    seen_keys: set[str] = set()
    risks: list[RiskFlag] = []

    for section in sections:
        full_text = f"{section.title} {section.body}"
        for rule in HEURISTIC_RULES:
            if rule["label"] in section.labels or rule["pattern"].search(full_text):
                key = f"{rule['category']}:{rule['severity']}"
                if key not in seen_keys:
                    excerpt = _find_excerpt(full_text, rule["pattern"])
                    risks.append(RiskFlag(
                        category=rule["category"],
                        severity=rule["severity"],
                        clause_excerpt=excerpt or f"Found in section: {section.title}",
                        explanation=rule["explanation"],
                    ))
                    seen_keys.add(key)

    llm_risks = llm_result.get("risks", [])
    for lr in llm_risks:
        if not isinstance(lr, dict):
            continue
        cat = lr.get("category", "other")
        sev = lr.get("severity", "medium")
        key = f"{cat}:{sev}"
        if key not in seen_keys:
            risks.append(RiskFlag(
                category=cat,
                severity=sev,
                clause_excerpt=lr.get("clause_excerpt", ""),
                explanation=lr.get("explanation", ""),
            ))
            seen_keys.add(key)

    severity_order = {"high": 0, "medium": 1, "low": 2}
    risks.sort(key=lambda r: severity_order.get(r.severity, 3))

    return risks
