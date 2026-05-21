from __future__ import annotations

import argparse
import re
from datetime import datetime
from pathlib import Path


# UI 노이즈 패턴 — Logos 앱 메뉴/광고 텍스트
_NOISE_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"^\$[\d,]+\.\d{2}\s", re.IGNORECASE),
    re.compile(r"무료\s*(도서|체험|증정)", re.IGNORECASE),
    re.compile(r"업그레이드하세요", re.IGNORECASE),
    re.compile(r"^(연구\s*길잡이|서재|검색|성경|스터디\s*어시스턴트|성경백과|도구|화면\s*구성|모두\s*닫기|대시보드|동기화|헬프\s*센터)$"),
    re.compile(r"^(인도자\s*메모|작성\s*메모)$"),
    re.compile(r"^(관찰\s*질문|해석\s*질문|적용\s*질문)$"),
    re.compile(r"Logos\s*(10|9|8|7)?\s*(에서|에|는|이|을|가)"),
]

# 키워드 기반 섹션 분류
_OBSERVATION_KEYWORDS = (
    "구조", "반복", "인물", "장소", "시간", "명령", "질문", "본문", "단락",
    "소개", "절", "구절", "교환", "대화", "부분",
)
_INTERPRETATION_KEYWORDS = (
    "배경", "문맥", "원어", "주석", "신학", "교차", "참조", "의미", "뜻",
    "역사", "발췌", "비유", "약속", "연결", "이중", "오해", "바리새",
)
_APPLICATION_KEYWORDS = (
    "적용", "묵상", "질문", "기도", "삶", "공동체", r"이번\s*주", "바꿀",
    "의존", "구합니다", "해달라", "실천",
)


def _is_noise(line: str) -> bool:
    stripped = line.strip()
    if not stripped:
        return False
    for pattern in _NOISE_PATTERNS:
        if pattern.search(stripped):
            return True
    return False


def _classify(line: str) -> str:
    """관찰 / 해석 / 적용 / 기타 분류."""
    text = line.strip()
    for kw in _OBSERVATION_KEYWORDS:
        if re.search(kw, text):
            return "observation"
    for kw in _INTERPRETATION_KEYWORDS:
        if re.search(kw, text):
            return "interpretation"
    for kw in _APPLICATION_KEYWORDS:
        if re.search(kw, text):
            return "application"
    return "other"


def _deduplicate(lines: list[str]) -> tuple[list[str], int]:
    seen: set[str] = set()
    result: list[str] = []
    removed = 0
    for line in lines:
        key = re.sub(r"\s+", " ", line.strip()).lower()
        if key in seen or key == "":
            removed += 1
            continue
        seen.add(key)
        result.append(line)
    return result, removed


def normalize(
    raw_text: str,
    passage: str,
    source_kind: str,
    source_file: str,
) -> str:
    raw_lines = raw_text.splitlines()

    # 헤더 섹션(캡처 메타) 건너뛰기
    content_start = 0
    for i, line in enumerate(raw_lines):
        if line.strip().startswith("## 캡처 내용"):
            content_start = i + 1
            break

    content_lines = raw_lines[content_start:]

    # 노이즈 제거
    clean_lines = [ln for ln in content_lines if not _is_noise(ln)]

    # 중복 제거
    deduped_lines, removed_count = _deduplicate(clean_lines)

    # 섹션별 분류
    observations: list[str] = []
    interpretations: list[str] = []
    applications: list[str] = []

    for line in deduped_lines:
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        cls = _classify(stripped)
        if cls == "observation":
            observations.append(stripped)
        elif cls == "interpretation":
            interpretations.append(stripped)
        elif cls == "application":
            applications.append(stripped)

    # 신뢰도 판단
    total = len(observations) + len(interpretations) + len(applications)
    all_content = len([ln for ln in deduped_lines if ln.strip()])
    if all_content == 0:
        confidence = "낮음"
    elif total / all_content >= 0.5:
        confidence = "높음"
    elif total / all_content >= 0.2:
        confidence = "보통"
    else:
        confidence = "낮음"

    # 출력 텍스트 조립
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cleaned_text = "\n".join(deduped_lines)

    obs_block = "\n".join(f"- {ln}" for ln in observations) or "- (자동 분류 결과 없음)"
    int_block = "\n".join(f"- {ln}" for ln in interpretations) or "- (자동 분류 결과 없음)"
    app_block = "\n".join(f"- {ln}" for ln in applications) or "- (자동 분류 결과 없음)"

    return f"""# Logos 연구 자료

## 기본 정보

- 본문: {passage}
- 자료 유형: {source_kind}
- 원본 캡처 파일: {source_file}
- 정규화 일시: {now}
- 주의: 이 파일은 설교 준비 참고 자료이며 최종 해석이 아닙니다.

## 빠른 검토

- 캡처 글자 수: {len(raw_text)}
- 제거한 중복 줄 수: {removed_count}
- 자동 분류 신뢰도: {confidence}

## 관찰 후보

{obs_block}

## 해석 참고 후보

{int_block}

## 적용 아이디어 후보

{app_block}

## 검토 필요

- 출처와 문맥을 직접 확인하세요.
- 자동 분류가 틀릴 수 있습니다.
- 설교의 최종 신학 판단으로 사용하지 마세요.

## 정리된 원문

{cleaned_text}
"""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Logos 캡처 원문을 설교 연구 참고 파일로 정규화합니다."
    )
    parser.add_argument("--input", required=True, help="캡처 원문 파일 경로 (raw .md)")
    parser.add_argument("--output", required=True, help="출력 연구 파일 경로")
    parser.add_argument("--passage", default="", help="본문 (예: 요한복음 3장)")
    parser.add_argument("--source-kind", default="passage-guide", help="자료 유형")
    parser.add_argument("--force", action="store_true", help="출력 파일 덮어쓰기 허용")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    input_path = Path(args.input)
    output_path = Path(args.output)

    if not input_path.exists():
        raise FileNotFoundError(f"입력 파일 없음: {input_path}")
    if output_path.exists() and not args.force:
        raise FileExistsError(
            f"출력 파일이 이미 있습니다. 덮어쓰려면 --force를 사용하세요: {output_path}"
        )

    raw_text = input_path.read_text(encoding="utf-8")
    result = normalize(
        raw_text=raw_text,
        passage=args.passage,
        source_kind=args.source_kind,
        source_file=str(input_path),
    )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(result, encoding="utf-8")
    print(f"정규화 완료: {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
