from __future__ import annotations

import argparse
from datetime import datetime
from pathlib import Path

from classify_logos_capture import build_report


SECTION_TITLES = {
    "bible-text": "본문 자료",
    "passage-guide": "Passage Guide",
    "exegetical-guide": "Exegetical Guide",
    "word-study": "Word Study",
    "commentary": "Commentary",
    "search": "Search",
    "notes": "Notes",
    "unknown": "Unknown",
}


SECTION_ORDER = [
    "bible-text",
    "passage-guide",
    "exegetical-guide",
    "word-study",
    "commentary",
    "search",
    "notes",
    "unknown",
]


def collect_files(input_dir: Path) -> list[Path]:
    if not input_dir.exists():
        raise FileNotFoundError(f"입력 폴더를 찾을 수 없습니다: {input_dir}")
    return sorted(path for path in input_dir.rglob("*.md") if path.is_file())


def render_file_entry(path: Path, passage: str | None, max_chars_per_file: int) -> tuple[str, str]:
    text = path.read_text(encoding="utf-8").strip()
    report = build_report(path, passage=passage, duplicate_dir=path.parent)
    capture_type = report["type"]
    excerpt = text
    truncated = False
    if max_chars_per_file > 0 and len(excerpt) > max_chars_per_file:
        excerpt = excerpt[:max_chars_per_file].rstrip()
        truncated = True

    body = [
        f"### {path.name}",
        "",
        f"- 출처 파일: `{path}`",
        f"- 추정 유형: `{capture_type}`",
        f"- 글자 수: {len(text)}",
        f"- 본문 포함: {'예' if report['contains_passage'] else '아니오/미확인'}",
        "",
        "```text",
        excerpt,
        "```",
    ]
    if truncated:
        body.extend(
            [
                "",
                f"> 길이 제한으로 이 파일은 앞부분 {max_chars_per_file}자만 포함했습니다. 원문은 출처 파일에서 확인하세요.",
            ]
        )
    body.append("")
    return capture_type, "\n".join(body)


def build_pack(files: list[Path], passage: str | None, max_chars_per_file: int) -> str:
    grouped: dict[str, list[str]] = {key: [] for key in SECTION_ORDER}
    for path in files:
        capture_type, entry = render_file_entry(path, passage=passage, max_chars_per_file=max_chars_per_file)
        grouped.setdefault(capture_type, []).append(entry)

    lines = [
        "# 로컬 설교 연구팩",
        "",
        f"- 생성 시각: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"- 본문: {passage or '미지정'}",
        f"- 포함 파일 수: {len(files)}",
        "- 주의: 이 파일은 목사님 검토용 1차 연구팩입니다. 긴 원문 인용은 출처 파일 단위로만 보존합니다.",
        "",
    ]

    for capture_type in SECTION_ORDER:
        lines.extend([f"## {SECTION_TITLES[capture_type]}", ""])
        if grouped.get(capture_type):
            lines.extend(grouped[capture_type])
        else:
            lines.extend(["- 해당 자료 없음", ""])
    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="검증된 Logos export들을 하나의 로컬 연구팩 Markdown으로 병합합니다.")
    parser.add_argument("--input-dir", required=True, help="validated Logos Markdown 폴더")
    parser.add_argument("--output", required=True, help="생성할 연구팩 Markdown 경로")
    parser.add_argument("--passage", default=None, help="본문 포함 여부 확인용 본문")
    parser.add_argument("--max-chars-per-file", type=int, default=12000, help="파일당 포함할 최대 글자 수. 0이면 제한 없음")
    parser.add_argument("--force", action="store_true", help="기존 출력 파일 덮어쓰기")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    input_dir = Path(args.input_dir)
    output_path = Path(args.output)
    if output_path.exists() and not args.force:
        raise FileExistsError(f"출력 파일이 이미 있습니다. 덮어쓰려면 --force를 사용하세요: {output_path}")

    files = collect_files(input_dir)
    if not files:
        raise FileNotFoundError(f"연구팩에 넣을 Markdown 파일이 없습니다: {input_dir}")

    pack = build_pack(files=files, passage=args.passage, max_chars_per_file=args.max_chars_per_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(pack, encoding="utf-8")
    print(f"로컬 연구팩 생성: {output_path}")
    print(f"- 포함 파일 수: {len(files)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
