"""
Run the Logos-Max v2.1 Logos-first workflow.

This script is a gate-first orchestrator.  It should not push the workflow into
AI deep research until:
1. Coverage audit exists and passes,
2. Capture quality audit exists and passes,
3. Logos Integration Summary is actually filled.
"""

from __future__ import annotations

import argparse
import re
import shutil
import subprocess
import sys
from pathlib import Path

from pipeline_utils import configure_utf8_stdio, load_yaml_simple, slugify_passage


configure_utf8_stdio()

SCRIPTS_DIR = Path("scripts")


def run(cmd: list[str], check: bool = True) -> int:
    print(f"\n$ {' '.join(cmd)}")
    result = subprocess.run(cmd)
    if check and result.returncode != 0:
        print(f"[ERROR] 명령 실패(exit {result.returncode}): {' '.join(cmd)}", file=sys.stderr)
    return result.returncode


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the Logos-Max v2.1 Logos-first workflow.")
    parser.add_argument("--book", default=None, help="Book name for new passage, e.g. John")
    parser.add_argument("--passage", default=None, help="Path to passage.yaml or passage ref, e.g. 13:14")
    parser.add_argument("--context", default=None, help="Context range for new passage, e.g. 13:1-17")
    parser.add_argument("--genre", default=None, help="Genre, e.g. gospel_farewell_discourse")
    parser.add_argument("--theme-hint", default="", help="Theme hint for new passage")
    parser.add_argument(
        "--step",
        choices=["setup", "recipe", "audit", "quality", "gate", "deep", "direction", "debrief", "all"],
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
    return {
        "John": "john",
        "Romans": "romans",
        "Matthew": "matthew",
        "Mark": "mark",
        "Luke": "luke",
        "Acts": "acts",
        "Genesis": "genesis",
        "Exodus": "exodus",
        "Psalms": "psalms",
    }.get(book, book.lower())


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
        print("[ERROR] passage.yaml 생성에는 --book, --passage, --context가 필요합니다.", file=sys.stderr)
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
    return run([sys.executable, str(SCRIPTS_DIR / "build_logos_recipe.py"), "--passage", str(passage_yaml)])


def step_coverage_audit(passage_yaml: Path, capture_dir: str) -> int:
    return run(
        [sys.executable, str(SCRIPTS_DIR / "audit_logos_coverage.py"), "--passage", str(passage_yaml), "--capture-dir", capture_dir],
        check=False,
    )


def step_quality_audit(passage_yaml: Path, capture_dir: str) -> int:
    return run(
        [sys.executable, str(SCRIPTS_DIR / "audit_capture_quality.py"), "--passage", str(passage_yaml), "--capture-dir", capture_dir],
        check=False,
    )


def step_gate(passage_yaml: Path, force: bool, reason: str) -> int:
    cmd = [sys.executable, str(SCRIPTS_DIR / "gate_deep_research.py"), "--passage", str(passage_yaml)]
    if force:
        cmd += ["--force", "--reason", reason]
    return run(cmd, check=False)


def step_build_context(passage_yaml: Path, force: bool = False) -> tuple[int, Path | None]:
    cmd = [sys.executable, str(SCRIPTS_DIR / "build_v21_research_context.py"), "--passage", str(passage_yaml)]
    if force:
        cmd.append("--force")
    rc = run(cmd, check=False)
    context_path = passage_yaml.parent / "06-research-context.md"
    return rc, context_path if context_path.exists() else None


def step_deep(passage_yaml: Path, args: argparse.Namespace, research_context: Path | None = None) -> int:
    data = load_yaml_simple(passage_yaml)
    passage_label = f"{data.get('book_korean', data.get('book', ''))} {data.get('passage', '')}".strip()
    cmd = [sys.executable, str(SCRIPTS_DIR / "run_logos_max_research.py"), "--passage", passage_label]
    if args.skip_ollama:
        cmd.append("--skip-ollama")
    if args.model:
        cmd += ["--model", args.model]
    capture_dir = Path(args.capture_dir)
    if capture_dir.exists():
        cmd += ["--capture-dir", str(capture_dir)]
    if research_context and research_context.exists():
        cmd += ["--research-context", str(research_context)]
    return run(cmd)


def step_direction(passage_yaml: Path, force: bool = False) -> int:
    cmd = [sys.executable, str(SCRIPTS_DIR / "generate_final_direction.py"), "--passage", str(passage_yaml)]
    if force:
        cmd.append("--force")
    return run(cmd, check=False)


def step_debrief(passage_yaml: Path, force: bool = False) -> int:
    cmd = [sys.executable, str(SCRIPTS_DIR / "generate_pulpit_debrief.py"), "--passage", str(passage_yaml)]
    if force:
        cmd.append("--force")
    return run(cmd, check=False)


def copy_deep_research_to_docs(passage_yaml: Path, passage_label: str) -> None:
    slug = slugify_passage(passage_label)
    src = Path("output/deep_research") / f"{slug}-deep-research.md"
    dst = passage_yaml.parent / "07-deep-research.md"
    if not src.exists():
        print(f"  [WARN] deep research 출력 없음: {src}")
        return
    if dst.exists():
        shutil.copy2(dst, dst.with_suffix(".bak"))
    shutil.copy2(src, dst)
    print(f"  docs/ 복사: {dst} ({dst.stat().st_size:,} bytes)")


REQUIRED_05_SECTIONS = [
    "Logos 연구에서 얻은 핵심 통찰",
    "설교에 반드시 반영할 통찰",
    "반영하지 않기로 한 자료",
    "도덕주의 위험",
    "그리스도 연결",
    "Big Idea",
    "Gate Decision",
]


def _section_body(content: str, heading: str) -> str:
    pattern = rf"##\s+.*{re.escape(heading)}.*\n(?P<body>.*?)(?=\n##\s+|\Z)"
    match = re.search(pattern, content, flags=re.DOTALL)
    return match.group("body").strip() if match else ""


def _has_substantive_body(body: str) -> bool:
    for line in body.splitlines():
        s = line.strip()
        if not s or s.startswith("<!--") or s.startswith(">"):
            continue
        if re.match(r"^\d+\.\s*$", s):
            continue
        if re.match(r"^-\s*(Coverage Score|Capture Quality Score|Gate Decision|Deep Research 진행 여부):\s*$", s):
            continue
        if len(s) >= 8:
            return True
    return False


def integration_summary_filled(summary_path: Path) -> bool:
    if not summary_path.exists():
        return False
    content = summary_path.read_text(encoding="utf-8", errors="replace")
    if "여기에 작성" in content or "<!--" in content:
        return False
    return all(_has_substantive_body(_section_body(content, section)) for section in REQUIRED_05_SECTIONS)


def generate_integration_summary_template(passage_yaml: Path, output_path: Path) -> None:
    data = load_yaml_simple(passage_yaml)
    book_korean = data.get("book_korean", data.get("book", ""))
    passage = data.get("passage", "")
    context = data.get("context_range", "")
    genre = data.get("genre", "")
    content = f"""# Logos Integration Summary - {book_korean} {passage}

> 이 문서는 AI가 대신 작성하는 최종 분석이 아닙니다.
> Logos에서 실제 확인한 자료를 목회자가 요약하고 분별한 뒤 deep research로 넘기는 검문소입니다.

- 본문: {book_korean} {context}
- 장르: `{genre}`
- 작성일: <!-- 여기에 작성: YYYY-MM-DD -->

## 1. Logos 연구에서 얻은 핵심 통찰 5개

1.
2.
3.
4.
5.

## 2. 설교에 반드시 반영할 통찰 3개

1.
2.
3.

## 3. 반영하지 않기로 한 자료와 이유

1.
2.
3.

## 4. 도덕주의 위험 경고

요 13:14는 "예수님이 섬기셨으니 우리도 섬기자"로 바로 가면 도덕주의가 됩니다.
반드시 13:1, 13:3, 13:8을 거쳐야 합니다.

## 5. 그리스도 연결의 안전한 경로

13:1 끝까지 사랑 → 13:3 주님의 정체성 → 13:4-5 낮아지심 → 13:8 씻김과 참여 → 13:14 서로 씻김.

## 6. Big Idea 후보

십자가까지 우리를 끝까지 씻기신 예수님의 사랑이, 우리를 서로의 먼지 앞에서 도망가지 않는 사람으로 빚어 간다.

## 7. Gate Decision

- Coverage Score:
- Capture Quality Score:
- Gate Decision:
- Deep Research 진행 여부:
"""
    output_path.write_text(content, encoding="utf-8")


def ensure_integration_summary(passage_yaml: Path) -> bool:
    summary_path = passage_yaml.parent / "05-logos-integration-summary.md"
    if not summary_path.exists():
        generate_integration_summary_template(passage_yaml, summary_path)
        print("\n[PAUSED] Logos Integration Summary 템플릿을 생성했습니다.")
        print(f"  파일: {summary_path}")
        print("  실제 Logos 연구 통찰을 채운 뒤 다시 실행하십시오.")
        return False
    if not integration_summary_filled(summary_path):
        print("\n[PAUSED] Logos Integration Summary가 아직 충분히 채워지지 않았습니다.")
        print(f"  파일: {summary_path}")
        print("  빈 번호, placeholder, 비어 있는 Gate Decision을 실제 내용으로 채우십시오.")
        return False
    return True


def ensure_capture_files(capture_dir: Path, force: bool) -> bool:
    has_files = capture_dir.exists() and bool(list(capture_dir.glob("*.md")) or list(capture_dir.glob("*.txt")))
    if has_files or force:
        return True
    print(f"\n[PAUSED] 캡처 파일이 없습니다: {capture_dir}")
    print("Logos 공식 UI / Copy / Export / Print로 자료를 캡처한 뒤 다시 실행하십시오.")
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

    if args.step == "quality":
        banner("5. Capture quality audit")
        return 0 if step_quality_audit(passage_yaml, args.capture_dir) in (0, 1) else 1

    if args.step in ("all", "gate", "deep"):
        banner("5. Capture quality audit")
        step_quality_audit(passage_yaml, args.capture_dir)

        banner("6. Combined gate decision")
        gate_rc = step_gate(passage_yaml, args.force_deep, args.force_reason)
        if args.step == "gate":
            return gate_rc
        if gate_rc == 1:
            print("\n[PAUSED] Gate가 보강을 요구했습니다. deep research를 보류합니다.")
            return 0
        if gate_rc != 0:
            print("\n[STOPPED] Gate 기준 미달입니다. deep research를 실행하지 않습니다.")
            return 1

    if args.step in ("all", "deep"):
        if not ensure_integration_summary(passage_yaml):
            return 0

        banner("6.5. v2.1 Research Context 생성")
        _, research_context = step_build_context(passage_yaml, force=True)
        if research_context:
            print(f"[OK] Research Context 준비됨: {research_context}")
        else:
            print("[WARN] Research Context 생성 실패. 기본 프롬프트로 진행합니다.")

        banner("7. Deep research")
        rc = step_deep(passage_yaml, args, research_context=research_context)
        passage_label = f"{data.get('book_korean', data.get('book', ''))} {data.get('passage', '')}".strip()
        copy_deep_research_to_docs(passage_yaml, passage_label)

        banner("8. Final direction 생성")
        step_direction(passage_yaml, force=True)
        return rc

    if args.step == "direction":
        banner("8. Final direction 생성")
        return step_direction(passage_yaml, force=args.force_deep)

    if args.step == "debrief":
        banner("9. 설교 후 debrief 템플릿 생성")
        return step_debrief(passage_yaml, force=args.force_deep)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
