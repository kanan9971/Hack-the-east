import re
from dataclasses import dataclass, field


@dataclass
class Section:
    title: str
    body: str
    index: int
    labels: list[str] = field(default_factory=list)


_BOILERPLATE_PATTERNS = [
    re.compile(r"^(skip to (main )?content|navigation|menu|footer|copyright|©|\d{4}\s+all rights reserved)", re.I),
    re.compile(r"^(cookie|accept all|reject all|manage preferences)", re.I),
    re.compile(r"^(sign in|sign up|log in|register|subscribe|newsletter)", re.I),
]

_HEADING_PATTERNS = [
    re.compile(r"^(\d{1,2})\.\s+(.+)$"),
    re.compile(r"^([IVXLC]+)\.\s+(.+)$"),
    re.compile(r"^(Section|Article|Clause)\s+\d+[.:]\s*(.+)$", re.I),
    re.compile(r"^([A-Z][A-Z\s,&]{4,})$"),
    re.compile(r"^#{1,3}\s+(.+)$"),
]


def _is_boilerplate(line: str) -> bool:
    return any(p.match(line.strip()) for p in _BOILERPLATE_PATTERNS)


def _is_heading(line: str) -> tuple[bool, str]:
    stripped = line.strip()
    if not stripped:
        return False, ""

    for pattern in _HEADING_PATTERNS:
        m = pattern.match(stripped)
        if m:
            title = m.group(m.lastindex) if m.lastindex else stripped
            return True, title.strip()

    return False, ""


def _clean_text(raw: str) -> str:
    lines = raw.splitlines()
    cleaned = []
    for line in lines:
        if _is_boilerplate(line):
            continue
        cleaned.append(line)
    return "\n".join(cleaned)


def parse_text(raw_text: str) -> list[Section]:
    text = _clean_text(raw_text)
    lines = text.splitlines()

    sections: list[Section] = []
    current_title = "Introduction"
    current_body_lines: list[str] = []
    idx = 0

    for line in lines:
        is_head, title = _is_heading(line)
        if is_head and title:
            body = "\n".join(current_body_lines).strip()
            if body:
                sections.append(Section(title=current_title, body=body, index=idx))
                idx += 1
            current_title = title
            current_body_lines = []
        else:
            current_body_lines.append(line)

    body = "\n".join(current_body_lines).strip()
    if body:
        sections.append(Section(title=current_title, body=body, index=idx))

    if not sections:
        sections.append(Section(title="Full Document", body=text.strip(), index=0))

    return sections
