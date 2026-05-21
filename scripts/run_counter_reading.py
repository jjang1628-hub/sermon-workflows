"""
run_counter_reading.py — Counter-Reading 생성기 (8관점)

연구 보고서에 대한 반론을 8개 관점에서 생성한다.
"반론을 먼저 찾는다" 원칙의 실행 도구. 생략 불가.

사용법:
    python scripts/run_counter_reading.py --research output/deep_research/jn-13-14-deep-research.md
    python scripts/run_counter_reading.py --research <파일> --passage "요한복음 13:14"
    python scripts/run_counter_reading.py --template --passage "요한복음 13:14"
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

COUNTER_READING_SYSTEM = """\
당신은 지금 악마의 변호인(Devil's Advocate) 역할을 맡습니다.
주어진 설교 연구 보고서의 주요 해석에 대해
가장 강력한 반론을 8개 관점에서 생성하세요.

중요:
- 이 반론 생성은 분석을 강화하기 위한 것입니다
- 반론은 학문적으로 진지해야 합니다 (억지 반박 금지)
- 각 반론에 반론 강도를 평가합니다: 🔴 강 / 🟡 중 / 🟢 약
- 반론 후 설교자 응답 옵션을 제시합니다

8개 관점:
CR-1: 대안 해석 (학문적으로 인정받는 다른 해석)
CR-2: 문맥 반론 (직전·직후 문맥과의 불일치)
CR-3: 원어 반론 (원어의 다른 의미 가능성)
CR-4: 역사 반론 (역사·문화 배경 과잉 단순화)
CR-5: 그리스도 연결 반론 (신학 체계 소급 적용 여부)
CR-6: 적용 반론 (율법주의 또는 값싼 은혜 위험)
CR-7: 설교자 편향 반론 (기존 신학 입장 확인용 읽기)
CR-8: 청중 반론 (청중의 합리적 의문 가능성)
"""

COUNTER_READING_PROMPT = """\
아래 연구 보고서에 대해 8개 관점에서 반론을 생성하세요.

## 연구 보고서
{research_content}

## 요구사항

다음 Markdown 형식으로 출력하세요.

---

# Counter-Reading 보고서 — {passage}

생성일시: {timestamp}

---

## CR-1: 대안 해석

**반론 강도**: 🔴 강 | 🟡 중 | 🟢 약

**반론 내용**: (내용)

**근거**: (학문적 근거)

**설교자 응답 옵션**:
- A) 반론 수용 → 해석 수정
- B) 반론 인정하되 기존 해석 유지 → 설교에서 언급
- C) 반론 기각 → 기각 근거:

---

## CR-2: 문맥 반론
(같은 형식)

... (CR-3 ~ CR-8)

---

## 종합 평가

| CR | 반론 강도 | 권고 조치 |
|----|-----------|----------|

---

## 반론 이후에도 확고한 핵심 주장

(Counter-Reading 이후에도 유지되는 핵심 해석)
"""


def slugify(passage: str) -> str:
    table = {
        "마태복음": "mt", "마가복음": "mk", "누가복음": "lk", "요한복음": "jn",
        "로마서": "ro", "고린도전서": "1co", "고린도후서": "2co", "갈라디아서": "ga",
        "에베소서": "eph", "빌립보서": "php", "히브리서": "heb", "야고보서": "jas",
        "베드로전서": "1pe", "요한일서": "1jn", "요한계시록": "re",
        "창세기": "ge", "출애굽기": "ex", "시편": "ps", "잠언": "pr",
        "이사야": "is", "예레미야": "je",
    }
    slug = passage
    for korean, abbr in table.items():
        if korean in passage:
            slug = passage.replace(korean, abbr)
            break
    slug = re.sub(r"[:\s]+", "-", slug)
    slug = re.sub(r"[^a-zA-Z0-9\-]", "", slug)
    return slug.strip("-").lower() or "passage"


def build_template(passage: str) -> str:
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cr_sections = [
        ("CR-1", "대안 해석", "학문적으로 인정받는 다른 해석이 있는가?"),
        ("CR-2", "문맥 반론", "이 해석이 직전·직후 문맥과 실제로 일치하는가?"),
        ("CR-3", "원어 반론", "원어 분석이 다른 번역이나 뜻을 허용하는가?"),
        ("CR-4", "역사 반론", "역사·문화 배경 해석이 과잉 단순화되지 않았는가?"),
        ("CR-5", "그리스도 연결 반론", "이 그리스도 연결이 실제로 본문 논리에서 나오는가?"),
        ("CR-6", "적용 반론", "이 적용이 율법주의나 값싼 은혜로 흐를 위험이 있는가?"),
        ("CR-7", "설교자 편향 반론", "설교자가 자신의 기존 신학 입장을 확인하기 위해 읽지는 않았는가?"),
        ("CR-8", "청중 반론", "청중이 이 해석에 합리적인 의문을 제기할 수 있는가?"),
    ]

    lines = [
        f"# Counter-Reading 보고서 — {passage}",
        f"",
        f"생성일시: {timestamp}",
        f"",
        f"> ⚠️ 이 파일은 수동 작성 템플릿입니다.",
        f"> 연구 분석 후 각 반론을 채워 넣으세요.",
        f"> Counter-Reading Pass는 생략할 수 없습니다.",
        f"",
        f"---",
        f"",
    ]

    for cr_id, cr_name, cr_question in cr_sections:
        lines += [
            f"## {cr_id}: {cr_name}",
            f"",
            f"> *{cr_question}*",
            f"",
            f"**반론 강도**: 🔴 강 | 🟡 중 | 🟢 약",
            f"",
            f"**반론 내용**: (여기에 반론을 작성하세요)",
            f"",
            f"**근거**: (학문적 근거 또는 논리적 근거)",
            f"",
            f"**설교자 응답 옵션**:",
            f"- A) 반론 수용 → 해석 수정",
            f"- B) 반론 인정하되 기존 해석 유지 → 설교에서 언급",
            f"- C) 반론 기각 → 기각 근거:",
            f"",
            f"---",
            f"",
        ]

    lines += [
        f"## 종합 평가",
        f"",
        f"| CR | 반론 강도 | 권고 조치 |",
        f"|----|-----------|----------|",
    ]
    for cr_id, cr_name, _ in cr_sections:
        lines.append(f"| {cr_id} | 🟡 중 | B) 인정하되 유지 |")

    lines += [
        f"",
        f"---",
        f"",
        f"## 반론 이후에도 확고한 핵심 주장",
        f"",
        f"(Counter-Reading 이후에도 유지되는 핵심 해석을 여기에 작성하세요)",
        f"",
        f"---",
        f"",
        f"⚠️ 이 자료는 연구 보조 자료입니다. 최종 설교는 목사님이 직접 작성하세요.",
    ]

    return "\n".join(lines)


def call_claude_api(api_key: str, system: str, prompt: str, model: str) -> str:
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
    with urllib.request.urlopen(req, timeout=120) as resp:
        data = json.loads(resp.read())
        return data["content"][0]["text"]


def main() -> int:
    parser = argparse.ArgumentParser(description="Counter-Reading 생성기")
    parser.add_argument("--passage", required=True)
    parser.add_argument("--research", default=None)
    parser.add_argument("--output", default=None)
    parser.add_argument("--template", action="store_true")
    parser.add_argument("--model", default="claude-opus-4-5")
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    slug = slugify(args.passage)
    output_path = Path(args.output) if args.output else \
        Path("output/deep_research") / f"{slug}-counter-reading.md"

    if output_path.exists() and not args.force:
        print(f"NG 출력 파일이 이미 있습니다. --force 사용: {output_path}")
        return 1

    output_path.parent.mkdir(parents=True, exist_ok=True)

    if args.template or not args.research:
        result = build_template(args.passage)
        print("OK 수동 작성 템플릿 생성")
    else:
        api_key = os.environ.get("ANTHROPIC_API_KEY", "")
        if not api_key:
            print("NG ANTHROPIC_API_KEY 없음 — 수동 템플릿으로 대체")
            result = build_template(args.passage)
        else:
            research_path = Path(args.research)
            if not research_path.exists():
                print(f"NG 연구 파일 없음: {research_path}")
                return 1

            research_content = research_path.read_text(encoding="utf-8", errors="replace")[:6000]
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            prompt = COUNTER_READING_PROMPT.format(
                research_content=research_content,
                passage=args.passage,
                timestamp=timestamp,
            )

            print("OK Claude API로 Counter-Reading 생성 중...")
            try:
                result = call_claude_api(api_key, COUNTER_READING_SYSTEM, prompt, args.model)
                print("OK 완료")
            except Exception as e:
                print(f"NG 실패: {e} — 수동 템플릿으로 대체")
                result = build_template(args.passage)

    if output_path.exists() and args.force:
        shutil.copy2(output_path, output_path.with_suffix(".bak"))

    temp = output_path.with_suffix(".tmp")
    temp.write_text(result, encoding="utf-8")
    if output_path.exists():
        output_path.unlink()
    temp.rename(output_path)

    print(f"OK Counter-Reading: {output_path}")
    print(f"   크기: {output_path.stat().st_size:,}바이트")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
