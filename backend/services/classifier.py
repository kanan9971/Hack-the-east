import re
from services.parser import Section

CATEGORY_PATTERNS: dict[str, list[re.Pattern]] = {
    "data_use": [
        re.compile(r"(collect|use|process|store|retain)\b.{0,40}\b(data|information|personal)", re.I),
        re.compile(r"(cookie|tracking|analytics|telemetry)", re.I),
    ],
    "data_sharing": [
        re.compile(r"(share|disclose|transfer|sell|provide)\b.{0,40}\b(data|information|third.?part|partner|affiliate)", re.I),
        re.compile(r"(third.?part|vendor|advertis)", re.I),
    ],
    "ip_assignment": [
        re.compile(r"(intellectual property|copyright|patent|trademark)", re.I),
        re.compile(r"(assign|transfer|grant|license)\b.{0,40}\b(rights?|ownership|ip\b)", re.I),
        re.compile(r"(work.?for.?hire|perpetual|irrevocable|worldwide)\b.{0,30}\b(license|right)", re.I),
    ],
    "dispute_resolution": [
        re.compile(r"(arbitrat|mediat|dispute|jurisdiction|governing law|venue|class.?action)", re.I),
        re.compile(r"(waive|waiver)\b.{0,30}\b(jury|class|trial)", re.I),
    ],
    "auto_renew": [
        re.compile(r"(auto.?renew|automatic.{0,10}renew|recurring|subscription)", re.I),
        re.compile(r"(cancel|opt.?out|terminate)\b.{0,30}\b(before|prior|within)\b.{0,20}\b(renewal|expir)", re.I),
    ],
    "termination": [
        re.compile(r"(terminat|cancel|end|expir)\b.{0,30}\b(agreement|contract|service|account)", re.I),
        re.compile(r"(notice period|30.?day|60.?day|90.?day)\b.{0,20}\b(notice|terminat|cancel)", re.I),
    ],
    "liability": [
        re.compile(r"(limit.{0,10}liabilit|disclaim|no.?warrant|as.?is|indemnif)", re.I),
        re.compile(r"(consequential|incidental|punitive|special)\s+damage", re.I),
        re.compile(r"(shall not (be liable|exceed)|maximum (liability|aggregate))", re.I),
    ],
    "non_compete": [
        re.compile(r"(non.?compete|non.?competition|restrictive covenant|non.?solicit)", re.I),
        re.compile(r"(compete|competing|competitive)\b.{0,30}\b(business|activit|employ)", re.I),
    ],
    "fees": [
        re.compile(r"(\$\d|fee|price|cost|payment|charge|billing|invoice)", re.I),
        re.compile(r"(refund|credit|penalty|late.?fee|interest)", re.I),
    ],
    "confidentiality": [
        re.compile(r"(confidential|non.?disclosure|nda|proprietary|trade.?secret)", re.I),
    ],
}


def classify_sections(sections: list[Section]) -> list[Section]:
    for section in sections:
        text = f"{section.title} {section.body}"
        labels: list[str] = []
        for category, patterns in CATEGORY_PATTERNS.items():
            if any(p.search(text) for p in patterns):
                labels.append(category)
        section.labels = labels if labels else ["other"]
    return sections
