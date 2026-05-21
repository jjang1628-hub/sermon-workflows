from __future__ import annotations

import re
from pathlib import Path


def _extract_section(text: str, heading: str) -> list[str]:
    """마크다운에서 특정 ## 섹션의 bullet 항목을 추출합니다."""
    lines = text.splitlines()
    in_section = False
    items: list[str] = []
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("## ") and heading in stripped:
            in_section = True
            continue
        if in_section and stripped.startswith("## "):
            break
        if in_section and stripped.startswith("- ") and stripped != "- (자동 분류 결과 없음)":
            items.append(stripped[2:].strip())
    return items


def load_research(path: Path) -> dict[str, list[str]]:
    """정규화된 연구 파일을 읽어 섹션별 항목 딕셔너리를 반환합니다.

    반환 키: "observations", "interpretations", "applications"
    파일이 없거나 읽기에 실패하면 빈 딕셔너리를 반환합니다.
    """
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return {}

    return {
        "observations": _extract_section(text, "관찰 후보"),
        "interpretations": _extract_section(text, "해석 참고 후보"),
        "applications": _extract_section(text, "적용 아이디어 후보"),
    }


def review_memo(research_path: Path) -> str:
    """출력 파일 하단에 붙일 검토 메모를 반환합니다."""
    return f"""
## 검토 메모

- 이 초안은 설교 개요와 Logos 연구 정리 파일을 함께 참고했습니다.
- Logos 연구 자료 출처: {research_path}
- Logos 연구 자료는 최종 해석이 아니며 본문 문맥과 설교 흐름에 맞게 직접 검토해야 합니다.
"""


def augment_questions(
    base_questions: list[str],
    research_items: list[str],
    max_additions: int = 2,
) -> list[str]:
    """연구 항목을 질문 형태로 변환해 기존 질문 목록에 추가합니다.

    - 최대 max_additions 개만 추가합니다.
    - 기존 질문은 변경하지 않습니다.
    """
    added = 0
    result = list(base_questions)
    for item in research_items:
        if added >= max_additions:
            break
        question = _to_question(item)
        if question and question not in result:
            result.append(question)
            added += 1
    return result


def _to_question(item: str) -> str:
    """항목 문장을 질문 형태로 변환합니다."""
    item = item.rstrip(".")
    if item.endswith("?") or item.endswith("요"):
        return item
    if len(item) < 5:
        return ""
    # 질문 접미사 패턴 추가
    if any(item.endswith(suffix) for suffix in ("입니다", "됩니다", "합니다", "없습니다")):
        return f"본문에서 '{item}'와 관련된 내용을 찾아보세요."
    return f"'{item}'는 본문에서 어떤 의미를 가지나요?"
