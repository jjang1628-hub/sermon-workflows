"""
Claude API를 사용한 완전 자동 설교 연구 스크립트.

사용법:
    python scripts/research_with_claude.py --passage "요한복음 3:16-17"
    python scripts/research_with_claude.py --passage "요한복음 3:16-17" --outline input/john-3-sermon-outline.md
    python scripts/research_with_claude.py --passage "요한복음 3:16-17" --run-all

환경변수:
    ANTHROPIC_API_KEY  Claude API 키 (필수)
"""

from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path

import anthropic


RESEARCH_SYSTEM_PROMPT = """
당신은 개혁주의 신학 전통(합동측)에 기반한 설교 연구 전문가입니다.

신학 원칙:
- 언약적·구속사적 해석: 창조–타락–구속–새창조 흐름 안에서 본문을 읽습니다.
- Big Idea: "하나님께서 그리스도 안에서 무엇을 하시며, 우리는 어떻게 응답하는가"
- 인물 영웅화 금지: 인간의 실패, 두려움, 자기보호를 정직하게 드러냅니다.
- 그리스도 연결: 억지 알레고리 금지. 본문의 논리에서 자연스러운 연결.
- 적용: 복음의 은혜 → 동기 변화 → 순종의 열매 순서를 따릅니다.
- 주석 참조: Carson, Keener, Köstenberger (요한), NICNT, BECNT, WBC 등.

출력 형식을 엄격히 지킵니다.
"""


RESEARCH_USER_PROMPT = """
아래 본문에 대해 설교 준비용 연구 분석을 수행하고, 지정된 Markdown 형식으로 출력하세요.

## 본문
{passage}

## 요구사항

다음 형식을 정확히 지켜서 출력하세요. 각 섹션은 bullet(-) 형식으로 작성합니다.

---

# Logos 연구 자료

## 기본 정보

- 본문: {passage}
- 자료 유형: claude-direct-research
- 정규화 일시: {timestamp}
- 주의: 이 파일은 설교 준비 참고 자료이며 최종 해석이 아닙니다.

## 빠른 검토

- 연구 출처: Claude 직접 분석 (개혁주의 구속사적 관점)
- 자동 분류 신뢰도: 높음

## 관찰 후보

(본문 구조, 핵심 단어, 반복 표현, 인물·장소·시간, 문학적 흐름을 bullet으로)

## 해석 참고 후보

(역사·문화 배경, 원어 분석, 주요 주석 관점, 교차 참조, 신학 주제, 그리스도 연결을 bullet으로)

## 적용 아이디어 후보

(복음의 은혜에서 출발한 적용, 삶의 변화 방향, 기도 제목을 bullet으로)

## 검토 필요

- Claude 분석은 설교의 최종 신학 판단이 아닙니다.
- 본문 문맥과 설교 흐름에 맞게 직접 검토하세요.
- 원어 분석과 주석 인용은 실제 텍스트로 확인하세요.

## 정리된 원문

(위 내용의 서사 형태 전문 분석. 본문 개요, 역사적 배경, 원어 심층 분석, 구속사적 위치, 설교 빅 아이디어를 상세히 서술)
"""


def slugify(passage: str) -> str:
    """본문 이름을 파일명 슬러그로 변환합니다."""
    table = {
        "창세기": "ge", "출애굽기": "ex", "레위기": "le", "민수기": "nu",
        "신명기": "dt", "여호수아": "jos", "사사기": "jdg", "룻기": "ru",
        "사무엘상": "1sa", "사무엘하": "2sa", "열왕기상": "1ki", "열왕기하": "2ki",
        "역대상": "1ch", "역대하": "2ch", "에스라": "ezr", "느헤미야": "ne",
        "에스더": "est", "욥기": "job", "시편": "ps", "잠언": "pr",
        "전도서": "ec", "아가": "ss", "이사야": "is", "예레미야": "je",
        "예레미야애가": "la", "에스겔": "eze", "다니엘": "da", "호세아": "ho",
        "요엘": "joe", "아모스": "am", "오바댜": "ob", "요나": "jon",
        "미가": "mic", "나훔": "na", "하박국": "hab", "스바냐": "zep",
        "학개": "hag", "스가랴": "zec", "말라기": "mal",
        "마태복음": "mt", "마가복음": "mk", "누가복음": "lk", "요한복음": "jn",
        "사도행전": "ac", "로마서": "ro", "고린도전서": "1co", "고린도후서": "2co",
        "갈라디아서": "ga", "에베소서": "eph", "빌립보서": "php", "골로새서": "col",
        "데살로니가전서": "1th", "데살로니가후서": "2th", "디모데전서": "1ti",
        "디모데후서": "2ti", "디도서": "tit", "빌레몬서": "phm", "히브리서": "heb",
        "야고보서": "jas", "베드로전서": "1pe", "베드로후서": "2pe",
        "요한일서": "1jn", "요한이서": "2jn", "요한삼서": "3jn",
        "유다서": "jude", "요한계시록": "re",
    }
    slug = passage
    for korean, abbr in table.items():
        if korean in passage:
            slug = passage.replace(korean, abbr)
            break
    slug = re.sub(r"[:\s]+", "-", slug)
    slug = re.sub(r"[^a-zA-Z0-9\-]", "", slug)
    slug = slug.strip("-").lower()
    return slug or "passage"


def run_research(passage: str) -> str:
    """Claude API로 본문 연구를 수행하고 결과 텍스트를 반환합니다."""
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise EnvironmentError(
            "ANTHROPIC_API_KEY 환경변수가 설정되지 않았습니다.\n"
            "  PowerShell에서 ANTHROPIC_API_KEY 환경변수를 설정하세요."
        )

    client = anthropic.Anthropic(api_key=api_key)
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    prompt = RESEARCH_USER_PROMPT.format(passage=passage, timestamp=timestamp)

    print(f"Claude API 연구 중: {passage}")
    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=4096,
        system=RESEARCH_SYSTEM_PROMPT,
        messages=[{"role": "user", "content": prompt}],
    )
    return message.content[0].text


def save_research(content: str, output_path: Path, force: bool = False) -> None:
    if output_path.exists() and not force:
        raise FileExistsError(
            f"연구 파일이 이미 있습니다. 덮어쓰려면 --force를 사용하세요: {output_path}"
        )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(content, encoding="utf-8")
    print(f"연구 저장: {output_path}")


def run_pipeline(
    outline_path: Path,
    research_path: Path,
    output_dir: Path,
) -> None:
    cmd = [
        sys.executable,
        "scripts/run_all.py",
        "--input", str(outline_path),
        "--research", str(research_path),
        "--output-dir", str(output_dir),
    ]
    print(f"파이프라인 실행: {' '.join(cmd)}")
    subprocess.run(cmd, check=True)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Claude API로 설교 본문을 직접 연구하고 결과물을 생성합니다."
    )
    parser.add_argument("--passage", required=True, help="연구할 성경 본문 (예: 요한복음 3:16-17)")
    parser.add_argument("--outline", default=None, help="설교 개요 파일 경로 (--run-all 시 필요)")
    parser.add_argument("--research-output", default=None, help="연구 파일 저장 경로 (기본: input/research/)")
    parser.add_argument("--output-dir", default="output", help="최종 출력 폴더 (기본: output/)")
    parser.add_argument("--run-all", action="store_true", help="연구 후 파이프라인 자동 실행")
    parser.add_argument("--force", action="store_true", help="기존 파일 덮어쓰기")
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    slug = slugify(args.passage)
    research_path = (
        Path(args.research_output)
        if args.research_output
        else Path("input/research") / f"{slug}-research.md"
    )

    # 연구 수행
    content = run_research(args.passage)
    save_research(content, research_path, force=args.force)

    # 파이프라인 실행
    if args.run_all:
        outline_path = Path(args.outline) if args.outline else Path(f"input/{slug}-sermon-outline.md")
        if not outline_path.exists():
            print(f"[경고] 설교 개요 파일 없음: {outline_path}")
            print("  --outline 옵션으로 개요 파일을 지정하거나, 직접 생성하세요.")
            return 1
        run_pipeline(
            outline_path=outline_path,
            research_path=research_path,
            output_dir=Path(args.output_dir),
        )

    print("\n완료.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
