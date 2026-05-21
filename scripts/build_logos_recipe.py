"""
build_logos_recipe.py — Logos 연구 레시피 + 캡처 체크리스트 생성기

passage.yaml을 읽어 장르별 Logos 도구 사용 순서와 캡처 체크리스트를 생성한다.

사용법:
    python scripts/build_logos_recipe.py --passage docs/john/13-14/00-passage.yaml
    python scripts/build_logos_recipe.py --passage docs/john/13-14/00-passage.yaml --output-dir docs/john/13-14
"""

from __future__ import annotations

import argparse
import sys
from datetime import datetime
from pathlib import Path

try:
    import yaml
    _YAML_AVAILABLE = True
except ImportError:
    _YAML_AVAILABLE = False

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

CONFIG_DIR = Path("config")


def load_yaml(path: Path) -> dict:
    if not _YAML_AVAILABLE:
        # yaml 없을 때 간단한 파서 (key: value 형식만 지원)
        data = {}
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line.startswith("#") or not line or line.startswith("-"):
                continue
            if ": " in line:
                k, v = line.split(": ", 1)
                data[k.strip()] = v.strip().strip('"')
        return data
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Logos 연구 레시피와 캡처 체크리스트를 생성합니다."
    )
    parser.add_argument("--passage", required=True, help="passage.yaml 경로")
    parser.add_argument("--output-dir", default=None,
                        help="출력 폴더 (기본값: passage.yaml과 같은 폴더)")
    return parser.parse_args()


GENRE_PRIORITY = {
    "gospel": [
        ("CAT-01", "본문 확정", "Passage Guide + Text Comparison"),
        ("CAT-02", "원어·문법", "Exegetical Guide + Bible Word Study"),
        ("CAT-05", "주석 비교", "Passage Guide > Commentaries (최소 3권)"),
        ("CAT-04", "교차본문", "Cross References + 병행복음서 비교"),
        ("CAT-03", "구조·담화", "Passage Analysis — 화자/청자/장면 전환"),
        ("CAT-08", "역사·문화 배경", "Factbook + Bible Dictionaries"),
        ("CAT-06", "성경신학", "Factbook Themes + Biblical Theology"),
        ("CAT-09", "설교 자료", "Sermon Starter Guide (보조)"),
        ("CAT-07", "조직신학", "Theology Guide (보조)"),
        ("CAT-10", "목회·적용", "Pastoral resources (보조)"),
    ],
    "epistle": [
        ("CAT-01", "본문 확정", "Passage Guide + Text Comparison"),
        ("CAT-02", "원어·문법", "Exegetical Guide + Bible Word Study — 신학 핵심어"),
        ("CAT-03", "구조·담화", "Clause Search — indicative/imperative 구분"),
        ("CAT-05", "주석 비교", "Passage Guide > Commentaries (최소 3권)"),
        ("CAT-04", "교차본문", "Cross References + OT 인용 확인"),
        ("CAT-07", "조직신학", "Theology Guide — 교리 연결"),
        ("CAT-06", "성경신학", "Biblical Theology — 구속사 위치"),
        ("CAT-09", "설교 자료", "Sermon Starter Guide (보조)"),
        ("CAT-10", "목회·적용", "Pastoral resources (보조)"),
    ],
    "psalm_wisdom": [
        ("CAT-01", "본문 확정", "Passage Guide — 시편 장르 확인"),
        ("CAT-02", "원어·문법", "Bible Word Study — 히브리 병행법 확인"),
        ("CAT-03", "구조·담화", "Passage Analysis — 키아즘·병행법 구조"),
        ("CAT-05", "주석 비교", "Commentaries (최소 2권)"),
        ("CAT-06", "성경신학", "Biblical Theology — 예배·지혜 테마"),
        ("CAT-04", "교차본문", "Cross References — 신약 성취"),
        ("CAT-08", "역사·문화 배경", "Factbook — 성전 예배 맥락"),
    ],
    "ot_narrative": [
        ("CAT-01", "본문 확정", "Passage Guide + Text Comparison"),
        ("CAT-03", "구조·담화", "Passage Analysis — 장면·인물·플롯"),
        ("CAT-08", "역사·문화 배경", "Factbook + Bible Dictionaries + Atlas"),
        ("CAT-05", "주석 비교", "Commentaries (최소 2권)"),
        ("CAT-04", "교차본문", "Cross References — 신약 성취"),
        ("CAT-06", "성경신학", "Biblical Theology — 구속사 위치"),
        ("CAT-02", "원어·문법", "Bible Word Study — 필요 시"),
    ],
    "prophetic": [
        ("CAT-01", "본문 확정", "Passage Guide + Text Comparison"),
        ("CAT-08", "역사·문화 배경", "Factbook — 역사적 배경·왕·시대"),
        ("CAT-02", "원어·문법", "Exegetical Guide"),
        ("CAT-04", "교차본문", "Cross References — 신약 성취"),
        ("CAT-05", "주석 비교", "Commentaries (최소 2권)"),
        ("CAT-06", "성경신학", "Biblical Theology"),
    ],
    "law_ritual": [
        ("CAT-01", "본문 확정", "Passage Guide"),
        ("CAT-08", "역사·문화 배경", "Factbook — 제사·정결 의식 배경"),
        ("CAT-02", "원어·문법", "Bible Word Study"),
        ("CAT-04", "교차본문", "Cross References — 히브리서 성취"),
        ("CAT-05", "주석 비교", "Commentaries (최소 2권)"),
        ("CAT-06", "성경신학", "Biblical Theology — 그림자/실체 구조"),
    ],
}

GENRE_CAUTIONS = {
    "gospel": [
        "인물 영웅화 금지 — 제자·바리새인을 단순 예화로 사용하지 마십시오.",
        "기적·비유: 감동 이야기가 아닌 구속사적 의미를 먼저 확인하십시오.",
        "그리스도 중심: 인물 이야기가 아닌 그리스도의 행동과 말씀에 초점을 두십시오.",
        "병행 복음서 비교를 반드시 하십시오.",
    ],
    "epistle": [
        "indicative(하나님이 하신 일) → imperative(우리의 응답) 구조를 반드시 확인하십시오.",
        "imperative만 설교하는 도덕주의를 피하십시오.",
        "핵심 신학 용어를 원어로 확인하십시오.",
    ],
    "psalm_wisdom": [
        "시편을 단순 감정 예화로 사용하지 마십시오.",
        "잠언을 번영 신학으로 연결하지 마십시오.",
        "메시아 시편의 기독론적 해석: 억지 연결 금지.",
    ],
    "ot_narrative": [
        "인물 영웅화 금지 — 아브라함·모세·다윗을 도덕 모범으로 제시하지 마십시오.",
        "구속사 경유 없이 역사 사건 → 현대 적용 직결 금지.",
        "신약과의 연결이 본문 자체의 논리에서 나와야 합니다.",
    ],
    "prophetic": [
        "예언 = 현대 사건 예측으로 연결하지 마십시오.",
        "묵시 상징의 과도한 현대화 금지.",
    ],
    "law_ritual": [
        "율법 직접 적용 금지 — 그리스도 안에서의 성취 경유 필수.",
        "의식법을 현대 생활로 직결하지 마십시오.",
    ],
}


def generate_recipe(passage_data: dict, output_dir: Path) -> Path:
    book_korean = passage_data.get("book_korean", "")
    passage = passage_data.get("passage", "")
    context = passage_data.get("context_range", "")
    genre = passage_data.get("genre", "gospel")
    subgenre = passage_data.get("subgenre", "")
    theme_hint = passage_data.get("theme_hint", "")
    today = datetime.now().strftime("%Y-%m-%d")

    priority_list = GENRE_PRIORITY.get(genre, GENRE_PRIORITY["gospel"])
    cautions = GENRE_CAUTIONS.get(genre, [])

    lines = [
        f"# Logos 연구 레시피 — {book_korean} {passage}",
        "",
        f"**생성일**: {today}  ",
        f"**본문**: {book_korean} {context}  ",
        f"**장르**: {genre}",
        f"**하위장르**: {subgenre}" if subgenre else "",
        f"**테마 힌트**: {theme_hint}" if theme_hint else "",
        "",
        "> 이 레시피대로 Logos를 순서대로 사용한 뒤,",
        "> 각 도구에서 캡처한 내용을 `tmp/logos-capture/raw/` 에 저장하십시오.",
        "",
        "---",
        "",
        "## Logos 도구 사용 순서",
        "",
        "| 순서 | 자료군 | 사용 도구 |",
        "|-----|--------|---------|",
    ]

    for i, (cat_id, label, tools) in enumerate(priority_list, 1):
        lines.append(f"| {i} | {label} | {tools} |")

    lines += [
        "",
        "---",
        "",
        "## 각 도구별 세부 지시",
        "",
    ]

    for i, (cat_id, label, tools) in enumerate(priority_list, 1):
        lines += [
            f"### {i}. {label}",
            f"**도구**: {tools}  ",
            f"**캡처 파일명**: `tmp/logos-capture/raw/{passage_data.get('book_slug', 'book')}-"
            f"{passage_data.get('passage_slug', 'pass')}-{label.replace('·', '-').replace(' ', '-').lower()}-"
            f"{today[:10].replace('-', '')}.md`",
            "",
        ]

    lines += [
        "---",
        "",
        "## 장르별 설교 주의사항",
        "",
    ]
    for c in cautions:
        lines.append(f"- ⚠️ {c}")

    lines += [
        "",
        "---",
        "",
        "## 캡처 완료 후 다음 단계",
        "",
        "```powershell",
        f"python scripts/audit_logos_coverage.py --passage {output_dir / '00-passage.yaml'}",
        "```",
        "",
        "> Logos Coverage Score가 75점 이상이면 심층 연구로 진행합니다.",
    ]

    recipe_path = output_dir / "01-logos-recipe.md"
    recipe_path.write_text("\n".join(l for l in lines if l is not None), encoding="utf-8")
    return recipe_path


def generate_checklist(passage_data: dict, output_dir: Path) -> Path:
    book_korean = passage_data.get("book_korean", "")
    passage = passage_data.get("passage", "")
    context = passage_data.get("context_range", "")
    genre = passage_data.get("genre", "gospel")
    today = datetime.now().strftime("%Y-%m-%d")

    lines = [
        f"# Logos 캡처 체크리스트 — {book_korean} {passage}",
        "",
        f"**본문**: {book_korean} {context}  ",
        f"**장르**: {genre}  ",
        f"**생성일**: {today}",
        "",
        "> 아래 항목을 Logos에서 순서대로 실행하십시오.",
        "> 각 항목 완료 후 `[x]`로 표시하고, 캡처 파일명을 기록하십시오.",
        "",
        "---",
        "",
        "## 필수 캡처 (모든 항목 완료 후 다음 단계 진행)",
        "",
        "- [ ] **C-01** 본문 범위 확정 (Passage Guide)",
        "  - 캡처 파일: ___",
        "  - 확정 범위: ___",
        "",
        "- [ ] **C-02** 번역 비교 (Text Comparison)",
        "  - 캡처 파일: ___",
        "  - 비교 번역본: ___",
        "",
        "- [ ] **C-03** 원어 핵심 단어 (Exegetical Guide / Bible Word Study)",
        "  - 캡처 파일: ___",
        "  - 확인한 단어: ___",
        "",
        "- [ ] **C-04** 교차본문 (Cross References)",
        "  - 캡처 파일: ___",
        "  - 선택한 교차본문 수: ___",
        "",
        "- [ ] **C-05** 주석 비교 (Commentaries)",
        "  - 캡처 파일: ___",
        "  - 확인한 주석: ___",
        "",
        "---",
        "",
        "## 권장 캡처 (장르: {})".format(genre),
        "",
    ]

    genre_recommended = {
        "gospel": [
            ("C-06", "구조·담화 분석 (Passage Analysis)"),
            ("C-07", "역사·문화 배경 (Factbook)"),
            ("C-08", "성경신학 테마 (Biblical Theology)"),
            ("C-09", "설교 자료 (Sermon Starter Guide)"),
        ],
        "epistle": [
            ("C-06", "구조·담화 (Clause Search — indicative/imperative)"),
            ("C-08", "성경신학 테마 (Biblical Theology)"),
            ("C-09", "설교 자료 (Sermon Starter Guide)"),
        ],
        "psalm_wisdom": [
            ("C-06", "구조·담화 (병행법·키아즘 분석)"),
            ("C-07", "역사·문화 배경 (성전 예배 맥락)"),
            ("C-08", "성경신학 테마"),
        ],
        "ot_narrative": [
            ("C-06", "구조·담화 (장면·인물·플롯)"),
            ("C-07", "역사·문화 배경 (Factbook + Atlas)"),
            ("C-08", "성경신학 테마"),
        ],
        "prophetic": [
            ("C-07", "역사·문화 배경 (왕·시대·정치 상황)"),
            ("C-08", "성경신학 테마"),
        ],
        "law_ritual": [
            ("C-07", "역사·문화 배경 (제사·정결 의식)"),
            ("C-08", "성경신학 테마 (그림자/실체)"),
        ],
    }

    for cid, title in genre_recommended.get(genre, []):
        lines += [
            f"- [ ] **{cid}** {title}",
            "  - 캡처 파일: ___",
            "",
        ]

    lines += [
        "---",
        "",
        "## 캡처 파일 명명 규칙",
        "",
        "```",
        f"tmp/logos-capture/raw/{{book-slug}}-{{passage-slug}}-{{tool}}-{{YYYYMMDD}}.md",
        "",
        "예시:",
        f"  tmp/logos-capture/raw/{passage_data.get('book_slug', 'book')}-"
        f"{passage_data.get('passage_slug', 'pass')}-passage-guide-{today[:10].replace('-', '')}.md",
        f"  tmp/logos-capture/raw/{passage_data.get('book_slug', 'book')}-"
        f"{passage_data.get('passage_slug', 'pass')}-word-study-{today[:10].replace('-', '')}.md",
        "```",
        "",
        "---",
        "",
        "## 모든 필수 항목 완료 후",
        "",
        "```powershell",
        f"python scripts/audit_logos_coverage.py --passage {output_dir / '00-passage.yaml'}",
        "```",
    ]

    checklist_path = output_dir / "02-logos-capture-checklist.md"
    checklist_path.write_text("\n".join(lines), encoding="utf-8")
    return checklist_path


def main() -> int:
    args = parse_args()
    passage_path = Path(args.passage)

    if not passage_path.exists():
        print(f"[ERROR] passage.yaml을 찾을 수 없습니다: {passage_path}", file=sys.stderr)
        print("  먼저 실행하십시오: python scripts/create_passage.py ...", file=sys.stderr)
        return 1

    passage_data = load_yaml(passage_path)
    output_dir = Path(args.output_dir) if args.output_dir else passage_path.parent

    recipe_path = generate_recipe(passage_data, output_dir)
    checklist_path = generate_checklist(passage_data, output_dir)

    book_korean = passage_data.get("book_korean", "")
    passage = passage_data.get("passage", "")
    print(f"✅ 레시피 생성: {recipe_path}")
    print(f"✅ 체크리스트 생성: {checklist_path}")
    print()
    print(f"다음 단계:")
    print(f"  1. {checklist_path} 를 열어 Logos에서 순서대로 캡처하십시오.")
    print(f"  2. 캡처 파일을 tmp/logos-capture/raw/ 에 저장하십시오.")
    print(f"  3. python scripts/audit_logos_coverage.py --passage {passage_path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
