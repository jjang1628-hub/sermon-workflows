"""
run_logos_max_research.py — Logos-Max 마스터 오케스트레이터

7단계 자동화 흐름을 실행하는 마스터 스크립트.

1단계: Logos 연구 레시피 추천
2단계: Logos 캡처 검증 게이트
3단계: 연구 팩 준비
4단계: Ollama 1차 분석 (옵션)
5단계: Claude 심층 연구
6단계: Evidence Ledger + Claim Audit + Counter-Reading
7단계: 출력 계약 검증

사용법:
    python scripts/run_logos_max_research.py --passage "요한복음 13:14"
    python scripts/run_logos_max_research.py --passage "요한복음 13:14" --mode deep
    python scripts/run_logos_max_research.py --passage "요한복음 13:14" --mode quick --skip-deep
    python scripts/run_logos_max_research.py --passage "요한복음 13:14" --capture tmp/logos-capture/raw/john-13-14-*.md

환경:
    ANTHROPIC_API_KEY — Claude API 사용 시 필요
    Ollama 실행 중 — 로컬 1차 분석 사용 시 필요
"""

from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path

# Windows cp949 콘솔에서 한글/특수문자 출력 깨짐 방지 — UTF-8로 강제 설정
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")


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


def run_step(label: str, cmd: list[str], optional: bool = False) -> tuple[bool, str]:
    """단일 단계를 실행하고 결과를 반환."""
    print(f"\n{'─'*50}")
    print(f"▶ {label}")
    print(f"{'─'*50}")
    print(f"   명령: {' '.join(cmd)}")

    # PYTHONUTF8=1: 서브프로세스가 Korean/Unicode 출력 시 cp949 대신 UTF-8 사용
    sub_env = dict(os.environ, PYTHONUTF8="1")
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            env=sub_env,
        )
        # 출력 표시
        if result.stdout:
            for line in result.stdout.strip().split("\n"):
                print(f"   {line}")
        if result.stderr:
            for line in result.stderr.strip().split("\n"):
                print(f"   [ERR] {line}")

        success = result.returncode == 0
        if success:
            print(f"   ✅ 완료")
        else:
            if optional:
                print(f"   ⚠️ 실패 (선택적 단계, 계속 진행)")
            else:
                print(f"   ❌ 실패 (exit code {result.returncode})")
        return success, result.stdout + result.stderr
    except FileNotFoundError as e:
        msg = f"명령을 찾을 수 없음: {e}"
        print(f"   ❌ {msg}")
        return False, msg


def find_capture_file(capture_dir: Path, slug: str) -> Path | None:
    """슬러그와 일치하는 캡처 파일을 찾는다."""
    prefix = slug.split("-")[0]
    for pattern in [f"*{slug}*.md", f"*{prefix}*.md"]:
        files = list(capture_dir.glob(pattern))
        if files:
            # 가장 최근 파일
            return max(files, key=lambda f: f.stat().st_mtime)
    return None


def main() -> int:
    parser = argparse.ArgumentParser(description="Logos-Max 마스터 오케스트레이터")
    parser.add_argument("--passage", required=True)
    parser.add_argument("--mode", choices=["quick", "standard", "deep", "expert"],
                        default="standard")
    parser.add_argument("--capture", default=None, help="Logos 캡처 파일 경로")
    parser.add_argument("--capture-dir", default="tmp/logos-capture/raw")
    parser.add_argument("--model", default="claude-opus-4-5", help="Claude 모델")
    parser.add_argument("--ollama-model", default="qwen3:1.7b", help="Ollama 모델")
    parser.add_argument("--skip-ollama", action="store_true", help="Ollama 1차 분석 건너뛰기")
    parser.add_argument("--skip-deep", action="store_true", help="Claude 심층 연구 건너뛰기")
    parser.add_argument("--skip-audit", action="store_true", help="감사 단계 건너뛰기")
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    slug = slugify(args.passage)
    py = sys.executable
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    print(f"\n{'='*60}")
    print(f"LOGOS-MAX 본문중심 연구 자동화")
    print(f"{'='*60}")
    print(f"본문: {args.passage}")
    print(f"슬러그: {slug}")
    print(f"모드: {args.mode.upper()}")
    print(f"시작: {timestamp}")
    print(f"{'='*60}")

    force_flag = ["--force"] if args.force else []
    steps_completed = []
    steps_failed = []

    # ──────────────────────────────────────────────────────────
    # 1단계: Logos 연구 레시피 추천
    # ──────────────────────────────────────────────────────────
    ok, _ = run_step(
        "1단계: Logos 연구 레시피 추천",
        [py, "scripts/recommend_logos_research_recipe.py",
         "--passage", args.passage,
         "--mode", args.mode] + force_flag,
    )
    if ok:
        steps_completed.append("레시피 추천")
    else:
        steps_failed.append("레시피 추천")

    # ──────────────────────────────────────────────────────────
    # 2단계: Logos 캡처 검증 게이트
    # ──────────────────────────────────────────────────────────
    capture_path = None
    if args.capture:
        capture_path = Path(args.capture)
    else:
        capture_path = find_capture_file(Path(args.capture_dir), slug)

    capture_valid = False
    if capture_path and capture_path.exists():
        ok, _ = run_step(
            "2단계: Logos 캡처 검증 게이트",
            [py, "scripts/validate_logos_capture.py",
             "--capture", str(capture_path),
             "--passage", args.passage,
             "--policy", "limited"] + force_flag,
        )
        capture_valid = ok
        if ok:
            steps_completed.append("캡처 검증")
        else:
            print("   ⚠️ 캡처 검증 실패 — 기본 자료로 계속 진행")
            steps_failed.append("캡처 검증")
    else:
        print(f"\n{'─'*50}")
        print("⚠️ 2단계: Logos 캡처 파일 없음 — 본문 정보만으로 진행")
        print(f"   캡처 디렉토리: {args.capture_dir}")

    # ──────────────────────────────────────────────────────────
    # 3단계: 연구 팩 준비
    # ──────────────────────────────────────────────────────────
    research_pack_path = Path("output/research_packs") / f"{slug}-research-pack.md"
    capture_arg = ["--capture-dir", args.capture_dir]
    if capture_path and capture_path.exists():
        capture_arg = ["--capture-dir", str(capture_path.parent)]

    ok, _ = run_step(
        "3단계: 연구 팩 준비",
        [py, "scripts/prepare_research_pack.py",
         "--passage", args.passage,
         "--mode", args.mode] + capture_arg + force_flag,
    )
    if ok:
        steps_completed.append("연구 팩")
    else:
        steps_failed.append("연구 팩")

    # ──────────────────────────────────────────────────────────
    # 4단계: Ollama 1차 분석 (선택)
    # ──────────────────────────────────────────────────────────
    if not args.skip_ollama and args.mode in ("standard", "deep", "expert"):
        capture_flags = []
        if capture_path and capture_path.exists():
            capture_flags = ["--logos-capture", str(capture_path)]

        ok, _ = run_step(
            "4단계: Ollama 1차 분석",
            [py, "scripts/run_local_research_with_ollama.py",
             "--passage", args.passage,
             "--model", args.ollama_model,
             "--research-mode", "quick"] + capture_flags + force_flag,
            optional=True,
        )
        # 0바이트 결과 감지 및 경고
        ollama_out = Path("output/local_research") / f"{slug}-local-research.md"
        if ok and ollama_out.exists() and ollama_out.stat().st_size == 0:
            print(f"   ⚠️ Ollama 출력 0바이트 — 모델이 응답을 생성하지 못했습니다.")
            print(f"      qwen3 think 모드 충돌 또는 RAM 부족일 수 있습니다.")
            ok = False
        if ok:
            steps_completed.append("Ollama 1차")
        else:
            steps_failed.append("Ollama 1차 (선택적)")
    else:
        print(f"\n{'─'*50}")
        print("⏭ 4단계: Ollama 1차 분석 건너뜀")

    # Ollama Quality Gate 결과 읽기 (Claude 단계에 전달)
    quality_gate_path = Path("output/local_research") / f"{slug}-quality-gate.md"
    ollama_critique_flags: list[str] = []
    ollama_verdict_code = ""
    if quality_gate_path.exists():
        ollama_critique_flags = ["--ollama-critique", str(quality_gate_path)]
        # Quality Gate 판정 표시
        qg_content = quality_gate_path.read_text(encoding="utf-8", errors="replace")
        verdict_match = re.search(r"최종 판정:\s*(.+)", qg_content)
        vc_match = re.search(r"verdict_code:\s*(\S+)", qg_content)
        if verdict_match:
            print(f"\n   🔍 Ollama 품질 판정: {verdict_match.group(1).strip()}")
        if vc_match:
            ollama_verdict_code = vc_match.group(1).strip()
            print(f"   📋 verdict_code: {ollama_verdict_code}")

    # direct_use_forbidden 시 --skip-deep 경고
    if ollama_verdict_code == "direct_use_forbidden" and args.skip_deep:
        print(f"\n{'!'*60}")
        print(f"🚨 경고: Ollama 결과 직접 사용 금지 상태에서 --skip-deep 지정됨!")
        print(f"   환각 주석 또는 심각한 신학 오류가 감지된 초안입니다.")
        print(f"   Claude 심층 분석 없이 이 자료를 사용하지 마십시오.")
        print(f"   권장: --skip-deep 제거 후 Claude 심층 분석을 실행하세요.")
        print(f"{'!'*60}")

    # ──────────────────────────────────────────────────────────
    # 5단계: Claude 심층 연구
    # ──────────────────────────────────────────────────────────
    deep_research_path = Path("output/deep_research") / f"{slug}-deep-research.md"

    if not args.skip_deep:
        api_key = os.environ.get("ANTHROPIC_API_KEY", "")
        if not api_key:
            print(f"\n{'─'*50}")
            print("⚠️ 5단계: ANTHROPIC_API_KEY 없음 — Claude 심층 연구 건너뜀")
            print("   $env:ANTHROPIC_API_KEY = 'sk-ant-...' 설정 후 재실행")
            steps_failed.append("Claude 심층 (API 키 없음)")
        else:
            pack_flags = []
            if research_pack_path.exists():
                pack_flags = ["--research-pack", str(research_pack_path)]
            elif capture_path and capture_path.exists():
                pack_flags = ["--logos-capture", str(capture_path)]

            ok, _ = run_step(
                "5단계: Claude 심층 연구 (20-Pass)",
                [py, "scripts/run_deep_research_with_claude.py",
                 "--passage", args.passage,
                 "--mode", args.mode,
                 "--model", args.model]
                + pack_flags
                + ollama_critique_flags   # Ollama 실패 목록 전달
                + force_flag,
            )
            if ok:
                steps_completed.append("Claude 심층")
            else:
                steps_failed.append("Claude 심층")
    else:
        print(f"\n{'─'*50}")
        print("⏭ 5단계: Claude 심층 연구 건너뜀 (--skip-deep)")

    # ──────────────────────────────────────────────────────────
    # 6단계: Evidence Ledger + Claim Audit + Counter-Reading
    # ──────────────────────────────────────────────────────────
    if not args.skip_audit:
        research_flags = []
        if deep_research_path.exists():
            research_flags = ["--research", str(deep_research_path)]

        # 6a: Evidence Ledger
        ok, _ = run_step(
            "6a단계: Evidence Ledger 생성",
            [py, "scripts/build_evidence_ledger.py",
             "--passage", args.passage] + research_flags + force_flag,
            optional=True,
        )
        if ok:
            steps_completed.append("Evidence Ledger")
        else:
            steps_failed.append("Evidence Ledger")

        ledger_path = Path("output/evidence_ledgers") / f"{slug}-evidence-ledger.md"
        ledger_flags = []
        if ledger_path.exists():
            ledger_flags = ["--ledger", str(ledger_path)]

        # 6b: Claim Audit
        ok, _ = run_step(
            "6b단계: Claim Audit (12문항)",
            [py, "scripts/audit_research_claims.py",
             "--passage", args.passage] + ledger_flags + force_flag,
            optional=True,
        )
        if ok:
            steps_completed.append("Claim Audit")
        else:
            steps_failed.append("Claim Audit")

        # 6c: Counter-Reading
        ok, _ = run_step(
            "6c단계: Counter-Reading (8관점)",
            [py, "scripts/run_counter_reading.py",
             "--passage", args.passage] + research_flags + force_flag,
            optional=True,
        )
        if ok:
            steps_completed.append("Counter-Reading")
        else:
            steps_failed.append("Counter-Reading")
    else:
        print(f"\n{'─'*50}")
        print("⏭ 6단계: 감사 단계 건너뜀 (--skip-audit)")

    # ──────────────────────────────────────────────────────────
    # 7단계: 출력 계약 검증
    # ──────────────────────────────────────────────────────────
    ok, _ = run_step(
        "7단계: 출력 계약 검증",
        [py, "scripts/validate_output_contract.py",
         "--passage", args.passage,
         "--mode", args.mode],
        optional=True,
    )
    if ok:
        steps_completed.append("출력 계약")
    else:
        steps_failed.append("출력 계약")

    # ──────────────────────────────────────────────────────────
    # 최종 보고
    # ──────────────────────────────────────────────────────────
    end_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"\n{'='*60}")
    print(f"LOGOS-MAX 실행 완료")
    print(f"{'='*60}")
    print(f"완료: {end_time}")
    print(f"")
    print(f"✅ 완료된 단계 ({len(steps_completed)}개):")
    for s in steps_completed:
        print(f"   ✅ {s}")

    if steps_failed:
        print(f"")
        print(f"⚠️ 실패/건너뜀 ({len(steps_failed)}개):")
        for s in steps_failed:
            print(f"   ⚠️ {s}")

    print(f"")
    print(f"생성된 파일 확인:")
    for dir_name in ["output/research_packs", "output/deep_research",
                     "output/evidence_ledgers", "output/claim_audits",
                     "output/local_research"]:
        dir_path = Path(dir_name)
        if dir_path.exists():
            files = [f for f in dir_path.glob(f"*{slug}*") if f.is_file()]
            for f in files:
                print(f"   📄 {f}")

    # direct_use_forbidden + Claude 심층 없이 종료 시 최종 경고
    claude_deep_ran = "Claude 심층" in steps_completed
    if ollama_verdict_code == "direct_use_forbidden" and not claude_deep_ran:
        print(f"")
        print(f"{'!'*60}")
        print(f"🚨 최종 경고: Ollama 초안 직접 사용 금지")
        print(f"   - verdict_code: direct_use_forbidden")
        print(f"   - Claude 심층 분석이 실행되지 않았습니다.")
        print(f"   - 환각 주석 또는 신학 오류가 포함된 자료입니다.")
        print(f"   - 반드시 Claude 심층 분석 후 사용하십시오.")
        print(f"{'!'*60}")

    print(f"{'='*60}")
    print(f"⚠️ 이 자료는 연구 보조 자료입니다. 최종 설교는 목사님이 직접 작성하세요.")

    return 0 if not steps_failed or all("선택적" in s or "건너뜀" in s or "API" in s
                                         for s in steps_failed) else 1


if __name__ == "__main__":
    raise SystemExit(main())
