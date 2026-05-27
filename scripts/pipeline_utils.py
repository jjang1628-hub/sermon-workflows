"""
Shared helpers for the Logos-Max v2.1 workflow.

The project intentionally avoids a hard dependency on PyYAML.  These helpers
parse the small, predictable passage.yaml files used by the workflow and read
the score/status lines emitted by audit reports.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path


def configure_utf8_stdio() -> None:
    """Make Windows console output tolerant of Korean and Greek text."""
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            try:
                stream.reconfigure(encoding="utf-8", errors="replace")
            except Exception:
                pass


configure_utf8_stdio()


def load_yaml_simple(path: Path) -> dict[str, str]:
    """Parse the limited YAML shape used by 00-passage.yaml.

    Supported:
    - key: value
    - key:
        - list item

    Returned list values are joined with ", " because the current pipeline only
    needs display and routing metadata.
    """
    data: dict[str, str] = {}
    current_key: str | None = None
    list_values: list[str] = []

    for raw_line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        stripped = raw_line.strip()
        if not stripped or stripped.startswith("#"):
            continue

        if current_key and stripped.startswith("-"):
            list_values.append(stripped.lstrip("- ").strip().strip('"').strip("'"))
            data[current_key] = ", ".join(list_values)
            continue

        current_key = None
        list_values = []
        if ":" not in stripped:
            continue

        key, value = stripped.split(":", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if value:
            data[key] = value
        else:
            current_key = key
            data[key] = ""

    return data


def find_score(text: str) -> int | None:
    """Extract the first N/100 score or explicit Score: N value from a report."""
    patterns = [
        r"###\s+(\d+)\s*/\s*100",
        r"(?:Coverage Score|Capture Quality Score|Score)\s*[:\-]\s*(\d+)\s*/?\s*100?",
        r"Score\s*[:\-]\s*(\d+)",
    ]
    for pattern in patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            return int(match.group(1))
    return None


def find_status_tag(text: str) -> str:
    """Extract a Markdown status tag like '- status: `review_required`'."""
    match = re.search(r"-\s+status:\s+`([^`]+)`", text)
    return match.group(1) if match else ""


def passage_label(yaml_data: dict[str, str]) -> str:
    """Return a human-facing passage label from parsed YAML."""
    book = yaml_data.get("book_korean") or yaml_data.get("book") or ""
    passage = yaml_data.get("passage", "")
    return f"{book} {passage}".strip()


BOOK_SLUGS: dict[str, str] = {
    "창세기": "ge",
    "출애굽기": "ex",
    "레위기": "le",
    "민수기": "nu",
    "신명기": "dt",
    "여호수아": "jos",
    "사사기": "jdg",
    "룻기": "ru",
    "사무엘상": "1sa",
    "사무엘하": "2sa",
    "열왕기상": "1ki",
    "열왕기하": "2ki",
    "역대상": "1ch",
    "역대하": "2ch",
    "에스라": "ezr",
    "느헤미야": "ne",
    "에스더": "est",
    "욥기": "job",
    "시편": "ps",
    "잠언": "pr",
    "전도서": "ec",
    "아가": "ss",
    "이사야": "is",
    "예레미야": "je",
    "예레미야애가": "la",
    "에스겔": "eze",
    "다니엘": "da",
    "호세아": "ho",
    "요엘": "joe",
    "아모스": "am",
    "오바댜": "ob",
    "요나": "jon",
    "미가": "mic",
    "나훔": "na",
    "하박국": "hab",
    "스바냐": "zep",
    "학개": "hag",
    "스가랴": "zec",
    "말라기": "mal",
    "마태복음": "mt",
    "마가복음": "mk",
    "누가복음": "lk",
    "요한복음": "jn",
    "사도행전": "ac",
    "로마서": "ro",
    "고린도전서": "1co",
    "고린도후서": "2co",
    "갈라디아서": "ga",
    "에베소서": "eph",
    "빌립보서": "php",
    "골로새서": "col",
    "데살로니가전서": "1th",
    "데살로니가후서": "2th",
    "디모데전서": "1ti",
    "디모데후서": "2ti",
    "디도서": "tit",
    "빌레몬서": "phm",
    "히브리서": "heb",
    "야고보서": "jas",
    "베드로전서": "1pe",
    "베드로후서": "2pe",
    "요한일서": "1jn",
    "요한이서": "2jn",
    "요한삼서": "3jn",
    "유다서": "jude",
    "요한계시록": "re",
    "John": "jn",
    "Matthew": "mt",
    "Mark": "mk",
    "Luke": "lk",
    "Acts": "ac",
    "Romans": "ro",
    "Genesis": "ge",
    "Exodus": "ex",
    "Psalms": "ps",
    "Isaiah": "is",
}


def slugify_passage(label: str) -> str:
    """Convert a passage label such as '요한복음 13:14' to 'jn-13-14'."""
    slug = label
    for name, abbr in BOOK_SLUGS.items():
        if name in slug:
            slug = slug.replace(name, abbr)
            break
    slug = re.sub(r"[:\s]+", "-", slug)
    slug = re.sub(r"[^a-zA-Z0-9\-]", "", slug)
    return slug.strip("-").lower() or "passage"
