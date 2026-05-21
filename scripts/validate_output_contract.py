"""
validate_output_contract.py — 출력 계약 검증기

output_contracts.yaml의 기준에 따라 생성된 출력 파일들을 검증한다.

사용법:
    python scripts/validate_output_contract.py --passage "요한복음 13:14" --mode standard
    python scripts/validate_output_contract.py --passage "요한복음 13:14" --mode deep
    python scripts/validate_output_contract.py --passage "요한복음 13:14" --mode quick --strict
"""

from __future__ import annotations

import argparse
import re
from datetime import datetime
from pathlib import Path


# 모드별 필수 출력 (output_contracts.yaml 기반)
CONTRACTS = {
    "quick": [
        ("QK-01", "output/deep_research/{slug}-quick-summary.md", 500),
    ],
    "standard": [
        ("ST-01", "output/research_packs/{slug}-research-pack.md", 2000),
        ("ST-02", "output/deep_research/{slug}-deep-research.md", 5000),
        ("ST-03", "output/evidence_ledgers/{slug}-evidence-ledger.md", 1000),
        ("ST-04", "output/claim_audits/{slug}-claim-audit.md", 1000),
        ("ST-05", "output/deep_research/{slug}-counter-reading.md", 1000),
        ("ST-06", "output/final_sermon_direction/{slug}-sermon-direction.md", 2000),
    ],
    "deep": [
        ("ST-01", "output/research_packs/{slug}-research-pack.md", 2000),
        ("ST-02", "output/deep_research/{slug}-deep-research.md", 5000),
        ("ST-03", "output/evidence_ledgers/{slug}-evidence-ledger.md", 1000),
        ("ST-04", "output/claim_audits/{slug}-claim-audit.md", 1000),
        ("ST-05", "output/deep_research/{slug}-counter-reading.md", 1000),
        ("ST-06", "output/final_sermon_direction/{slug}-sermon-direction.md", 2000),
        ("DP-01", "output/research_packs/{slug}-logos-recipe.md", 500),
        ("DP-02", "output/local_research/{slug}-local-research.md", 500),
        ("DP-08", "output/final_sermon_direction/{slug}-internalization.md", 500),
        ("DP-12", "output/final_sermon_direction/{slug}-outline-draft.md", 1000),
        ("DP-13", "output/{slug}-small-group-guide.md", 500),
        ("DP-14", "output/{slug}-ppt-draft.md", 500),
        ("DP-15", "output/{slug}-short-summary.md", 200),
    ],
}
CONTRACTS["expert"] = CONTRACTS["deep"]  # Expert는 Deep과 동일 최소 요구


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


def validate_contract(passage: str, mode: str, base_dir: Path, strict: bool = False) -> list[dict]:
    slug = slugify(passage)
    contract = CONTRACTS.get(mode, CONTRACTS["standard"])
    results = []

    for item_id, path_template, min_size in contract:
        path_str = path_template.replace("{slug}", slug)
        file_path = base_dir / path_str

        exists = file_path.exists()
        size = file_path.stat().st_size if exists else 0
        size_ok = size >= min_size

        status = "OK" if (exists and size_ok) else ("소형" if exists else "없음")
        results.append({
            "id": item_id,
            "path": str(file_path.relative_to(base_dir)),
            "exists": exists,
            "size": size,
            "min_size": min_size,
            "size_ok": size_ok,
            "status": status,
        })

    return results


def build_report(passage: str, mode: str, results: list[dict]) -> str:
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    total = len(results)
    passed = sum(1 for r in results if r["exists"] and r["size_ok"])
    failed = [r for r in results if not r["exists"] or not r["size_ok"]]

    overall = "✅ 완료" if not failed else f"⚠️ {len(failed)}개 미흡"

    lines = [
        f"# 출력 계약 검증 보고서",
        f"",
        f"- **본문**: {passage}",
        f"- **모드**: {mode.upper()}",
        f"- **검증 일시**: {timestamp}",
        f"- **전체 결과**: {overall} ({passed}/{total} 통과)",
        f"",
        f"---",
        f"",
        f"## 항목별 결과",
        f"",
        f"| ID | 파일 | 크기 | 최소 | 상태 |",
        f"|----|------|------|------|------|",
    ]

    for r in results:
        icon = "✅" if (r["exists"] and r["size_ok"]) else ("⚠️" if r["exists"] else "❌")
        size_str = f"{r['size']:,}B" if r["exists"] else "없음"
        lines.append(f"| {r['id']} | {r['path']} | {size_str} | {r['min_size']}B | {icon} |")

    if failed:
        lines += [
            f"",
            f"---",
            f"",
            f"## 미흡 항목",
            f"",
        ]
        for r in failed:
            if not r["exists"]:
                lines.append(f"- ❌ **{r['id']}**: `{r['path']}` — 파일 없음")
            else:
                lines.append(f"- ⚠️ **{r['id']}**: `{r['path']}` — 크기 부족 ({r['size']}B < {r['min_size']}B)")

    lines += [
        f"",
        f"---",
        f"",
        f"⚠️ 이 자료는 연구 보조 자료입니다. 최종 설교는 목사님이 직접 작성하세요.",
    ]

    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="출력 계약 검증기")
    parser.add_argument("--passage", required=True)
    parser.add_argument("--mode", choices=["quick", "standard", "deep", "expert"], default="standard")
    parser.add_argument("--base-dir", default=".", help="프로젝트 루트 경로")
    parser.add_argument("--output", default=None)
    parser.add_argument("--strict", action="store_true", help="실패 시 exit code 1")
    args = parser.parse_args()

    base_dir = Path(args.base_dir)
    results = validate_contract(args.passage, args.mode, base_dir, args.strict)

    passed = sum(1 for r in results if r["exists"] and r["size_ok"])
    total = len(results)
    failed = [r for r in results if not r["exists"] or not r["size_ok"]]

    print(f"\n{'='*50}")
    print(f"출력 계약 검증: {args.passage} / {args.mode.upper()}")
    print(f"{'='*50}")

    for r in results:
        icon = "OK" if (r["exists"] and r["size_ok"]) else ("WA" if r["exists"] else "NG")
        size_str = f"{r['size']:,}B" if r["exists"] else "없음"
        print(f"{icon} [{r['id']}] {r['path']} ({size_str})")

    print(f"{'='*50}")
    overall_icon = "OK" if not failed else "NG"
    print(f"{overall_icon} {passed}/{total} 통과")

    # 보고서 저장
    slug = slugify(args.passage)
    if args.output:
        output_path = Path(args.output)
    else:
        output_path = Path("output/research_packs") / f"{slug}-output-contract.md"

    output_path.parent.mkdir(parents=True, exist_ok=True)
    report = build_report(args.passage, args.mode, results)
    output_path.write_text(report, encoding="utf-8")
    print(f"OK 보고서: {output_path}")

    if failed and args.strict:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
