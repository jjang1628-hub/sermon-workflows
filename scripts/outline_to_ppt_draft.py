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
    return ideas[:4]


def render_markdown(
    title: str,
    scripture: str,
    big_idea: str,
    sub_ideas: list[str],
    research_path: Path | None = None,
) -> str:
    movements = sub_ideas or [
        "종교적 익숙함은 새 생명을 대신하지 못합니다.",
        "새 생명은 성령이 일으키시는 하나님의 역사입니다.",
        "들리신 인자를 믿을 때 영생이 시작됩니다.",
    ]

    lines = [
        "# PPT 초안",
        "",
        "## 슬라이드 1",
        f"- 제목: {title}",
        "",
        "## 슬라이드 2",
        f"- 본문: {scripture}",
        "",
        "## 슬라이드 3",
        f"- 메인 문장: {big_idea}",
        "",
    ]

    for index, movement in enumerate(movements, start=4):
        lines.extend(
            [
                f"## 슬라이드 {index}",
                f"- 전개 문장: {movement}",
                "",
            ]
        )

    next_slide = len(movements) + 4
    lines.extend(
        [
            f"## 슬라이드 {next_slide}",
            "- 적용: 종교적 익숙함이 아니라 성령의 새 하심을 구합시다.",
            "",
            f"## 슬라이드 {next_slide + 1}",
            "- 결론: 다시 남은 들리신 인자 예수를 믿을 때 시작됩니다.",
            "",
            "## 작성 메모",
            "- 한 슬라이드에 한 문장 원칙으로 유지해 주세요.",
            "- 이 초안은 시각 디자인이 아니라 발표용 문장 초안입니다.",
            "- 생성된 내용은 최종 신학 판단이나 최종 목회 자료가 아닙니다.",
        ]
    )

    if research_path is not None:
        research = load_research(research_path)
        notes = research.get("interpretations", [])[:3]
        if notes:
            lines.append("")
            lines.append("## 배경 설명 메모 (Logos 참고)")
            for note in notes:
                lines.append(f"- {note}")
        lines.append(review_memo(research_path))

    return "\n".join(lines) + "\n"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="설교 개요 Markdown 파일을 PPT 초안 Markdown으로 변환합니다."
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
