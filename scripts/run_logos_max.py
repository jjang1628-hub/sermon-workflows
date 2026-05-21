"""
run_logos_max.py — Logos-Max v2 마스터 파이프라인

새 본문 연구 시작부터 심층 연구 통과까지의 전체 흐름을 실행한다.

Logos-Max v2 흐름:
  0. passage.yaml 확인 / 생성
  1. Logos 연구 레시피 생성
  2. Logos 캡처 체크리스트 생성
  3. 캡처 파일 존재 여부 확인
  4. Coverage Audit 실행
  5. Coverage Gate — 기준 미달 시 중단
  6. (통과 시) deep research 실행

사용법:
    # 새 본문 시작
    python scripts/run_logos_max.py --book John --passage 13:14 --context 13:1-17 --genre gospel

    # 이미 passage.yaml이 있는 경우
    python scripts/run_logos_max.py --passage docs/john/13-14/00-passage.yaml

    # 캡처 완료 후 coverage 감사만
    python scripts/run_logos_max.py --passage docs/john/13-14/00-passage.yaml --step audit

    # coverage 통과 후 deep research 실행
    python scripts/run_logos_max.py --passage docs/john/13-14/00-passage.yaml --step deep

    # coverage 점수와 무관하게 deep research 강행 (테스트용)
    python scripts/run_logos_max.py --passage docs/john/13-14/00-passage.yaml --force-deep
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

SCRIPTS_DIR = Path("scripts")


def run(cmd: list[str], check: bool = True) -> int:
    """서브프로세스 실행 후 returncode 반환."""
    result = subprocess.run(cmd)
    if check and result.returncode not in (0, 1):
        print(f"[ERROR] 명령 실패 (exit {result.returncode}): {' '.join(cmd)}", file=sys.stderr)
    return result.returncode


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


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Logos-Max v2 마스터 파이프라인"
    )
    # 새 본문 시작 옵션
    parser.add_argument("--book", default=None, help="영어 책 이름 (신규 시작 시)")
    parser.add_argument("--passage", default=None,
                        help="passage.yaml 경로 또는 새 본문 (e.g. 13:14)")
    parser.add_argument("--context", default=None, help="문맥 범위 (신규 시작 시)")
    parser.add_argument("--genre", default=None, help="장르 (신규 시작 시)")
    parser.add_argument("--theme-hint", default="", help="테마 힌트")

    # 실행 제어
    parser.add_argument("--step",
                        choices=["setup", "recipe", "audit", "gate", "deep", "all"],
                        default="all",
                        help="실행 단계 (기본: all)")
    parser.add_argument("--min-score", type=int, default=75,
                        help="Coverage Gate 최소 점수 (기본: 75)")
    parser.add_argument("--force-deep", action="store_true",
                        help="Coverage 점수와 무관하게 deep research 실행")
    parser.add_argument("--capture-dir", default="tmp/logos-capture/raw",
                        help="캡처 파일 폴더")

    # Deep research 옵션
    parser.add_argument("--model", default=None, help="Claude 모델")
    parser.add_argument("--skip-ollama", action="store_true", help="Ollama 건너뛰기")

    return parser.parse_args()


def find_passage_yaml(args: argparse.Namespace) -> Path | None:
    """passage.yaml 경로를 결정한다."""
    if args.passage and args.passage.endswith(".yaml"):
        p = Path(args.passage)
        return p if p.exists() else None

    # --book + --passage 조합으로 경로 추론
    if args.book and args.passage:
        book_map = {
            "John": "john", "Romans": "romans", "Matthew": "matthew",
            "Mark": "mark", "Luke": "luke", "Acts": "acts",
            "Genesis": "genesis", "Exodus": "exodus", "Psalms": "psalms",
        }
        book_folder = book_map.get(args.book, args.book.lower())
        slug = args.passage.replace(":", "-")
        p = Path("docs") / book_folder / slug / "00-passage.yaml"
        return p if p.exists() else None

    return None


def step_setup(args: argparse.Namespace) -> tuple[int, Path | None]:
    """0단계: passage.yaml 생성"""
    if not args.book or not args.passage or not args.context:
        print("[ERROR] 신규 시작에는 --book, --passage, --context 가 모두 필요합니다.",
              file=sys.stderr)
        return 1, None

    cmd = [
        sys.executable, str(SCRIPTS_DIR / "create_passage.py"),
        "--book", args.book,
        "--passage", args.passage,
        "--context", args.context,
    ]
    if args.genre:
        cmd += ["--genre", args.genre]
    if args.theme_hint:
        cmd += ["--theme-hint", args.theme_hint]

    rc = run(cmd)
    if rc != 0:
        return rc, None

    # 생성된 passage.yaml 경로 추론
    passage_yaml = find_passage_yaml(args)
    return 0, passage_yaml


def step_recipe(passage_yaml: Path) -> int:
    """1–2단계: 레시피 + 체크리스트 생성"""
    return run([
        sys.executable, str(SCRIPTS_DIR / "build_logos_recipe.py"),
        "--passage", str(passage_yaml),
    ])


def step_audit(passage_yaml: Path, capture_dir: str) -> int:
    """4단계: Coverage Audit"""
    return run([
        sys.executable, str(SCRIPTS_DIR / "audit_logos_coverage.py"),
        "--passage", str(passage_yaml),
        "--capture-dir", capture_dir,
    ], check=False)  # exit 1 = 보류 (오류 아님)


def step_gate(passage_yaml: Path, min_score: int, force: bool) -> int:
    """5단계: Coverage Gate"""
    cmd = [
        sys.executable, str(SCRIPTS_DIR / "gate_deep_research.py"),
        "--passage", str(passage_yaml),
        "--min-score", str(min_score),
    ]
    if force:
        cmd.append("--force")
    return run(cmd, check=False)


def step_deep(passage_yaml: Path, args: argparse.Namespace) -> int:
    """6단계: Deep Research"""
    data = load_yaml_simple(passage_yaml)
    book_korean = data.get("book_korean", "")
    passage = data.get("passage", "")
    passage_str = f"{book_korean} {passage}"

    cmd = [
        sys.executable, str(SCRIPTS_DIR / "run_logos_max_research.py"),
        "--passage", passage_str,
    ]
    if args.skip_ollama:
        cmd.append("--skip-ollama")
    if args.model:
        cmd += ["--model", args.model]

    # 캡처 파일 지정
    capture_dir = Path(args.capture_dir)
    if capture_dir.exists():
        cmd += ["--capture-dir", str(capture_dir)]

    return run(cmd)


def print_banner(title: str) -> None:
    print(f"\n{'─'*55}")
    print(f"  {title}")
    print(f"{'─'*55}\n")


def main() -> int:
    args = parse_args()

    print_banner("Logos-Max v2 — Sermon Research Pipeline")

    # passage.yaml 경로 결정
    passage_yaml = find_passage_yaml(args)

    step = args.step

    # === 0단계: setup ===
    if passage_yaml is None or step == "setup":
        print_banner("0단계: passage.yaml 생성")
        rc, passage_yaml = step_setup(args)
        if rc != 0 or passage_yaml is None:
            print("\n[STOPPED] passage.yaml 생성 실패")
            return 1
        if step == "setup":
            return 0

    if not passage_yaml.exists():
        print(f"[ERROR] passage.yaml 없음: {passage_yaml}", file=sys.stderr)
        print("  python scripts/create_passage.py --book ... --passage ... --context ...",
              file=sys.stderr)
        return 1

    data = load_yaml_simple(passage_yaml)
    book_korean = data.get("book_korean", "")
    passage_ref = data.get("passage", "")
    print(f"본문: {book_korean} {passage_ref}")
    print(f"장르: {data.get('genre', '—')}")

    # === 1–2단계: recipe ===
    if step in ("all", "recipe"):
        print_banner("1–2단계: Logos 레시피 + 체크리스트 생성")
        rc = step_recipe(passage_yaml)
        if rc != 0:
            return rc
        if step == "recipe":
            print("\n체크리스트를 열어 Logos에서 캡처를 진행하십시오.")
            print(f"  {passage_yaml.parent / '02-logos-capture-checklist.md'}")
            return 0

    # === 3단계: 캡처 확인 (audit 이전) ===
    if step in ("all", "audit", "gate", "deep"):
        capture_dir = Path(args.capture_dir)
        if not capture_dir.exists() or not list(capture_dir.glob("*.md")):
            if not args.force_deep:
                print(f"\n[PAUSED] 캡처 파일이 없습니다: {capture_dir}")
                print()
                print("  Logos에서 아래 체크리스트를 따라 캡처하십시오:")
                print(f"  {passage_yaml.parent / '02-logos-capture-checklist.md'}")
                print()
                print("  캡처 완료 후 재실행:")
                print(f"  python scripts/run_logos_max.py --passage {passage_yaml} --step audit")
                return 0

    # === 4단계: audit ===
    if step in ("all", "audit", "gate", "deep"):
        print_banner("4단계: Logos Coverage Audit")
        audit_rc = step_audit(passage_yaml, args.capture_dir)
        if step == "audit":
            return 0

    # === 5단계: gate ===
    if step in ("all", "gate", "deep"):
        print_banner("5단계: Coverage Gate")
        gate_rc = step_gate(passage_yaml, args.min_score, args.force_deep)
        if gate_rc == 2:
            print("\n[STOPPED] 필수 자료 누락 — 파이프라인을 중단합니다.")
            return 1
        elif gate_rc == 1 and not args.force_deep:
            print("\n[PAUSED] 보강 권장 — deep research를 보류합니다.")
            print("  Logos에서 누락 자료를 보강하거나 --force-deep 으로 진행하십시오.")
            return 0
        if step == "gate":
            return 0

    # === 6단계: deep research ===
    if step in ("all", "deep"):
        print_banner("6단계: Logos-Max Deep Research")
        return step_deep(passage_yaml, args)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
