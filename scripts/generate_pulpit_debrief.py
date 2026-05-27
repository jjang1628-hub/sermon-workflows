"""
generate_pulpit_debrief.py — Phase D: 설교 후 강단 데브리프 템플릿

설교 후 30분 이내 기록용 반성 문서를 생성한다.
05 (통합 요약)와 08 (최종 방향)에서 계획된 내용을 가져와
"계획 ↔ 실제" 비교 구조로 구성한다.

출력: docs/{book}/{passage}/09-pulpit-debrief.md

사용법:
    python scripts/generate_pulpit_debrief.py --passage docs/john/13-14/00-passage.yaml
    python scripts/generate_pulpit_debrief.py --passage docs/john/13-14/00-passage.yaml --force
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
# 파싱: 05, 08에서 계획 정보 추출
# ─────────────────────────────────────────────────────────────────────────────

def _extract_field(text: str, keywords: list[str], max_chars: int = 200) -> str:
    """헤더 키워드로 섹션을 찾아 첫 의미 있는 줄을 반환한다."""
    sections = []
    current_header = ""
    current_lines: list[str] = []

    for line in text.splitlines():
        if re.match(r"^#{1,4}\s+", line):
            if current_header or current_lines:
                sections.append((current_header, "\n".join(current_lines)))
            current_header = line.strip()
            current_lines = []
        else:
            current_lines.append(line)
    if current_header or current_lines:
        sections.append((current_header, "\n".join(current_lines)))

    for header, content in sections:
        h_lower = header.lower()
        if any(kw.lower() in h_lower for kw in keywords):
            # 첫 번째 실질적 줄
            for line in content.splitlines():
                s = line.strip().lstrip(">").strip()
                if not s or s.startswith("<!--") or "여기에 작성" in s:
                    continue
                if s.startswith("#") or s.startswith("-") or len(s) < 10:
                    continue
                return s[:max_chars]
    return ""


def load_planned_big_idea(docs_dir: Path) -> str:
    """05 또는 08에서 목사님 Big Idea 초안을 추출한다."""
    # 08 우선 (더 최신)
    f08 = docs_dir / "08-final-direction.md"
    if f08.exists():
        text = f08.read_text(encoding="utf-8", errors="replace")
        idea = _extract_field(text, ["Big Idea 비교", "Big Idea"])
        if idea and "미기록" not in idea and "미생성" not in idea:
            # 표 행에서 | 사이 내용 추출
            for line in text.splitlines():
                m = re.match(r"\|\s+\*\*목사님 초안\*\*.*?\|\s+(.+?)\s+\|", line)
                if m:
                    return m.group(1).strip()

    f05 = docs_dir / "05-logos-integration-summary.md"
    if f05.exists():
        text = f05.read_text(encoding="utf-8", errors="replace")
        return _extract_field(text, ["Big Idea", "설교 방향", "방향의 씨앗"])

    return ""


def load_planned_christ_path(docs_dir: Path) -> str:
    """05에서 그리스도 연결 경로를 추출한다."""
    f05 = docs_dir / "05-logos-integration-summary.md"
    if not f05.exists():
        return ""
    text = f05.read_text(encoding="utf-8", errors="replace")
    return _extract_field(text, ["그리스도 연결", "구속사", "안전한 경로"], 300)


def load_planned_red_line(docs_dir: Path) -> str:
    """05에서 도덕주의 경계선을 추출한다."""
    f05 = docs_dir / "05-logos-integration-summary.md"
    if not f05.exists():
        return ""
    text = f05.read_text(encoding="utf-8", errors="replace")
    return _extract_field(text, ["도덕주의", "위험 경고", "경계선"], 200)


# load_yaml_simple: pipeline_utils 에서 import됨


# ─────────────────────────────────────────────────────────────────────────────
# 09-pulpit-debrief.md 생성
# ─────────────────────────────────────────────────────────────────────────────

def generate_09(
    passage_label: str,
    planned_big_idea: str,
    planned_christ_path: str,
    planned_red_line: str,
    timestamp: str,
) -> str:
    L: list[str] = []

    def add(*lines: str) -> None:
        L.extend(lines)

    # ── 헤더 ────────────────────────────────────────────────────────────────
    add(
        f"# 설교 데브리프 — {passage_label}",
        "",
        f"> 템플릿 생성: {timestamp}",
        f"> 설교일: _________  |  설교자: 이종헌 목사",
        "",
        "> 설교 후 30분 이내에 기록하십시오.",
        "> 솔직한 기록이 다음 설교를 만듭니다.",
        "",
    )

    # ── ⚡ 즉시 기록 ─────────────────────────────────────────────────────────
    add(
        "## ⚡ 즉시 기록 (설교 후 30분 이내)",
        "",
        "**말씀이 가장 크게 살아났던 순간:**",
        "",
        "_여기에 기록_",
        "",
        "**청중 반응이 가장 뜨거웠던 지점:**",
        "",
        "_여기에 기록_",
        "",
        "**스스로 흔들리거나 아쉬웠던 지점:**",
        "",
        "_여기에 기록_",
        "",
    )

    # ── 1. Big Idea 전달 확인 ─────────────────────────────────────────────────
    add("## 1. Big Idea 전달 확인", "")

    if planned_big_idea:
        add(
            f"> **계획한 Big Idea** (05/08 기준): {planned_big_idea}",
            "",
        )

    add(
        "**실제 사용한 Big Idea:**",
        "",
        "_여기에 기록_",
        "",
        "**전달 점검:**",
        "",
        "- [ ] 처음부터 끝까지 Big Idea가 일관되게 전달되었다",
        "- [ ] 청중이 한 문장으로 집에 가져갈 수 있는 수준이었다",
        "- [ ] 계획과 실제 Big Idea 사이에 의미 있는 차이가 있었다",
        "  - 있었다면 → 차이: _여기에 기록_",
        "",
    )

    # ── 2. 복음 방어선 점검 ───────────────────────────────────────────────────
    add("## 2. 복음 방어선 점검", "")

    if planned_red_line:
        add(
            f"> **계획한 경계선** (05 기준): {planned_red_line}",
            "",
        )

    add(
        "**도덕주의 방어:**",
        "",
        "- [ ] 도덕주의로 흐르지 않았다 (복음이 먼저, 순종이 그 결과였다)",
        "- [ ] 부분적으로 흘렀다 — 지점: _여기에 기록_",
        "- [ ] 흘러버렸다 — 지점: _여기에 기록_",
        "",
        "**복음 동기:**",
        "",
        "- [ ] 은혜에서 흘러나오는 적용 구조였다",
        "- [ ] 적용이 책임/의무 언어로만 닫혔다",
        "",
    )

    # ── 3. 그리스도 연결 점검 ─────────────────────────────────────────────────
    add("## 3. 그리스도 연결 점검", "")

    if planned_christ_path:
        add(
            f"> **계획한 경로** (05 기준): {planned_christ_path}",
            "",
        )

    add(
        "**그리스도 연결:**",
        "",
        "- [ ] 연결이 자연스러웠다 — 본문 논리에서 나왔다",
        "- [ ] 약간 억지였다 — 지점: _여기에 기록_",
        "- [ ] 연결을 건너뛰었다",
        "",
        "**억지 알레고리 여부:**",
        "",
        "- [ ] 없었다",
        "- [ ] 있었다 — 부분: _여기에 기록_",
        "",
    )

    # ── 4. 청중 반응 ─────────────────────────────────────────────────────────
    add(
        "## 4. 청중 반응",
        "",
        "**전체 집중도:** [ ] 높음  [ ] 보통  [ ] 낮음",
        "",
        "**이번 주 순종 전달:**",
        "",
        "- [ ] 구체적이고 명확하게 전달되었다",
        "- [ ] 모호하게 끝났다",
        "",
        "**기억할 특이 반응:**",
        "",
        "_여기에 기록_",
        "",
    )

    # ── 5. 다음을 위한 개선 ───────────────────────────────────────────────────
    add(
        "## 5. 다음 설교를 위한 개선",
        "",
        "**바꿀 것:**",
        "",
        "_여기에 기록_",
        "",
        "**강화할 것:**",
        "",
        "_여기에 기록_",
        "",
        "**관련 본문 준비 시 주의할 점:**",
        "",
        "_여기에 기록_",
        "",
    )

    # ── 6. 개인 영적 점검 ────────────────────────────────────────────────────
    add(
        "## 6. 개인 영적 점검",
        "",
        "> *\"강단 위와 아래가 분리되지 않는가?\"*",
        "",
        "**이 말씀이 내 삶에서 먼저 살아났는가?**",
        "",
        "_여기에 기록_",
        "",
        "**오늘 설교에서 내가 먼저 들은 말씀:**",
        "",
        "_여기에 기록_",
        "",
    )

    # ── 푸터 ────────────────────────────────────────────────────────────────
    add(
        "---",
        "> 이 데브리프는 다음 설교 준비 시 참고 자료가 됩니다.",
        "> 특히 같은 본문을 다시 설교하거나 시리즈 연속 설교 시 활용하십시오.",
    )

    return "\n".join(L)


# ─────────────────────────────────────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────────────────────────────────────

def main() -> int:
    parser = argparse.ArgumentParser(
        description="Phase D: 09-pulpit-debrief.md 설교 데브리프 템플릿 생성"
    )
    parser.add_argument(
        "--passage", required=True,
        help="Path to 00-passage.yaml",
    )
    parser.add_argument(
        "--force", action="store_true",
        help="Overwrite existing 09-pulpit-debrief.md",
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

    f09 = docs_dir / "09-pulpit-debrief.md"

    if f09.exists() and not args.force:
        print(f"[SKIP] 09 파일 이미 존재: {f09.name}  (재생성: --force)")
        print("  ⚠️  데브리프는 설교 후 직접 작성하는 문서입니다. 덮어쓰지 않습니다.")
        return 0

    print(f"[Phase D] 데브리프 템플릿 생성: {passage_label}")

    planned_big_idea  = load_planned_big_idea(docs_dir)
    planned_christ    = load_planned_christ_path(docs_dir)
    planned_red_line  = load_planned_red_line(docs_dir)

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    content = generate_09(passage_label, planned_big_idea, planned_christ, planned_red_line, timestamp)

    # backup + temp replace (09는 설교 후 직접 편집하는 문서 — 특히 신중하게)
    tmp = f09.with_suffix(".tmp")
    tmp.write_text(content, encoding="utf-8")
    if f09.exists():
        shutil.copy2(f09, f09.with_suffix(".bak"))
    shutil.move(str(tmp), str(f09))

    print(f"[OK] 생성됨: {f09.name}  ({f09.stat().st_size:,}바이트)")
    if planned_big_idea:
        print(f"  Big Idea 자동 삽입: {planned_big_idea[:60]}...")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
