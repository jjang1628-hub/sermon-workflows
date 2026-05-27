"""
build_evidence_ledger.py — Evidence Ledger 생성기

연구 보고서에서 주장을 추출하고 Evidence Ledger를 생성한다.
Claude API를 사용하여 자동 추출하거나, 수동 템플릿을 생성한다.

사용법:
    python scripts/build_evidence_ledger.py --research output/deep_research/jn-13-14-deep-research.md
    python scripts/build_evidence_ledger.py --research <파일> --passage "요한복음 13:14"
    python scripts/build_evidence_ledger.py --template --passage "요한복음 13:14"
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path


ANTHROPIC_API_URL = "https://api.anthropic.com/v1/messages"

EVIDENCE_LEDGER_SYSTEM = """\
당신은 신학 연구의 증거 관리자입니다.
주어진 연구 보고서에서 모든 해석 주장을 추출하고,
각 주장에 대한 증거를 체계적으로 기록합니다.

원칙:
- 모든 주장은 출처가 있어야 한다
- 출처 없는 주장은 "⚪ 확인필요" 레이블을 붙인다
- 신뢰도를 객관적으로 평가한다
- 신뢰도: 🔵 높음 (원어+주석2종+교차참조) / 🟡 중간 (주석1종) / 🔴 낮음 (추론) / ⚪ 확인필요
"""

EVIDENCE_LEDGER_PROMPT = """\
아래 연구 보고서에서 모든 해석 주장을 추출하여
Evidence Ledger 형식으로 출력하세요.

## 연구 보고서
{research_content}

## 요구사항

다음 Markdown 형식으로 정확히 출력하세요.

---

# Evidence Ledger — {passage}

생성일시: {timestamp}
본문: {passage}

---

## 주장 목록

### EL-001
- **주장**: (주장 내용)
- **유형**: 본문관찰 | 원어분석 | 역사배경 | 신학해석 | 적용
- **출처**: (출처명 — 인용 또는 요약)
- **신뢰도**: 🔵 높음 | 🟡 중간 | 🔴 낮음 | ⚪ 확인필요
- **신뢰도 근거**: (왜 이 등급인가)
- **설교 관련성**: 핵심 | 보조 | 배경 | 무관
- **Logos 확인 필요**: yes | no

(EL-002, EL-003 ... 계속)

---

## 미확인 주장 요약

| ID | 주장 요약 | 확인 방법 |
|----|-----------|-----------|

---

## 신뢰도 분포

| 레이블 | 수 |
|--------|-----|
| 🔵 높음 | n |
| 🟡 중간 | n |
| 🔴 낮음 | n |
| ⚪ 확인필요 | n |
"""


def slugify(passage: str) -> str:
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
    return slug.strip("-").lower() or "passage"


def call_claude_api(api_key: str, system: str, prompt: str, model: str = "claude-opus-4-5") -> str:
    payload = json.dumps({
        "model": model,
        "max_tokens": 4000,
        "system": system,
        "messages": [{"role": "user", "content": prompt}],
    }).encode("utf-8")

    req = urllib.request.Request(
        ANTHROPIC_API_URL,
        data=payload,
        headers={
            "Content-Type": "application/json",
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            data = json.loads(resp.read())
            return data["content"][0]["text"]
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"Claude API 오류: {e.code} {e.reason}") from e


def build_template(passage: str) -> str:
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    slug = slugify(passage)

    return f"""# Evidence Ledger — {passage}

생성일시: {timestamp}
본문: {passage}

> ⚠️ 이 파일은 수동 작성 템플릿입니다.
> 연구 분석 후 각 항목을 채워 넣으세요.

---

## 주장 목록

### EL-001
- **주장**: (주장 내용을 여기에 작성)
- **유형**: 본문관찰 | 원어분석 | 역사배경 | 신학해석 | 적용
- **출처**: (출처명 — 인용 또는 요약)
- **신뢰도**: 🔵 높음 | 🟡 중간 | 🔴 낮음 | ⚪ 확인필요
- **신뢰도 근거**: (왜 이 등급인가)
- **설교 관련성**: 핵심 | 보조 | 배경 | 무관
- **Logos 확인 필요**: yes | no

### EL-002
- **주장**:
- **유형**:
- **출처**:
- **신뢰도**:
- **신뢰도 근거**:
- **설교 관련성**:
- **Logos 확인 필요**:

---

## 미확인 주장 요약

| ID | 주장 요약 | 확인 방법 |
|----|-----------|-----------|
| EL-xxx | | Logos에서 확인 |

---

## 신뢰도 분포

| 레이블 | 수 |
|--------|-----|
| 🔵 높음 | 0 |
| 🟡 중간 | 0 |
| 🔴 낮음 | 0 |
| ⚪ 확인필요 | 0 |

---

⚠️ 이 자료는 연구 보조 자료입니다. 최종 설교는 목사님이 직접 작성하세요.
"""


def main() -> int:
    parser = argparse.ArgumentParser(description="Evidence Ledger 생성기")
    parser.add_argument("--passage", required=True)
    parser.add_argument("--research", default=None, help="연구 보고서 파일 경로")
    parser.add_argument("--output", default=None)
    parser.add_argument("--template", action="store_true", help="수동 템플릿만 생성")
    parser.add_argument("--model", default="claude-opus-4-5")
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    slug = slugify(args.passage)
    output_path = Path(args.output) if args.output else \
        Path("output/evidence_ledgers") / f"{slug}-evidence-ledger.md"

    if output_path.exists() and not args.force:
        print(f"NG 출력 파일이 이미 있습니다. --force 사용: {output_path}")
        return 1

    output_path.parent.mkdir(parents=True, exist_ok=True)

    # 수동 템플릿 모드
    if args.template or not args.research:
        ledger = build_template(args.passage)
        print("OK 수동 작성 템플릿 생성")
    else:
        # Claude API 자동 생성
        api_key = os.environ.get("ANTHROPIC_API_KEY", "")
        if not api_key:
            print("NG ANTHROPIC_API_KEY 없음 — 수동 템플릿으로 대체")
            ledger = build_template(args.passage)
        else:
            research_path = Path(args.research)
            if not research_path.exists():
                print(f"NG 연구 파일 없음: {research_path}")
                return 1

            research_content = research_path.read_text(encoding="utf-8", errors="replace")
            research_content = research_content[:8000]  # 토큰 제한

            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            prompt = EVIDENCE_LEDGER_PROMPT.format(
                research_content=research_content,
                passage=args.passage,
                timestamp=timestamp,
            )

            print(f"OK Claude API로 Evidence Ledger 생성 중...")
            try:
                ledger = call_claude_api(api_key, EVIDENCE_LEDGER_SYSTEM, prompt, args.model)
                print("OK 생성 완료")
            except RuntimeError as e:
                print(f"NG 생성 실패: {e}")
                print("OK 수동 템플릿으로 대체")
                ledger = build_template(args.passage)

    # 저장
    if output_path.exists() and args.force:
        shutil.copy2(output_path, output_path.with_suffix(".bak"))

    temp = output_path.with_suffix(".tmp")
    temp.write_text(ledger, encoding="utf-8")
    if output_path.exists():
        output_path.unlink()
    temp.rename(output_path)

    print(f"OK Evidence Ledger: {output_path}")
    print(f"   크기: {output_path.stat().st_size:,}바이트")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
