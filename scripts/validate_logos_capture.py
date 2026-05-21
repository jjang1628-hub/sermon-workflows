"""
validate_logos_capture.py — Logos 캡처 검증 게이트

Logos 캡처 파일의 완전성을 검사하고 proceed/limited/need_more/stop 결정을 내린다.

사용법:
    python scripts/validate_logos_capture.py --capture tmp/logos-capture/raw/john-13-14-passage-guide-20260521.md
    python scripts/validate_logos_capture.py --capture <파일> --passage "요한복음 13:14"
    python scripts/validate_logos_capture.py --capture <파일> --policy error
"""

from __future__ import annotations

import argparse
import re
import shutil
from datetime import datetime
from pathlib import Path


VALIDATION_CHECKS = [
    {"id": "V-01", "name": "파일 존재", "required": True, "check": "file_exists"},
    {"id": "V-02", "name": "최소 크기 (500자)", "required": True, "check": "min_size", "threshold": 500},
    {"id": "V-03", "name": "성경 본문 포함", "required": True, "check": "has_keywords",
     "keywords": ["절", "장", "본문", "성경", "개역", "한글"]},
    {"id": "V-04", "name": "주석 자료 포함", "required": False, "check": "has_keywords",
     "keywords": ["주석", "commentary", "Carson", "Keener", "Moo", "Morris",
                  "박대영", "NICNT", "BECNT", "Pillar"]},
    {"id": "V-05", "name": "원어 분석 포함", "required": False, "check": "has_keywords",
     "keywords": ["헬라어", "히브리어", "Greek", "Hebrew", "원어", "BDAG", "lexicon"]},
    {"id": "V-06", "name": "Logos 도구 흔적", "required": False, "check": "has_keywords",
     "keywords": ["Passage Guide", "Exegetical Guide", "Bible Word Study",
                  "Factbook", "Cross-Reference"]},
    {"id": "V-07", "name": "구조화된 섹션", "required": False, "check": "has_sections",
     "pattern": r"^#{1,3}\s+\w"},
]


def run_checks(capture_path: Path) -> list[dict]:
    content = ""
    if capture_path.exists():
        content = capture_path.read_text(encoding="utf-8", errors="replace")
    content_lower = content.lower()

    results = []
    for check in VALIDATION_CHECKS:
        cid = check["id"]
        name = check["name"]
        required = check["required"]
        check_type = check["check"]
        passed = False
        detail = ""

        if check_type == "file_exists":
            passed = capture_path.exists()
            detail = "파일 존재" if passed else "파일 없음"
        elif check_type == "min_size":
            size = len(content)
            threshold = check.get("threshold", 500)
            passed = size >= threshold
            detail = f"{size}자 (기준: {threshold}자)"
        elif check_type == "has_keywords":
            keywords = [kw.lower() for kw in check.get("keywords", [])]
            found = [kw for kw in keywords if kw in content_lower]
            passed = len(found) > 0
            detail = f"발견: {found[:3]}" if found else "발견 없음"
        elif check_type == "has_sections":
            pattern = check.get("pattern", "")
            passed = bool(re.search(pattern, content, re.MULTILINE))
            detail = "섹션 구조 감지됨" if passed else "섹션 구조 없음"

        results.append({"id": cid, "name": name, "required": required,
                        "passed": passed, "detail": detail})
    return results


def decide_policy(results: list[dict]) -> tuple[str, str]:
    required_failed = [r for r in results if r["required"] and not r["passed"]]
    optional_passed = [r for r in results if not r["required"] and r["passed"]]
    optional_total = [r for r in results if not r["required"]]

    if required_failed:
        return "stop", f"필수 항목 실패: {[r['name'] for r in required_failed]}"
    if len(optional_passed) >= len(optional_total):
        return "proceed", "모든 검증 통과"
    if len(optional_total) > 0 and len(optional_passed) >= len(optional_total) // 2:
        return "limited", f"선택 항목 {len(optional_passed)}/{len(optional_total)} 통과"
    return "need_more", f"선택 항목 부족: {len(optional_passed)}/{len(optional_total)} 통과"


def build_report(capture_path: Path, passage: str, results: list[dict],
                 decision: str, reason: str) -> str:
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    emoji = {"proceed": "✅", "limited": "⚠️", "need_more": "⛔", "stop": "🛑"}.get(decision, "❓")

    lines = [
        f"# 캡처 검증 보고서",
        f"",
        f"- **본문**: {passage or '(미지정)'}",
        f"- **파일**: {capture_path}",
        f"- **검증 일시**: {timestamp}",
        f"- **최종 결정**: {emoji} **{decision.upper()}** — {reason}",
        f"",
        f"## 항목별 검증 결과",
        f"",
        f"| ID | 항목 | 필수 | 결과 | 세부 |",
        f"|----|------|------|------|------|",
    ]
    for r in results:
        icon = "✅" if r["passed"] else ("❌" if r["required"] else "⚠️")
        req = "필수" if r["required"] else "선택"
        lines.append(f"| {r['id']} | {r['name']} | {req} | {icon} | {r['detail']} |")

    lines += ["", "---", "",
              "⚠️ 이 자료는 연구 보조 자료입니다. 최종 설교는 목사님이 직접 작성하세요."]
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Logos 캡처 검증 게이트")
    parser.add_argument("--capture", required=True)
    parser.add_argument("--passage", default="")
    parser.add_argument("--output", default=None)
    parser.add_argument("--policy", choices=["error", "limited", "skip"], default="limited")
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    capture_path = Path(args.capture)
    results = run_checks(capture_path)
    decision, reason = decide_policy(results)

    print(f"\n{'='*50}")
    for r in results:
        icon = "OK" if r["passed"] else ("NG" if r["required"] else "--")
        print(f"{icon} [{r['id']}] {r['name']}: {r['detail']}")
    print(f"{'='*50}")

    decision_labels = {
        "proceed": "OK 진행", "limited": "OK 제한적", "need_more": "NG 추가필요", "stop": "NG 중단",
    }
    print(f"{decision_labels[decision]} — {reason}")

    # 보고서 저장
    if args.output:
        output_path = Path(args.output)
    else:
        stem = capture_path.stem
        output_path = Path("output/research_packs") / f"{stem}-capture-validation.md"

    output_path.parent.mkdir(parents=True, exist_ok=True)
    report = build_report(capture_path, args.passage, results, decision, reason)

    if output_path.exists() and args.force:
        shutil.copy2(output_path, output_path.with_suffix(".bak"))

    temp = output_path.with_suffix(".tmp")
    temp.write_text(report, encoding="utf-8")
    if output_path.exists():
        output_path.unlink()
    temp.rename(output_path)
    print(f"OK 보고서: {output_path}")

    exit_codes = {"proceed": 0, "limited": 0,
                  "need_more": 1 if args.policy == "error" else 0, "stop": 1}
    return exit_codes.get(decision, 1)


if __name__ == "__main__":
    raise SystemExit(main())
