"""
Audit Capture Quality Score for Logos-Max v2.1.

Coverage asks whether the needed Logos categories are present.
Quality asks whether the captured material is useful for exegesis, theological
integration, and sermon direction.
"""

from __future__ import annotations

import argparse
import re
import shutil
import sys
from datetime import datetime
from pathlib import Path

from pipeline_utils import configure_utf8_stdio, load_yaml_simple


configure_utf8_stdio()


QUALITY_RULES: dict[str, dict] = {
    "commentaries": {
        "label": "주석 비교",
        "points": 20,
        "min_sources": 2,
        "source_keywords": ["Keener", "Carson", "Culpepper", "Beale", "Köstenberger", "박대영", "김새윤", "권해생", "주석", "commentary"],
        "required_elements": {
            "interpretive_summary": ["주석", "해석", "설명", "견해", "본문은", "commentary"],
            "interpretive_comparison": ["비교", "차이", "반면", "동의", "다르게", "논쟁", "agree", "disagree"],
            "sermon_application": ["설교", "강단", "적용", "반영", "Big Idea", "implication"],
        },
        "warnings": [
            "주석 견해가 2개 미만입니다.",
            "해석 차이점이 정리되지 않았습니다.",
            "설교 반영 판단이 없습니다.",
        ],
    },
    "cross_references": {
        "label": "교차본문",
        "points": 15,
        "min_references": 3,
        "required_elements": {
            "connection_reason": ["교차", "참조", "연결", "관련", "이유", "cross reference"],
            "canonical_direction": ["정경", "구속사", "성취", "예표", "구약", "신약", "canonical"],
            "risk_check": ["주의", "경계", "억지", "과도", "무리", "알레고리", "risk"],
        },
        "warnings": [
            "교차본문 연결 이유가 부족합니다.",
            "억지 연결 위험 검토가 없습니다.",
        ],
    },
    "biblical_theology": {
        "label": "성경신학",
        "points": 20,
        "required_elements": {
            "covenant_connection": ["언약", "구속", "구원", "covenant", "redemption"],
            "redemptive_history": ["구속사", "창조", "타락", "새창조", "역사", "흐름"],
            "christ_fulfillment": ["그리스도", "예수", "십자가", "부활", "성취", "완성"],
            "anti_allegory": ["알레고리", "억지", "경계", "본문 아래", "자연스럽", "anti-allegory"],
        },
        "warnings": [
            "그리스도 성취 논리가 약합니다.",
            "정경적 위치 설명이 부족합니다.",
            "억지 알레고리 위험 점검이 없습니다.",
        ],
    },
    "original_language": {
        "label": "원어·문법",
        "points": 15,
        "required_elements": {
            "key_terms": ["원어", "헬라어", "Greek", "νίπτω", "λούω", "ὀφείλετε", "μέρος", "εἰς τέλος"],
            "contextual_meaning": ["문맥", "본문에서", "의미", "context", "usage"],
            "sermon_relevance": ["설교", "강단", "중요한 이유", "선명", "relevance"],
            "overuse_warning": ["과시", "주의", "최대", "3개", "필요한", "생략", "overuse"],
        },
        "warnings": [
            "원어가 본문 의미를 실제로 선명하게 하는지 불분명합니다.",
            "원어 과시 위험 점검이 없습니다.",
        ],
    },
    "structure_discourse": {
        "label": "구조·담화",
        "points": 10,
        "required_elements": {
            "paragraph_flow": ["흐름", "단락", "구조", "먼저", "이후", "flow"],
            "repetition_contrast": ["반복", "대조", "반면", "그러나", "contrast"],
            "turning_point": ["전환", "절정", "핵심", "climax", "turning point"],
        },
        "warnings": [
            "단락 흐름 분석이 부족합니다.",
            "반복·대조·전환 관찰이 부족합니다.",
        ],
    },
    "background": {
        "label": "역사·문화 배경",
        "points": 10,
        "required_elements": {
            "relevant_background": ["배경", "문화", "당시", "유대", "로마", "종", "발 씻김", "background"],
            "textual_contribution": ["본문 이해", "의미", "기여", "따라서", "contribution"],
            "overuse_warning": ["주의", "과도", "직접", "필요한 범위", "overuse"],
        },
        "warnings": [
            "배경 정보가 본문 해석에 어떻게 기여하는지 불분명합니다.",
        ],
    },
    "application_pastoral": {
        "label": "목회·적용",
        "points": 10,
        "required_elements": {
            "false_gospel_diagnosis": ["자기구원", "인정", "불안", "정죄", "회피", "거짓 복음", "false gospel"],
            "gospel_motive": ["복음", "은혜", "먼저 씻김", "사랑받았기에", "gospel motive"],
            "one_obedience": ["이번 주", "한 순종", "구체", "실천", "one obedience"],
        },
        "warnings": [
            "오늘 청중의 자기구원 방식 진단이 부족합니다.",
            "복음의 은혜에서 출발하는 적용 구조가 약합니다.",
            "이번 주 한 순종이 분명하지 않습니다.",
        ],
    },
}


BOOK_ALIASES = {
    "jn": ["jn", "john"],
    "mt": ["mt", "matt", "matthew"],
    "mk": ["mk", "mark"],
    "lk": ["lk", "luke"],
    "ac": ["ac", "acts"],
    "ro": ["ro", "rom", "romans"],
    "ge": ["ge", "gen", "genesis"],
    "ex": ["ex", "exo", "exodus"],
    "ps": ["ps", "psa", "psalm", "psalms"],
    "is": ["is", "isa", "isaiah"],
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Audit Logos capture quality for Logos-Max v2.1.")
    parser.add_argument("--passage", required=True, help="Path to 00-passage.yaml")
    parser.add_argument("--capture-dir", default="tmp/logos-capture/raw", help="Capture directory")
    parser.add_argument("--output", default=None, help="Output report path")
    parser.add_argument("--verbose", action="store_true", help="Print capture files used")
    return parser.parse_args()


def is_template_capture(path: Path) -> bool:
    try:
        preview = path.read_text(encoding="utf-8", errors="replace")[:1600].lower()
    except OSError:
        return False
    return "capture_status: template" in preview


def collect_captures(capture_dir: Path, book_slug: str, passage_slug: str) -> list[Path]:
    all_files = sorted(list(capture_dir.glob("*.md")) + list(capture_dir.glob("*.txt")))
    if not all_files:
        return []

    aliases = BOOK_ALIASES.get(book_slug, [book_slug] if book_slug else [])
    passage_clean = passage_slug.replace("-", "").replace(":", "").lower()
    chapter = passage_slug.split("-")[0] if passage_slug else ""
    verse = passage_slug.split("-")[1] if "-" in passage_slug else ""
    content_ref = f"{chapter}:{verse}" if chapter and verse else ""
    matched: list[Path] = []

    for file_path in all_files:
        if is_template_capture(file_path):
            continue
        try:
            preview = file_path.read_text(encoding="utf-8", errors="replace")[:2000].lower()
        except OSError:
            preview = ""

        stem = file_path.stem.lower()
        compact = stem.replace("-", "").replace("_", "")
        exact_match = aliases and any(f"{alias}{passage_clean}" in compact for alias in aliases)
        chapter_match = chapter and aliases and any(
            stem.startswith(f"{alias}-{chapter}-") for alias in aliases
        )
        content_match = content_ref and (
            f"passage_ref: john {content_ref}" in preview
            or f"passage_ref: 요한복음 {content_ref}" in preview
            or f"john {content_ref}" in preview
            or f"요한복음 {content_ref}" in preview
        )
        if exact_match or chapter_match or content_match:
            matched.append(file_path)

    if not matched:
        matched = [p for p in sorted(all_files, key=lambda f: f.stat().st_mtime, reverse=True) if not is_template_capture(p)][:15]

    return list(dict.fromkeys(matched))


def count_references(text: str) -> int:
    pattern = re.compile(r"(?:[1-3]\s*)?(?:[A-Za-z가-힣]{1,18})\s*\d{1,3}:\d{1,3}")
    return len(set(pattern.findall(text)))


def count_sources(text: str, keywords: list[str]) -> int:
    lower = text.lower()
    return len({keyword.lower() for keyword in keywords if keyword.lower() in lower})


def element_passed(text_lower: str, keywords: list[str]) -> bool:
    return any(keyword.lower() in text_lower for keyword in keywords)


def assess_quality(text: str) -> tuple[int, list[dict]]:
    text_lower = text.lower()
    total = 0
    results: list[dict] = []

    for key, rule in QUALITY_RULES.items():
        element_results = []
        for element_key, keywords in rule["required_elements"].items():
            passed = element_passed(text_lower, keywords)
            element_results.append({"id": element_key, "passed": passed})

        element_count = len(element_results)
        passed_count = sum(1 for item in element_results if item["passed"])
        ratio = passed_count / element_count if element_count else 0

        quantity_passed = True
        quantity_detail = "해당 없음"
        if "min_sources" in rule:
            source_count = count_sources(text, rule.get("source_keywords", []))
            quantity_passed = source_count >= rule["min_sources"]
            quantity_detail = f"source_count={source_count}, required={rule['min_sources']}"
        elif "min_references" in rule:
            reference_count = count_references(text)
            quantity_passed = reference_count >= rule["min_references"]
            quantity_detail = f"reference_count={reference_count}, required={rule['min_references']}"

        if not quantity_passed:
            ratio = min(ratio, 0.5)

        earned = round(rule["points"] * ratio)
        total += earned
        missing_elements = [item["id"] for item in element_results if not item["passed"]]
        results.append({
            "id": key,
            "label": rule["label"],
            "points_max": rule["points"],
            "points_earned": earned,
            "passed_elements": passed_count,
            "total_elements": element_count,
            "quantity_passed": quantity_passed,
            "quantity_detail": quantity_detail,
            "missing_elements": missing_elements,
            "warnings": rule["warnings"],
        })

    return total, results


def status_for_score(score: int) -> tuple[str, str]:
    if score >= 80:
        return "excellent", "자료 품질은 우수합니다. 단, Coverage Gate도 함께 통과해야 합니다."
    if score >= 70:
        return "acceptable", "자료 품질은 deep research 진행에 충분합니다."
    if score >= 60:
        return "review_required", "자료 품질 보강을 권장합니다."
    return "quality_blocked", "자료 품질이 부족하여 deep research를 중단해야 합니다."


def build_report(
    passage_data: dict[str, str],
    captures: list[Path],
    text_length: int,
    score: int,
    status: str,
    status_label: str,
    results: list[dict],
) -> str:
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    book_korean = passage_data.get("book_korean", passage_data.get("book", ""))
    passage = passage_data.get("passage", "")
    weak = [item for item in results if item["points_earned"] < item["points_max"]]

    lines = [
        f"# Capture Quality Report - {book_korean} {passage}",
        "",
        f"- 감사 시각: {now}",
        f"- 캡처 파일 수: {len(captures)}",
        f"- 통합 텍스트 길이: {text_length:,}자",
        "",
        "## Capture Quality Score",
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
        "## 자료군별 품질",
        "",
        "| 자료군 | 배점 | 획득 | 요소 통과 | 수량 요건 |",
        "|---|---:|---:|---|---|",
    ]
    for item in results:
        quantity = "통과" if item["quantity_passed"] else f"미달 ({item['quantity_detail']})"
        lines.append(
            f"| {item['label']} | {item['points_max']} | {item['points_earned']} | "
            f"{item['passed_elements']}/{item['total_elements']} | {quantity} |"
        )

    lines += ["", "## Weak Categories", ""]
    if weak:
        for item in weak:
            lines += [
                f"### {item['label']} ({item['points_earned']}/{item['points_max']}점)",
                f"- missing_required_elements: {', '.join(item['missing_elements']) if item['missing_elements'] else '없음'}",
                f"- quantity: {'통과' if item['quantity_passed'] else item['quantity_detail']}",
            ]
            for warning in item["warnings"]:
                lines.append(f"- 경고: {warning}")
            lines.append("")
    else:
        lines.append("- 없음")

    lines += [
        "## Gate 참고",
        "",
        "- 이 보고서는 Coverage Score를 대체하지 않습니다.",
        "- Coverage Score와 Capture Quality Score가 모두 기준을 통과해야 deep research로 넘어갑니다.",
        "- 품질 점수가 낮으면 자료는 있어도 본문 연구에 실제로 기여하지 못한 것으로 판단합니다.",
    ]
    return "\n".join(lines)


def main() -> int:
    args = parse_args()
    passage_path = Path(args.passage)
    capture_dir = Path(args.capture_dir)

    if not passage_path.exists():
        print(f"[ERROR] passage.yaml 없음: {passage_path}", file=sys.stderr)
        return 2

    passage_data = load_yaml_simple(passage_path)
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

    score, results = assess_quality(combined_text)
    status, status_label = status_for_score(score)
    output_path = Path(args.output) if args.output else passage_path.parent / "04-capture-quality-report.md"
    report = build_report(passage_data, captures, len(combined_text), score, status, status_label, results)
    tmp = output_path.with_suffix(".tmp")
    tmp.write_text(report, encoding="utf-8")
    if output_path.exists():
        shutil.copy2(output_path, output_path.with_suffix(".bak"))
    shutil.move(str(tmp), str(output_path))

    print(f"\nCapture Quality Score: {score}/100")
    print(f"status: {status} - {status_label}")
    if args.verbose:
        print("\n사용한 캡처 파일:")
        for path in captures:
            print(f"  - {path}")
    weak = [item for item in results if item["points_earned"] < item["points_max"]]
    if weak:
        print("\nWeak categories:")
        for item in weak:
            print(f"  - {item['label']}: {item['points_earned']}/{item['points_max']}")
    print(f"\n보고서: {output_path}")

    if score >= 70:
        return 0
    if score >= 60:
        return 1
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
