"""MarkItDown 래퍼: 파일(PDF/DOCX/PPTX/XLSX/HTML/이미지 등) → Markdown.

사용:
  python scripts/md_convert.py <입력파일> [-o 출력.md]
  기본 출력: tmp/markitdown/<입력파일명>.md

덮어쓰기 시 기존 파일을 .bak으로 백업하고 .tmp → rename 패턴을 따른다.
"""
import argparse
import os
import shutil
import sys
from pathlib import Path

DEFAULT_OUT_DIR = Path("tmp/markitdown")


def convert(src: Path, dst: Path) -> Path:
    try:
        from markitdown import MarkItDown
    except ImportError:
        sys.exit("markitdown 미설치: pip install -r requirements.txt")

    text = MarkItDown().convert(str(src)).text_content
    dst.parent.mkdir(parents=True, exist_ok=True)
    if dst.exists():
        shutil.copy2(dst, dst.with_suffix(dst.suffix + ".bak"))
    tmp = dst.with_suffix(dst.suffix + ".tmp")
    tmp.write_text(text, encoding="utf-8")
    os.replace(tmp, dst)
    return dst


def main() -> None:
    ap = argparse.ArgumentParser(description="파일을 Markdown으로 변환 (MarkItDown)")
    ap.add_argument("input", type=Path)
    ap.add_argument("-o", "--output", type=Path)
    args = ap.parse_args()

    if not args.input.is_file():
        sys.exit(f"입력 파일 없음: {args.input}")
    dst = args.output or DEFAULT_OUT_DIR / (args.input.name + ".md")
    print(f"변환 완료: {convert(args.input, dst)}")


if __name__ == "__main__":
    main()
