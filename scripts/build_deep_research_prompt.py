from __future__ import annotations

import argparse
import re
from datetime import datetime
from pathlib import Path


DEFAULT_TEMPLATE = Path("templates/deep_research_prompt_template.md")
DEFAULT_PROMPT_DIR = Path("tmp/prompts")


BOOK_SLUGS = {
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
}


def slugify(passage: str) -> str:
    slug = passage
    for korean, abbr in BOOK_SLUGS.items():
        if korean in passage:
            slug = passage.replace(korean, abbr)
            break
    slug = re.sub(r"[:\s]+", "-", slug)
    slug = re.sub(r"[^a-zA-Z0-9\-]", "", slug)
    return slug.strip("-").lower() or "passage"


def read_optional(path: Path | None, label: str) -> str:
    if path is None:
        return f"(제공된 {label} 없음)"
    if not path.exists():
        raise FileNotFoundError(f"{label} 파일을 찾을 수 없습니다: {path}")
    return path.read_text(encoding="utf-8").strip()


def render_prompt(
    template: str,
    passage: str,
    outline_text: str,
    logos_capture_text: str,
    existing_research_text: str,
) -> str:
    replacements = {
        "{{passage}}": passage,
        "{{timestamp}}": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "{{outline_text}}": outline_text,
        "{{logos_capture_text}}": logos_capture_text,
        "{{existing_research_text}}": existing_research_text,
    }
    rendered = template
    for key, value in replacements.items():
        rendered = rendered.replace(key, value)
    return rendered


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="GPT/Claude 프롬프터에 넣을 설교 본문 심층 연구 프롬프트를 생성합니다."
    )
    parser.add_argument("--passage", required=True, help="연구할 본문. 예: 요한복음 13:14")
    parser.add_argument("--outline", default=None, help="설교 개요 Markdown 파일")
    parser.add_argument("--logos-capture", default=None, help="Logos 원본 캡처 Markdown 파일")
    parser.add_argument("--existing-research", default=None, help="기존 연구 Markdown 파일")
    parser.add_argument("--template", default=str(DEFAULT_TEMPLATE), help="프롬프트 템플릿 경로")
    parser.add_argument("--output", default=None, help="생성할 프롬프트 파일 경로")
    parser.add_argument("--force", action="store_true", help="기존 출력 파일 덮어쓰기")
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    template_path = Path(args.template)
    if not template_path.exists():
        raise FileNotFoundError(f"프롬프트 템플릿을 찾을 수 없습니다: {template_path}")

    slug = slugify(args.passage)
    output_path = Path(args.output) if args.output else DEFAULT_PROMPT_DIR / f"{slug}-deep-research-prompt.md"

    if output_path.exists() and not args.force:
        raise FileExistsError(f"출력 파일이 이미 있습니다. 덮어쓰려면 --force를 사용하세요: {output_path}")

    prompt = render_prompt(
        template=template_path.read_text(encoding="utf-8"),
        passage=args.passage,
        outline_text=read_optional(Path(args.outline) if args.outline else None, "설교 개요"),
        logos_capture_text=read_optional(Path(args.logos_capture) if args.logos_capture else None, "Logos 캡처"),
        existing_research_text=read_optional(
            Path(args.existing_research) if args.existing_research else None,
            "기존 연구",
        ),
    )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(prompt, encoding="utf-8")
    print(f"심층 연구 프롬프트 생성: {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
