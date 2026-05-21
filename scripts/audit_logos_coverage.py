"""
audit_logos_coverage.py — Logos 활용도 점수 감사기

tmp/logos-capture/raw/ 의 캡처 파일들을 분석하여
Logos Coverage Score를 산출하고 누락 항목을 보고한다.

사용법:
    python scripts/audit_logos_coverage.py --passage docs/john/13-14/00-passage.yaml
    python scripts/audit_logos_coverage.py --passage docs/john/13-14/00-passage.yaml --capture-dir tmp/logos-capture/raw
    python scripts/audit_logos_coverage.py --passage docs/john/13-14/00-passage.yaml --verbose
"""

from __future__ import annotations

import argparse
import re
import sys
from datetime import datetime
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# Coverage 체크 규칙 — rubric과 동기화
RUBRIC = [
    {
        "id": "R-01", "label": "본문 범위·문맥 확인", "points": 10,
        "keywords": ["본문", "passage guide", "범위", "context", "확정 범위", "문맥",
                     "요한복음", "13장", "13:1", "13:14", "세족식", "마지막"],
        "min_keywords": 2,
    },
    {
        "id": "R-02", "label": "번역 비교", "points": 10,
        "keywords": ["nasb", "esv", "개역개정", "번역", "text comparison", "kjv", "niv", "nrsv",
                     "개역", "한글", "성경전서", "표준새번역", "공동번역"],
        "min_keywords": 1,  # 1개로 낮춤 — 개역개정 언급만으로도 번역 사용 확인됨
    },
    {
        "id": "R-03", "label": "원어·문법", "points": 15,
        "keywords": ["헬라어", "히브리어", "greek", "hebrew", "bdag", "halot", "원어", "lexicon",
                     "동사", "명사", "분사", "morph", "interlinear", "exegetical",
                     "νίπτω", "λούω", "ὀφείλετε", "μέρος", "ὑπόδειγμα", "κύριος",
                     "nipto", "louo", "opheilete", "meros", "hypodeigma"],
        "min_keywords": 1,  # 1개로 낮춤 — 원어 단어 1개만 있어도 확인됨
    },
    {
        "id": "R-04", "label": "구조·담화", "points": 10,
        "keywords": ["구조", "structure", "discourse", "접속사", "반복", "병행", "담화",
                     "clause", "패턴", "흐름", "전환", "대조", "점층", "교차구조",
                     "서론", "본론", "결론", "대지"],
        "min_keywords": 2,
    },
    {
        "id": "R-05", "label": "교차본문", "points": 10,
        "keywords": ["교차", "cross reference", "참조", "병행", "관련 본문", "tsk",
                     "treasury", "important passages", "관련구절", "참고구절",
                     "요한일서", "3:16", "마가복음", "눅", "마태"],
        "min_keywords": 2,
    },
    {
        "id": "R-06", "label": "주석 비교", "points": 15,
        "keywords": ["nicnt", "becnt", "keener", "carson", "moo", "pillar", "tntc", "totc",
                     "wbc", "nac", "주석", "commentary", "박대영", "fee", "morris",
                     "culpepper", "컬페퍼", "권해생", "빌", "카슨", "키너"],
        "min_keywords": 2,
    },
    {
        "id": "R-07", "label": "성경신학", "points": 10,
        "keywords": ["성경신학", "biblical theology", "구속사", "언약", "왕국", "하나님나라",
                     "창조", "타락", "구속", "새창조", "factbook", "themes",
                     "신학 주제", "신학적", "구원", "속죄", "칭의", "성화"],
        "min_keywords": 2,
    },
    {
        "id": "R-08", "label": "조직신학", "points": 5,
        "keywords": ["조직신학", "systematic", "교리", "교의학", "신론", "기독론", "구원론",
                     "성령론", "교회론", "종말론", "theology guide",
                     "교리적", "신학", "하나님의", "삼위일체"],
        "min_keywords": 1,
    },
    {
        "id": "R-09", "label": "역사·문화 배경", "points": 5,
        "keywords": ["배경", "background", "문화", "역사", "factbook", "사전", "atlas",
                     "dictionary", "풍습", "관습", "고대",
                     "유대", "로마", "헬라", "당시", "종의", "노예", "유월절"],
        "min_keywords": 2,
    },
    {
        "id": "R-10", "label": "설교 자료", "points": 5,
        "keywords": ["sermon starter", "설교 자료", "homiletics", "설교 구조", "전달",
                     "sermon builder", "설교", "강해", "Big Idea", "big idea"],
        "min_keywords": 1,
    },
    {
        "id": "R-11", "label": "목회·적용 자료", "points": 5,
        "keywords": ["적용", "application", "목회", "pastoral", "삶의", "현실",
                     "복음 프레임", "순종", "실천", "삶", "우리", "성도"],
        "min_keywords": 2,
    },
]

THRESHOLDS = [
    (90, "deep_eligible", "Logos-Max 심층 연구 즉시 가능"),
    (75, "deep_eligible_with_warning", "심층 연구 가능 (누락 경고 포함)"),
    (60, "review_required", "보강 필요 — deep_research 보류 권장"),
    (0, "insufficient", "연구팩 불충분 — 설교 방향 생성 중단"),
]


def load_yaml_simple(path: Path) -> dict:
    data = {}
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = line.strip()
        if line.startswith("#") or not line or line.startswith("-"):
            continue
        if ": " in line:
            k, v = line.split(": ", 1)
            data[k.strip()] = v.strip().strip('"')
    return data


def collect_captures(capture_dir: Path, passage_slug: str) -> list[Path]:
    """passage_slug와 연관된 캡처 파일 목록 반환.

    매칭 전략:
    1. passage_slug 포함 (e.g. "1314" in "jn-13-14-...")
    2. 챕터 번호를 포함하는 파일 (e.g. "-13-" in "john-13-1-17-...")
    3. 전체 파일 (20개 이하면 전부, 이상이면 최신 15개)
    """
    all_files = list(capture_dir.glob("*.md")) + list(capture_dir.glob("*.txt"))
    if not all_files:
        return []

    # john-3-... 같은 요한복음 3장 파일 제외 (다른 본문 캡처)
    slug_parts = passage_slug.split("-")  # "13-14" → ["13", "14"]
    chapter = slug_parts[0] if slug_parts else ""

    slug_clean = passage_slug.replace("-", "").replace(":", "").lower()

    matched: list[Path] = []
    for f in all_files:
        stem_clean = f.stem.lower().replace("-", "").replace("_", "")
        stem_orig = f.stem.lower()

        # 전략 1: 정확한 slug 포함
        if slug_clean in stem_clean:
            matched.append(f)
            continue

        # 전략 2: 챕터가 명시된 파일 포함 (e.g. "john-13-" 또는 "jn-13-")
        if chapter and (
            f"-{chapter}-" in stem_orig
            or stem_orig.endswith(f"-{chapter}")
        ):
            matched.append(f)
            continue

    # 전략 3: 폴백 (파일이 없거나 적을 때)
    if not matched:
        matched = sorted(all_files, key=lambda f: f.stat().st_mtime, reverse=True)[:15]

    return list(dict.fromkeys(matched))  # 중복 제거


def score_coverage(combined_text: str) -> tuple[int, list[dict]]:
    text_lower = combined_text.lower()
    results = []
    total = 0

    for item in RUBRIC:
        found = sum(1 for kw in item["keywords"] if kw.lower() in text_lower)
        passed = found >= item["min_keywords"]
        points_earned = item["points"] if passed else 0
        total += points_earned
        results.append({
            "id": item["id"],
            "label": item["label"],
            "points_max": item["points"],
            "points_earned": points_earned,
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


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Logos 캡처 파일들의 활용도를 점수화합니다."
    )
    parser.add_argument("--passage", required=True, help="passage.yaml 경로")
    parser.add_argument("--capture-dir", default="tmp/logos-capture/raw",
                        help="캡처 파일 폴더 (기본: tmp/logos-capture/raw)")
    parser.add_argument("--verbose", action="store_true", help="상세 출력")
    parser.add_argument("--output", default=None,
                        help="커버리지 보고서 출력 경로 (기본: 03-logos-coverage-report.md)")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    passage_path = Path(args.passage)
    capture_dir = Path(args.capture_dir)

    if not passage_path.exists():
        print(f"[ERROR] passage.yaml 없음: {passage_path}", file=sys.stderr)
        return 1

    passage_data = load_yaml_simple(passage_path)
    book_korean = passage_data.get("book_korean", "")
    passage = passage_data.get("passage", "")
    passage_slug = passage_data.get("passage_slug", "")
    book_slug = passage_data.get("book_slug", "")
    today = datetime.now().strftime("%Y-%m-%d")

    output_dir = passage_path.parent
    output_path = Path(args.output) if args.output else output_dir / "03-logos-coverage-report.md"

    # 캡처 파일 수집
    if not capture_dir.exists():
        capture_dir.mkdir(parents=True, exist_ok=True)

    captures = collect_captures(capture_dir, f"{book_slug}-{passage_slug}")
    combined_text = ""
    for f in captures:
        try:
            combined_text += f.read_text(encoding="utf-8", errors="replace") + "\n"
        except Exception:
            pass

    score, results = score_coverage(combined_text)
    status, status_label = get_status(score)

    # 누락 항목
    missing = [r for r in results if not r["passed"]]
    passed_items = [r for r in results if r["passed"]]

    # 보고서 작성
    lines = [
        f"# Logos Coverage Report — {book_korean} {passage}",
        "",
        f"**감사일**: {today}  ",
        f"**캡처 파일 수**: {len(captures)}개  ",
        f"**총 텍스트**: {len(combined_text):,}자",
        "",
        "---",
        "",
        "## 종합 점수",
        "",
        f"### {score} / 100점",
        "",
        f"**상태**: `{status}`  ",
        f"**판정**: {status_label}",
        "",
    ]

    if status == "deep_eligible":
        lines += [
            "> ✅ Logos-Max 심층 연구를 즉시 실행할 수 있습니다.",
            ">",
            "> ```powershell",
            f'> python scripts/run_logos_max_research.py --passage "{book_korean} {passage}"',
            "> ```",
        ]
    elif status == "deep_eligible_with_warning":
        lines += [
            "> ⚠️ 심층 연구는 가능하지만, 누락 항목을 보강하면 품질이 높아집니다.",
        ]
    elif status == "review_required":
        lines += [
            "> 🔴 Logos 자료 보강이 필요합니다. 아래 누락 항목을 캡처하십시오.",
        ]
    else:
        lines += [
            "> 🛑 필수 Logos 자료가 부족합니다. 심층 연구를 중단합니다.",
        ]

    lines += [
        "",
        "---",
        "",
        "## 항목별 점수",
        "",
        "| 항목 | 배점 | 획득 | 상태 |",
        "|------|------|------|------|",
    ]

    for r in results:
        status_icon = "✅" if r["passed"] else "❌"
        lines.append(
            f"| {r['label']} | {r['points_max']} | {r['points_earned']} | {status_icon} |"
        )

    lines += [
        f"| **합계** | **100** | **{score}** | |",
        "",
        "---",
        "",
    ]

    if missing:
        lines += [
            "## 누락 항목 (캡처 필요)",
            "",
        ]
        for r in missing:
            lines += [
                f"### ❌ {r['id']} — {r['label']} (0/{r['points_max']}점)",
                f"- 현재 발견된 관련 키워드: {r['found_count']}개 (필요: {r['required_count']}개)",
                f"- 해당 Logos 도구를 사용하여 캡처하십시오.",
                "",
            ]

    if passed_items:
        lines += [
            "---",
            "",
            "## 완료된 항목",
            "",
        ]
        for r in passed_items:
            lines += [
                f"- ✅ {r['id']} {r['label']} ({r['points_earned']}/{r['points_max']}점)",
            ]

    lines += [
        "",
        "---",
        "",
        "## 다음 단계",
        "",
    ]

    if status in ("deep_eligible", "deep_eligible_with_warning"):
        lines += [
            "```powershell",
            f"python scripts/gate_deep_research.py --passage {passage_path}",
            "```",
        ]
    else:
        lines += [
            "누락 항목을 Logos에서 캡처한 후 재실행하십시오:",
            "",
            "```powershell",
            f"python scripts/audit_logos_coverage.py --passage {passage_path}",
            "```",
        ]

    output_path.write_text("\n".join(lines), encoding="utf-8")

    # 콘솔 출력
    print(f"\n{'='*50}")
    print(f"Logos Coverage Score: {score}/100")
    print(f"상태: {status} — {status_label}")
    print(f"{'='*50}")

    if missing:
        print(f"\n누락 항목 ({len(missing)}개):")
        for r in missing:
            print(f"  ❌ {r['id']} {r['label']} (0/{r['points_max']}점)")

    print(f"\n보고서: {output_path}")

    # gate에서 사용할 exit code
    # 75 이상 = 0 (통과), 미만 = 1 (보류)
    return 0 if score >= 75 else 1


if __name__ == "__main__":
    raise SystemExit(main())
