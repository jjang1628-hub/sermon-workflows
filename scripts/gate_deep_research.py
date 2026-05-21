"""
gate_deep_research.py — Logos Coverage Gate

Logos Coverage Score를 읽어 심층 연구 진행 여부를 결정한다.
기준 미달이면 중단하고 누락 항목을 안내한다.

사용법:
    python scripts/gate_deep_research.py --passage docs/john/13-14/00-passage.yaml
    python scripts/gate_deep_research.py --passage docs/john/13-14/00-passage.yaml --min-score 75
    python scripts/gate_deep_research.py --passage docs/john/13-14/00-passage.yaml --force

Exit codes:
    0 = 통과 (deep research 진행 가능)
    1 = 보류 (보강 필요)
    2 = 중단 (필수 자료 누락)
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Logos Coverage Gate — 심층 연구 진행 여부를 결정합니다."
    )
    parser.add_argument("--passage", required=True, help="passage.yaml 경로")
    parser.add_argument("--min-score", type=int, default=75,
                        help="심층 연구 최소 점수 (기본: 75)")
    parser.add_argument("--force", action="store_true",
                        help="점수와 관계없이 진행 (테스트용)")
    parser.add_argument("--coverage-report", default=None,
                        help="커버리지 보고서 경로 (기본: 03-logos-coverage-report.md)")
    return parser.parse_args()


def load_yaml_simple(path: Path) -> dict:
    data = {}
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = line.strip()
        if line.startswith("#") or not line or line.startswith("-"):
            continue
        if ": " in line:
            k, v = line.split(": ", 1)
            data[k.strip()] = v.strip().strip('"')
    return data


def extract_score_from_report(report_path: Path) -> int | None:
    """03-logos-coverage-report.md 에서 점수를 파싱한다."""
    if not report_path.exists():
        return None
    text = report_path.read_text(encoding="utf-8", errors="replace")
    # "### 87 / 100점" 패턴
    match = re.search(r"###\s+(\d+)\s*/\s*100", text)
    if match:
        return int(match.group(1))
    # "Score: 87/100" 패턴
    match = re.search(r"[Ss]core[:\s]+(\d+)\s*/\s*100", text)
    if match:
        return int(match.group(1))
    return None


def extract_missing_from_report(report_path: Path) -> list[str]:
    """보고서에서 누락 항목을 추출한다."""
    if not report_path.exists():
        return []
    text = report_path.read_text(encoding="utf-8", errors="replace")
    missing = re.findall(r"❌\s+(R-\d+)\s+—\s+([^\n(]+)", text)
    return [f"{rid} {label.strip()}" for rid, label in missing]


def main() -> int:
    args = parse_args()
    passage_path = Path(args.passage)

    if not passage_path.exists():
        print(f"[ERROR] passage.yaml 없음: {passage_path}", file=sys.stderr)
        return 2

    passage_data = load_yaml_simple(passage_path)
    book_korean = passage_data.get("book_korean", "")
    passage = passage_data.get("passage", "")
    output_dir = passage_path.parent

    coverage_path = (
        Path(args.coverage_report)
        if args.coverage_report
        else output_dir / "03-logos-coverage-report.md"
    )

    print(f"\n{'='*55}")
    print(f"  Logos Coverage Gate — {book_korean} {passage}")
    print(f"{'='*55}")

    # --force 모드
    if args.force:
        print("\n⚠️  --force 모드: 점수 확인 없이 통과합니다.")
        print("   (실제 사용 시 제거하십시오.)")
        _print_next_steps(book_korean, passage)
        return 0

    # 커버리지 보고서 확인
    if not coverage_path.exists():
        print(f"\n[GATE BLOCKED] 커버리지 보고서가 없습니다: {coverage_path}")
        print("\n먼저 실행하십시오:")
        print(f"  python scripts/audit_logos_coverage.py --passage {passage_path}")
        return 2

    score = extract_score_from_report(coverage_path)
    if score is None:
        print(f"\n[GATE BLOCKED] 보고서에서 점수를 읽을 수 없습니다: {coverage_path}")
        print("  audit_logos_coverage.py를 다시 실행하십시오.")
        return 2

    missing = extract_missing_from_report(coverage_path)

    print(f"\n  Coverage Score: {score}/100")
    print(f"  최소 기준: {args.min_score}/100")

    if score >= 90:
        print(f"\n✅ GATE PASSED (최고 등급)")
        print(f"   Logos-Max 심층 연구를 즉시 실행할 수 있습니다.")
        _print_next_steps(book_korean, passage)
        return 0

    elif score >= args.min_score:
        print(f"\n✅ GATE PASSED (경고 포함)")
        if missing:
            print(f"\n⚠️  누락 항목 ({len(missing)}개) — 보강하면 품질이 높아집니다:")
            for m in missing:
                print(f"   - {m}")
        _print_next_steps(book_korean, passage)
        return 0

    elif score >= 60:
        print(f"\n🔴 GATE BLOCKED — 보강 필요")
        print(f"   현재 점수: {score}점 (기준: {args.min_score}점)")
        print(f"\n누락 항목:")
        for m in missing:
            print(f"  ❌ {m}")
        print(f"\n보강 후 재실행하십시오:")
        print(f"  python scripts/audit_logos_coverage.py --passage {passage_path}")
        print(f"\n  (점수와 무관하게 진행하려면: --force 옵션)")
        return 1

    else:
        print(f"\n🛑 GATE STOPPED — 연구팩 불충분")
        print(f"   현재 점수: {score}점 (기준: {args.min_score}점)")
        print(f"\n필수 Logos 자료가 누락되었습니다:")
        for m in missing:
            print(f"  ❌ {m}")
        print(f"\nLogos 캡처 체크리스트를 확인하십시오:")
        print(f"  {output_dir / '02-logos-capture-checklist.md'}")
        return 2


def _print_next_steps(book_korean: str, passage: str) -> None:
    print(f"\n다음 단계:")
    print(f'  python scripts/run_logos_max_research.py --passage "{book_korean} {passage}"')
    print()


if __name__ == "__main__":
    raise SystemExit(main())
