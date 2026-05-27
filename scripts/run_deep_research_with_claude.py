"""
run_deep_research_with_claude.py — Claude 심층 연구 실행기

20-Pass Multi-Pass Deep Research 프로토콜로 Claude API를 사용하여
심층 신학 분석을 수행한다.

사용법:
    python scripts/run_deep_research_with_claude.py --passage "요한복음 13:14"
    python scripts/run_deep_research_with_claude.py --passage "요한복음 13:14" --research-pack output/research_packs/jn-13-14-research-pack.md
    python scripts/run_deep_research_with_claude.py --passage "요한복음 13:14" --mode deep --force

환경:
    ANTHROPIC_API_KEY 환경변수 필요
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import sys
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path

# Windows cp949 환경에서 한글/특수문자 UnicodeEncodeError 방지
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
if hasattr(sys.stderr, "reconfigure"):
    try:
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass


ANTHROPIC_API_URL = "https://api.anthropic.com/v1/messages"

# theological_core.md를 직접 로드하거나 여기에 내장
THEOLOGICAL_CORE = """\
개혁주의 신학 전통(합동측)에 기반한 설교 연구 전문가입니다.

신학 원칙:
- 복음 프레임: 창조–타락–구속–새창조 흐름
- Big Idea: "인간의 문제에도 불구하고 하나님께서 그리스도 안에서 무엇을 하시며, 우리는 어떻게 응답하는가"
- 그리스도 연결: 본문의 실패·갈망·약속·심판·구원이 십자가와 부활 안에서 완성되는 논리 (억지 알레고리 금지)
- 인물 영웅화 금지: 인간의 두려움·욕망·자기보호를 정직하게 드러낸다
- 적용 구조: 복음의 은혜 → 동기 변화 → 순종의 열매

분석 철학:
- "설교자가 본문 아래 서 있는가"를 먼저 점검한다
- 모든 주장은 Evidence Ledger에 기록 가능한 수준의 근거를 갖춰야 한다
- 반론을 먼저 찾는다
- 불확실성을 정직하게 표시한다 (신뢰도: 🔵 높음/🟡 중간/🔴 낮음/⚪ 확인필요)

주석 우선순위:
1순위 (원어 기반): Carson (NICNT/Pillar), Keener (CLC), Morris (NICNT), Moo (NICNT), Schreiner (BECNT)
2순위 (신학적): Wright, Witherington, Thiselton, Cranfield, Dunn
3순위 (적용): Barclay, NICBC

이 분석은 연구 보조 자료입니다. 최종 신학 판단은 설교자에게 있습니다.
"""

DEEP_RESEARCH_PROMPT = """\
아래 본문에 대해 20-Pass Multi-Pass Deep Research 프로토콜로 심층 분석을 수행하세요.

## 본문
{passage}

## 연구 자료
{research_content}

{v21_brief}

## 20-Pass 프로토콜

다음 Markdown 형식으로 정확히 출력하세요:

---

# 심층 연구 보고서 — {passage}

생성일시: {timestamp}
분석 모델: {model}
운영 모드: {mode}

> ⚠️ 이 보고서는 연구 보조 자료입니다. 최종 신학 판단은 설교자에게 있습니다.

---

## Pass 1–3: 본문 기초

### Pass 1: 본문 경계 확인
(이 본문의 시작과 끝이 어디인가? 어떤 단락에 속하는가?)

### Pass 2: 문학 장르 분류
(장르: 복음서 / 서신서 / 시편 / 예언 / 내러티브)

### Pass 3: 본문 구조 분석
(문단 구조, 키아즘, 평행법, 논증 흐름)

---

## Pass 4–7: 언어·배경 분석

### Pass 4: 핵심 단어 목록
(원어 단어 + 한국어 번역 + 신뢰도 레이블)

### Pass 5: 원어 심층 분석
(헬라어/히브리어 핵심 단어 2–3개 상세 분석)

### Pass 6: 역사·문화 배경
(1세기 맥락, 유대·헬레니즘 배경)

### Pass 7: 문학적 흐름
(저자의 논증 전개 방식)

---

## Pass 8–11: 저자·독자·구속사

### Pass 8: 저자 의도
(저자가 이 구절을 통해 무엇을 말하려 했는가?)

### Pass 9: 원독자 상황
(최초 독자가 이 말씀을 어떻게 들었을까?)

### Pass 10: 구속사적 위치
(창조–타락–구속–새창조 흐름에서 이 본문의 위치)

### Pass 11: 그리스도 연결 논리
(본문이 자연스럽게 가리키는 그리스도의 사역)

---

## Pass 12–15: 주석·신학

### Pass 12: 주석 비교

| 주석 | 핵심 관점 | 신뢰도 |
|------|-----------|--------|

### Pass 13: 신학 주제
(개혁주의 구속사적 관점에서의 신학 주제)

### Pass 14: 교리적 함의
(이 본문이 교의학적으로 어떤 함의를 갖는가?)

### Pass 15: 교차 참조
(연결되는 성경 본문 3–5개)

---

## Pass 16: 반론 및 대안 해석

(최소 2개 대안 해석 + 반론 강도 평가)

---

## Pass 17–19: 설교 설계

### Pass 17: 현대 적용 원리

### Pass 18: 설교 Big Idea (한 문장)
> (Big Idea: 복음 선언 형식으로)

### Pass 19: 적용 구조
(복음의 은혜 → 동기 변화 → 순종의 열매)

---

## Pass 20: 통합 검토

### 약점 및 주의사항
### 추가 연구 권장 사항
### 신뢰도 지도 요약

{v21_calibration}
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


def load_system_prompt(prompts_dir: Path) -> str:
    theological_core_path = prompts_dir / "theological_core.md"
    deep_research_path = prompts_dir / "claude_deep_research.md"

    system = THEOLOGICAL_CORE  # 기본값

    if theological_core_path.exists():
        system = theological_core_path.read_text(encoding="utf-8", errors="replace")
        if deep_research_path.exists():
            system += "\n\n" + deep_research_path.read_text(encoding="utf-8", errors="replace")

    return system


def call_claude_api(api_key: str, system: str, prompt: str, model: str) -> str:
    payload = json.dumps({
        "model": model,
        "max_tokens": 8000,
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
        with urllib.request.urlopen(req, timeout=300) as resp:
            data = json.loads(resp.read())
            return data["content"][0]["text"]
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace") if hasattr(e, "read") else ""
        raise RuntimeError(f"Claude API 오류 {e.code}: {body[:200]}") from e


def main() -> int:
    parser = argparse.ArgumentParser(description="Claude 심층 연구 실행기")
    parser.add_argument("--passage", required=True)
    parser.add_argument("--mode", choices=["quick", "standard", "deep", "expert"], default="standard")
    parser.add_argument("--research-pack", default=None, help="연구 팩 파일 경로")
    parser.add_argument("--logos-capture", default=None, help="Logos 캡처 파일 경로")
    parser.add_argument("--ollama-critique", default=None,
                        help="Ollama Quality Gate 결과 파일 — Ollama 1차 분석의 실패 항목을 Claude에게 전달")
    parser.add_argument("--research-context", default=None,
                        help="v2.1 Research Context 파일 경로 (06-research-context.md) — Coverage/Quality 강도 지도 주입")
    parser.add_argument("--output", default=None)
    parser.add_argument("--model", default="claude-opus-4-5")
    parser.add_argument("--prompts-dir", default="prompts")
    parser.add_argument("--force", action="store_true")
    parser.add_argument(
        "--dry-run", action="store_true",
        help="API 호출 없이 실제 전송될 프롬프트를 출력한다 (API 키 불필요)",
    )
    args = parser.parse_args()

    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key and not args.dry_run:
        print("NG ANTHROPIC_API_KEY 환경변수가 설정되어 있지 않습니다.")
        print("   $env:ANTHROPIC_API_KEY = '<ANTHROPIC_API_KEY>'")
        print("   (프롬프트 미리보기: --dry-run 플래그 사용)")
        return 1

    slug = slugify(args.passage)

    if args.output:
        output_path = Path(args.output)
    else:
        output_path = Path("output/deep_research") / f"{slug}-deep-research.md"

    if output_path.exists() and not args.force and not args.dry_run:
        print(f"NG 출력 파일이 이미 있습니다. --force 사용: {output_path}")
        return 1

    # output 디렉터리 생성은 dry-run이 아닐 때만 (dry-run은 파일 시스템에 영향 없음)
    if not args.dry_run:
        output_path.parent.mkdir(parents=True, exist_ok=True)

    # 연구 자료 로드 (토큰 예산: brief ~1200자 + calibration ~2500자 = 여유 ~4300자)
    # brief+calibration이 주입되면 research_content 한도를 줄여 총 입력을 8000자 이내로 유지
    RESEARCH_CONTENT_LIMIT = 6000   # context 없을 때 기본 한도
    RESEARCH_CONTENT_LIMIT_WITH_CTX = 4000   # context 주입 시 한도
    # 실제 한도는 context 파일 로드 후 결정하므로 우선 6000으로 로드
    research_content = ""
    if args.research_pack and Path(args.research_pack).exists():
        raw = Path(args.research_pack).read_text(encoding="utf-8", errors="replace")
        research_content = raw[:RESEARCH_CONTENT_LIMIT]
        print(f"OK 연구 팩 로드: {args.research_pack} ({len(research_content)}자)")
    elif args.logos_capture and Path(args.logos_capture).exists():
        raw = Path(args.logos_capture).read_text(encoding="utf-8", errors="replace")
        research_content = raw[:RESEARCH_CONTENT_LIMIT]
        print(f"OK Logos 캡처 로드: {args.logos_capture} ({len(research_content)}자)")
    else:
        print("OK 연구 자료 없음 - 본문 정보만으로 분석합니다")

    # Ollama Quality Gate 결과 로드 (있으면 프롬프트에 포함)
    ollama_critique_section = ""
    if args.ollama_critique and Path(args.ollama_critique).exists():
        critique_raw = Path(args.ollama_critique).read_text(encoding="utf-8", errors="replace")
        ollama_critique_section = (
            "\n\n## Ollama 1차 분석 비판 목록 (Claude가 반드시 교정해야 할 항목)\n\n"
            "> 아래는 Ollama 1차 분석의 품질 게이트 실패 항목입니다.\n"
            "> 이 항목들은 신학 오류 또는 환각일 수 있습니다. 반드시 본문 기반으로 재분석하십시오.\n\n"
            + critique_raw
        )
        print(f"OK Ollama 비판 로드: {args.ollama_critique}")

    # v2.1 Research Context 로드 — BRIEF(전) + CALIBRATION(후) 분리 주입
    v21_brief_section = ""
    v21_calibration_section = ""
    CALIBRATION_MARKER = "<!-- V21_CALIBRATION_START -->"

    if args.research_context and Path(args.research_context).exists():
        ctx_raw = Path(args.research_context).read_text(encoding="utf-8", errors="replace")
        if CALIBRATION_MARKER in ctx_raw:
            brief_part, cal_part = ctx_raw.split(CALIBRATION_MARKER, 1)
            # 파일 헤더 제거: "# Title" 줄과 "> 메타데이터" 줄은 파일용이지 프롬프트용이 아님
            import re as _re
            brief_clean = _re.sub(r"^# [^\n]+\n+(?:>[^\n]+\n+)*", "", brief_part.strip())
            v21_brief_section = brief_clean.strip()
            v21_calibration_section = cal_part.strip()
        else:
            # 구버전 파일: 헤더 제거 후 전체를 brief 구역에 주입
            import re as _re
            brief_clean = _re.sub(r"^# [^\n]+\n+(?:>[^\n]+\n+)*", "", ctx_raw.strip())
            v21_brief_section = brief_clean.strip()

        print(
            f"OK v2.1 컨텍스트 로드: {args.research_context} "
            f"(brief {len(v21_brief_section)}자 | calibration {len(v21_calibration_section)}자)"
        )
        # context가 있으면 research_content 한도를 줄여 총 입력 예산 보호
        if research_content and len(research_content) > RESEARCH_CONTENT_LIMIT_WITH_CTX:
            research_content = research_content[:RESEARCH_CONTENT_LIMIT_WITH_CTX]
            print(f"OK 연구 자료 한도 조정: {RESEARCH_CONTENT_LIMIT_WITH_CTX}자 (context 주입으로 공간 확보)")
    else:
        print("OK v2.1 컨텍스트 없음 - 표준 프롬프트로 진행")

    # 시스템 프롬프트 로드
    prompts_dir = Path(args.prompts_dir)
    system = load_system_prompt(prompts_dir)
    print(f"OK 시스템 프롬프트 로드 ({len(system)}자)")

    # 프롬프트 빌드
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    research_section = (
        f"```\n{research_content}\n```" + ollama_critique_section
        if research_content
        else "(연구 자료 없음)" + ollama_critique_section
    )
    prompt = DEEP_RESEARCH_PROMPT.format(
        passage=args.passage,
        research_content=research_section,
        v21_brief=v21_brief_section,
        v21_calibration=v21_calibration_section,
        timestamp=timestamp,
        model=args.model,
        mode=args.mode.upper(),
    )

    # ── dry-run: API 호출 없이 프롬프트만 출력 ─────────────────────────────────
    if args.dry_run:
        total_chars = len(system) + len(prompt)
        token_est = total_chars // 4  # 한국어 포함 시 대략 4자/토큰
        sep = "=" * 60
        print(f"\n{sep}")
        print(f"  DRY-RUN - 실제 API 호출 없음")
        print(f"  본문: {args.passage} | 모델: {args.model} | 모드: {args.mode.upper()}")
        print(f"  시스템 프롬프트: {len(system):,}자")
        print(f"  사용자 프롬프트: {len(prompt):,}자")
        print(f"  총 입력: {total_chars:,}자 (~{token_est:,} 토큰 추정)")
        print(sep)
        print("\n[ 시스템 프롬프트 미리보기 - 처음 500자 ]\n")
        print(system[:500])
        print("\n... (생략) ...\n")
        print(f"[ 사용자 프롬프트 미리보기 - 처음 2000자 ]\n")
        print(prompt[:2000])
        if len(prompt) > 2000:
            print(f"\n... (이하 {len(prompt)-2000:,}자 생략) ...")
        print(f"\n{sep}")
        print(f"  API 호출: 건너뜀")
        print(f"  실제 실행: ANTHROPIC_API_KEY 설정 후 --dry-run 제거")
        print(sep)
        return 0

    print(f"\n{'='*50}")
    print(f"Claude 심층 연구: {args.passage} / {args.mode.upper()}")
    print(f"모델: {args.model}")
    print(f"{'='*50}\n")

    try:
        result = call_claude_api(api_key, system, prompt, args.model)
    except RuntimeError as e:
        print(f"NG 생성 실패: {e}")
        return 1

    # 저장
    if output_path.exists() and args.force:
        shutil.copy2(output_path, output_path.with_suffix(".bak"))

    temp = output_path.with_suffix(".tmp")
    temp.write_text(result, encoding="utf-8")
    if output_path.exists():
        output_path.unlink()
    temp.rename(output_path)

    print(f"\n{'='*50}")
    print(f"OK 저장 완료: {output_path}")
    print(f"   크기: {output_path.stat().st_size:,}바이트")
    print(f"{'='*50}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

