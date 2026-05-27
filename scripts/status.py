"""
Print a Logos-Max v2.1 passage dashboard.

Important policy:
- PASS means normal Gate pass.
- FORCE means a force override log exists; it is not the same as normal pass.
"""

from __future__ import annotations

import argparse
import re
from datetime import datetime
from pathlib import Path

from pipeline_utils import configure_utf8_stdio, find_score, find_status_tag, load_yaml_simple


configure_utf8_stdio()

_COV_THRESHOLD = 75
_QUAL_THRESHOLD = 70


REQUIRED_05_SECTIONS = [
    "Logos 연구에서 얻은 핵심 통찰",
    "설교에 반드시 반영할 통찰",
    "반영하지 않기로 한 자료",
    "도덕주의 위험",
    "그리스도 연결",
    "Big Idea",
    "Gate Decision",
]


def discover_passages(docs_dir: Path) -> list[Path]:
    return sorted(docs_dir.glob("*/*/00-passage.yaml"))


def extract_score_and_status(path: Path) -> tuple[int | None, str]:
    if not path.exists():
        return None, ""
    text = path.read_text(encoding="utf-8", errors="replace")
    return find_score(text), find_status_tag(text)


def _section_body(content: str, heading: str) -> str:
    pattern = rf"##\s+.*{re.escape(heading)}.*\n(?P<body>.*?)(?=\n##\s+|\Z)"
    match = re.search(pattern, content, flags=re.DOTALL)
    return match.group("body").strip() if match else ""


def _has_substantive_body(body: str) -> bool:
    for line in body.splitlines():
        s = line.strip()
        if not s:
            continue
        if s.startswith("<!--") or s.startswith(">"):
            continue
        if re.match(r"^\d+\.\s*$", s):
            continue
        if re.match(r"^-\s*(Coverage Score|Capture Quality Score|Gate Decision|Deep Research 진행 여부):\s*$", s):
            continue
        if len(s) >= 8:
            return True
    return False


def check_05_filled(path: Path) -> bool:
    if not path.exists():
        return False
    content = path.read_text(encoding="utf-8", errors="replace")
    if "여기에 작성" in content or "<!--" in content:
        return False
    return all(_has_substantive_body(_section_body(content, section)) for section in REQUIRED_05_SECTIONS)


def force_confirmed(path: Path) -> bool:
    if not path.exists():
        return False
    text = path.read_text(encoding="utf-8", errors="replace")
    return "- [x]" in text.lower()


def derive_gate(cov_score: int | None, cov_status: str, qual_score: int | None, docs_dir: Path) -> str:
    force_log = docs_dir / "force-override-log.md"
    if force_log.exists():
        return "FORCE_OK" if force_confirmed(force_log) else "FORCE"
    if cov_score is None:
        return "-"
    if cov_status == "insufficient" or cov_score < 60:
        return "FAIL"
    if cov_score < _COV_THRESHOLD:
        return "REV."
    if qual_score is None:
        return "REV."
    if qual_score < 60:
        return "FAIL"
    if qual_score < _QUAL_THRESHOLD:
        return "REV."
    return "PASS"


def _08_status(docs_dir: Path) -> str:
    f08 = docs_dir / "08-final-direction.md"
    f07 = docs_dir / "07-deep-research.md"
    if not f08.exists():
        return "--"
    return "OK" if f07.exists() else "SC"


def derive_next_step(state: dict) -> str:
    gate = state["gate"]
    if not state["has_03"]:
        return "Coverage audit 실행"
    if not state["has_04"]:
        return "Quality audit 실행"
    if gate == "FAIL":
        return "Logos 자료 보강 필요"
    if gate == "FORCE":
        return "FORCE 기록 검토: 보강 또는 목회자 확인 필요"
    if gate == "FORCE_OK":
        return "제한 진행 가능: 정상 PASS 아님"
    if gate in ("REV.", "-"):
        return "자료 보강 후 Gate 재실행"
    if gate == "PASS":
        if not state["has_05_filled"]:
            return "05 Integration Summary 작성"
        if not state["has_07"]:
            return "Deep research 실행"
        if not state["has_06"]:
            return "Research Context 재생성"
        if state["08_status"] == "--":
            return "Final direction 생성"
        if state["08_status"] == "SC":
            return "Deep research 후 direction 재생성"
        return "설교 작성 착수 가능"
    return "상태 확인 필요"


def collect_state(yaml_path: Path) -> dict:
    docs_dir = yaml_path.parent
    data = load_yaml_simple(yaml_path)
    label = f"{data.get('book_korean', data.get('book', ''))} {data.get('passage', '')}".strip()
    cov_score, cov_status = extract_score_and_status(docs_dir / "03-logos-coverage-report.md")
    qual_score, qual_status = extract_score_and_status(docs_dir / "04-capture-quality-report.md")
    gate = derive_gate(cov_score, cov_status, qual_score, docs_dir)
    s08 = _08_status(docs_dir)
    state = {
        "label": label,
        "docs_dir": docs_dir,
        "cov_score": cov_score,
        "qual_score": qual_score,
        "cov_status": cov_status,
        "qual_status": qual_status,
        "gate": gate,
        "has_03": (docs_dir / "03-logos-coverage-report.md").exists(),
        "has_04": (docs_dir / "04-capture-quality-report.md").exists(),
        "has_05_filled": check_05_filled(docs_dir / "05-logos-integration-summary.md"),
        "has_06": (docs_dir / "06-research-context.md").exists(),
        "has_07": (docs_dir / "07-deep-research.md").exists(),
        "has_08": (docs_dir / "08-final-direction.md").exists(),
        "08_status": s08,
    }
    state["next"] = derive_next_step(state)
    return state


def fmt_score(score: int | None) -> str:
    return "--" if score is None else str(score)


def render_table(states: list[dict]) -> str:
    now = datetime.now().strftime("%Y-%m-%d")
    lines = [
        f"Logos-Max v2.1 파이프라인 현황 ({now})",
        "-" * 100,
        f"{'본문':<20} {'Cov':>5} {'Qual':>5} {'Gate':<9} {'05':<3} {'06':<3} {'07':<3} {'08':<3} 다음 단계",
        "-" * 100,
    ]
    counts: dict[str, int] = {}
    for state in states:
        counts[state["gate"]] = counts.get(state["gate"], 0) + 1
        lines.append(
            f"{state['label'][:20]:<20} "
            f"{fmt_score(state['cov_score']):>5} "
            f"{fmt_score(state['qual_score']):>5} "
            f"{state['gate']:<9} "
            f"{'Y' if state['has_05_filled'] else 'N':<3} "
            f"{'Y' if state['has_06'] else 'N':<3} "
            f"{'Y' if state['has_07'] else 'N':<3} "
            f"{state['08_status']:<3} "
            f"{state['next']}"
        )
    lines.append("-" * 100)
    summary = "  ".join(f"{key}: {value}" for key, value in sorted(counts.items()))
    lines.append(f"총 {len(states)}개 본문  {summary}")
    return "\n".join(lines)


def render_detail(state: dict) -> str:
    docs_dir = state["docs_dir"]
    return "\n".join([
        f"[{state['label']}] 상세 현황",
        f"- docs dir: {docs_dir}",
        f"- Coverage: {fmt_score(state['cov_score'])}/100 [{state['cov_status'] or '-'}]",
        f"- Quality: {fmt_score(state['qual_score'])}/100 [{state['qual_status'] or '-'}]",
        f"- Gate: {state['gate']}",
        f"- 05 integration summary: {'OK' if state['has_05_filled'] else '미완료'}",
        f"- 06 research context: {'OK' if state['has_06'] else '--'}",
        f"- 07 deep research: {'OK' if state['has_07'] else '--'}",
        f"- 08 final direction: {state['08_status']}",
        f"- force override log: {'있음' if (docs_dir / 'force-override-log.md').exists() else '없음'}",
        f"- 다음 단계: {state['next']}",
    ])


def main() -> int:
    parser = argparse.ArgumentParser(description="Show Logos-Max v2.1 pipeline status.")
    parser.add_argument("--docs", default="docs", help="docs root directory")
    parser.add_argument("--passage", help="Path to one 00-passage.yaml")
    parser.add_argument("--save", action="store_true", help="Save dashboard to docs/STATUS.md")
    args = parser.parse_args()

    docs_root = Path(args.docs)
    if args.passage:
        yaml_path = Path(args.passage)
        if not yaml_path.exists():
            print(f"[ERROR] passage.yaml 없음: {yaml_path}")
            return 1
        state = collect_state(yaml_path)
        print(render_table([state]))
        print()
        print(render_detail(state))
        return 0

    yamls = discover_passages(docs_root)
    if not yamls:
        print(f"[INFO] passage.yaml을 찾지 못했습니다: {docs_root}")
        return 0

    states = [collect_state(path) for path in yamls]
    table = render_table(states)
    print(table)
    if args.save:
        out = docs_root / "STATUS.md"
        out.write_text(f"```\n{table}\n```\n", encoding="utf-8")
        print(f"\n[OK] 저장됨: {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
