"""
create_passage.py — 본문 연구 시작 파일 생성기

passage.yaml을 생성하고 docs/{book}/{passage}/ 디렉토리 구조를 만든다.

사용법:
    python scripts/create_passage.py --book John --passage 13:14 --context 13:1-17 --genre gospel
    python scripts/create_passage.py --book Romans --passage 8:1 --context 8:1-11 --genre epistle
    python scripts/create_passage.py --book Exodus --passage 20:1-17 --context 20:1-21 --genre law_ritual
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


BOOK_MAP = {
    # 구약
    "Genesis": ("창세기", "ge", "ot_narrative"),
    "Exodus": ("출애굽기", "ex", "ot_narrative"),
    "Leviticus": ("레위기", "le", "law_ritual"),
    "Numbers": ("민수기", "nu", "law_ritual"),
    "Deuteronomy": ("신명기", "dt", "law_ritual"),
    "Joshua": ("여호수아", "jos", "ot_narrative"),
    "Judges": ("사사기", "jdg", "ot_narrative"),
    "Ruth": ("룻기", "ru", "ot_narrative"),
    "1Samuel": ("사무엘상", "1sa", "ot_narrative"),
    "2Samuel": ("사무엘하", "2sa", "ot_narrative"),
    "1Kings": ("열왕기상", "1ki", "ot_narrative"),
    "2Kings": ("열왕기하", "2ki", "ot_narrative"),
    "Psalms": ("시편", "ps", "psalm_wisdom"),
    "Proverbs": ("잠언", "pr", "psalm_wisdom"),
    "Ecclesiastes": ("전도서", "ec", "psalm_wisdom"),
    "Isaiah": ("이사야", "is", "prophetic"),
    "Jeremiah": ("예레미야", "je", "prophetic"),
    "Ezekiel": ("에스겔", "eze", "prophetic"),
    "Daniel": ("다니엘", "da", "prophetic"),
    # 신약
    "Matthew": ("마태복음", "mt", "gospel"),
    "Mark": ("마가복음", "mk", "gospel"),
    "Luke": ("누가복음", "lk", "gospel"),
    "John": ("요한복음", "jn", "gospel"),
    "Acts": ("사도행전", "ac", "ot_narrative"),
    "Romans": ("로마서", "ro", "epistle"),
    "1Corinthians": ("고린도전서", "1co", "epistle"),
    "2Corinthians": ("고린도후서", "2co", "epistle"),
    "Galatians": ("갈라디아서", "ga", "epistle"),
    "Ephesians": ("에베소서", "eph", "epistle"),
    "Philippians": ("빌립보서", "php", "epistle"),
    "Colossians": ("골로새서", "col", "epistle"),
    "1Thessalonians": ("데살로니가전서", "1th", "epistle"),
    "2Thessalonians": ("데살로니가후서", "2th", "epistle"),
    "1Timothy": ("디모데전서", "1ti", "epistle"),
    "2Timothy": ("디모데후서", "2ti", "epistle"),
    "Hebrews": ("히브리서", "heb", "epistle"),
    "James": ("야고보서", "jas", "epistle"),
    "1Peter": ("베드로전서", "1pe", "epistle"),
    "2Peter": ("베드로후서", "2pe", "epistle"),
    "1John": ("요한일서", "1jn", "epistle"),
    "Revelation": ("요한계시록", "rev", "prophetic"),
}

VALID_GENRES = ["gospel", "epistle", "psalm_wisdom", "ot_narrative", "prophetic", "law_ritual"]


def passage_to_slug(passage: str) -> str:
    """13:14 → 13-14, 8:1-11 → 8-1-11"""
    return passage.replace(":", "-").replace("–", "-").replace("—", "-")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="passage.yaml 및 연구 폴더를 생성합니다."
    )
    parser.add_argument("--book", required=True, help="영어 책 이름 (e.g. John, Romans, Exodus)")
    parser.add_argument("--passage", required=True, help="핵심 본문 (e.g. 13:14, 8:1)")
    parser.add_argument("--context", required=True, help="문맥 범위 (e.g. 13:1-17, 8:1-11)")
    parser.add_argument("--genre", default=None,
                        help=f"장르 (자동 감지 가능): {', '.join(VALID_GENRES)}")
    parser.add_argument("--theme-hint", default="", help="테마 힌트 (선택)")
    parser.add_argument("--subgenre", default="", help="하위 장르 (선택)")
    parser.add_argument("--mode", default="preaching",
                        choices=["preaching", "teaching", "small_group"],
                        help="설교 모드")
    parser.add_argument("--audience", default="adult_congregation",
                        help="대상 청중")
    parser.add_argument("--docs-dir", default="docs", help="docs 폴더 경로")
    return parser.parse_args()


def resolve_book(book: str) -> tuple[str, str, str]:
    """책 이름 → (한국어, slug, 기본 장르) 반환"""
    if book in BOOK_MAP:
        return BOOK_MAP[book]
    # 대소문자 무시 검색
    for k, v in BOOK_MAP.items():
        if k.lower() == book.lower():
            return v
    raise ValueError(
        f"알 수 없는 책 이름: '{book}'\n"
        f"지원 목록: {', '.join(BOOK_MAP.keys())}"
    )


def make_folder_name(book_slug: str) -> str:
    """jn, ro, ex → john, romans, exodus (폴더명 정규화)"""
    slug_to_folder = {
        "ge": "genesis", "ex": "exodus", "le": "leviticus", "nu": "numbers",
        "dt": "deuteronomy", "jos": "joshua", "jdg": "judges", "ru": "ruth",
        "1sa": "1samuel", "2sa": "2samuel", "1ki": "1kings", "2ki": "2kings",
        "ps": "psalms", "pr": "proverbs", "ec": "ecclesiastes",
        "is": "isaiah", "je": "jeremiah", "eze": "ezekiel", "da": "daniel",
        "mt": "matthew", "mk": "mark", "lk": "luke", "jn": "john",
        "ac": "acts", "ro": "romans", "1co": "1corinthians", "2co": "2corinthians",
        "ga": "galatians", "eph": "ephesians", "php": "philippians", "col": "colossians",
        "1th": "1thessalonians", "2th": "2thessalonians",
        "1ti": "1timothy", "2ti": "2timothy",
        "heb": "hebrews", "jas": "james", "1pe": "1peter", "2pe": "2peter",
        "1jn": "1john", "rev": "revelation",
    }
    return slug_to_folder.get(book_slug, book_slug)


def main() -> int:
    args = parse_args()

    book_korean, book_slug, default_genre = resolve_book(args.book)
    genre = args.genre if args.genre in VALID_GENRES else default_genre
    passage_slug = passage_to_slug(args.passage)
    folder_book = make_folder_name(book_slug)

    docs_dir = Path(args.docs_dir)
    passage_dir = docs_dir / folder_book / passage_slug
    passage_dir.mkdir(parents=True, exist_ok=True)

    passage_yaml_path = passage_dir / "00-passage.yaml"

    if passage_yaml_path.exists():
        print(f"[INFO] 이미 존재합니다: {passage_yaml_path}")
        print("[INFO] --force 없이는 덮어쓰지 않습니다.")
        return 0

    content = f"""# passage.yaml — Logos-Max Sermon Workflow v2
# 이 파일이 있어야 레시피·체크리스트·커버리지 감사가 실행됩니다.

book: {args.book}
book_korean: {book_korean}
book_slug: {book_slug}
passage: "{args.passage}"
passage_slug: "{passage_slug}"
context_range: "{args.context}"
genre: {genre}
subgenre: "{args.subgenre}"
sermon_mode: {args.mode}
target_audience: {args.audience}
theme_hint: "{args.theme_hint}"

# 자동 생성 정보
created: "{datetime.now().strftime('%Y-%m-%d')}"
workflow_version: "logos-max-v2"

# 다음 단계
# 1. build_logos_recipe.py --passage {passage_yaml_path}
# 2. Logos에서 캡처 실행 → tmp/logos-capture/raw/에 저장
# 3. audit_logos_coverage.py --passage {passage_yaml_path}
# 4. gate_deep_research.py --passage {passage_yaml_path}
# 5. (통과 시) run_logos_max_research.py --passage "{book_korean} {args.passage}"
"""

    passage_yaml_path.write_text(content, encoding="utf-8")
    print(f"✅ 생성됨: {passage_yaml_path}")
    print(f"   책: {book_korean} ({args.book})")
    print(f"   본문: {args.passage} (문맥: {args.context})")
    print(f"   장르: {genre}")
    print(f"   폴더: {passage_dir}")
    print()
    print("다음 단계:")
    print(f"  python scripts/build_logos_recipe.py --passage {passage_yaml_path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
