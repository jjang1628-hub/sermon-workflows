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
    # 1순위: "- 제목:" 불릿 형식 (예: "- 제목: 주님처럼 씻기라")
    for line in lines:
        stripped = clean_line(line).lstrip("-*+# ").strip()
        if stripped.startswith("제목:") or stripped.startswith("제목 :"):
            return stripped.split(":", 1)[1].strip()
    # 2순위: 첫 번째 h1 이후 h2 제목 (섹션명 건너뜀)
    seen_h1 = False
    for line in lines:
        stripped = clean_line(line)
        if stripped.startswith("# ") and not seen_h1:
            seen_h1 = True
            continue
        if stripped.startswith("## "):
            return stripped.lstrip("#").strip()
    return fallback


def find_scripture(lines: list[str]) -> str:
    # 불릿(-  * +) 및 heading(#) 접두사를 모두 제거 후 "본문:" 패턴 매칭
    for line in lines:
        stripped = clean_line(line).lstrip("-*+# ").strip()
        if stripped.startswith("본문:") or stripped.startswith("본문 :"):
            return stripped.split(":", 1)[1].strip()
    return "본문 보완 필요"


def find_main_idea(lines: list[str]) -> str:
    # 1순위: "- 메인 아이디어:" 불릿 형식
    for line in lines:
        stripped = clean_line(line).lstrip("-*+# ").strip()
        if stripped.startswith("메인 아이디어:") or stripped.startswith("메인아이디어:"):
            return stripped.split(":", 1)[1].strip()
    # 2순위: "## 메인 아이디어" 섹션 아래 첫 문장
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
    return ""


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
    movements = sub_ideas or ["(서브 아이디어를 개요에 추가해 주세요.)"]

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
            "- 적용: (적용 문장을 직접 작성해 주세요.)",
            "",
            f"## 슬라이드 {next_slide + 1}",
            "- 결론: (결론 문장을 직접 작성해 주세요.)",
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
