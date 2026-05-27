"""
generate_final_direction.py — Phase B: 최종 설교 방향 설정

입력:
  05-logos-integration-summary.md  → 목사님 Big Idea · 경계선 · 질문
  07-deep-research.md              → AI 20-Pass 분석 결과 (없으면 scaffold 모드)

출력:
  08-final-direction.md            → 최종 설교 방향 결정 문서

역할: AI 분석 수렴 검증 + 목사님 최종 결정 지원 (설교 작성 착수 전 1분 점검)

사용법:
    python scripts/generate_final_direction.py --passage docs/john/13-14/00-passage.yaml
    python scripts/generate_final_direction.py --passage docs/john/13-14/00-passage.yaml --force
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
# 05 파싱: 목사님 통찰 추출
# (지원 포맷: 구형 7-섹션 / 신 템플릿 6-섹션 / 현재 John 13:14 형식)
# ─────────────────────────────────────────────────────────────────────────────

def _split_sections(text: str) -> list[tuple[str, str]]:
    """마크다운을 (헤더, 내용) 쌍의 목록으로 분리한다."""
    sections: list[tuple[str, str]] = []
    current_header = ""
    current_lines: list[str] = []

    for line in text.splitlines():
        if re.match(r"^#{1,3}\s+", line):
            if current_header or current_lines:
                sections.append((current_header, "\n".join(current_lines).strip()))
            current_header = line.strip()
            current_lines = []
        else:
            current_lines.append(line)

    if current_header or current_lines:
        sections.append((current_header, "\n".join(current_lines).strip()))

    return sections


def _find_section(sections: list[tuple[str, str]], keywords: list[str]) -> str:
    """헤더에 키워드 중 하나라도 포함된 첫 번째 섹션의 내용을 반환한다."""
    for header, content in sections:
        h_lower = header.lower()
        if any(kw.lower() in h_lower for kw in keywords):
            return content
    return ""


def _extract_big_idea(content: str) -> str:
    """섹션 내용에서 Big Idea 문장 한 줄을 추출한다."""
    for line in content.splitlines():
        s = line.strip()
        # 템플릿 플레이스홀더 / 빈 줄 / 헤더 / 불릿 / 인용 건너뛰기
        if not s:
            continue
        if "여기에 작성" in s or s.startswith("<!--") or "-->" in s:
            continue
        if s.startswith("#") or s.startswith("-") or s.startswith("*"):
            continue
        if len(s) < 12:
            continue
        # blockquote 기호 제거
        s = s.lstrip(">").strip()
        if s:
            return s
    return ""


def _extract_questions(content: str) -> list[str]:
    """섹션 내용에서 질문 항목 목록을 추출한다 (불릿·번호·Q: 형식)."""
    questions: list[str] = []
    for line in content.splitlines():
        s = line.strip()
        if not s or "여기에 작성" in s or s.startswith("<!--"):
            continue
        # 불릿 또는 번호
        m = re.match(r"^[-*\d]+[.)]\s*(.+)", s)
        if m:
            q = m.group(1).strip()
            if len(q) > 5:
                questions.append(q)
            continue
        # Q: 또는 Q1: 형식
        if re.match(r"^Q\d*[:.]\s*", s):
            q = re.sub(r"^Q\d*[:.]\s*", "", s).strip()
            if len(q) > 5:
                questions.append(q)
    return questions


def parse_05(path: Path) -> dict:
    """05-logos-integration-summary.md 파싱 → 목사님 인사이트 딕셔너리."""
    if not path.exists():
        return {"found": False}

    text = path.read_text(encoding="utf-8", errors="replace")
    sections = _split_sections(text)

    # Big Idea: 섹션 헤더 키워드 기반
    big_idea_raw = _find_section(sections, [
        "Big Idea", "big idea", "설교 방향", "방향의 씨앗", "Big_Idea",
    ])
    big_idea = _extract_big_idea(big_idea_raw)

    # 도덕주의 경계선
    red_raw = _find_section(sections, ["도덕주의", "위험 경고", "경계선", "moralism"])
    red_lines = red_raw[:500] if red_raw else ""

    # 그리스도 연결 경로
    christ_raw = _find_section(sections, [
        "그리스도 연결", "구속사", "정경적 연결", "christ", "안전한 경로",
    ])
    christ_path = christ_raw[:400] if christ_raw else ""

    # 목사님이 Deep Research에 요청한 질문
    q_raw = _find_section(sections, [
        "Deep Research", "요청할 것", "요청", "질문",
    ])
    questions = _extract_questions(q_raw)

    return {
        "found": True,
        "big_idea": big_idea,
        "red_lines": red_lines,
        "christ_path": christ_path,
        "questions": questions,
    }


# ─────────────────────────────────────────────────────────────────────────────
# 07 파싱: AI 20-Pass 분석 결과 추출
# ─────────────────────────────────────────────────────────────────────────────

def _find_pass_section(text: str, pass_label: str) -> str:
    """Pass N 섹션을 찾아 내용을 반환한다 (헤더 패턴 다양 지원)."""
    # ## Pass 18: ... / ### Pass 18 — ... / **Pass 18** ... 형식 지원
    # 주의: f-string에서 {1,4}는 표현식으로 평가되므로 {{1,4}}로 이스케이프
    escaped = re.escape(pass_label)
    patterns = [
        # 마크다운 헤더 (##, ###, ####)
        rf"(?m)^#{{1,4}}\s+{escaped}[:\s—\-–][^\n]*\n(.*?)(?=\n#{{1,4}}\s+Pass\s|\Z)",
        # 볼드 패턴
        rf"(?m)\*\*{escaped}\*\*[:\s—\-–][^\n]*\n(.*?)(?=\n\*\*Pass\s|\Z)",
        # 헤더만 있고 콜론 없는 경우
        rf"(?m)^#{{1,4}}\s+{escaped}\s*\n(.*?)(?=\n#{{1,4}}\s+Pass\s|\Z)",
    ]
    for pat in patterns:
        m = re.search(pat, text, re.DOTALL | re.IGNORECASE)
        if m:
            return m.group(1).strip()[:2000]
    return ""


def _extract_first_substantive_line(text: str) -> str:
    """텍스트에서 첫 번째 실질적인 문장(헤더·메타 제외, 충분한 길이)을 추출한다."""
    for line in text.splitlines():
        s = line.strip().lstrip(">").strip()
        if not s or s.startswith("#") or s.startswith("|") or s.startswith("-"):
            continue
        if len(s) < 15:
            continue
        # 메타 정보 건너뛰기
        if any(kw in s for kw in ["생성일시", "Pass ", "패스", "pass ", "timestamp", "model"]):
            continue
        # "Big Idea:" 접두어가 있으면 뒤 내용만
        m = re.match(r"^(?:설교\s*)?Big Idea\s*[:\-–]\s*(.+)", s)
        if m:
            return m.group(1).strip()
        return s
    return ""


def parse_07(path: Path) -> dict:
    """07-deep-research.md 파싱 → AI 분석 딕셔너리."""
    if not path.exists():
        return {"found": False}

    text = path.read_text(encoding="utf-8", errors="replace")

    # Pass 18: Big Idea
    pass18 = _find_pass_section(text, "Pass 18")
    ai_big_idea = _extract_first_substantive_line(pass18) if pass18 else ""

    # Pass 21: 캘리브레이션 감사
    pass21 = _find_pass_section(text, "Pass 21")

    # Pass 21에서 도덕주의 관련 줄 추출
    moralism_lines: list[str] = []
    if pass21:
        for line in pass21.splitlines():
            if any(kw in line for kw in ["도덕", "Pass 17", "Pass 18", "Pass 19", "적용", "Big Idea"]):
                moralism_lines.append(line)

    # Pass 17: 현대 적용 (참고용)
    pass17 = _find_pass_section(text, "Pass 17")

    # Pass 12: 주석 비교 (참고용)
    pass12 = _find_pass_section(text, "Pass 12")

    return {
        "found": True,
        "ai_big_idea": ai_big_idea,
        "pass18_excerpt": pass18[:400] if pass18 else "",
        "pass21_excerpt": pass21[:700] if pass21 else "",
        "pass21_moralism": "\n".join(moralism_lines[:8]).strip()[:400],
        "pass17_excerpt": pass17[:300] if pass17 else "",
        "pass12_excerpt": pass12[:300] if pass12 else "",
    }


# ─────────────────────────────────────────────────────────────────────────────
# 수렴 분석
# ─────────────────────────────────────────────────────────────────────────────

def convergence_check(pastor_idea: str, ai_idea: str) -> str:
    """목사님 Big Idea ↔ AI Big Idea 한국어 단어 겹침 기반 수렴 판정."""
    if not pastor_idea:
        return "판단 불가 — 목사님 Big Idea 미기록"
    if not ai_idea:
        return "판단 불가 — AI Pass 18 미추출"

    def kr_words(s: str) -> set[str]:
        return set(re.findall(r"[가-힣]{2,}", s))

    pw = kr_words(pastor_idea)
    aw = kr_words(ai_idea)

    if not pw:
        return "판단 불가 — 한국어 단어 없음"

    overlap = pw & aw
    ratio = len(overlap) / max(len(pw), 1)

    if ratio >= 0.45:
        return f"✅ 수렴 ({len(overlap)}/{len(pw)} 핵심 단어 일치) — 초안 유지 검토"
    elif ratio >= 0.2:
        return f"⚠️ 부분 수렴 ({len(overlap)}/{len(pw)} 단어 일치) — 조정 검토"
    else:
        return f"❌ 발산 ({len(overlap)}/{len(pw)} 단어만 일치) — 재검토 권장"


# ─────────────────────────────────────────────────────────────────────────────
# 08-final-direction.md 생성
# ─────────────────────────────────────────────────────────────────────────────

def generate_08(
    passage_label: str,
    data05: dict,
    data07: dict,
    timestamp: str,
) -> str:
    """08-final-direction.md 마크다운 문자열을 생성한다."""
    L: list[str] = []

    def add(*lines: str) -> None:
        L.extend(lines)

    # ── 헤더 ────────────────────────────────────────────────────────────────
    add(
        f"# 최종 설교 방향 — {passage_label}",
        "",
        f"> 생성일시: {timestamp}  |  자동 생성 · 목사님이 직접 확정하는 문서입니다.",
        "",
    )

    # ── 07 없음 경고 ─────────────────────────────────────────────────────────
    if not data07["found"]:
        add(
            "## ⚠️ Deep Research 미완료",
            "",
            "> `07-deep-research.md`가 없습니다. 먼저 파이프라인을 완료하세요:",
            "> ```powershell",
            "> python scripts/run_logos_max.py --passage <yaml경로> --force-deep --force-reason '보강 완료'",
            "> ```",
            "",
            "> 아래는 `05` 정보만으로 생성한 방향 설정 골격입니다.",
            "",
        )

    # ── ⚡ 즉시 결정 표 ──────────────────────────────────────────────────────
    conv = convergence_check(data05.get("big_idea", ""), data07.get("ai_big_idea", ""))
    moralism_status = "⚠️ 3번에서 확인 필요" if data05.get("red_lines") else "_(05 미기록)_"

    add(
        "## ⚡ 지금 결정할 것",
        "",
        "| 항목 | 상태 |",
        "|------|------|",
        f"| Big Idea 수렴 | {conv} |",
        f"| 도덕주의 방어선 | {moralism_status} |",
        "| 이번 주 한 순종 | _(7번에서 결정)_ |",
        "",
    )

    # ── 1. Big Idea 비교 ─────────────────────────────────────────────────────
    pastor_idea = data05.get("big_idea") or "_(05 Big Idea 미기록)_"
    ai_idea = (
        data07.get("ai_big_idea") or "_(Pass 18 미추출)_"
        if data07["found"]
        else "_(07 미생성)_"
    )

    add(
        "## 1. Big Idea 비교",
        "",
        "| 출처 | Big Idea |",
        "|------|----------|",
        f"| **목사님 초안** (05) | {pastor_idea} |",
        f"| **AI 분석** (07 Pass 18) | {ai_idea} |",
        f"| **수렴 판단** | {conv} |",
        "",
    )

    if "❌" in conv:
        add(
            "> ⚠️ **Big Idea 발산**: AI 분석과 목사님 초안이 크게 다릅니다.",
            "> 07-deep-research.md → Pass 18을 직접 확인하고 어느 쪽이 본문 논리에 더 충실한지 판단하십시오.",
            "",
        )

    # ── 2. 그리스도 연결 경로 ─────────────────────────────────────────────────
    add("## 2. 그리스도 연결 경로 검증", "")

    if data05.get("christ_path"):
        add(
            "**05 설정 경로:**",
            "",
            data05["christ_path"],
            "",
        )
    else:
        add("> _(05에 그리스도 연결 경로 미기록)_", "")

    if data07["found"]:
        if data07.get("pass18_excerpt"):
            # 멀티라인 blockquote 형식으로 삽입 (최대 350자)
            excerpt = data07["pass18_excerpt"][:350].replace("\n", "\n> ")
            add(
                "**AI Pass 18 발췌:**",
                "",
                f"> {excerpt}",
                "",
                "> _(전체 내용: 07-deep-research.md → Pass 18 직접 확인)_",
                "",
            )
        else:
            add("> _(Pass 18 추출 실패 — 07 직접 확인 필요)_", "")

    # ── 3. 도덕주의 방어선 ───────────────────────────────────────────────────
    add("## 3. 도덕주의 방어선", "")

    if data05.get("red_lines"):
        add(
            "**05 경계선:**",
            "",
            data05["red_lines"],
            "",
        )
    else:
        add("> _(05에 도덕주의 경고 미기록)_", "")

    if data07["found"]:
        if data07.get("pass21_moralism"):
            add(
                "**Pass 21 도덕주의 진단 (발췌):**",
                "",
                data07["pass21_moralism"],
                "",
            )
        else:
            add("> _(Pass 21에서 도덕주의 관련 항목 미발견 — 07 직접 확인 필요)_", "")

    # ── 4. 목사님 질문 → AI 분석 현황 ─────────────────────────────────────────
    add("## 4. 목사님 질문 → AI 분석 현황", "")

    questions = data05.get("questions", [])
    if questions:
        add(
            "| # | 질문 (05 Section 6) | 처리 상태 |",
            "|---|---------------------|-----------|",
        )
        for i, q in enumerate(questions[:6], 1):
            q_disp = (q[:65] + "…") if len(q) > 65 else q
            status = "✅ 07 분석 완료" if data07["found"] else "⏳ 07 미생성"
            add(f"| Q{i} | {q_disp} | {status} |")
        add(
            "",
            "> 답변 전체 내용: `07-deep-research.md` → 해당 Pass 직접 확인",
            "",
        )
    else:
        add(
            "> 05 Section 6에 목사님 질문이 없습니다.",
            "> **06-research-context.md** Pass 21의 자동 생성 질문에 대해",
            "> AI가 어떻게 답했는지 07-deep-research.md에서 확인하십시오.",
            "",
        )

    # ── 5. Pass 21 캘리브레이션 감사 결과 ────────────────────────────────────
    add("## 5. Pass 21 캘리브레이션 감사 결과", "")

    if data07["found"] and data07.get("pass21_excerpt"):
        add(
            data07["pass21_excerpt"],
            "",
            "> _(전체 감사: 07-deep-research.md → Pass 21 직접 확인)_",
            "",
        )
    elif data07["found"]:
        add(
            "> _(Pass 21 추출 실패 — 07-deep-research.md 직접 확인 필요)_",
            "",
            "**수동 확인 필요 카테고리** (06-research-context.md 기준):",
            "- `주석 비교` — interpretive_comparison 미분석 여부",
            "- `성경신학` — anti_allegory 점검 여부",
            "- `목회·적용` — false_gospel_diagnosis 여부",
            "",
        )
    else:
        add(
            "> _(07 미생성 — 파이프라인 완료 후 재실행하십시오.)_",
            "",
            "**현재 알려진 약한 카테고리 (06 기준):**",
            "- 주석 비교 (65%) — interpretive_comparison 미분석",
            "- 성경신학 (75%) — anti_allegory 미분석",
            "- 목회·적용 (70%) — false_gospel_diagnosis 미분석",
            "",
        )

    # ── 6. 확정 체크리스트 ───────────────────────────────────────────────────
    add(
        "## 6. 설교 방향 확정 체크리스트",
        "",
        "- [ ] Big Idea 확정됨 (목사님 초안 또는 AI 분석 기반)",
        "- [ ] 그리스도 연결 경로 명확 — 알레고리 없음",
        "- [ ] 도덕주의 전환점 식별됨 (3번 확인)",
        "- [ ] 복음의 은혜에서 적용이 흘러나오는 구조 확인",
        "- [ ] 이번 주 순종 1가지 결정됨",
        "- [ ] 추가 Logos 연구 필요 항목 파악됨 (Pass 21 결과 기반)",
        "",
    )

    # ── 7. 체득 압축본 씨앗 ─────────────────────────────────────────────────
    seed_big_idea = data05.get("big_idea") or data07.get("ai_big_idea") or "_(결정 필요)_"

    add(
        "## 7. 체득 압축본 씨앗",
        "",
        "> 설교문 작성 **전** 이 7가지를 완성하세요.",
        "> 지금은 씨앗 단계 — 설교 준비 중 채워가십시오.",
        "",
        "**① 30초 흐름**: _기록 필요_",
        "",
        f"**② Big Idea**: {seed_big_idea}",
        "",
        "**③ 대지별 핵심문장**:",
        "  - 대지 1: _기록 필요_",
        "  - 대지 2: _기록 필요_",
        "  - 대지 3: _기록 필요_",
        "",
        "**④ 전환문장**: _기록 필요_",
        "",
        "**⑤ 결론 3문장**: _기록 필요_",
        "",
        "**⑥ 강단에서 붙들 한 문장**: _기록 필요_",
        "",
        "**⑦ 이번 주 한 순종**: _기록 필요_",
        "",
    )

    # ── 푸터 ────────────────────────────────────────────────────────────────
    add(
        "---",
        "> ⚠️ 이 파일은 자동 생성 보조 자료입니다. 최종 신학 판단은 목사님께 있습니다.",
    )

    return "\n".join(L)


# ─────────────────────────────────────────────────────────────────────────────
# 유틸리티
# ─────────────────────────────────────────────────────────────────────────────

# load_yaml_simple: pipeline_utils 에서 import됨

# ─────────────────────────────────────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────────────────────────────────────

def main() -> int:
    parser = argparse.ArgumentParser(
        description="Phase B: 05 + 07 → 08-final-direction.md"
    )
    parser.add_argument(
        "--passage", required=True,
        help="Path to 00-passage.yaml (e.g. docs/john/13-14/00-passage.yaml)",
    )
    parser.add_argument(
        "--force", action="store_true",
        help="Overwrite existing 08-final-direction.md",
    )
    args = parser.parse_args()

    passage_yaml = Path(args.passage)
    if not passage_yaml.exists():
        print(f"[ERROR] passage.yaml 없음: {passage_yaml}", file=sys.stderr)
        return 1

    docs_dir = passage_yaml.parent
    yaml_data = load_yaml_simple(passage_yaml)
    book_korean = yaml_data.get("book_korean", yaml_data.get("book", ""))
    passage = yaml_data.get("passage", "")
    passage_label = f"{book_korean} {passage}".strip()

    f05 = docs_dir / "05-logos-integration-summary.md"
    f07 = docs_dir / "07-deep-research.md"
    f08 = docs_dir / "08-final-direction.md"

    # 이미 존재하고 --force 없으면 건너뜀
    if f08.exists() and not args.force:
        print(f"[SKIP] 08 파일 이미 존재: {f08.name}  (재생성: --force)")
        return 0

    print(f"[Phase B] 최종 방향 생성: {passage_label}")
    print(f"  05: {'OK' if f05.exists() else '없음'}")
    print(f"  07: {'OK' if f07.exists() else '없음 (scaffold 모드)'}")

    data05 = parse_05(f05)
    data07 = parse_07(f07)

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    content = generate_08(passage_label, data05, data07, timestamp)

    # backup + temp replace
    tmp = f08.with_suffix(".tmp")
    tmp.write_text(content, encoding="utf-8")
    if f08.exists():
        shutil.copy2(f08, f08.with_suffix(".bak"))
    shutil.move(str(tmp), str(f08))

    print(f"[OK] 생성됨: {f08.name}  ({f08.stat().st_size:,}바이트)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
