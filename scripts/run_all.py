from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


DEFAULT_INPUT = Path("input/john-3-sermon-outline.md")
DEFAULT_OUTPUT_DIR = Path("output")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="설교 개요 입력 파일로 목장 나눔지, PPT 초안, 짧은 요약을 한 번에 생성합니다."
    )
    parser.add_argument(
        "--input",
        default=str(DEFAULT_INPUT),
        help="입력 Markdown 파일 경로",
    )
    parser.add_argument(
        "--output-dir",
        default=str(DEFAULT_OUTPUT_DIR),
        help="출력 폴더 경로",
    )
    parser.add_argument(
        "--research",
        default=None,
        help="Logos 연구 파일 경로 (선택). 지정하면 세 출력물 모두에 참고 자료로 추가됩니다.",
    )
    return parser.parse_args()


def build_jobs(input_path: Path, output_dir: Path) -> list[tuple[str, Path, Path]]:
    stem = input_path.stem
    return [
        (
            "목장 나눔지",
            Path("scripts/outline_to_small_group.py"),
            output_dir / f"{stem}-small-group-guide.md",
        ),
        (
            "PPT 초안",
            Path("scripts/outline_to_ppt_draft.py"),
            output_dir / f"{stem}-ppt-draft.md",
        ),
        (
            "짧은 사역 요약",
            Path("scripts/outline_to_short_summary.py"),
            output_dir / f"{stem}-short-summary.md",
        ),
    ]


def run_job(
    label: str,
    script_path: Path,
    input_path: Path,
    output_path: Path,
    research_path: Path | None = None,
) -> None:
    command = [
        sys.executable,
        str(script_path),
        "--input", str(input_path),
        "--output", str(output_path),
    ]
    if research_path is not None:
        command += ["--research", str(research_path)]
    subprocess.run(command, check=True)
    print(f"{label} 생성: {output_path}")


def main() -> int:
    args = parse_args()
    input_path = Path(args.input)
    output_dir = Path(args.output_dir)
    research_path = Path(args.research) if args.research else None

    if not input_path.exists():
        raise FileNotFoundError(f"입력 파일을 찾을 수 없습니다: {input_path}")
    if research_path is not None and not research_path.exists():
        raise FileNotFoundError(f"연구 파일을 찾을 수 없습니다: {research_path}")

    output_dir.mkdir(parents=True, exist_ok=True)

    for label, script_path, output_path in build_jobs(input_path=input_path, output_dir=output_dir):
        run_job(
            label=label,
            script_path=script_path,
            input_path=input_path,
            output_path=output_path,
            research_path=research_path,
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
