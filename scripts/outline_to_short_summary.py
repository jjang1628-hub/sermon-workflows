from __future__ import annotations

import argparse
import re
from pathlib import Path

from research_support import load_research, review_memo


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def clean_line(line: str) -> str:
    return re.sub(r"\s+", " ", line.strip())


def find_title(lines: list[str], fallback: str) -> str:
    for line in lines:
        stripped = clean_line(line)
        if stripped.startswith("#"):
            return stripped.lstrip("#").strip()
    return fallback


def find_scripture(lines: list[str]) -> str:
    for line in lines:
        stripped = clean_line(line).lstrip("#").strip()
        if stripped.startswith("본문:") or stripped.startswith("본문 :"):
            return stripped.split(":", 1)[1].strip()
    return "본문 보완 필요"


def find_main_idea(lines: list[str]) -> str:
    in_section = False
    for line in lines:
        stripped = clean_line(line)
        if stripped.startswith("## ") and "메인 아이디어" in stripped:
            in_section = True
            continue
        if in_section and stripped.startswith("## "):
            break
        if in_section and stripped:
            return stripped.strip("*")
    return "신앙은 다시 나는 데서 시작됩니다."


def find_sub_ideas(lines: list[str]) -> list[str]:
    ideas: list[str] = []
    in_section = False
    for line in lines:
        stripped = clean_line(line)
        if stripped.startswith("## ") and "서브 아이디어" in stripped:
            in_section = True
            continue
        if in_section and stripped.startswith("## "):
            break
        if in_section and re.match(r"^\d+\.\s+", stripped):
            ideas.append(re.sub(r"^\d+\.\s*", "", stripped).strip("*"))
    return ideas[:3]


def render_markdown(
    title: str,
    scripture: str,
    big_idea: str,
    sub_ideas: list[str],
    research_path: Path | None = None,
) -> str:
    bullets = "\n".join(f"- {idea}" for idea in sub_ideas)
    if not bullets:
        bullets = "- 종교적 익숙함은 새 생명을 대신하지 못합니다.\n- 새 생명은 성령이 일으키시는 것입니다.\n- 들리신 인자를 믿을 때 영생이 시작됩니다."

    extra = ""
    if research_path is not None:
        research = load_research(research_path)
        apps = research.get("applications", [])[:2]
        if apps:
            app_lines = "\n".join(f"- {a}" for a in apps)
            extra = f"\n## 적용 참고 (Logos)\n\n{app_lines}\n"
        extra += review_memo(research_path)

    return f"""# 짧은 사역 요약

## 기본 정보

- 제목: {title}
- 본문: {scripture}

## 한 문장 요약

- {big_idea}

## 핵심 정리

{bullets}

## 전달 메모

- 이 요약은 설교 원고를 바탕으로 만든 짧은 사역용 초안입니다.
- 생성된 내용은 최종 신학 판단이나 최종 목회 자료가 아닙니다.
{extra}"""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="설교 개요 Markdown 파일을 짧은 사역 요약 Markdown으로 변환합니다."
    )
    parser.add_argument("--input", required=True, help="입력 Markdown 파일 경로")
    parser.add_argument("--output", required=True, help="출력 Markdown 파일 경로")
    parser.add_argument("--research", default=None, help="Logos 연구 파일 경로 (선택)")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    input_path = Path(args.input)
    output_path = Path(args.output)
    research_path = Path(args.research) if args.research else None

    if not input_path.exists():
        raise FileNotFoundError(f"입력 파일을 찾을 수 없습니다: {input_path}")
    if research_path is not None and not research_path.exists():
        raise FileNotFoundError(f"연구 파일을 찾을 수 없습니다: {research_path}")

    lines = read_text(input_path).splitlines()
    title = find_title(lines, fallback=input_path.stem)
    scripture = find_scripture(lines)
    big_idea = find_main_idea(lines)
    sub_ideas = find_sub_ideas(lines)
    rendered = render_markdown(
        title=title, scripture=scripture, big_idea=big_idea,
        sub_ideas=sub_ideas, research_path=research_path,
    )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(rendered, encoding="utf-8")

    print(f"생성 완료: {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
