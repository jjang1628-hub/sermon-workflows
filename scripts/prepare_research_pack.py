"""
prepare_research_pack.py — 연구 팩 준비기

Logos 캡처 파일들을 모아 11섹션 연구 팩을 생성한다.

사용법:
    python scripts/prepare_research_pack.py --passage "요한복음 13:14"
    python scripts/prepare_research_pack.py --passage "요한복음 13:14" --capture-dir tmp/logos-capture/raw
    python scripts/prepare_research_pack.py --passage "요한복음 13:14" --mode deep --force
"""

from __future__ import annotations

import argparse
import re
import shutil
from datetime import datetime
from pathlib import Path


RESEARCH_PACK_SECTIONS = [
    ("S01", "성경 원문", "캡처된 성경 원문 (한국어 + 원어)"),
    ("S02", "본문 문맥", "전후 장·절 맥락"),
    ("S03", "Passage Guide", "Logos Passage Guide 캡처"),
    ("S04", "Exegetical Guide", "원어 분석 (Logos Exegetical Guide)"),
    ("S05", "원어 단어 연구", "Bible Word Study 캡처"),
    ("S06", "주석 자료", "주석 핵심 섹션 (최대 3종)"),
    ("S07", "교차 참조", "Cross-Reference 캡처"),
    ("S08", "Factbook", "배경 인물·지명·문화 (Factbook)"),
    ("S09", "신학 주제", "Theology Guide 캡처"),
    ("S10", "연구 노트", "사용자 추가 노트"),
    ("S11", "누락 데이터 보고", "캡처되지 않은 자료 목록"),
]


def slugify(passage: str) -> str:
    table = {
        "창세기": "ge", "출애굽기": "ex", "레위기": "le", "민수기": "nu",
        "신명기": "dt", "여호수아": "jos", "사사기": "jdg", "룻기": "ru",
        "사무엘상": "1sa", "사무엘하": "2sa", "열왕기상": "1ki", "열왕기하": "2ki",
        "역대상": "1ch", "역대하": "2ch", "에스라": "ezr", "느헤미야": "ne",
        "에스더": "est", "욥기": "job", "시편": "ps", "잠언": "pr",
        "전도서": "ec", "아가": "ss", "이사야": "is", "예레미야": "je",
        "예레미야애가": "la", "에스겔": "eze", "다니엘": "da", "호세아": "ho",
        "요엘": "joe", "아모스": "am", "오바댜": "ob", "요나": "jon",
        "미가": "mic", "나훔": "na", "하박국": "hab", "스바냐": "zep",
        "학개": "hag", "스가랴": "zec", "말라기": "mal",
        "마태복음": "mt", "마가복음": "mk", "누가복음": "lk", "요한복음": "jn",
        "사도행전": "ac", "로마서": "ro", "고린도전서": "1co", "고린도후서": "2co",
        "갈라디아서": "ga", "에베소서": "eph", "빌립보서": "php", "골로새서": "col",
        "데살로니가전서": "1th", "데살로니가후서": "2th", "디모데전서": "1ti",
        "디모데후서": "2ti", "디도서": "tit", "빌레몬서": "phm", "히브리서": "heb",
        "야고보서": "jas", "베드로전서": "1pe", "베드로후서": "2pe",
        "요한일서": "1jn", "요한이서": "2jn", "요한삼서": "3jn",
        "유다서": "jude", "요한계시록": "re",
    }
    slug = passage
    for korean, abbr in table.items():
        if korean in passage:
            slug = passage.replace(korean, abbr)
            break
    slug = re.sub(r"[:\s]+", "-", slug)
    slug = re.sub(r"[^a-zA-Z0-9\-]", "", slug)
    return slug.strip("-").lower() or "passage"


def find_capture_files(capture_dir: Path, passage: str) -> dict[str, Path]:
    """캡처 디렉토리에서 관련 파일을 자동으로 찾는다."""
    slug = slugify(passage)
    # 슬러그의 앞 4자 (예: jn-1 → jn, ro-8 → ro)
    prefix = slug.split("-")[0]

    # 영어 책 이름 대체 접두사 (예: jn → john, lk → luke 등)
    _prefix_aliases = {
        "jn": ["john", "jn"],
        "mt": ["matt", "matthew", "mt"],
        "mk": ["mark", "mk"],
        "lk": ["luke", "lk"],
        "ac": ["acts", "ac"],
        "ro": ["rom", "ro"],
        "ge": ["gen", "ge"],
        "ex": ["exo", "ex"],
        "ps": ["psa", "ps"],
        "is": ["isa", "is"],
    }
    prefix_variants = _prefix_aliases.get(prefix, [prefix])

    found = {}
    section_keywords = {
        "S03": ["passage", "guide", "passage-guide"],
        "S04": ["exegetical", "exeg"],
        "S05": ["word-study", "word_study", "wordst", "text-study", "bible-text"],
        "S06": ["commentary", "comment", "encyclopedia", "encycl"],
        "S07": ["cross-ref", "crossref", "cross_ref"],
        "S08": ["factbook", "fact"],
        "S09": ["theology", "theol"],
    }

    if not capture_dir.exists():
        return found

    for f in sorted(capture_dir.glob("*.md")):
        fname = f.name.lower()
        # 슬러그 또는 접두사 변형이 파일명에 포함되어 있는지 확인
        slug_match = slug in fname
        prefix_match = any(pv in fname for pv in prefix_variants)
        if not slug_match and not prefix_match:
            continue
        for sec_id, keywords in section_keywords.items():
            if any(kw in fname for kw in keywords):
                if sec_id not in found:
                    found[sec_id] = f
    return found


def build_research_pack(passage: str, mode: str, capture_files: dict[str, Path],
                        extra_notes: str = "") -> str:
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    slug = slugify(passage)

    captured_sections = set(capture_files.keys())
    missing_sections = [s for s in RESEARCH_PACK_SECTIONS if s[0] not in captured_sections
                        and s[0] not in ("S01", "S10", "S11")]

    lines = [
        f"# 연구 팩 — {passage}",
        f"",
        f"- **본문**: {passage}",
        f"- **슬러그**: {slug}",
        f"- **운영 모드**: {mode.upper()}",
        f"- **생성 일시**: {timestamp}",
        f"- **캡처 파일 수**: {len(capture_files)}개",
        f"",
        f"---",
        f"",
    ]

    for sec_id, sec_name, sec_desc in RESEARCH_PACK_SECTIONS:
        lines.append(f"## {sec_id}: {sec_name}")
        lines.append(f"")
        lines.append(f"> {sec_desc}")
        lines.append(f"")

        if sec_id in capture_files:
            cap_file = capture_files[sec_id]
            content = cap_file.read_text(encoding="utf-8", errors="replace")
            # 최대 3000자만 포함
            if len(content) > 3000:
                content = content[:3000] + "\n\n[... 이하 생략 — 원본 파일 참조 ...]"
            lines.append(f"**출처**: `{cap_file}`")
            lines.append(f"")
            lines.append(content)
        elif sec_id == "S10":
            if extra_notes:
                lines.append(extra_notes)
            else:
                lines.append("(연구 중 추가 노트를 여기에 작성하세요)")
        elif sec_id == "S11":
            if missing_sections:
                lines.append("다음 자료가 캡처되지 않았습니다. Logos에서 추가 캡처를 권장합니다:")
                lines.append("")
                for ms_id, ms_name, ms_desc in RESEARCH_PACK_SECTIONS:
                    if ms_id in [s[0] for s in [(x, x, x) for x in [m[0] for m in
                                 [s for s in RESEARCH_PACK_SECTIONS if s[0] not in captured_sections
                                  and s[0] not in ("S01", "S10", "S11")]]]]:
                        pass
                for ms in missing_sections:
                    lines.append(f"- [ ] {ms[0]}: {ms[1]} — {ms[2]}")
            else:
                lines.append("✅ 모든 주요 섹션이 캡처되었습니다.")
        else:
            lines.append(f"⚠️ 캡처 없음 — Logos에서 {sec_name} 캡처 필요")

        lines.append(f"")
        lines.append(f"---")
        lines.append(f"")

    lines.append("⚠️ 이 자료는 연구 보조 자료입니다. 최종 설교는 목사님이 직접 작성하세요.")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="연구 팩 준비기")
    parser.add_argument("--passage", required=True)
    parser.add_argument("--mode", choices=["quick", "standard", "deep", "expert"], default="standard")
    parser.add_argument("--capture-dir", default="tmp/logos-capture/raw")
    parser.add_argument("--output", default=None)
    parser.add_argument("--notes", default="", help="추가 연구 노트")
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    capture_dir = Path(args.capture_dir)
    slug = slugify(args.passage)

    print(f"OK 본문: {args.passage}")
    print(f"OK 슬러그: {slug}")
    print(f"OK 캡처 디렉토리: {capture_dir}")

    # 캡처 파일 찾기
    capture_files = find_capture_files(capture_dir, args.passage)
    print(f"OK 발견된 캡처 파일: {len(capture_files)}개")
    for sec_id, path in capture_files.items():
        print(f"   {sec_id}: {path.name}")

    # 출력 경로
    if args.output:
        output_path = Path(args.output)
    else:
        output_path = Path("output/research_packs") / f"{slug}-research-pack.md"

    if output_path.exists() and not args.force:
        print(f"NG 출력 파일이 이미 있습니다. --force 사용: {output_path}")
        return 1

    output_path.parent.mkdir(parents=True, exist_ok=True)

    # 연구 팩 생성
    pack = build_research_pack(args.passage, args.mode, capture_files, args.notes)

    if output_path.exists() and args.force:
        shutil.copy2(output_path, output_path.with_suffix(".bak"))

    temp = output_path.with_suffix(".tmp")
    temp.write_text(pack, encoding="utf-8")
    if output_path.exists():
        output_path.unlink()
    temp.rename(output_path)

    print(f"OK 연구 팩 저장: {output_path}")
    print(f"   크기: {output_path.stat().st_size:,}바이트")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
