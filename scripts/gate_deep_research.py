"""
Combined deep-research gate for Logos-Max v2.1.

Deep research may run only when both scores are adequate:
- Logos Coverage Score: required research categories are present.
- Capture Quality Score: captured material is useful for sermon research.

Force override is allowed only with an explicit reason and writes
force-override-log.md into the passage docs folder.
"""

from __future__ import annotations

import argparse
import re
import sys
from datetime import datetime
from pathlib import Path

from pipeline_utils import configure_utf8_stdio, load_yaml_simple


configure_utf8_stdio()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Decide whether Logos-Max deep research may run.")
    parser.add_argument("--passage", required=True, help="Path to 00-passage.yaml")
    parser.add_argument("--coverage-report", default=None, help="Path to 03-logos-coverage-report.md")
    parser.add_argument("--quality-report", default=None, help="Path to 04-capture-quality-report.md")
    parser.add_argument("--min-coverage", type=int, default=75, help="Minimum coverage score for normal PASS")
    parser.add_argument("--min-quality", type=int, default=70, help="Minimum quality score for normal PASS")
    parser.add_argument("--force", action="store_true", help="Override gate after recording reason")
    parser.add_argument("--reason", default="", help="Required when --force is used")
    return parser.parse_args()


def extract_score(report_path: Path, label_hint: str = "") -> int | None:
    if not report_path.exists():
        return None
    text = report_path.read_text(encoding="utf-8", errors="replace")

    if label_hint:
        pattern = rf"{re.escape(label_hint)}.*?(\d+)\s*/\s*100"
        match = re.search(pattern, text, flags=re.IGNORECASE | re.DOTALL)
        if match:
            return int(match.group(1))

    for pattern in (r"###\s+(\d+)\s*/\s*100", r"[Ss]core[:\s]+(\d+)\s*/?\s*100?"):
        match = re.search(pattern, text)
        if match:
            return int(match.group(1))
    return None


def extract_missing_coverage(report_path: Path) -> list[str]:
    if not report_path.exists():
        return []
    text = report_path.read_text(encoding="utf-8", errors="replace")
    missing: list[str] = []
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("### R-") and "(0/" in stripped:
            missing.append(stripped.lstrip("# ").strip())
    return missing[:20]


def extract_weak_quality(report_path: Path) -> list[str]:
    if not report_path.exists():
        return []
    text = report_path.read_text(encoding="utf-8", errors="replace")
    weak: list[str] = []
    in_weak = False
    for line in text.splitlines():
        if line.strip().startswith("## Weak Categories"):
            in_weak = True
            continue
        if in_weak and line.startswith("## "):
            break
        if in_weak and line.startswith("### "):
            weak.append(line.lstrip("# ").strip())
    return weak


def decide_status(
    coverage: int,
    quality: int,
    min_coverage: int = 75,
    min_quality: int = 70,
) -> tuple[str, int, str]:
    """Return (status, exit_code, explanation)."""
    if coverage < 60:
        return "gate_blocked", 2, "Coverage Score가 60점 미만입니다."
    if coverage < min_coverage:
        return "capture_incomplete", 1, f"Coverage Score가 {min_coverage}점 미만입니다."
    if quality < 60:
        return "quality_blocked", 2, "Capture Quality Score가 60점 미만입니다."
    if quality < min_quality:
        return "review_required", 1, f"Capture Quality Score가 {min_quality}점 미만입니다."
    if coverage >= 90 and quality >= 80:
        return "logos_max_deep_eligible", 0, "Logos-Max deep research 기준을 넉넉히 통과했습니다."
    return "deep_eligible", 0, "deep research 진행 가능 기준을 통과했습니다."


def write_force_log(
    passage_path: Path,
    passage_data: dict[str, str],
    coverage: int | None,
    quality: int | None,
    missing: list[str],
    weak: list[str],
    reason: str,
) -> Path:
    log_path = passage_path.parent / "force-override-log.md"
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    passage_label = f"{passage_data.get('book_korean', passage_data.get('book', ''))} {passage_data.get('passage', '')}".strip()

    lines = [
        "# Force Override Log",
        "",
        f"- Passage: {passage_label}",
        f"- Timestamp: {now}",
        f"- Coverage Score: {coverage if coverage is not None else 'unknown'}",
        f"- Capture Quality Score: {quality if quality is not None else 'unknown'}",
        f"- Override Reason: {reason}",
        "",
        "## Missing Categories",
        "",
    ]
    lines += [f"- {item}" for item in missing] if missing else ["- 없음 또는 파싱 불가"]
    lines += ["", "## Weak Categories", ""]
    lines += [f"- {item}" for item in weak] if weak else ["- 없음 또는 파싱 불가"]
    lines += [
        "",
        "## Risks Acknowledged",
        "",
        "- Logos 자료가 충분하지 않거나 약한 상태일 수 있습니다.",
        "- AI deep research 결과는 최종 신학 판단이 아닙니다.",
        "- 설교자는 본문과 실제 Logos 자료를 다시 검토해야 합니다.",
        "",
        "## Pastor Confirmation",
        "",
        "- [ ] 위 위험을 확인했고 제한적 진행을 승인함",
    ]
    log_path.write_text("\n".join(lines), encoding="utf-8")
    return log_path


def main() -> int:
    args = parse_args()
    passage_path = Path(args.passage)
    if not passage_path.exists():
        print(f"[ERROR] passage.yaml 없음: {passage_path}", file=sys.stderr)
        return 2

    passage_data = load_yaml_simple(passage_path)
    output_dir = passage_path.parent
    coverage_path = Path(args.coverage_report) if args.coverage_report else output_dir / "03-logos-coverage-report.md"
    quality_path = Path(args.quality_report) if args.quality_report else output_dir / "04-capture-quality-report.md"

    coverage = extract_score(coverage_path, "Coverage Score")
    quality = extract_score(quality_path, "Capture Quality Score")
    missing = extract_missing_coverage(coverage_path)
    weak = extract_weak_quality(quality_path)

    print("\n" + "=" * 60)
    print("  Logos-Max v2.1 Deep Research Gate")
    print("=" * 60)
    print(f"Passage: {passage_data.get('book_korean', passage_data.get('book', ''))} {passage_data.get('passage', '')}")
    print(f"Coverage report: {coverage_path}")
    print(f"Quality report:  {quality_path}")

    if coverage is None:
        print("\n[GATE BLOCKED] Coverage Score를 읽을 수 없습니다.")
        print(f"먼저 실행: python scripts/audit_logos_coverage.py --passage {passage_path}")
        return 2
    if quality is None:
        print("\n[GATE BLOCKED] Capture Quality Score를 읽을 수 없습니다.")
        print(f"먼저 실행: python scripts/audit_capture_quality.py --passage {passage_path}")
        return 2

    status, exit_code, explanation = decide_status(
        coverage,
        quality,
        min_coverage=args.min_coverage,
        min_quality=args.min_quality,
    )

    print(f"\nCoverage Score: {coverage}/100")
    print(f"Capture Quality Score: {quality}/100")
    print(f"Gate Decision: {status}")
    print(f"Reason: {explanation}")

    if missing:
        print("\nMissing coverage categories:")
        for item in missing[:10]:
            print(f"  - {item}")
    if weak:
        print("\nWeak quality categories:")
        for item in weak[:10]:
            print(f"  - {item}")

    if args.force:
        if not args.reason.strip():
            print("\n[FORCE REJECTED] --force 사용 시 --reason 이 필요합니다.", file=sys.stderr)
            return 2
        log_path = write_force_log(
            passage_path,
            passage_data,
            coverage,
            quality,
            missing,
            weak,
            args.reason.strip(),
        )
        print("\n[FORCE OVERRIDE RECORDED]")
        print(f"Log: {log_path}")
        print("제한적 deep research 진행은 허용되지만 정상 Gate 통과가 아닙니다.")
        return 0

    if exit_code == 0:
        print("\n[GATE PASSED] deep research를 진행할 수 있습니다.")
        return 0

    if exit_code == 1:
        print("\n[GATE PAUSED] 자료 보강 또는 목회적 검토 후 진행하십시오.")
        print("강제 진행이 꼭 필요하면 사유를 남기십시오:")
        print(f'  python scripts/gate_deep_research.py --passage {passage_path} --force --reason "사유"')
        return 1

    print("\n[GATE BLOCKED] 현재 상태에서는 deep research를 중단합니다.")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
