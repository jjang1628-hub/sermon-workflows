"""
Ollama 로컬 모델을 사용한 설교 연구 스크립트.
Logos 캡처 파일을 읽어 로컬 LLM으로 신학 분석 후 연구 파일을 생성합니다.

사용법:
    python scripts/run_local_research_with_ollama.py \
      --passage "요한복음 13:14" \
      --logos-capture .\\tmp\\logos-capture\\raw\\john-13-14-passage-guide-20260521.md \
      --output .\\output\\local_research\\jn-13-14-local-research.md \
      --model qwen3:8b \
      --research-mode quick

환경:
    Ollama가 설치되어 있어야 합니다 (http://localhost:11434)
    모델 설치: ollama pull qwen3:8b
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path

# Windows cp949 콘솔 깨짐 방지
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

OLLAMA_BASE_URL = "http://localhost:11434"

# 기본 fallback 시스템 프롬프트 (prompts/ollama_local_research.md 없을 때 사용)
_FALLBACK_SYSTEM_PROMPT = """\
당신은 제공된 Logos 캡처 자료만을 근거로 개혁주의 설교 연구 초안을 작성하는 1차 분석자입니다.

절대 규칙:
- 제공된 Logos 캡처에 없는 주석명, 저자명, 책 제목, 원어 사전명을 절대 생성하지 말라.
- 자료에 없으면 반드시 "[제공된 자료에서 확인되지 않음]"이라고 표시하라.
- 모든 해석 주장은 [본문] / [자료] / [추론] / [보류] 중 하나로 분류하라.

분석 관점:
- 창조-타락-구속-새창조 흐름 안에서 본문을 읽는다.
- Big Idea: "하나님께서 그리스도 안에서 무엇을 하시며, 우리는 어떻게 응답하는가"
- 적용: 복음의 은혜 먼저 → 동기 변화 → 순종의 열매 (명령이 먼저 오지 않는다)
- 인물 영웅화 금지. 그리스도 연결: 억지 알레고리 금지.

이 분석은 Logos 캡처 자료 기반 1차 초안입니다. 최종 신학 판단이 아닙니다.
"""


def load_system_prompt(prompts_dir: Path | None = None) -> str:
    """prompts/ollama_local_research.md를 로드한다. 없으면 fallback 사용."""
    candidates = []
    if prompts_dir:
        candidates.append(prompts_dir / "ollama_local_research.md")
    candidates.append(Path("prompts/ollama_local_research.md"))

    for candidate in candidates:
        if candidate.exists():
            content = candidate.read_text(encoding="utf-8", errors="replace")
            # Markdown 파일에서 실제 지시 텍스트 추출 (# 헤더 이후)
            return content
    return _FALLBACK_SYSTEM_PROMPT


RESEARCH_PROMPT_TEMPLATE = """\
아래 Logos 성경 연구 캡처 자료를 바탕으로 설교 준비용 연구 분석을 수행하세요.

중요: 제공된 Logos 캡처에 없는 주석명, 저자명, 책 제목을 절대 생성하지 마십시오.
자료에 없으면 "[제공된 자료에서 확인되지 않음]"이라고 표시하십시오.
모든 해석 주장에 [본문] / [자료] / [추론] / [보류] 레이블을 붙이십시오.

## 본문
{passage}

## 제공된 Logos 캡처 자료 ({capture_size}자)
{capture_content}

## 출력 형식

다음 Markdown 형식을 정확히 지켜서 출력하세요.

---

> ⚠️ 1차 초안 — 주석명·원어·신학 결론은 반드시 Logos와 Claude 심층 분석으로 검증하세요.
> 제공 자료에서 확인되지 않은 내용은 [제공된 자료에서 확인되지 않음]으로 표시됩니다.

# Logos 연구 자료 (로컬 분석)

## 기본 정보

- 본문: {passage}
- 자료 유형: logos-capture-local-analysis
- 분석 모델: {model}
- 정규화 일시: {timestamp}
- 캡처 파일: {capture_path}
- 캡처 크기: {capture_size}자 {capture_warning}

## 관찰 후보

각 항목에 [본문] / [자료] / [추론] / [보류] 레이블 필수:
- 본문 구조와 문학적 흐름
- 핵심 단어와 반복 표현
- 앞뒤 절 문맥 연결 (반드시 포함)

## 해석 참고 후보

각 항목에 [본문] / [자료] / [추론] / [보류] 레이블 필수:
- 제공된 자료에 실제로 나온 주석 내용 ([자료] 레이블)
- 주석이 없으면: "제공된 Logos 캡처 안에는 해당 주석 정보가 없습니다. [제공된 자료에서 확인되지 않음]"
- 신학 주제: 그리스도 연결은 본문 논리에서 자연스럽게 ([추론] 레이블)

## 적용 아이디어 후보

복음의 은혜 먼저 → 동기 변화 → 순종의 열매 순서로:
- 각 항목에 [본문] / [추론] / [보류] 레이블 필수

## 검토 필요

- 이 분석은 로컬 LLM({model}) 1차 초안입니다.
- 주석명, 저자명, 원어는 실제 Logos에서 반드시 확인하세요.
- [제공된 자료에서 확인되지 않음] 항목은 사용 전 반드시 검증하세요.

## 정리된 원문

본문 핵심 메시지, 구속사적 위치, 설교 Big Idea 후보 (본문 논리 기반):
"""


def check_ollama_available() -> tuple[bool, str]:
    try:
        req = urllib.request.Request(f"{OLLAMA_BASE_URL}/api/tags")
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read())
        models = [m["name"] for m in data.get("models", [])]
        return True, "Ollama 서버 실행 중. 모델 목록: " + (", ".join(models) if models else "(없음)")
    except urllib.error.URLError:
        return False, "Ollama 서버에 연결할 수 없습니다. 'ollama serve' 또는 Ollama 앱을 실행하세요."
    except Exception as e:
        return False, f"Ollama 확인 오류: {e}"


def list_ollama_models() -> list[str]:
    try:
        req = urllib.request.Request(f"{OLLAMA_BASE_URL}/api/tags")
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read())
        return [m["name"] for m in data.get("models", [])]
    except Exception:
        return []


def run_ollama_generate(model: str, system: str, prompt: str) -> str:
    # qwen3 계열은 thinking 모드를 비활성화해야 response 토큰이 정상 수신된다.
    # Ollama 0.5+ 에서 qwen3의 thinking 토큰은 chunk["thinking"]에 들어가고
    # chunk["response"]는 비어 있어 0바이트 출력 문제가 발생한다.
    is_qwen3 = "qwen3" in model.lower()
    payload_dict: dict = {
        "model": model,
        "system": system,
        "prompt": prompt,
        "stream": True,
        "options": {
            "temperature": 0.3,
            "num_predict": 4096,
        },
    }
    if is_qwen3:
        payload_dict["think"] = False  # thinking 모드 비활성화

    payload = json.dumps(payload_dict).encode("utf-8")

    req = urllib.request.Request(
        f"{OLLAMA_BASE_URL}/api/generate",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    full_response = []
    try:
        with urllib.request.urlopen(req, timeout=300) as resp:
            for line in resp:
                if not line.strip():
                    continue
                try:
                    chunk = json.loads(line)
                    token = chunk.get("response", "")
                    full_response.append(token)
                    try:
                        print(token, end="", flush=True)
                    except UnicodeEncodeError:
                        # Windows cp949 콘솔에서 인코딩 불가 문자 → 무시
                        print("?", end="", flush=True)
                    if chunk.get("done"):
                        break
                except json.JSONDecodeError:
                    continue
    except urllib.error.URLError as e:
        raise RuntimeError(f"Ollama API 오류: {e}") from e

    print()
    return "".join(full_response)


# ──────────────────────────────────────────────────────
# Ollama Output Quality Gate v2 — Keyword + Logic 2층 구조
# ──────────────────────────────────────────────────────

# 알려진 환각 유발 패턴 (Logos 캡처에 없는데 모델이 자주 생성하는 것들)
_HALLUCINATION_INDICATOR_PATTERNS = [
    r"고신총회",
    r"IBT 신학",
    r"CLC 신약 주석 시리즈",
    r"신약의 구약사용 주석",
    r"대한예수교장로회 고신",
    r"기독교문서선교회 주석",
    r"합신대학원 주석",
]

# Capture Sufficiency 등급
_CAPTURE_GRADES = [
    (2_000,  "Quick only — Standard/Deep 불가",        "quick_only"),
    (6_000,  "Standard limited — 주석 추가 권장",       "standard_limited"),
    (15_000, "Standard ok / Deep limited",             "standard_ok"),
    (999_999, "Deep eligible — 모든 모드 가능",          "deep_eligible"),
]


def _near_check(text: str, triggers: list[str], context_words: list[str],
                window: int = 300) -> bool:
    """triggers 중 하나가 context_words 중 하나와 window 문자 이내에 공존하는지 확인."""
    tl = text.lower()
    for trigger in triggers:
        tl_trigger = trigger.lower()
        idx = 0
        while True:
            pos = tl.find(tl_trigger, idx)
            if pos == -1:
                break
            neighborhood = tl[max(0, pos - window): pos + len(tl_trigger) + window]
            if any(cw.lower() in neighborhood for cw in context_words):
                return True
            idx = pos + 1
    return False


def assess_capture_sufficiency(capture_size: int) -> dict:
    """캡처 자료 크기 등급 평가."""
    for threshold, label, code in _CAPTURE_GRADES:
        if capture_size < threshold:
            pass_flag = code != "quick_only"
            return {
                "id": "QG-CAP",
                "name": "캡처 충분성",
                "pass": pass_flag,
                "detail": f"{capture_size}자 → {label}",
                "grade_code": code,
            }
    return {"id": "QG-CAP", "name": "캡처 충분성", "pass": True,
            "detail": f"{capture_size}자 → Deep eligible", "grade_code": "deep_eligible"}


def assess_quality_gate(
    result: str,
    passage: str,
    capture_content: str,
    capture_size: int = 0,
) -> tuple[list[dict], str, str]:
    """
    Ollama 결과물 품질을 평가한다. (Keyword Gate + Logic Gate 2층)
    Returns: (gate_results, final_verdict, verdict_code)
    """
    r = result.lower()
    c = capture_content.lower()

    # ── QG-CAP: 캡처 충분성 ───────────────────────────────
    qg_cap = assess_capture_sufficiency(capture_size or len(capture_content))

    # ── QG-01: 본문 문맥 반영 (Keyword) ──────────────────
    context_refs: list[str] = []
    verse_match = re.search(r"(\d+):(\d+)", passage)
    if verse_match:
        chap = int(verse_match.group(1))
        vnum = int(verse_match.group(2))
        for v in range(max(1, vnum - 5), vnum + 5):
            if v != vnum:
                ref = f"{chap}:{v}"
                if ref in result:
                    context_refs.append(ref)
    qg01_pass = len(context_refs) >= 1
    qg01_detail = f"인접 절 언급: {context_refs}" if context_refs else "인접 절 언급 없음"

    # ── QG-02: 핵심 구절 반영 (Keyword) ──────────────────
    verse_kws: list[str] = []
    if "발" in r: verse_kws.append("발")
    if "씻" in r: verse_kws.append("씻")
    if "주" in r and "선생" in r: verse_kws.append("주·선생")
    if "마땅" in r or "옳" in r: verse_kws.append("마땅/옳")
    qg02_pass = len(verse_kws) >= 2
    qg02_detail = f"핵심 단어: {verse_kws}" if verse_kws else "핵심 단어 부족"

    # ── QG-03: 은혜→순종 구조 (Logic) ────────────────────
    has_grace = any(kw in r for kw in ["은혜", "먼저", "씻김 받", "사랑하시되", "먼저 씻", "먼저 사랑"])
    has_obedience = any(kw in r for kw in ["순종", "열매", "명령", "마땅", "서로 씻"])
    logic_marker = "ὅτι" in result or "그러므로" in result or "때문에" in r or "[추론]" in result
    # Logic: 은혜가 순종 앞에 와야 함 — "씻었으니 → 너희도" 패턴
    grace_first_logic = _near_check(
        result,
        ["씻었으니", "내가 씻", "먼저 씻", "먼저 사랑", "은혜"],
        ["너희도", "서로 씻", "따라서", "그러므로", "마땅", "순종"],
    )
    qg03_pass = (has_grace and has_obedience) or logic_marker or grace_first_logic
    qg03_detail = (
        f"은혜({'있음' if has_grace else '없음'}) + 순종({'있음' if has_obedience else '없음'})"
        + (" / 선행-응답 논리 있음" if grace_first_logic else "")
        + (" / 논리 접속사" if logic_marker else "")
    )

    # ── QG-04: 그리스도 중심 연결 (Keyword) ──────────────
    christ_terms = ["십자가", "그리스도", "구속", "성육신", "예수님의",
                    "하나님의 아들", "대속", "구원", "낮아지심", "부활"]
    christ_found = [t for t in christ_terms if t in r]
    qg04_pass = len(christ_found) >= 1
    qg04_detail = f"그리스도 용어: {christ_found[:3]}" if christ_found else "그리스도 연결 없음"

    # ── QG-05: 환각 자료 감지 ────────────────────────────
    hallucinated: list[str] = []
    for pat in _HALLUCINATION_INDICATOR_PATTERNS:
        if re.search(pat, result):
            hallucinated.append(re.sub(r"\\", "", pat))
    cited_authors = re.findall(r"[–\-]\s*([가-힣A-Za-z\s\.]+)\s*\(\d{4}\)", result)
    for author in cited_authors:
        a = author.strip()
        if a and a.lower() not in c:
            hallucinated.append(f"저자?:{a}")
    qg05_pass = len(hallucinated) == 0
    qg05_detail = f"환각 의심: {hallucinated[:3]}" if hallucinated else "환각 패턴 없음"

    # ── QG-ETHICS: 섬김 윤리 축소 경고 (Logic) ───────────
    has_ethics_lang = any(t in r for t in ["섬김", "겸손", "낮아짐", "섬기"])
    has_gospel_balance = any(t in r for t in ["은혜", "구원", "십자가", "복음", "씻김 받"])
    ethics_reduction = has_ethics_lang and not has_gospel_balance
    qg_ethics_pass = not ethics_reduction
    qg_ethics_detail = ("섬김 윤리 단독 사용 — 복음 연결 없음 ⚠️"
                        if ethics_reduction else "윤리+복음 균형 또는 윤리 단독 없음")

    # ── QG-06: 종합 판정 (computed) ──────────────────────
    base_fails = sum([not qg01_pass, not qg02_pass, not qg03_pass, not qg04_pass])
    has_hallucination = not qg05_pass

    if has_hallucination:
        verdict = "직접 사용 금지 — 환각 주석 제거 후 Claude 심층 분석 필수"
        verdict_code = "direct_use_forbidden"
    elif base_fails >= 3 or qg_cap["grade_code"] == "quick_only":
        verdict = "재캡처 권장 — 본문 자료 부족 또는 문맥 실패, Claude 보강 필수"
        verdict_code = "recapture_required"
    elif base_fails >= 1 or ethics_reduction:
        verdict = "Claude 심층 분석 필수 — 신학 보강 필요"
        verdict_code = "claude_required"
    else:
        verdict = "초안 사용 가능 — Claude 보강 권장"
        verdict_code = "draft_usable"

    gate_results: list[dict] = [
        qg_cap,
        {"id": "QG-01", "name": "본문 문맥 반영 [K]",    "pass": qg01_pass, "detail": qg01_detail},
        {"id": "QG-02", "name": "핵심 구절 반영 [K]",    "pass": qg02_pass, "detail": qg02_detail},
        {"id": "QG-03", "name": "은혜→순종 구조 [L]",    "pass": qg03_pass, "detail": qg03_detail},
        {"id": "QG-04", "name": "그리스도 연결 [K]",     "pass": qg04_pass, "detail": qg04_detail},
        {"id": "QG-05", "name": "환각 자료 감지",         "pass": qg05_pass, "detail": qg05_detail},
        {"id": "QG-ETH", "name": "섬김 윤리 축소 경고 [L]", "pass": qg_ethics_pass, "detail": qg_ethics_detail},
        {"id": "QG-06", "name": "종합 판정",              "pass": None,      "detail": verdict},
    ]

    # ── 요한복음 13장 전용: Keyword + Logic ───────────────
    if "요한복음 13" in passage or "jn-13" in passage.lower():
        # QG-J131-K: 13:1 키워드 존재
        j131_kw = ["13:1", "끝까지 사랑", "사랑하시되 끝까지"]
        j131_k = any(kw in result for kw in j131_kw)
        gate_results.append({"id": "QG-J131-K", "name": "요 13:1 언급 [K]",
                              "pass": j131_k, "detail": f"{'발견' if j131_k else '누락'}: 끝까지 사랑"})

        # QG-J131-L: 13:1이 세족 단락 해석 액자로 사용됨
        j131_l = j131_k and _near_check(
            result, j131_kw,
            ["세족", "발을 씻", "배경", "문맥", "때문에", "사랑이", "사랑에서",
             "토대", "출발", "시작", "이유", "근거", "아가페"],
        )
        gate_results.append({"id": "QG-J131-L", "name": "요 13:1 해석 액자 [L]",
                              "pass": j131_l,
                              "detail": ("13:1이 세족 해석의 액자로 사용됨"
                                         if j131_l else "13:1 언급만 있고 해석 연결 없음 또는 누락")})

        # QG-J133-K: 13:3 키워드 (아버지께로 가심 — 자발적 낮아짐)
        j133_kw = ["13:3", "아버지께로", "아버지께 돌아", "돌아가실"]
        j133_k = any(kw in result for kw in j133_kw)
        gate_results.append({"id": "QG-J133-K", "name": "요 13:3 언급 [K]",
                              "pass": j133_k, "detail": f"{'발견' if j133_k else '누락'}: 아버지께로 가심"})

        # QG-J138-K: 13:8 키워드 존재
        j138_kw = ["13:8", "씻어 주지 않으면", "상관이 없느니라", "내가 씻어 주지"]
        j138_k = any(kw in result for kw in j138_kw)
        gate_results.append({"id": "QG-J138-K", "name": "요 13:8 언급 [K]",
                              "pass": j138_k, "detail": f"{'발견' if j138_k else '누락'}: 씻어 주지 않으면"})

        # QG-J138-L: 13:8이 정결/관계/구원론과 연결됨
        j138_l = j138_k and _near_check(
            result, j138_kw,
            ["관계", "정결", "구원", "참여", "연결", "상관", "씻김"],
        )
        gate_results.append({"id": "QG-J138-L", "name": "요 13:8 구원론적 연결 [L]",
                              "pass": j138_l,
                              "detail": ("씻김이 예수와의 관계/정결과 연결됨"
                                         if j138_l else "13:8 언급만 있고 구원론 연결 없음 또는 누락")})

        # QG-J1414-L: 13:14 "내가 씻었으니 → 너희도" 은혜 선행 구조
        j1414_l = _near_check(
            result,
            ["씻었으니", "내가 씻", "먼저 씻어"],
            ["너희도", "서로 씻", "따라서", "마땅", "은혜에서", "은혜로"],
        )
        gate_results.append({"id": "QG-J1414-L", "name": "13:14 선행 은혜→응답 [L]",
                              "pass": j1414_l,
                              "detail": ("은혜 선행 → 응답 순종 논리 있음"
                                         if j1414_l else "선행 은혜 구조 미확인 — 명령 중심 설교 위험")})

        # 요 13 전용 Claude 필수 여부: 13:8 누락이면 require_claude 강화
        if not j138_k:
            if verdict_code not in ("direct_use_forbidden", "recapture_required"):
                verdict_code = "claude_required"
                verdict = "Claude 심층 분석 필수 — 요 13:8 구원론적 씻김 누락"
                gate_results[-1 - gate_results[::-1].index(
                    next(g for g in gate_results if g["id"] == "QG-06")
                )]["detail"] = verdict

    return gate_results, verdict, verdict_code


def build_quality_gate_report(
    gate_results: list[dict], passage: str, model: str,
    verdict: str = "", verdict_code: str = "",
) -> str:
    """Quality Gate 결과 Markdown 보고서 (Keyword/Logic 2층 구조 표시)."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    require_claude = verdict_code in ("direct_use_forbidden", "recapture_required", "claude_required")

    lines = [
        "",
        "---",
        "",
        "## Ollama Output Quality Gate v2",
        "",
        f"- **본문**: {passage}",
        f"- **모델**: {model}",
        f"- **검증 일시**: {timestamp}",
        f"- **verdict_code**: `{verdict_code}`",
        f"- **require_claude_deep_research**: `{'true' if require_claude else 'false'}`",
        "",
        "> [K] = Keyword Gate (단어 존재 확인)  [L] = Logic Gate (논리 반영 확인)",
        "",
        "| ID | 항목 | 결과 | 세부 내용 |",
        "|----|------|------|----------|",
    ]
    for r in gate_results:
        if r["pass"] is None:
            icon = "🔵"
        elif r["pass"]:
            icon = "✅"
        else:
            icon = "❌"
        lines.append(f"| {r['id']} | {r['name']} | {icon} | {r['detail']} |")

    lines += [
        "",
        f"**최종 판정**: {verdict}",
        "",
        "> 이 게이트는 키워드·패턴 기반 자동 평가입니다. 최종 판단은 목사님이 직접 하세요.",
    ]
    return "\n".join(lines)


def validate_capture(capture_path: Path, must_contain: list[str]) -> tuple[bool, list[str]]:
    if not capture_path.exists():
        return False, [f"파일 없음: {capture_path}"]
    content = capture_path.read_text(encoding="utf-8", errors="replace")
    missing = [kw for kw in must_contain if kw not in content]
    return len(missing) == 0, missing


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


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Ollama 로컬 모델로 Logos 캡처를 분석하여 설교 연구 파일을 생성합니다."
    )
    parser.add_argument("--passage", default="", help="성경 본문 (예: 요한복음 13:14)")
    parser.add_argument("--logos-capture", default=None, help="Logos 캡처 파일 경로")
    parser.add_argument("--output", default=None, help="출력 파일 경로")
    parser.add_argument("--model", default="qwen3:8b", help="Ollama 모델 이름")
    parser.add_argument("--research-mode", choices=["quick", "full"], default="quick")
    parser.add_argument("--validate-capture", action="store_true")
    parser.add_argument("--capture-must-contain", action="append", default=[], metavar="TEXT")
    parser.add_argument("--missing-data-policy", choices=["error", "limited", "skip"], default="limited")
    parser.add_argument("--allow-limited-analysis", action="store_true")
    parser.add_argument("--check-ollama", action="store_true")
    parser.add_argument("--force", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    if args.check_ollama:
        ok, msg = check_ollama_available()
        print(("OK " if ok else "NG ") + msg)
        if ok:
            models = list_ollama_models()
            if any(args.model in m for m in models):
                print(f"OK 모델 '{args.model}' 사용 가능")
            else:
                print(f"NG 모델 '{args.model}' 미설치. 'ollama pull {args.model}' 실행 필요")
                print(f"   설치된 모델: {', '.join(models) if models else '없음'}")
        return 0 if ok else 1

    # Ollama 서버 확인
    ok, msg = check_ollama_available()
    if not ok:
        print(f"NG {msg}")
        return 1
    print(f"OK {msg}")

    # 모델 확인
    models = list_ollama_models()
    actual_model = next((m for m in models if args.model in m), None)
    if not actual_model:
        print(f"NG 모델 '{args.model}' 미설치. 'ollama pull {args.model}' 실행 후 다시 시도하세요.")
        print(f"   설치된 모델: {', '.join(models) if models else '없음'}")
        return 1
    print(f"OK 모델: {actual_model}")

    # 캡처 파일
    capture_content = ""
    capture_path_str = args.logos_capture or ""

    if args.logos_capture:
        capture_path = Path(args.logos_capture)
        if args.validate_capture or args.capture_must_contain:
            valid, missing = validate_capture(capture_path, args.capture_must_contain)
            if not valid:
                print(f"NG 캡처 파일 검사 실패. 누락 항목: {missing}")
                if args.missing_data_policy == "error":
                    return 1
                elif args.missing_data_policy == "skip":
                    print("   정책: skip")
                    return 0
                else:
                    if not args.allow_limited_analysis:
                        print("   정책: limited (--allow-limited-analysis 없음) — 중단")
                        return 1
                    print("   정책: limited — 제한적 분석 진행")

        if capture_path.exists():
            raw = capture_path.read_text(encoding="utf-8", errors="replace")
            capture_content = raw[:8000] + ("\n\n[... 이하 생략 ...]" if len(raw) > 8000 else "")
            print(f"OK 캡처 파일 로드: {capture_path} ({len(capture_content)}자)")
        else:
            print(f"NG 캡처 파일 없음: {capture_path}")
            if args.missing_data_policy == "error":
                return 1
    else:
        print("NG Logos 캡처 파일 없음 — 본문 정보만으로 분석합니다")

    # 출력 경로
    slug = slugify(args.passage) if args.passage else "passage"
    if args.output:
        output_path = Path(args.output)
    else:
        output_path = Path("output/local_research") / f"{slug}-local-research.md"
    quality_gate_path = output_path.parent / f"{slug}-quality-gate.md"

    if output_path.exists() and not args.force:
        print(f"NG 출력 파일이 이미 있습니다. --force 사용: {output_path}")
        return 1

    output_path.parent.mkdir(parents=True, exist_ok=True)

    # 시스템 프롬프트 로드 (prompts/ollama_local_research.md 우선)
    system_prompt = load_system_prompt(Path("prompts"))
    print(f"OK 시스템 프롬프트 로드 ({len(system_prompt)}자)")

    # 프롬프트 빌드
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    capture_size = len(capture_content)
    capture_warning = "⚠️ 캡처 자료 부족 (2,000자 미만) — 추가 캡처 권장" if capture_size < 2000 else ""
    capture_section = (
        f"```\n{capture_content}\n```" if capture_content
        else "(Logos 캡처 자료 없음 — 본문 정보만 사용)"
    )
    prompt = RESEARCH_PROMPT_TEMPLATE.format(
        passage=args.passage or "(본문 미지정)",
        capture_content=capture_section,
        capture_size=capture_size,
        capture_warning=capture_warning,
        model=actual_model,
        timestamp=timestamp,
        capture_path=capture_path_str,
    )

    # 실행
    print(f"\n{'='*50}")
    print(f"모델: {actual_model} | 본문: {args.passage} | 모드: {args.research_mode}")
    print(f"{'='*50}\n")

    try:
        result = run_ollama_generate(actual_model, system_prompt, prompt)
    except RuntimeError as e:
        print(f"\nNG 생성 실패: {e}")
        return 1

    # 빈 결과 방어
    if not result.strip():
        print("\n⚠️ 모델 응답이 비어 있음 — 진단 템플릿을 저장합니다.")
        timestamp_now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        result = (
            f"# Logos 연구 자료 (로컬 분석 — 모델 응답 없음)\n\n"
            f"- 본문: {args.passage or '(본문 미지정)'}\n"
            f"- 모델: {actual_model}\n"
            f"- 일시: {timestamp_now}\n\n"
            f"## 진단\n\n"
            f"모델이 응답을 생성하지 못했습니다.\n"
            f"가능한 원인: qwen3 think 모드 충돌 / RAM 부족 / 컨텍스트 초과\n\n"
            f"조치: `--skip-ollama`로 건너뛰거나 `ollama run {actual_model} \"안녕\"` 확인\n\n"
            f"⚠️ 이 자료는 연구 보조 자료입니다.\n"
        )

    # Quality Gate 실행
    gate_results, verdict, verdict_code = assess_quality_gate(
        result, args.passage, capture_content, capture_size=capture_size
    )
    gate_report = build_quality_gate_report(
        gate_results, args.passage, actual_model,
        verdict=verdict, verdict_code=verdict_code,
    )

    # 결과 파일 저장 (본문 + Quality Gate 통합)
    final_content = result + gate_report

    if output_path.exists() and args.force:
        import shutil
        shutil.copy2(output_path, output_path.with_suffix(".bak"))

    temp = output_path.with_suffix(".tmp")
    temp.write_text(final_content, encoding="utf-8")
    if output_path.exists():
        output_path.unlink()
    temp.rename(output_path)

    # Quality Gate 요약 별도 저장 (오케스트레이터가 읽음)
    require_claude = verdict_code in ("direct_use_forbidden", "recapture_required", "claude_required")
    gate_summary_lines = [
        f"# Ollama Quality Gate — {args.passage}",
        f"",
        f"- 모델: {actual_model}",
        f"- 최종 판정: {verdict}",
        f"- verdict_code: {verdict_code}",
        f"- require_claude_deep_research: {'true' if require_claude else 'false'}",
        f"",
        "## 실패 항목",
        "",
    ]
    failed = [r for r in gate_results if r["pass"] is False]
    if failed:
        for r in failed:
            gate_summary_lines.append(f"- [{r['id']}] {r['name']}: {r['detail']}")
    else:
        gate_summary_lines.append("- 없음")
    gate_summary = "\n".join(gate_summary_lines)

    qg_temp = quality_gate_path.with_suffix(".tmp")
    qg_temp.write_text(gate_summary, encoding="utf-8")
    if quality_gate_path.exists():
        quality_gate_path.unlink()
    qg_temp.rename(quality_gate_path)

    # 결과 출력
    print(f"\n{'='*50}")
    print(f"OK 저장 완료: {output_path}")
    print(f"   크기: {output_path.stat().st_size:,}바이트")
    print(f"OK Quality Gate: {verdict}")
    for r in gate_results:
        icon = "OK" if r["pass"] else ("NG" if r["pass"] is False else "--")
        print(f"   {icon} [{r['id']}] {r['name']}: {r['detail']}")
    print(f"OK Quality Gate 파일: {quality_gate_path}")
    print(f"{'='*50}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
