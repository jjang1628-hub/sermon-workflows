"""
audit_logos_coverage.py - Logos Coverage Score audit.

Coverage Score asks whether the required Logos research categories are present.
It does not judge depth. Depth is handled by audit_capture_quality.py.

Template files marked with ``capture_status: template`` are ignored so blank
scaffolds never inflate the score.
"""

from __future__ import annotations

import argparse
import sys
from datetime import datetime
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")


RUBRIC = [
    {
        "id": "R-01", "label": "본문 범위·문맥 확인", "points": 10,
        "keywords": ["본문", "passage", "context", "문맥", "요한복음", "13:1", "13:14"],
        "min_keywords": 2,
    },
    {
        "id": "R-02", "label": "번역 비교", "points": 10,
        "keywords": ["번역", "text comparison", "개역개정", "새번역", "ESV", "NIV", "NASB", "LEB"],
        "min_keywords": 1,
    },
    {
        "id": "R-03", "label": "원어·문법", "points": 15,
        "keywords": ["원어", "헬라어", "Greek", "νίπτω", "λούω", "ὀφείλετε", "μέρος", "εἰς τέλος", "nipto"],
        "min_keywords": 1,
    },
    {
        "id": "R-04", "label": "구조·담화", "points": 10,
        "keywords": ["구조", "담화", "structure", "discourse", "흐름", "반복", "대조", "전환점", "절정"],
        "min_keywords": 2,
    },
    {
        "id": "R-05", "label": "교차본문", "points": 10,
        "keywords": ["교차", "참조", "cross reference", "Mark 10:45", "Luke 22", "Philippians 2", "1 John 3:16", "Ephesians 5"],
        "min_keywords": 2,
    },
    {
        "id": "R-06", "label": "주석 비교", "points": 15,
        "keywords": ["주석", "commentary", "Keener", "Carson", "Culpepper", "Beale", "박대영", "김새윤", "권해생"],
        "min_keywords": 2,
    },
    {
        "id": "R-07", "label": "성경신학", "points": 10,
        "keywords": ["성경신학", "biblical theology", "구속사", "언약", "성취", "그리스도", "십자가", "새 공동체"],
        "min_keywords": 2,
    },
    {
        "id": "R-08", "label": "조직신학", "points": 5,
        "keywords": ["조직신학", "systematic", "교리", "구원론", "교회론", "기독론", "성령론"],
        "min_keywords": 1,
    },
    {
        "id": "R-09", "label": "역사·문화 배경", "points": 5,
        "keywords": ["배경", "문화", "역사", "1세기", "유대", "로마", "종", "환대", "발 씻김"],
        "min_keywords": 2,
    },
    {
        "id": "R-10", "label": "설교 자료", "points": 5,
        "keywords": ["설교", "sermon", "강단", "Big Idea", "homiletic", "sermon starter"],
        "min_keywords": 1,
    },
    {
        "id": "R-11", "label": "목회·적용 자료", "points": 5,
        "keywords": ["적용", "목회", "pastoral", "거짓 복음", "자기구원", "한 순종", "이번 주", "실천"],
        "min_keywords": 2,
    },
]

THRESHOLDS = [
    (90, "deep_eligible", "Logos-Max deep research 즉시 가능"),
    (75, "deep_eligible_with_warning", "deep research 가능, 누락 경고 포함"),
    (60, "review_required", "보강 필요, deep research 보류 권장"),
    (0, "insufficient", "연구팩 불충분, 설교 방향 생성 중단"),
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Audit Logos Coverage Score.")
    parser.add_argument("--passage", required=True, help="Path to 00-passage.yaml")
    parser.add_argument("--capture-dir", default="tmp/logos-capture/raw", help="Raw capture directory")
    parser.add_argument("--output", default=None, help="Output report path")
    parser.add_argument("--verbose", action="store_true", help="Print capture files used")
    return parser.parse_args()


def load_yaml_simple(path: Path) -> dict[str, str]:
    data: dict[str, str] = {}
    for raw_line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        stripped = raw_line.strip()
        if not stripped or stripped.startswith("#") or stripped.startswith("-"):
            continue
        if ":" in stripped:
            key, value = stripped.split(":", 1)
            data[key.strip()] = value.strip().strip('"')
    return data


def is_template_capture(path: Path) -> bool:
    try:
        preview = path.read_text(encoding="utf-8", errors="replace")[:1200].lower()
    except OSError:
        return False
    return "capture_status: template" in preview


def collect_captures(capture_dir: Path, book_slug: str, passage_slug: str) -> list[Path]:
    all_files = list(capture_dir.glob("*.md")) + list(capture_dir.glob("*.txt"))
    if not all_files:
        return []

    chapter = passage_slug.split("-")[0] if passage_slug else ""
    verse = passage_slug.split("-")[1] if "-" in passage_slug else ""
    passage_compact = passage_slug.replace("-", "").replace(":", "").lower()
    content_ref = f"{chapter}:{verse}" if chapter and verse else ""
    aliases = {
        "jn": ["jn", "john"],
        "mt": ["mt", "matt", "matthew"],
        "mk": ["mk", "mark"],
        "lk": ["lk", "luke"],
    }.get(book_slug, [book_slug])

    matched: list[Path] = []
    for path in sorted(all_files):
        if is_template_capture(path):
            continue
        stem = path.stem.lower()
        compact = stem.replace("-", "").replace("_", "")
        try:
            preview = path.read_text(encoding="utf-8", errors="replace")[:1600].lower()
        except OSError:
            preview = ""

        exact = any(f"{alias}{passage_compact}" in compact for alias in aliases)
        chapter_match = chapter and any(stem.startswith(f"{alias}-{chapter}-") for alias in aliases)
        content_match = content_ref and (
            f"passage_ref: john {content_ref}" in preview
            or f"passage_ref: 요한복음 {content_ref}" in preview
            or f"john {content_ref}" in preview
            or f"요한복음 {content_ref}" in preview
        )
        if exact or chapter_match or content_match:
            matched.append(path)

    if not matched:
        matched = [path for path in sorted(all_files, key=lambda f: f.stat().st_mtime, reverse=True) if not is_template_capture(path)][:15]

    return list(dict.fromkeys(matched))


def capture_has_category(captures: list[Path], category: str, filename_terms: list[str]) -> bool:
    for path in captures:
        stem = path.stem.lower()
        if any(term in stem for term in filename_terms):
            return True
        try:
            preview = path.read_text(encoding="utf-8", errors="replace")[:1200].lower()
        except OSError:
            preview = ""
        if f"category: {category}" in preview and "capture_status: template" not in preview:
            return True
    return False


def score_coverage(combined_text: str, captures: list[Path]) -> tuple[int, list[dict]]:
    text_lower = combined_text.lower()
    total = 0
    results: list[dict] = []
    strict_category_markers = {
        "R-04": ("structure_discourse", ["structure", "discourse", "구조", "담화"]),
        "R-05": ("cross_references", ["cross", "reference", "cross-references", "교차", "참조"]),
        "R-07": ("biblical_theology", ["biblical-theology", "biblical_theology", "성경신학"]),
        "R-09": ("background", ["background", "historical", "cultural", "배경"]),
        "R-11": ("application_pastoral", ["application", "pastoral", "목회", "적용"]),
    }

    for item in RUBRIC:
        found = sum(1 for keyword in item["keywords"] if keyword.lower() in text_lower)
        passed = found >= item["min_keywords"]
        if item["id"] in strict_category_markers:
            category, filename_terms = strict_category_markers[item["id"]]
            passed = passed and capture_has_category(captures, category, filename_terms)
        earned = item["points"] if passed else 0
        total += earned
        results.append({
            "id": item["id"],
            "label": item["label"],
            "points_max": item["points"],
            "points_earned": earned,
            "passed": passed,
            "found_count": found,
            "required_count": item["min_keywords"],
        })

    return total, results


def get_status(score: int) -> tuple[str, str]:
    for threshold, status, label in THRESHOLDS:
        if score >= threshold:
            return status, label
    return "insufficient", "연구팩 불충분"


def build_report(
    passage_data: dict[str, str],
    passage_path: Path,
    captures: list[Path],
    combined_text: str,
    score: int,
    results: list[dict],
) -> str:
    book_korean = passage_data.get("book_korean", "")
    passage = passage_data.get("passage", "")
    status, status_label = get_status(score)
    today = datetime.now().strftime("%Y-%m-%d")
    missing = [item for item in results if not item["passed"]]
    passed_items = [item for item in results if item["passed"]]

    lines = [
        f"# Logos Coverage Report - {book_korean} {passage}",
        "",
        f"- 감사일: {today}",
        f"- 캡처 파일 수: {len(captures)}",
        f"- 통합 텍스트 길이: {len(combined_text):,}자",
        "",
        "## Coverage Score",
        "",
        f"### {score} / 100점",
        "",
        f"- status: `{status}`",
        f"- 판정: {status_label}",
        "",
        "## 사용한 캡처 파일",
        "",
    ]
    lines += [f"- `{path}` ({path.stat().st_size:,} bytes)" for path in captures] or ["- 없음"]
    lines += [
        "",
        "## 항목별 점수",
        "",
        "| 항목 | 배점 | 획득 | 상태 |",
        "|---|---:|---:|---|",
    ]
    for item in results:
        icon = "✅" if item["passed"] else "❌"
        lines.append(f"| {item['label']} | {item['points_max']} | {item['points_earned']} | {icon} |")
    lines.append(f"| **합계** | **100** | **{score}** | |")

    lines += ["", "## 누락 자료군", ""]
    if missing:
        for item in missing:
            lines += [
                f"### ❌ {item['id']} — {item['label']} (0/{item['points_max']}점)",
                f"- 발견 키워드: {item['found_count']}개 / 필요: {item['required_count']}개",
                "- 해당 Logos 자료군을 실제로 확인하고 캡처 또는 요약하십시오.",
                "",
            ]
    else:
        lines.append("- 없음")

    lines += ["", "## 통과 자료군", ""]
    lines += [f"- ✅ {item['id']} {item['label']} ({item['points_earned']}/{item['points_max']}점)" for item in passed_items] or ["- 없음"]

    lines += [
        "",
        "## 다음 단계",
        "",
        "Coverage는 자료군 존재 여부만 평가합니다. 이어서 Capture Quality를 확인하십시오.",
        "",
        "```powershell",
        f"python scripts/audit_capture_quality.py --passage {passage_path}",
        f"python scripts/gate_deep_research.py --passage {passage_path}",
        "```",
    ]
    return "\n".join(lines)


def main() -> int:
    args = parse_args()
    passage_path = Path(args.passage)
    capture_dir = Path(args.capture_dir)

    if not passage_path.exists():
        print(f"[ERROR] passage.yaml 없음: {passage_path}", file=sys.stderr)
        return 1

    passage_data = load_yaml_simple(passage_path)
    output_path = Path(args.output) if args.output else passage_path.parent / "03-logos-coverage-report.md"

    capture_dir.mkdir(parents=True, exist_ok=True)
    captures = collect_captures(
        capture_dir,
        passage_data.get("book_slug", ""),
        passage_data.get("passage_slug", ""),
    )

    combined_parts = []
    for path in captures:
        try:
            combined_parts.append(path.read_text(encoding="utf-8", errors="replace"))
        except OSError:
            continue
    combined_text = "\n\n".join(combined_parts)

    score, results = score_coverage(combined_text, captures)
    status, status_label = get_status(score)
    output_path.write_text(
        build_report(passage_data, passage_path, captures, combined_text, score, results),
        encoding="utf-8",
    )

    print(f"\n{'=' * 50}")
    print(f"Logos Coverage Score: {score}/100")
    print(f"상태: {status} — {status_label}")
    print(f"{'=' * 50}")
    missing = [item for item in results if not item["passed"]]
    if missing:
        print(f"\n누락 항목 ({len(missing)}개):")
        for item in missing:
            print(f"  ❌ {item['id']} {item['label']} (0/{item['points_max']}점)")
    if args.verbose:
        print("\n사용한 캡처 파일:")
        for path in captures:
            print(f"  - {path}")
    print(f"\n보고서: {output_path}")
    return 0 if score >= 75 else 1


if __name__ == "__main__":
    raise SystemExit(main())
