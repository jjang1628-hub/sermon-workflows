"""
build_v21_research_context.py — v2.1 Research Context Builder  (v2)

세 가지 gate 출력 파일을 통합하여 Claude 심층 연구용 컨텍스트를 생성한다:
  - 03-logos-coverage-report.md  → Coverage Score + 미수집 카테고리
  - 04-capture-quality-report.md → Quality Score + 자료군 강도 분류
  - 05-logos-integration-summary.md → 목사님 통찰 + Big Idea + Deep Research 질문

출력: docs/{book}/{passage}/06-research-context.md

파일 구조 (두 구역으로 분리):
  ─── BRIEF 구역 ───
  Gate Summary · 자료군 강도 지도 · 설교 Big Idea · 해석 경계선
  → 20-Pass 시작 전 주입: 모든 Pass를 안내하는 핵심 제약

  ─── CALIBRATION 구역 (<!-- V21_CALIBRATION_START --> 마커 이후) ───
  Per-Pass Calibration 표 · 목사님 질문(또는 자동 생성 질문) · 보강 필요 상세
  → Pass 20 직후 주입: 생성된 분석을 품질 신호 대비 자체감사

사용법:
    python scripts/build_v21_research_context.py --passage docs/john/13-14/00-passage.yaml
    python scripts/build_v21_research_context.py --passage docs/john/13-14/00-passage.yaml --force
"""

from __future__ import annotations

import argparse
import re
import shutil
import sys
from datetime import datetime
from pathlib import Path

from pipeline_utils import load_yaml_simple  # noqa: E402


# ─────────────────────────────────────────────────────────────────────────────
# 상수: Logos 품질 카테고리 → 20-Pass 번호 매핑
# ─────────────────────────────────────────────────────────────────────────────

CATEGORY_TO_PASS: dict[str, str] = {
    "원어·문법":      "Pass 4–5 (핵심 단어·원어 심층)",
    "역사·문화 배경":  "Pass 6 (역사·문화 배경)",
    "구조·담화":      "Pass 3, 7 (구조 분석·문학 흐름)",
    "주석 비교":      "Pass 12 (주석 비교)",
    "교차본문":       "Pass 15 (교차 참조)",
    "성경신학":       "Pass 10–11, 13 (구속사·그리스도 연결·신학 주제)",
    "목회·적용":      "Pass 17–19 (현대 적용·Big Idea·적용 구조)",
}

# ─────────────────────────────────────────────────────────────────────────────
# 상수: 누락 요소 → 구체적 신학 질문 자동 생성 매핑
# ─────────────────────────────────────────────────────────────────────────────

WEAK_ELEMENT_AUTO_QUESTIONS: dict[str, str] = {
    # 주석 비교
    "interpretive_comparison": (
        "Carson, Keener, Morris 중 이 본문 해석의 핵심 차이점은 무엇인가? "
        "어느 견해가 본문 문맥에 더 충실하며, 설교 Big Idea에 어떤 영향을 주는가?"
    ),
    "interpretive_summary": (
        "이 본문에 대해 주석들이 공통적으로 강조하는 신학 포인트는 무엇인가? "
        "이견이 있는 부분은 무엇이며 그 이견의 신학적 함의는?"
    ),
    "sermon_application": (
        "주석의 분석이 설교 Big Idea를 어떻게 강화하거나 수정하는가? "
        "주석이 제시하는 본문 핵심이 강단에 어떻게 적용되어야 하는가?"
    ),
    # 성경신학
    "christ_fulfillment": (
        "이 본문이 그리스도의 어떤 구체적 사역(십자가·부활·현재 간구)으로 이어지는가? "
        "억지 알레고리 없이 본문 자체의 언어와 논리 안에서만 연결하라."
    ),
    "anti_allegory": (
        "이 본문에서 억지 알레고리 위험이 가장 높은 요소는 무엇인가? "
        "어떤 해석이 본문 의도를 벗어나 투영하는 것이며, 어떤 경계를 지켜야 하는가?"
    ),
    "covenant_connection": (
        "이 본문은 구약의 어떤 언약 주제(아브라함·모세·다윗·새 언약)와 연결되는가? "
        "그 연결이 본문 자체의 언어에서 지지되는가, 아니면 외부에서 가져온 것인가?"
    ),
    "redemptive_history": (
        "창조–타락–구속–새창조 흐름에서 이 본문은 정확히 어디에 위치하는가? "
        "이 위치가 설교의 무게 중심(진단·선언·촉구)을 어떻게 결정하는가?"
    ),
    # 목회·적용
    "false_gospel_diagnosis": (
        "오늘 한국 청중이 이 본문을 들을 때 자기구원으로 이동하는 방식은 무엇인가? "
        "성과 지향·인정 욕구·도덕적 자부심·종교적 수행 중 어느 거짓 복음이 가장 강하게 작동하는가?"
    ),
    "gospel_motive": (
        "이 본문의 명령·권고는 복음의 은혜로부터 어떻게 흘러나오는가? "
        "'이기 위해'가 아닌 '이미 받았기에'의 구조가 이 본문에서 어떻게 작동하며, "
        "설교에서 그 전환점은 어디인가?"
    ),
    "one_obedience": (
        "이 본문이 오늘 청중에게 요구하는 가장 구체적이고 단순한 한 가지 순종은 무엇인가? "
        "그것이 복음의 은혜에서 자연스럽게 나오는 응답인지 확인하라."
    ),
    # 교차본문
    "connection_reason": (
        "이 본문과 연결되는 핵심 교차 본문들의 연결 이유를 명확히 설명하라. "
        "주제 연결인가, 언어·단어 연결인가, 구속사 연결인가? 각각 어떤 근거인가?"
    ),
    "canonical_direction": (
        "이 본문은 구약을 향해 소급하는가(예표·약속), 아니면 신약을 향해 전진하는가(성취·응용)? "
        "정경적 방향이 설교의 주안점에 어떤 영향을 주는가?"
    ),
    "risk_check": (
        "교차 본문 중 무리하게 연결된 것이 있는가? "
        "어떤 연결이 본문 문맥을 벗어나며, 설교에서 제외해야 할 연결은 무엇인가?"
    ),
}


# load_yaml_simple: pipeline_utils 에서 import됨


# ─────────────────────────────────────────────────────────────────────────────
# Section parser (handles both old/new 05 formats)
# ─────────────────────────────────────────────────────────────────────────────

def parse_sections(content: str) -> dict[str, str]:
    """## 섹션 제목 → 본문 텍스트 딕셔너리로 파싱.
    섹션 번호(1. 2. 3...) 제거, 키워드만 남긴다."""
    sections: dict[str, str] = {}
    parts = re.split(r"(?m)^## ", content)
    for part in parts[1:]:
        lines = part.split("\n")
        raw_title = lines[0].strip()
        title = re.sub(r"^\d+\.\s*", "", raw_title).strip()
        body = "\n".join(lines[1:]).strip()
        body = re.sub(r"<!--.*?-->", "", body, flags=re.DOTALL).strip()
        sections[title] = body
    return sections


def find_section(sections: dict[str, str], *keywords: str) -> str:
    """키워드 중 하나를 제목에 포함하는 첫 섹션의 본문을 반환.
    빈 번호 줄(플레이스홀더)은 필터링한다."""
    for title, body in sections.items():
        if any(kw in title for kw in keywords):
            lines = [
                ln for ln in body.splitlines()
                if ln.strip() and not re.match(r"^\d+\.\s*$", ln.strip())
            ]
            return "\n".join(lines)
    return ""


# ─────────────────────────────────────────────────────────────────────────────
# Coverage report parser
# ─────────────────────────────────────────────────────────────────────────────

def parse_coverage_report(path: Path) -> dict:
    result: dict = {
        "score": 0,
        "status": "unknown",
        "missing": [],   # list of {"name": str, "max": int, "earned": int}
        "passing": [],
    }
    if not path.exists():
        return result

    content = path.read_text(encoding="utf-8", errors="replace")

    m = re.search(r"###\s+(\d+)\s*/\s*100점", content)
    if m:
        result["score"] = int(m.group(1))

    m = re.search(r"-\s*status:\s*`([^`]+)`", content)
    if m:
        result["status"] = m.group(1)

    # 항목별 점수 table: | 항목 | 배점 | 획득 | 상태 |
    for row in re.finditer(
        r"\|\s*\*{0,2}([^|*]+?)\*{0,2}\s*\|\s*(\d+)\s*\|\s*(\d+)\s*\|\s*(✅|❌)\s*\|",
        content,
    ):
        name = row.group(1).strip()
        if name.lower() in ("항목", "합계"):
            continue
        entry = {"name": name, "max": int(row.group(2)), "earned": int(row.group(3))}
        if "❌" in row.group(4):
            result["missing"].append(entry)
        else:
            result["passing"].append(entry)

    return result


# ─────────────────────────────────────────────────────────────────────────────
# Quality report parser
# ─────────────────────────────────────────────────────────────────────────────

def parse_quality_report(path: Path) -> dict:
    result: dict = {
        "score": 0,
        "status": "unknown",
        "categories": [],  # list of {name, max, earned, ratio, strength}
        "weak": [],        # list of {name, missing_elements, warnings}
    }
    if not path.exists():
        return result

    content = path.read_text(encoding="utf-8", errors="replace")

    m = re.search(r"###\s+(\d+)\s*/\s*100점", content)
    if m:
        result["score"] = int(m.group(1))

    m = re.search(r"-\s*status:\s*`([^`]+)`", content)
    if m:
        result["status"] = m.group(1)

    # 자료군별 품질 table
    for row in re.finditer(
        r"\|\s*\*{0,2}([^|*]+?)\*{0,2}\s*\|\s*(\d+)\s*\|\s*(\d+)\s*\|[^|]+\|[^|]+\|",
        content,
    ):
        name = row.group(1).strip()
        if name.lower() in ("자료군", "합계"):
            continue
        max_pts = int(row.group(2))
        earned  = int(row.group(3))
        if max_pts == 0:
            continue
        ratio = earned / max_pts
        strength = "STRONG" if ratio >= 0.8 else ("MEDIUM" if ratio >= 0.5 else "WEAK")
        result["categories"].append(
            {"name": name, "max": max_pts, "earned": earned, "ratio": ratio, "strength": strength}
        )

    # Weak Categories subsections
    wc_m = re.search(r"## Weak Categories\n(.*?)(?=\n## |\Z)", content, re.DOTALL)
    if wc_m:
        for sub in re.split(r"\n### ", wc_m.group(1)):
            if not sub.strip():
                continue
            header = sub.split("\n")[0].strip()
            name_m = re.match(r"(.+?)\s*\(\d+/\d+점\)", header)
            if not name_m:
                continue
            result["weak"].append({
                "name": name_m.group(1).strip(),
                "missing_elements": re.findall(r"-\s*missing_required_elements:\s*(\S+)", sub),
                "warnings": re.findall(r"-\s*경고:\s*(.+)", sub),
            })

    return result


# ─────────────────────────────────────────────────────────────────────────────
# Integration summary parser
# ─────────────────────────────────────────────────────────────────────────────

def parse_integration_summary(path: Path) -> dict:
    result: dict = {
        "big_idea": "",
        "pastor_questions": [],  # 목사님 직접 작성 질문
        "red_lines": [],         # 도덕주의·알레고리 경계
        "christ_connection": "",
        "core_insights": [],
    }
    if not path.exists():
        return result

    content = path.read_text(encoding="utf-8", errors="replace")
    sections = parse_sections(content)

    # Big Idea: 전용 섹션 우선, 없으면 inline 검색
    bi_text = find_section(sections, "Big Idea", "빅 아이디어")
    if bi_text:
        for line in bi_text.splitlines():
            clean = line.strip().lstrip("-*> ").strip()
            if clean:
                result["big_idea"] = clean
                break
    if not result["big_idea"]:
        m = re.search(r"Big Idea[^:\n]*:\s*(.+)", content)
        if m:
            result["big_idea"] = m.group(1).strip().strip('"*>').strip()

    # Red lines
    red_text = find_section(sections, "도덕주의", "경고", "경계", "알레고리")
    if red_text:
        lines = [ln.strip().lstrip("-*> ").strip() for ln in red_text.splitlines() if ln.strip()]
        result["red_lines"] = [ln for ln in lines if len(ln) > 8]

    # Christ connection
    christ_text = find_section(sections, "그리스도 연결", "Christ", "구속사")
    if christ_text:
        result["christ_connection"] = christ_text[:600]

    # Core insights
    insight_text = find_section(sections, "핵심 통찰", "발견한 것", "반드시 반영")
    if insight_text:
        lines = [ln.strip().lstrip("-*0123456789. ").strip() for ln in insight_text.splitlines() if ln.strip()]
        result["core_insights"] = [ln for ln in lines if len(ln) > 8][:5]

    # Pastor's Deep Research questions (Section 6 of new template)
    q_text = find_section(sections, "Deep Research에 요청", "요청할 것", "불확실한 해석")
    if q_text:
        lines = [ln.strip().lstrip("-*0123456789. ").strip() for ln in q_text.splitlines() if ln.strip()]
        result["pastor_questions"] = [ln for ln in lines if len(ln) > 8][:8]

    return result


# ─────────────────────────────────────────────────────────────────────────────
# Auto question generator (when pastor Section 6 is blank)
# ─────────────────────────────────────────────────────────────────────────────

def generate_auto_pastor_questions(
    quality: dict,
    integration: dict,
) -> list[str]:
    """약한 카테고리의 누락 요소에서 구체적 신학 질문을 자동 생성.
    목사님 질문이 있으면 사용하지 않는다."""
    if integration["pastor_questions"]:
        return integration["pastor_questions"]

    questions: list[str] = []

    # Weak categories → missing elements → specific questions
    for weak_cat in quality["weak"]:
        for elem in weak_cat["missing_elements"]:
            q = WEAK_ELEMENT_AUTO_QUESTIONS.get(elem)
            if q and q not in questions:
                questions.append(q)

    # Red lines → gospel inversion question
    if integration["red_lines"]:
        for red in integration["red_lines"][:2]:
            if "도덕주의" in red or "섬기" in red:
                q = (
                    "이 본문이 도덕주의로 넘어가는 정확한 해석 지점은 어디인가? "
                    "복음을 지렛대로 삼아 그 전환점을 설교에서 어떻게 막을 수 있는가?"
                )
                if q not in questions:
                    questions.append(q)
                break

    # If still empty, add a default Big Idea validation question
    if not questions and integration["big_idea"]:
        questions.append(
            f"아래 Big Idea 초안이 본문 신학에 충실한지 검증하라: "
            f"'{integration['big_idea']}' — "
            f"이 선언이 억지 알레고리나 도덕주의 없이 본문 자체의 논리에서 나오는가?"
        )

    return questions[:6]


# ─────────────────────────────────────────────────────────────────────────────
# Per-Pass calibration generator
# ─────────────────────────────────────────────────────────────────────────────

def generate_per_pass_calibration(quality: dict, coverage: dict) -> str:
    """Pass 별 품질 캘리브레이션 표 생성.
    각 Pass가 어떤 Logos 카테고리에 의존하며, 그 강도가 무엇인지 명시한다."""

    # Build lookup: category name → strength + earned/max
    cat_strength: dict[str, dict] = {}
    for c in quality["categories"]:
        cat_strength[c["name"]] = c

    # Build lookup: coverage missing names
    missing_names: set[str] = {m["name"] for m in coverage["missing"]}
    quality_names: set[str] = {c["name"] for c in quality["categories"]}

    lines: list[str] = [
        "| Pass | 관련 Logos 카테고리 | 강도 | 캘리브레이션 지침 |",
        "|------|---------------------|------|-------------------|",
    ]

    for cat_name, pass_label in CATEGORY_TO_PASS.items():
        if cat_name in cat_strength:
            c = cat_strength[cat_name]
            icon = {"STRONG": "🟢", "MEDIUM": "🟡", "WEAK": "🔴"}.get(c["strength"], "⚪")
            strength_str = f"{icon} {c['strength']} ({c['ratio']*100:.0f}%)"

            # Derive calibration instruction — PROHIBITION, not warning
            if c["strength"] == "STRONG":
                directive = "자료 충분 → 깊이 활용. 캡처된 내용에 근거한 주장 전개"
            elif c["strength"] == "MEDIUM":
                missing_elems = next(
                    (w["missing_elements"] for w in quality["weak"] if w["name"] == cat_name),
                    []
                )
                if missing_elems:
                    elem_str = ", ".join(missing_elems)
                    directive = (
                        f"[{elem_str} 미분석] "
                        "Logos 캡처에 있는 내용만 인용. "
                        "없는 주석·사실은 생성하지 말고 '추가 Logos 연구 필요'로 대체"
                    )
                else:
                    directive = (
                        "캡처 일부 — Logos 자료에 있는 것만 인용. "
                        "없는 내용은 '추가 Logos 연구 필요'로 대체"
                    )
            else:  # WEAK
                directive = (
                    "캡처 부족 → 외부 자료 인용 금지. "
                    "본문 원어·구조·논증만 사용. 주석·통계·고고학 생성 금지"
                )

            # Indirect capture note (Logos module not opened)
            if cat_name in missing_names and cat_name in quality_names:
                directive += " / 전용 Logos 모듈 미열람 — 직접 열람 권장"

        elif cat_name in missing_names:
            strength_str = "❌ 완전 미수집"
            directive = (
                "생성 금지 — Logos에서 이 카테고리 자료 없음. "
                "해당 Pass 항목을 '이 카테고리 Logos 연구 필요 [미수집]'으로 대체. "
                "주석·인용·수치를 만들어 채우지 말 것"
            )
        else:
            strength_str = "⚪ 데이터 없음"
            directive = "캡처 데이터 없음 — 신중하게 분석, 외부 인용 최소화"

        lines.append(f"| {pass_label} | {cat_name} | {strength_str} | {directive} |")

    return "\n".join(lines)


# ─────────────────────────────────────────────────────────────────────────────
# AI directives (brief upfront instructions)
# ─────────────────────────────────────────────────────────────────────────────

def build_ai_directives_brief(categories: list[dict], missing_coverage: list[dict]) -> str:
    """BRIEF 구역용: 카테고리 강도 요약 (3줄 이내).

    Coverage-missing이지만 Quality-STRONG/MEDIUM인 카테고리는
    '(Coverage 모듈 미열람)' 주석을 붙여 캡처 파일은 있지만
    전용 Logos 모듈을 직접 열람하지 않았음을 Claude에 알린다.
    """
    missing_names = {m["name"] for m in missing_coverage}
    quality_names = {c["name"] for c in categories}
    truly_missing = [m["name"] for m in missing_coverage if m["name"] not in quality_names]

    def _fmt(name: str) -> str:
        """Coverage 미열람 카테고리에 주석 추가."""
        return f"{name} (전용 Logos 모듈 미열람)" if name in missing_names else name

    strong = [_fmt(c["name"]) for c in categories if c["strength"] == "STRONG"]
    medium = [_fmt(c["name"]) for c in categories if c["strength"] == "MEDIUM"]
    weak   = [c["name"]       for c in categories if c["strength"] == "WEAK"]

    parts: list[str] = []
    if strong:
        parts.append(f"🟢 STRONG (깊이 활용): {', '.join(strong)}")
    if medium:
        parts.append(f"🟡 MEDIUM (신중 활용): {', '.join(medium)}")
    if weak:
        parts.append(f"🔴 WEAK (본문 논리만): {', '.join(weak)}")
    if truly_missing:
        parts.append(f"❌ MISSING (환각 금지): {', '.join(truly_missing)}")
    return "\n".join(parts)


# ─────────────────────────────────────────────────────────────────────────────
# Context document generator
# ─────────────────────────────────────────────────────────────────────────────

def generate_context_md(
    passage_ref: str,
    coverage: dict,
    quality: dict,
    integration: dict,
    timestamp: str,
) -> str:
    """06-research-context.md 생성.

    두 구역:
    1. BRIEF  : 20-Pass 시작 전 주입 (Big Idea·경계선·강도 한줄 요약)
    2. CALIBRATION : Pass 20 직후 주입 (Per-Pass 표·목사님 질문·보강 상세)
       마커: <!-- V21_CALIBRATION_START -->
    """
    cov_score  = coverage["score"]
    qual_score = quality["score"]

    # Auto-generate questions if pastor Section 6 is blank
    questions = generate_auto_pastor_questions(quality, integration)
    questions_source = "목사님 직접 작성" if integration["pastor_questions"] else "자동 생성 (약한 카테고리 기반)"

    # ── Gate label ──────────────────────────────────────────────────────────
    if cov_score >= 90 and qual_score >= 80:
        gate_label = "✅ Logos-Max Deep Eligible"
    elif cov_score >= 75 and qual_score >= 70:
        gate_label = "✅ Deep Eligible"
    elif cov_score >= 60 or qual_score >= 60:
        gate_label = "⚠️ Review Required"
    else:
        gate_label = "🔴 자료 부족"

    # ────────────────────────────────────────────────────────────────────────
    # SECTION 1: BRIEF (20-Pass 전 주입)
    # ────────────────────────────────────────────────────────────────────────
    brief: list[str] = [
        f"# v2.1 Research Context — {passage_ref}",
        f"",
        f"> 생성일시: {timestamp}  |  이 파일은 자동 생성됩니다.",
        f"",
        f"## ▶ 분석 시작 전 핵심 제약 (모든 Pass에 적용)",
        f"",
        f"**게이트**: {gate_label}  |  Coverage {cov_score}/100  |  Quality {qual_score}/100",
        f"",
    ]

    # Big Idea upfront
    if integration["big_idea"]:
        brief += [
            f"**설교 Big Idea (목사님 초안)**",
            f"> {integration['big_idea']}",
            f"",
            f"→ 이 Big Idea가 본문 자체의 논리에서 나오는지 검증하라. 억지 알레고리 금지.",
            f"",
        ]

    # Red lines upfront
    if integration["red_lines"]:
        brief += ["**⛔ 절대 경계선 (이것을 넘으면 설교가 무너진다)**", ""]
        for r in integration["red_lines"]:
            brief.append(f"- {r}")
        brief.append("")

    # Christ connection
    if integration["christ_connection"]:
        brief += [
            "**그리스도 연결 경로 (목사님 확인)**",
            f"> {integration['christ_connection'][:300]}",
            "",
        ]

    # Strength summary (one-liner per category)
    brief += [
        "**자료군 강도 요약**",
        "",
        build_ai_directives_brief(quality["categories"], coverage["missing"]),
        "",
        "→ 강도에 따라 분석 깊이를 조정하라. 세부 Pass별 지침은 Pass 20 이후 Calibration 구역 참조.",
        "",
    ]

    # ────────────────────────────────────────────────────────────────────────
    # SECTION 2: CALIBRATION (Pass 20 직후 주입)
    # ────────────────────────────────────────────────────────────────────────
    calibration: list[str] = [
        "<!-- V21_CALIBRATION_START -->",
        "",
        f"## Pass 21: v2.1 품질 캘리브레이션 감사",
        f"",
        f"> Pass 1–20에서 생성한 분석을 아래 기준으로 자체 감사하라.",
        f"> 품질 기준 미달 항목은 신뢰도를 하향 조정하고 추가 연구 권장 사항에 기록하라.",
        f"",
        f"### Pass별 Logos 자료 강도 대조표",
        f"",
        generate_per_pass_calibration(quality, coverage),
        f"",
        f"### 감사 체크리스트",
        f"",
        f"- [ ] Pass 12 주석 비교: 실제 캡처된 주석만 인용했는가? 없는 주석을 생성하지 않았는가?",
        f"- [ ] Pass 15 교차 참조: 각 교차 본문의 연결 이유를 명시했는가?",
        f"- [ ] Pass 10-11 구속사: 억지 알레고리 없이 본문 논리 안에서만 연결했는가?",
        f"- [ ] Pass 17-19 적용: 복음의 은혜에서 출발하는 적용 구조인가, 아니면 도덕주의인가?",
        f"- [ ] Pass 18 Big Idea: 목사님 초안과 비교했는가? 차이가 있다면 어느 쪽이 더 본문에 충실한가?",
        f"",
    ]

    # Questions
    calibration += [
        f"### 목사님 요청 질문에 대한 답변 ({questions_source})",
        f"",
        f"> 아래 질문들은 분석 중 반드시 답해야 할 핵심 신학 포인트입니다.",
        f"",
    ]
    if questions:
        for i, q in enumerate(questions, 1):
            calibration.append(f"**Q{i}**: {q}")
            calibration.append("")
    else:
        calibration += [
            "> (질문 없음 — Pass 20 통합 검토 기준으로만 감사)",
            "",
        ]

    # Weak category detail
    if quality["weak"]:
        calibration += [
            "### 보강 필요 항목 상세",
            "",
        ]
        for w in quality["weak"]:
            calibration += [f"**{w['name']}**"]
            if w["missing_elements"]:
                calibration.append(f"- 누락 분석 요소: {', '.join(w['missing_elements'])}")
            for warn in w["warnings"]:
                calibration.append(f"- ⚠️ {warn}")
            calibration.append("")

    # Coverage gaps detail
    quality_names_set = {c["name"] for c in quality["categories"]}
    truly_missing = [m for m in coverage["missing"] if m["name"] not in quality_names_set]
    if truly_missing:
        calibration += [
            "### Logos 미수집 카테고리 (환각 특별 주의)",
            "",
        ]
        for m in truly_missing:
            calibration.append(
                f"- **{m['name']}**: 전용 Logos 모듈 미열람 — "
                "구체적 인용·수치 생성 금지, 모든 주장 🔴 낮음"
            )
        calibration.append("")

    calibration += [
        "---",
        f"> ⚠️ 이 컨텍스트는 연구 보조 자료입니다. 최종 신학 판단은 설교자에게 있습니다.",
    ]

    return "\n".join(brief) + "\n\n" + "\n".join(calibration)


# ─────────────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────────────

def main() -> int:
    parser = argparse.ArgumentParser(description="v2.1 Research Context Builder v2")
    parser.add_argument("--passage", required=True, help="00-passage.yaml 경로")
    parser.add_argument("--force", action="store_true", help="기존 파일 덮어쓰기")
    args = parser.parse_args()

    passage_yaml = Path(args.passage)
    if not passage_yaml.exists():
        print(f"[ERROR] passage.yaml 없음: {passage_yaml}", file=sys.stderr)
        return 1

    docs_dir = passage_yaml.parent
    data = load_yaml_simple(passage_yaml)
    book_korean = data.get("book_korean", data.get("book", ""))
    passage     = data.get("passage", "")
    passage_ref = f"{book_korean} {passage}".strip()

    coverage_path    = docs_dir / "03-logos-coverage-report.md"
    quality_path     = docs_dir / "04-capture-quality-report.md"
    integration_path = docs_dir / "05-logos-integration-summary.md"
    output_path      = docs_dir / "06-research-context.md"

    print(f"\n[build_v21_research_context v2] {passage_ref}")
    print(f"  Coverage:    {coverage_path.name} {'✅' if coverage_path.exists() else '❌ 없음'}")
    print(f"  Quality:     {quality_path.name} {'✅' if quality_path.exists() else '❌ 없음'}")
    print(f"  Integration: {integration_path.name} {'✅' if integration_path.exists() else '❌ 없음'}")

    if not coverage_path.exists() and not quality_path.exists():
        print("[ERROR] Coverage·Quality 보고서가 모두 없습니다.", file=sys.stderr)
        return 1

    if output_path.exists() and not args.force:
        print(f"[SKIP] 이미 존재: {output_path}  (--force로 덮어쓰기)")
        return 0

    coverage    = parse_coverage_report(coverage_path)
    quality     = parse_quality_report(quality_path)
    integration = parse_integration_summary(integration_path)

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    content = generate_context_md(passage_ref, coverage, quality, integration, timestamp)

    # Write with backup + temp-replace
    if output_path.exists():
        shutil.copy2(output_path, output_path.with_suffix(".bak"))
    temp = output_path.with_suffix(".tmp")
    temp.write_text(content, encoding="utf-8")
    if output_path.exists():
        output_path.unlink()
    temp.rename(output_path)

    # Stats
    auto_q = generate_auto_pastor_questions(quality, integration)
    q_source = "목사님 직접" if integration["pastor_questions"] else "자동 생성"
    print(f"\n[OK] 저장: {output_path}")
    print(f"  크기:      {output_path.stat().st_size:,}바이트")
    print(f"  Coverage:  {coverage['score']}/100 ({coverage['status']})")
    print(f"  Quality:   {quality['score']}/100 ({quality['status']})")
    print(f"  카테고리:  {len(quality['categories'])}개 분류 | WEAK: {len(quality['weak'])}개")
    print(f"  질문:      {len(auto_q)}개 ({q_source})")
    print(f"  Big Idea:  {'있음' if integration['big_idea'] else '없음'}")
    print(f"  경계선:    {len(integration['red_lines'])}개")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
