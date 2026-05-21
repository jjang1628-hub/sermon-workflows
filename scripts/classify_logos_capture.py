"""
classify_logos_capture.py — Logos 캡처 분류기

캡처 파일을 분석하여 어떤 Logos 도구에서 캡처한 것인지 자동으로 분류하고
validated 또는 rejected 폴더로 이동한다.

사용법:
    python scripts/classify_logos_capture.py --capture tmp/logos-capture/raw/john-13-14-passage-guide-20260521.md
    python scripts/classify_logos_capture.py --scan-dir tmp/logos-capture/raw
"""

from __future__ import annotations

import argparse
import shutil
from datetime import datetime
from pathlib import Path


# 도구 분류 키워드
TOOL_CLASSIFIERS = {
    "passage_guide": {
        "keywords": ["passage guide", "passage_guide", "본문 안내", "개요", "context",
                     "literary context", "cross references section"],
        "label": "Passage Guide",
    },
    "exegetical_guide": {
        "keywords": ["exegetical guide", "exegetical_guide", "원어 분석", "greek",
                     "hebrew", "헬라어", "히브리어", "morphology", "syntax"],
        "label": "Exegetical Guide",
    },
    "bible_word_study": {
        "keywords": ["bible word study", "word study", "단어 연구", "lexicon",
                     "semantic domain", "usage"],
        "label": "Bible Word Study",
    },
    "factbook": {
        "keywords": ["factbook", "fact book", "배경", "background", "culture",
                     "archaeology", "geography", "인물", "지명"],
        "label": "Factbook",
    },
    "theology_guide": {
        "keywords": ["theology guide", "theology_guide", "신학", "theology",
                     "doctrine", "dogmatics"],
        "label": "Theology Guide",
    },
    "cross_reference": {
        "keywords": ["cross-reference", "cross reference", "교차 참조", "parallel",
                     "see also"],
        "label": "Cross-Reference",
    },
    "commentary": {
        "keywords": ["commentary", "주석", "nicnt", "becnt", "pillar", "wbc",
                     "nicot", "nac", "barclay", "carson", "keener", "moo"],
        "label": "Commentary",
    },
    "bible_text": {
        "keywords": ["개역개정", "새번역", "esv", "nasb", "niv", "성경", "bible text"],
        "label": "Bible Text",
    },
}


def classify_capture(file_path: Path) -> str:
    """캡처 파일을 분류하여 도구 레이블 반환."""
    content = file_path.read_text(encoding="utf-8", errors="replace").lower()

    scores = {}
    for tool_id, classifier in TOOL_CLASSIFIERS.items():
        score = sum(1 for kw in classifier["keywords"] if kw.lower() in content)
        if score > 0:
            scores[tool_id] = score

    if not scores:
        return "unknown"

    best = max(scores, key=scores.get)
    return best


def get_quality_score(file_path: Path) -> int:
    """캡처 파일의 품질 점수 (0–100)."""
    content = file_path.read_text(encoding="utf-8", errors="replace")
    score = 0

    # 크기 기반 (최대 40점)
    size = len(content)
    if size >= 3000:
        score += 40
    elif size >= 1000:
        score += 25
    elif size >= 500:
        score += 10

    # 구조 기반 (최대 30점)
    import re
    if re.search(r"^#{1,3}\s+", content, re.MULTILINE):
        score += 15
    if re.search(r"^\s*[-*]\s+", content, re.MULTILINE):
        score += 15

    # 내용 기반 (최대 30점)
    has_korean = bool(re.search(r"[가-힣]", content))
    has_original = bool(re.search(r"[α-ωΑ-Ωא-ת]", content))
    if has_korean:
        score += 15
    if has_original:
        score += 15

    return min(score, 100)


def process_file(file_path: Path, output_base: Path, dry_run: bool = False) -> dict:
    """단일 파일을 분류하고 이동."""
    tool = classify_capture(file_path)
    quality = get_quality_score(file_path)

    classifier = TOOL_CLASSIFIERS.get(tool)
    tool_label = classifier["label"] if classifier else "Unknown"

    # 품질 기준: 30점 이상 → validated, 미만 → rejected
    is_valid = quality >= 30
    dest_dir = output_base / ("validated" if is_valid else "rejected")

    result = {
        "file": file_path.name,
        "tool": tool_label,
        "quality": quality,
        "valid": is_valid,
        "dest": dest_dir / file_path.name,
    }

    if not dry_run:
        dest_dir.mkdir(parents=True, exist_ok=True)
        # 이미 있으면 덮어쓰기 (분류 재실행 허용)
        shutil.copy2(file_path, result["dest"])

    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="Logos 캡처 분류기")
    parser.add_argument("--capture", default=None, help="단일 캡처 파일")
    parser.add_argument("--scan-dir", default=None, help="캡처 디렉토리 전체 스캔")
    parser.add_argument("--output-base", default="tmp/logos-capture",
                        help="validated/rejected 기본 경로")
    parser.add_argument("--dry-run", action="store_true", help="실제 이동 없이 분류만")
    args = parser.parse_args()

    output_base = Path(args.output_base)

    if args.capture:
        files = [Path(args.capture)]
    elif args.scan_dir:
        scan_dir = Path(args.scan_dir)
        if not scan_dir.exists():
            print(f"NG 디렉토리 없음: {scan_dir}")
            return 1
        files = list(scan_dir.glob("*.md"))
        print(f"OK 발견된 파일: {len(files)}개")
    else:
        print("NG --capture 또는 --scan-dir 필요")
        return 1

    if not files:
        print("OK 처리할 파일 없음")
        return 0

    results = []
    for f in files:
        if not f.exists():
            print(f"NG 파일 없음: {f}")
            continue
        r = process_file(f, output_base, args.dry_run)
        results.append(r)
        status = "OK" if r["valid"] else "NG"
        dry = " (dry-run)" if args.dry_run else ""
        print(f"{status} {r['file']} → {r['tool']} / 품질:{r['quality']}{dry}")

    valid_count = sum(1 for r in results if r["valid"])
    print(f"\n{'='*50}")
    print(f"OK {valid_count}/{len(results)} 파일 validated")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
