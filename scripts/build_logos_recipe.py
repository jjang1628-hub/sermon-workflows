"""
build_logos_recipe.py - Logos research recipe and capture checklist builder.

Reads docs/{book}/{passage}/00-passage.yaml and writes:
- 01-logos-recipe.md
- 02-logos-capture-checklist.md

No external YAML dependency is required.
"""

from __future__ import annotations

import argparse
import shutil
import sys
from datetime import datetime
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")


CATEGORY_TOOLS = {
    "text_establishment": ("본문 확정", "Passage Guide, Bible panel, Text Comparison"),
    "translation_comparison": ("번역 비교", "Text Comparison"),
    "original_language": ("원어·문법", "Exegetical Guide, Bible Word Study, Interlinear"),
    "structure_discourse": ("구조·담화", "Passage Analysis, Clause Search, Discourse resources"),
    "cross_references": ("교차본문", "Cross References, Important Passages, Treasury of Scripture Knowledge"),
    "commentaries": ("주석 비교", "Passage Guide > Commentaries"),
    "biblical_theology": ("성경신학", "Factbook themes, Biblical Theology resources"),
    "systematic_theology": ("조직신학", "Theology Guide, Systematic Theology resources"),
    "background": ("역사·문화 배경", "Factbook, Bible Dictionaries, Atlas"),
    "sermon_homiletics": ("설교 자료", "Sermon Starter Guide, Sermon Builder"),
    "application_pastoral": ("목회·적용", "Pastoral theology, counseling resources, notes"),
    "media_teaching": ("시각·교육 자료", "Media, Visual Copy, Atlas images"),
}


GENRE_RECIPES = {
    "gospel": [
        "text_establishment", "translation_comparison", "original_language",
        "structure_discourse", "cross_references", "commentaries",
        "biblical_theology", "background", "application_pastoral",
    ],
    "gospel_farewell_discourse": [
        "text_establishment", "translation_comparison", "structure_discourse",
        "original_language", "cross_references", "commentaries",
        "biblical_theology", "application_pastoral", "background",
    ],
    "gospel_symbolic_action": [
        "text_establishment", "structure_discourse", "original_language",
        "background", "biblical_theology", "commentaries", "application_pastoral",
    ],
    "gospel_discipleship": [
        "text_establishment", "structure_discourse", "cross_references",
        "biblical_theology", "application_pastoral", "commentaries",
    ],
    "gospel_parable": [
        "text_establishment", "structure_discourse", "background",
        "commentaries", "biblical_theology", "application_pastoral",
    ],
    "gospel_miracle": [
        "text_establishment", "structure_discourse", "cross_references",
        "commentaries", "biblical_theology", "background",
    ],
    "epistle": [
        "text_establishment", "translation_comparison", "structure_discourse",
        "original_language", "commentaries", "cross_references",
        "systematic_theology", "biblical_theology", "application_pastoral",
    ],
    "epistle_doctrinal": [
        "text_establishment", "structure_discourse", "original_language",
        "commentaries", "systematic_theology", "biblical_theology",
    ],
    "epistle_exhortation": [
        "text_establishment", "structure_discourse", "original_language",
        "application_pastoral", "commentaries", "biblical_theology",
    ],
    "torah_law": [
        "text_establishment", "background", "original_language",
        "cross_references", "biblical_theology", "commentaries",
    ],
    "torah_narrative": [
        "text_establishment", "structure_discourse", "background",
        "cross_references", "biblical_theology", "commentaries",
    ],
    "psalm_lament": [
        "text_establishment", "structure_discourse", "original_language",
        "cross_references", "biblical_theology", "commentaries",
    ],
    "psalm_praise": [
        "text_establishment", "structure_discourse", "original_language",
        "biblical_theology", "commentaries",
    ],
    "prophetic_judgment": [
        "text_establishment", "background", "structure_discourse",
        "cross_references", "commentaries", "biblical_theology",
    ],
    "prophetic_restoration": [
        "text_establishment", "background", "cross_references",
        "commentaries", "biblical_theology", "application_pastoral",
    ],
}


GENRE_EMPHASIS = {
    "gospel_farewell_discourse": [
        "고별 담화 전체 흐름",
        "제자 공동체 형성",
        "십자가 전 문맥",
        "사랑과 순종의 관계",
        "그리스도의 낮아지심",
    ],
    "gospel_symbolic_action": [
        "상징 행위와 십자가 연결",
        "행위가 설명되는 문맥",
        "과도한 알레고리 경계",
    ],
    "gospel_discipleship": [
        "명령 이전의 은혜",
        "제자 공동체의 삶",
        "도덕주의 위험 점검",
    ],
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build Logos research recipe and checklist.")
    parser.add_argument("--passage", required=True, help="Path to 00-passage.yaml")
    parser.add_argument("--output-dir", default=None, help="Output directory")
    return parser.parse_args()


def load_yaml_simple(path: Path) -> dict[str, str]:
    data: dict[str, str] = {}
    current_key = ""
    list_values: list[str] = []
    for raw_line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        stripped = raw_line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if current_key and stripped.startswith("-"):
            list_values.append(stripped.lstrip("- ").strip().strip('"'))
            data[current_key] = ", ".join(list_values)
            continue
        current_key = ""
        list_values = []
        if ":" in stripped:
            key, value = stripped.split(":", 1)
            key = key.strip()
            value = value.strip().strip('"')
            if value:
                data[key] = value
            else:
                current_key = key
                data[key] = ""
    return data


def recipe_for_genre(genre: str) -> list[str]:
    return GENRE_RECIPES.get(genre, GENRE_RECIPES["gospel"])


def make_capture_filename(data: dict[str, str], category_key: str) -> str:
    book_slug = data.get("book_slug", "book")
    passage_slug = data.get("passage_slug", "passage")
    date = datetime.now().strftime("%Y%m%d")
    return f"tmp/logos-capture/raw/{book_slug}-{passage_slug}-{category_key}-{date}.md"


def generate_recipe(data: dict[str, str], output_dir: Path) -> Path:
    book_korean = data.get("book_korean", "")
    passage = data.get("passage", "")
    context = data.get("context_range", "")
    genre = data.get("genre", "gospel")
    secondary = data.get("secondary_genres", "")
    theme = data.get("theme_hint", "")
    categories = recipe_for_genre(genre)

    lines = [
        f"# Logos 연구 레시피 - {book_korean} {passage}",
        "",
        f"- 본문: {book_korean} {context}",
        f"- 장르: `{genre}`",
        f"- 보조 장르: {secondary or '없음'}",
        f"- 주제 힌트: {theme or '없음'}",
        "",
        "이 레시피의 목적은 AI가 먼저 설교하지 못하게 하고, Logos 자료를 먼저 충분히 보게 만드는 것입니다.",
        "",
        "## 장르 핵심 강조점",
        "",
    ]
    emphasis = GENRE_EMPHASIS.get(genre, ["본문 문맥", "주석 비교", "정경 연결", "복음적 적용"])
    lines += [f"- {item}" for item in emphasis]

    lines += [
        "",
        "## Logos 도구 사용 순서",
        "",
        "| 순서 | 자료군 | Logos 도구 | 캡처 파일 제안 |",
        "|---:|---|---|---|",
    ]
    for index, category_key in enumerate(categories, 1):
        label, tools = CATEGORY_TOOLS[category_key]
        lines.append(
            f"| {index} | {label} | {tools} | `{make_capture_filename(data, category_key)}` |"
        )

    lines += [
        "",
        "## 다음 단계",
        "",
        "1. 아래 체크리스트 파일을 열고 Logos에서 자료를 캡처하십시오.",
        "2. 캡처 파일은 `tmp/logos-capture/raw/`에 저장하십시오.",
        "3. Coverage audit과 Capture quality audit을 실행하십시오.",
        "",
        "```powershell",
        f"python scripts/run_logos_max.py --passage {output_dir / '00-passage.yaml'} --step audit",
        "```",
    ]
    path = output_dir / "01-logos-recipe.md"
    tmp = path.with_suffix(".tmp")
    tmp.write_text("\n".join(lines), encoding="utf-8")
    if path.exists():
        shutil.copy2(path, path.with_suffix(".bak"))
    shutil.move(str(tmp), str(path))
    return path


def generate_checklist(data: dict[str, str], output_dir: Path) -> Path:
    book_korean = data.get("book_korean", "")
    passage = data.get("passage", "")
    context = data.get("context_range", "")
    genre = data.get("genre", "gospel")
    categories = recipe_for_genre(genre)

    lines = [
        f"# Logos 캡처 체크리스트 - {book_korean} {passage}",
        "",
        f"- 본문: {book_korean} {context}",
        f"- 장르: `{genre}`",
        "",
        "체크리스트는 설교문을 빨리 만들기 위한 것이 아니라, 본문 아래 충분히 머물기 위한 장치입니다.",
        "",
        "## 필수/권장 캡처",
        "",
    ]
    for index, category_key in enumerate(categories, 1):
        label, tools = CATEGORY_TOOLS[category_key]
        lines += [
            f"### {index}. {label}",
            f"- [ ] Logos 도구: {tools}",
            f"- [ ] 캡처 파일: `{make_capture_filename(data, category_key)}`",
            "- [ ] 본문 이해에 실제로 기여하는 요약 또는 메모 포함",
            "",
        ]

    lines += [
        "## 완료 후 실행",
        "",
        "```powershell",
        f"python scripts/audit_logos_coverage.py --passage {output_dir / '00-passage.yaml'}",
        f"python scripts/audit_capture_quality.py --passage {output_dir / '00-passage.yaml'}",
        f"python scripts/gate_deep_research.py --passage {output_dir / '00-passage.yaml'}",
        "```",
    ]
    path = output_dir / "02-logos-capture-checklist.md"
    tmp = path.with_suffix(".tmp")
    tmp.write_text("\n".join(lines), encoding="utf-8")
    if path.exists():
        shutil.copy2(path, path.with_suffix(".bak"))
    shutil.move(str(tmp), str(path))
    return path


def main() -> int:
    args = parse_args()
    passage_path = Path(args.passage)
    if not passage_path.exists():
        print(f"[ERROR] passage.yaml 없음: {passage_path}", file=sys.stderr)
        return 1

    data = load_yaml_simple(passage_path)
    output_dir = Path(args.output_dir) if args.output_dir else passage_path.parent
    output_dir.mkdir(parents=True, exist_ok=True)

    recipe_path = generate_recipe(data, output_dir)
    checklist_path = generate_checklist(data, output_dir)

    print(f"레시피 생성: {recipe_path}")
    print(f"체크리스트 생성: {checklist_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
