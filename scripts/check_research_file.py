from __future__ import annotations

import argparse
from pathlib import Path


REQUIRED_SECTIONS = [
    "## 기본 정보",
    "## 빠른 검토",
    "## 관찰 후보",
    "## 해석 참고 후보",
    "## 적용 아이디어 후보",
    "## 검토 필요",
    "## 정리된 원문",
]


def count_bullets_in_section(text: str, heading: str) -> int:
    lines = text.splitlines()
    in_section = False
    count = 0
    for line in lines:
        stripped = line.strip()
        if stripped == heading:
            in_section = True
            continue
        if in_section and stripped.startswith("## "):
            break
        if in_section and stripped.startswith("- "):
            count += 1
    return count


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="연구 파일이 워크플로 입력 형식을 만족하는지 점검합니다.")
    parser.add_argument("--input", required=True, help="검사할 연구 Markdown 파일")
    parser.add_argument("--min-bullets", type=int, default=5, help="후보 섹션별 최소 bullet 개수")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    input_path = Path(args.input)
    if not input_path.exists():
        raise FileNotFoundError(f"연구 파일을 찾을 수 없습니다: {input_path}")

    text = input_path.read_text(encoding="utf-8")
    failures: list[str] = []

    for section in REQUIRED_SECTIONS:
        if section not in text:
            failures.append(f"필수 섹션 없음: {section}")

    for section in ["## 관찰 후보", "## 해석 참고 후보", "## 적용 아이디어 후보"]:
        count = count_bullets_in_section(text, section)
        if count < args.min_bullets:
            failures.append(f"{section} bullet 부족: {count}개, 최소 {args.min_bullets}개")

    if "최종 해석이 아닙니다" not in text:
        failures.append("안전 문구 없음: '최종 해석이 아닙니다'")

    if failures:
        print("연구 파일 점검 실패")
        for failure in failures:
            print(f"- {failure}")
        return 1

    print("연구 파일 점검 통과")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
