from __future__ import annotations

import argparse
import re
from pathlib import Path

from research_support import augment_questions, load_research, review_memo


POINT_PREFIXES = ("-", "*", "+")
SCRIPTURE_LABELS = ("본문", "성경본문", "성구", "말씀")


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def clean_line(line: str) -> str:
    return re.sub(r"\s+", " ", line.strip())


def extract_title(lines: list[str], fallback: str) -> str:
    # 1순위: "- 제목:" 불릿 형식
    for line in lines:
        stripped = clean_line(line).lstrip("-*+# ").strip()
        if stripped.startswith("제목:") or stripped.startswith("제목 :"):
            return stripped.split(":", 1)[1].strip()
    # 2순위: 첫 번째 h1 이후 h2
    seen_h1 = False
    for line in lines:
        stripped = clean_line(line)
        if stripped.startswith("# ") and not seen_h1:
            seen_h1 = True
            continue
        if stripped.startswith("## "):
            return stripped.lstrip("#").strip()
    return fallback


def extract_scripture(lines: list[str]) -> str:
    # 불릿·heading 접두사 모두 제거 후 본문 레이블 매칭
    for raw_line in lines:
        line = clean_line(raw_line).lstrip("-*+# ").strip()
        if not line:
            continue
        for label in SCRIPTURE_LABELS:
            if line.startswith(f"{label}:") or line.startswith(f"{label} :"):
                return line.split(":", 1)[1].strip()

    return "본문을 확인해 직접 보완해 주세요."


def is_point_line(line: str) -> bool:
    stripped = line.lstrip()
    if not stripped:
        return False
    if stripped.startswith(POINT_PREFIXES):
        return True
    return bool(re.match(r"^(\d+[\.\)]|[가-힣A-Za-z][\.\)])\s+", stripped))


def normalize_point(line: str) -> str:
    stripped = line.strip()
    stripped = re.sub(r"^[-*+]\s*", "", stripped)
    stripped = re.sub(r"^(\d+[\.\)]|[가-힣A-Za-z][\.\)])\s*", "", stripped)
    return clean_line(stripped)


def heading_text(line: str) -> str:
    stripped = line.strip()
    if not stripped.startswith("#"):
        return ""
    return stripped.lstrip("#").strip()


def is_outline_section(name: str) -> bool:
    return any(keyword in name for keyword in ("설교", "개요", "핵심", "대지", "서브 아이디어"))


def extract_points(lines: list[str]) -> list[str]:
    scoped_points: list[str] = []
    fallback_points: list[str] = []
    current_heading = ""

    for raw_line in lines:
        next_heading = heading_text(raw_line)
        if next_heading:
            current_heading = next_heading
            continue

        if not is_point_line(raw_line):
            continue

        point = normalize_point(raw_line)
        if not point:
            continue

        fallback_points.append(point)
        if is_outline_section(current_heading):
            scoped_points.append(point)

    points = scoped_points or fallback_points

    unique_points: list[str] = []
    seen: set[str] = set()
    for point in points:
        if point not in seen:
            seen.add(point)
            unique_points.append(point)

    return unique_points[:4]


def build_observation_questions(points: list[str]) -> list[str]:
    if not points:
        return [
            "본문에서 반복되거나 강조되는 표현은 무엇인가요?",
            "예수님이 니고데모에게 먼저 짚으시는 문제는 무엇인가요?",
        ]

    return [f"'{point}'와 연결되는 본문 관찰은 무엇인가요?" for point in points]


def build_interpretation_questions(points: list[str]) -> list[str]:
    if not points:
        return [
            "이 본문이 우리에게 말하는 새 생명의 핵심은 무엇인가요?",
            "왜 예수님은 니고데모의 종교적 익숙함을 먼저 흔드셨을까요?",
        ]

    return [f"'{point}'가 왜 중요한지 본문 흐름 안에서 설명해 보세요." for point in points]


def build_application_questions(points: list[str]) -> list[str]:
    if not points:
        return [
            "내가 신앙의 익숙함으로 대신하고 있는 부분은 무엇인가요?",
            "이번 주에 성령의 역사에 더 의지하기 위해 바꿀 한 가지는 무엇인가요?",
        ]

    return [f"'{point}'를 이번 주 삶에 적용한다면 어떤 행동 변화가 필요할까요?" for point in points]


def render_markdown(
    title: str,
    scripture: str,
    points: list[str],
    research_path: Path | None = None,
) -> str:
    point_lines = "\n".join(f"- {point}" for point in points)
    if not point_lines:
        point_lines = "- 설교 개요의 핵심 포인트를 직접 보완해 주세요."

    obs_questions = build_observation_questions(points)
    int_questions = build_interpretation_questions(points)
    app_questions = build_application_questions(points)

    if research_path is not None:
        research = load_research(research_path)
        obs_questions = augment_questions(obs_questions, research.get("observations", []))
        int_questions = augment_questions(int_questions, research.get("interpretations", []))
        app_questions = augment_questions(app_questions, research.get("applications", []))

    observation_lines = "\n".join(f"1. {q}" for q in obs_questions)
    interpretation_lines = "\n".join(f"1. {q}" for q in int_questions)
    application_lines = "\n".join(f"1. {q}" for q in app_questions)

    extra = review_memo(research_path) if research_path is not None else ""

    return f"""# 목장 나눔지 초안

## 기본 정보

- 제목: {title}
- 본문: {scripture}

## 설교 핵심 정리

{point_lines}

## 나눔 질문

### 1. 관찰

{observation_lines}

### 2. 해석

{interpretation_lines}

### 3. 적용

{application_lines}
1. 이번 주에 한 가지 실천으로 정한다면 무엇을 하시겠습니까?

## 함께 기도하기

- 종교적 익숙함보다 새 생명을 구하게 해 달라고 기도합니다.
- 성령으로 다시 나게 하시고, 들리신 인자를 믿는 믿음 안에 서게 해 달라고 기도합니다.

## 인도자 메모

- 자동 생성된 초안이므로 본문 의도와 설교 흐름에 맞게 반드시 검토해 주세요.
- 생성된 내용은 최종 신학 판단이나 최종 목회 자료가 아닙니다.
{extra}"""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="설교 개요 Markdown 파일을 목장 나눔지 Markdown 초안으로 변환합니다."
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

    text = read_text(input_path)
    lines = text.splitlines()

    title = extract_title(lines, fallback=input_path.stem)
    scripture = extract_scripture(lines)
    points = extract_points(lines)
    rendered = render_markdown(title=title, scripture=scripture, points=points, research_path=research_path)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(rendered, encoding="utf-8")

    print(f"생성 완료: {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
