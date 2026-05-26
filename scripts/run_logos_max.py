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


def ensure_integration_summary(passage_yaml: Path) -> bool:
    """05-logos-integration-summary.md가 있고 실제로 채워져 있는지 확인한다.

    없으면 템플릿을 자동 생성하고 False를 반환한다.
    파일이 있더라도 템플릿 상태(미작성)이면 경고 후 False를 반환한다.
    실제로 채워진 경우에만 True를 반환하여 deep research로 진행한다.
    """
    summary_path = passage_yaml.parent / "05-logos-integration-summary.md"

    if not summary_path.exists():
        _generate_integration_summary_template(passage_yaml, summary_path)
        print("\n[PAUSED] Logos Integration Summary 템플릿을 생성했습니다.")
        print(f"  파일: {summary_path}")
        print("  Logos 연구에서 얻은 통찰을 직접 작성한 후 재실행하십시오.")
        print("  (AI 결과가 아닌 목사님의 실제 Logos 탐구 내용을 기록하십시오)")
        return False

    content = summary_path.read_text(encoding="utf-8", errors="replace")
    if "<!-- 여기에 작성" in content or content.strip() == "":
        print("\n[PAUSED] Logos Integration Summary가 아직 채워지지 않았습니다.")
        print(f"  파일: {summary_path}")
        print("  <!-- 여기에 작성 --> 플레이스홀더를 실제 내용으로 교체하십시오.")
        return False

    return True


def _generate_integration_summary_template(passage_yaml: Path, output_path: Path) -> None:
    """Logos Integration Summary 작성 템플릿을 생성한다."""
    data = load_yaml_simple(passage_yaml)
    book_korean = data.get("book_korean", "")
    passage = data.get("passage", "")
    context = data.get("context_range", "")
    genre = data.get("genre", "")

    lines = [
        f"# Logos Integration Summary — {book_korean} {passage}",
        "",
        "> **이 문서는 AI가 작성하는 것이 아닙니다.**",
        "> Logos에서 직접 연구한 내용을 목사님이 직접 정리하는 공간입니다.",
        "> Deep research로 넘어가기 전 마지막 분별 단계입니다.",
        "",
        f"- 본문: {book_korean} {context}",
        f"- 장르: `{genre}`",
        f"- 작성일: <!-- 여기에 작성: 오늘 날짜 -->",
        "",
        "---",
        "",
        "## 1. 본문에서 직접 발견한 것",
        "",
        "<!-- 여기에 작성:",
        "Logos Passage Guide, Interlinear, 구조 분석에서 눈에 들어온 것들",
        "원어 단어, 반복 표현, 문법적 특이점, 구조적 흐름 등 -->",
        "",
        "---",
        "",
        "## 2. 주석이 확인해 준 핵심 해석",
        "",
        "<!-- 여기에 작성:",
        "사용한 주석 이름과 핵심 견해를 간략히 기록",
        "서로 다른 견해가 있다면 그 차이도 기록",
        "설교에 실제로 쓸 해석이 무엇인지 판단 -->",
        "",
        "---",
        "",
        "## 3. 아직 불확실한 해석 포인트",
        "",
        "<!-- 여기에 작성:",
        "아직 결론 내리지 못한 해석 질문",
        "주석 간 이견 중 어느 쪽을 택할지 모르는 것 -->",
        "",
        "---",
        "",
        "## 4. 구속사·정경적 연결",
        "",
        "<!-- 여기에 작성:",
        "이 본문이 성경 전체 흐름에서 어디에 위치하는가",
        "그리스도와의 연결 논리 (억지 알레고리 아닌 본문 자체의 논리)",
        "구약 배경 또는 신약 성취가 있다면 기록 -->",
        "",
        "---",
        "",
        "## 5. 설교 방향의 씨앗",
        "",
        "<!-- 여기에 작성:",
        "복음 프레임: 본문이 드러내는 인간의 문제는? 하나님이 그리스도 안에서 무엇을 하시는가?",
        "적용 방향: 복음의 은혜에서 나오는 순종은?",
        "Big Idea 초안 한 문장 -->",
        "",
        "---",
        "",
        "## 6. Deep Research에 요청할 것",
        "",
        "<!-- 여기에 작성:",
        "AI 심층 분석에서 특별히 확인하고 싶은 신학적 질문",
        "반론이 필요한 해석",
        "더 깊이 파야 할 원어 또는 주석 포인트 -->",
        "",
        "---",
        "",
        "> 이 파일을 채운 후 재실행하십시오:",
        "> ```powershell",
        f"> python scripts/run_logos_max.py --passage {passage_yaml} --step deep",
        "> ```",
    ]
    output_path.write_text("\n".join(lines), encoding="utf-8")


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
        if gate_rc == 1:
            print("\n[PAUSED] 자료 보강 권장 — deep research를 보류합니다.")
            print("누락 자료 또는 약한 자료군을 보강한 뒤 재실행하십시오.")
            return 0
        if gate_rc != 0:
            print("\n[STOPPED] Gate 기준 미달 — deep research를 실행할 수 없습니다.")
            print("Coverage 또는 Quality Score를 기준 이상으로 높인 후 재실행하십시오.")
            return 1

    if args.step in ("all", "deep"):
        if not ensure_integration_summary(passage_yaml):
            return 0
        banner("7. Deep research")
        return step_deep(passage_yaml, args)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
