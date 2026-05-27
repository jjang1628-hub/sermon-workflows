"""
audit_research_claims.py — Claim Audit 실행기 (12문항)

Evidence Ledger의 주장들을 12개 감사 질문으로 검사한다.

사용법:
    python scripts/audit_research_claims.py --ledger output/evidence_ledgers/jn-13-14-evidence-ledger.md
    python scripts/audit_research_claims.py --ledger <파일> --passage "요한복음 13:14"
    python scripts/audit_research_claims.py --template --passage "요한복음 13:14"
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

AUDIT_SYSTEM = """\
당신은 신학 해석의 품질 감사관입니다.
주어진 Evidence Ledger의 주장들에 대해 12개 감사 질문을 적용합니다.

12개 감사 질문:
Q01: 이 주장은 본문에서 직접 관찰된 것인가, 아니면 추론인가?
Q02: 원어 주장은 실제 원어 텍스트로 뒷받침되는가?
Q03: 역사·문화 배경 주장은 신뢰할 수 있는 학문 자료로 뒷받침되는가?
Q04: 이 해석이 본문의 문학적 흐름과 일치하는가?
Q05: 저자의 원래 의도에 충실한가?
Q06: 그리스도 연결이 본문의 논리에서 자연스럽게 나오는가?
Q07: 인물이 영웅화되어 있지 않은가?
Q08: 적용이 복음의 은혜에서 출발하는가?
Q09: 반론이 있는가? 대안적 해석을 고려했는가?
Q10: 이 주장은 개혁주의 신학 전통과 일치하는가?
Q11: 출처 인용이 정확한가?
Q12: 이 주장이 설교에서 실제로 사용 가능한가?

각 질문에 ✅ 통과 / ⚠️ 조건부 / ❌ 실패로 판정하고
실패/조건부인 경우 수정 방향을 제시하세요.
"""

AUDIT_PROMPT = """\
아래 Evidence Ledger의 주장들에 대해 12개 감사 질문을 적용하세요.

## Evidence Ledger
{ledger_content}

## 요구사항

다음 Markdown 형식으로 출력하세요.

---

# Claim Audit 보고서 — {passage}

감사일시: {timestamp}

---

## 감사 결과 요약

| ID | 주장 요약 | Q01-Q04 | Q05-Q08 | Q09-Q12 | 최종 |
|----|-----------|---------|---------|---------|------|

---

## 실패/조건부 주장 상세

### (ID) — 조건부/실패
- **실패 질문**: Q0x
- **이유**:
- **수정 방향**:

---

## 통과율: xx%

---

## 권고 사항
"""


def slugify(passage: str) -> str:
    table = {
        "창세기": "ge", "마태복음": "mt", "마가복음": "mk", "누가복음": "lk",
        "요한복음": "jn", "로마서": "ro", "고린도전서": "1co", "고린도후서": "2co",
        "갈라디아서": "ga", "에베소서": "eph", "빌립보서": "php", "골로새서": "col",
        "히브리서": "heb", "야고보서": "jas", "요한계시록": "re", "시편": "ps",
        "잠언": "pr", "이사야": "is", "예레미야": "je",
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
    return f"""# Claim Audit 보고서 — {passage}

감사일시: {timestamp}

> ⚠️ 이 파일은 수동 작성 템플릿입니다.
> Evidence Ledger 검토 후 각 항목을 채워 넣으세요.

---

## 12개 감사 질문 체크리스트

각 주장(EL-001, EL-002 ...)에 대해 다음을 체크하세요:

| 질문 | 내용 |
|------|------|
| Q01 | 본문에서 직접 관찰 vs 추론 구분 |
| Q02 | 원어 주장에 실제 원어 근거 있음 |
| Q03 | 역사·문화 배경에 학문 자료 출처 있음 |
| Q04 | 해석이 문학적 흐름과 일치함 |
| Q05 | 저자 의도에 충실 (시대착오 없음) |
| Q06 | 그리스도 연결이 본문 논리에서 나옴 |
| Q07 | 인물 영웅화 없음 |
| Q08 | 적용이 복음의 은혜에서 출발함 |
| Q09 | 반론/대안 해석 언급됨 |
| Q10 | 개혁주의 신학 전통과 일치함 |
| Q11 | 출처 인용 정확함 |
| Q12 | 설교에서 실제 사용 가능함 |

---

## 주장별 감사 결과

### EL-001
| Q01 | Q02 | Q03 | Q04 | Q05 | Q06 | Q07 | Q08 | Q09 | Q10 | Q11 | Q12 |
|-----|-----|-----|-----|-----|-----|-----|-----|-----|-----|-----|-----|
| ✅  | ✅  | ✅  | ✅  | ✅  | ✅  | ✅  | ✅  | ✅  | ✅  | ✅  | ✅  |

**최종**: 통과

---

## 통과율: ___%

---

⚠️ 이 자료는 연구 보조 자료입니다. 최종 설교는 목사님이 직접 작성하세요.
"""


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
    parser = argparse.ArgumentParser(description="Claim Audit 실행기")
    parser.add_argument("--passage", required=True)
    parser.add_argument("--ledger", default=None, help="Evidence Ledger 파일")
    parser.add_argument("--output", default=None)
    parser.add_argument("--template", action="store_true")
    parser.add_argument("--model", default="claude-opus-4-5")
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    slug = slugify(args.passage)
    output_path = Path(args.output) if args.output else \
        Path("output/claim_audits") / f"{slug}-claim-audit.md"

    if output_path.exists() and not args.force:
        print(f"NG 출력 파일이 이미 있습니다. --force 사용: {output_path}")
        return 1

    output_path.parent.mkdir(parents=True, exist_ok=True)

    if args.template or not args.ledger:
        audit = build_template(args.passage)
        print("OK 수동 작성 템플릿 생성")
    else:
        api_key = os.environ.get("ANTHROPIC_API_KEY", "")
        if not api_key:
            print("NG ANTHROPIC_API_KEY 없음 — 수동 템플릿으로 대체")
            audit = build_template(args.passage)
        else:
            ledger_path = Path(args.ledger)
            if not ledger_path.exists():
                print(f"NG Ledger 파일 없음: {ledger_path}")
                return 1

            ledger_content = ledger_path.read_text(encoding="utf-8", errors="replace")[:6000]
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            prompt = AUDIT_PROMPT.format(
                ledger_content=ledger_content,
                passage=args.passage,
                timestamp=timestamp,
            )

            print("OK Claude API로 Claim Audit 실행 중...")
            try:
                audit = call_claude_api(api_key, AUDIT_SYSTEM, prompt, args.model)
                print("OK 완료")
            except Exception as e:
                print(f"NG 실패: {e} — 수동 템플릿으로 대체")
                audit = build_template(args.passage)

    if output_path.exists() and args.force:
        shutil.copy2(output_path, output_path.with_suffix(".bak"))

    temp = output_path.with_suffix(".tmp")
    temp.write_text(audit, encoding="utf-8")
    if output_path.exists():
        output_path.unlink()
    temp.rename(output_path)

    print(f"OK Claim Audit: {output_path}")
    print(f"   크기: {output_path.stat().st_size:,}바이트")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
