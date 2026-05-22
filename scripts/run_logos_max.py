"""
run_logos_max.py - Logos-Max v2.1 master pipeline

Pipeline:
  1. passage.yaml 확인/생성
  2. Logos recipe 생성
  3. capture checklist 생성
  4. Coverage audit
  5. Capture quality audit
  6. Combined gate decision
  7. Gate 통과 시에만 deep research 실행

This is a Logos-first gate system, not a direct sermon generator.
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
    print(f"\n$ {' '.join(cmd)}")
    result = subprocess.run(cmd)
    if check and result.returncode != 0:
        print(f"[ERROR] 명령 실패(exit {result.returncode}): {' '.join(cmd)}", file=sys.stderr)
    return result.returncode


def load_yaml_simple(path: Path) -> dict[str, str]:
    data: dict[str, str] = {}
    for raw_line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        stripped = raw_line.strip()
        if not stripped or stripped.startswith("#") or stripped.startswith("-"):
            continue
        if ":" in stripped:
            key, value = stripped.split(":", 1)
            data[key.strip()] = value.strip().strip('"')
    return data


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the Logos-Max v2.1 Logos-first workflow.")
    parser.add_argument("--book", default=None, help="Book name for new passage, e.g. John")
    parser.add_argument("--passage", default=None, help="Path to passage.yaml or passage ref, e.g. 13:14")
    parser.add_argument("--context", default=None, help="Context range for new passage, e.g. 13:1-17")
    parser.add_argument("--genre", default=None, help="Genre, e.g. gospel_farewell_discourse")
    parser.add_argument("--theme-hint", default="", help="Theme hint for new passage")
    parser.add_argument(
        "--step",
        choices=["setup", "recipe", "audit", "quality", "gate", "deep", "all"],
        default="all",
        help="Pipeline step to run",
    )
    parser.add_argument("--capture-dir", default="tmp/logos-capture/raw", help="Raw Logos capture directory")
    parser.add_argument("--force-deep", action="store_true", help="Override gate and run deep research")
    parser.add_argument("--force-reason", default="", help="Required with --force-deep")
    parser.add_argument("--model", default=None, help="Claude model for downstream deep research")
    parser.add_argument("--skip-ollama", action="store_true", help="Pass through to deep research pipeline")
    return parser.parse_args()


def infer_book_folder(book: str) -> str:
    book_map = {
        "John": "john",
        "Romans": "romans",
        "Matthew": "matthew",
        "Mark": "mark",
        "Luke": "luke",
        "Acts": "acts",
        "Genesis": "genesis",
        "Exodus": "exodus",
        "Psalms": "psalms",
    }
    return book_map.get(book, book.lower())


def find_passage_yaml(args: argparse.Namespace) -> Path | None:
    if args.passage and args.passage.endswith(".yaml"):
        path = Path(args.passage)
        return path if path.exists() else None

    if args.book and args.passage:
        folder = infer_book_folder(args.book)
        slug = args.passage.replace(":", "-")
        path = Path("docs") / folder / slug / "00-passage.yaml"
        return path if path.exists() else None

    return None


def step_setup(args: argparse.Namespace) -> tuple[int, Path | None]:
    if not args.book or not args.passage or not args.context:
        print("[ERROR] 새 passage.yaml 생성에는 --book, --passage, --context가 필요합니다.", file=sys.stderr)
        return 1, None

    cmd = [
        sys.executable,
        str(SCRIPTS_DIR / "create_passage.py"),
        "--book",
        args.book,
        "--passage",
        args.passage,
        "--context",
        args.context,
    ]
    if args.genre:
        cmd += ["--genre", args.genre]
    if args.theme_hint:
        cmd += ["--theme-hint", args.theme_hint]

    rc = run(cmd)
    return rc, find_passage_yaml(args)


def step_recipe(passage_yaml: Path) -> int:
    return run([
        sys.executable,
        str(SCRIPTS_DIR / "build_logos_recipe.py"),
        "--passage",
        str(passage_yaml),
    ])


def step_coverage_audit(passage_yaml: Path, capture_dir: str) -> int:
    return run([
        sys.executable,
        str(SCRIPTS_DIR / "audit_logos_coverage.py"),
        "--passage",
        str(passage_yaml),
        "--capture-dir",
        capture_dir,
    ], check=False)


def step_quality_audit(passage_yaml: Path, capture_dir: str) -> int:
    return run([
        sys.executable,
        str(SCRIPTS_DIR / "audit_capture_quality.py"),
        "--passage",
        str(passage_yaml),
        "--capture-dir",
        capture_dir,
    ], check=False)


def step_gate(passage_yaml: Path, force: bool, reason: str) -> int:
    cmd = [
        sys.executable,
        str(SCRIPTS_DIR / "gate_deep_research.py"),
        "--passage",
        str(passage_yaml),
    ]
    if force:
        cmd += ["--force", "--reason", reason]
    return run(cmd, check=False)


def step_deep(passage_yaml: Path, args: argparse.Namespace) -> int:
    data = load_yaml_simple(passage_yaml)
    book_korean = data.get("book_korean", data.get("book", ""))
    passage = data.get("passage", "")
    passage_label = f"{book_korean} {passage}".strip()

    cmd = [
        sys.executable,
        str(SCRIPTS_DIR / "run_logos_max_research.py"),
        "--passage",
        passage_label,
    ]
    if args.skip_ollama:
        cmd.append("--skip-ollama")
    if args.model:
        cmd += ["--model", args.model]
    capture_dir = Path(args.capture_dir)
    if capture_dir.exists():
        cmd += ["--capture-dir", str(capture_dir)]
    return run(cmd)


def ensure_capture_files(capture_dir: Path, force: bool) -> bool:
    has_files = capture_dir.exists() and bool(list(capture_dir.glob("*.md")) or list(capture_dir.glob("*.txt")))
    if has_files or force:
        return True
    print(f"\n[PAUSED] 캡처 파일이 없습니다: {capture_dir}")
    print("Logos에서 체크리스트에 따라 자료를 캡처한 뒤 다시 실행하십시오.")
    return False


def banner(title: str) -> None:
    print("\n" + "=" * 60)
    print(f"  {title}")
    print("=" * 60)


def main() -> int:
    args = parse_args()
    banner("Logos-Max v2.1 - Logos-first Sermon Workflow")

    passage_yaml = find_passage_yaml(args)

    if passage_yaml is None or args.step == "setup":
        banner("1. passage.yaml 확인/생성")
        rc, passage_yaml = step_setup(args)
        if rc != 0 or passage_yaml is None:
            print("[STOPPED] passage.yaml을 준비하지 못했습니다.")
            return 1
        if args.step == "setup":
            return 0

    if not passage_yaml.exists():
        print(f"[ERROR] passage.yaml 없음: {passage_yaml}", file=sys.stderr)
        return 1

    data = load_yaml_simple(passage_yaml)
    print(f"본문: {data.get('book_korean', data.get('book', ''))} {data.get('passage', '')}")
    print(f"장르: {data.get('genre', '')}")

    if args.step in ("all", "recipe"):
        banner("2-3. Logos recipe + capture checklist")
        rc = step_recipe(passage_yaml)
        if rc != 0:
            return rc
        if args.step == "recipe":
            print(f"\n체크리스트: {passage_yaml.parent / '02-logos-capture-checklist.md'}")
            return 0

    capture_dir = Path(args.capture_dir)
    if args.step in ("all", "audit", "quality", "gate", "deep"):
        if not ensure_capture_files(capture_dir, args.force_deep):
            return 0

    if args.step in ("all", "audit", "gate", "deep"):
        banner("4. Coverage audit")
        step_coverage_audit(passage_yaml, args.capture_dir)
        if args.step == "audit":
            banner("5. Capture quality audit")
            step_quality_audit(passage_yaml, args.capture_dir)
            return 0

    if args.step in ("quality",):
        banner("5. Capture quality audit")
        return 0 if step_quality_audit(passage_yaml, args.capture_dir) in (0, 1) else 1

    if args.step in ("all", "gate", "deep"):
        banner("5. Capture quality audit")
        step_quality_audit(passage_yaml, args.capture_dir)

        banner("6. Combined gate decision")
        gate_rc = step_gate(passage_yaml, args.force_deep, args.force_reason)
        if args.step == "gate":
            return 0 if gate_rc == 0 else gate_rc
        if gate_rc != 0:
            print("\n[STOPPED] Gate 기준을 통과하지 못해 deep research를 실행하지 않습니다.")
            print("누락 자료 또는 약한 자료군을 보강한 뒤 다시 실행하십시오.")
            return 0 if gate_rc == 1 else 1

    if args.step in ("all", "deep"):
        banner("7. Deep research")
        return step_deep(passage_yaml, args)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
