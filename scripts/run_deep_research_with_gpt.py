from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime
from pathlib import Path

from build_deep_research_prompt import (
    DEFAULT_TEMPLATE,
    read_optional,
    render_prompt,
    slugify,
)
from validate_logos_capture import DEFAULT_BAD_PHRASES, split_terms, validate_capture


DEFAULT_MODEL = os.environ.get("OPENAI_MODEL", "gpt-5")
RESPONSES_URL = "https://api.openai.com/v1/responses"
MODELS_URL = "https://api.openai.com/v1/models"


GPT_INSTRUCTIONS = """\
당신은 설교 본문 심층 연구 보조자입니다.
한국어로 답하세요.
출력은 사용자가 제공한 Markdown 형식을 지키세요.
최종 신학 판단을 대신하지 말고, 확실한 내용과 검토가 필요한 내용을 구분하세요.
"""


def load_prompt(args: argparse.Namespace) -> str:
    if args.prompt:
        prompt_path = Path(args.prompt)
        if not prompt_path.exists():
            raise FileNotFoundError(f"프롬프트 파일을 찾을 수 없습니다: {prompt_path}")
        return prompt_path.read_text(encoding="utf-8")

    if not args.passage:
        raise ValueError("--prompt를 쓰지 않을 때는 --passage가 필요합니다.")

    template_path = Path(args.template)
    if not template_path.exists():
        raise FileNotFoundError(f"프롬프트 템플릿을 찾을 수 없습니다: {template_path}")

    return render_prompt(
        template=template_path.read_text(encoding="utf-8"),
        passage=args.passage,
        outline_text=read_optional(Path(args.outline) if args.outline else None, "설교 개요"),
        logos_capture_text=read_optional(Path(args.logos_capture) if args.logos_capture else None, "Logos 캡처"),
        existing_research_text=read_optional(
            Path(args.existing_research) if args.existing_research else None,
            "기존 연구",
        ),
    )


def validate_capture_if_requested(args: argparse.Namespace) -> None:
    if not args.validate_capture:
        return
    if not args.logos_capture:
        raise ValueError("--validate-capture를 사용하려면 --logos-capture가 필요합니다.")

    capture_path = Path(args.logos_capture)
    if not capture_path.exists():
        raise FileNotFoundError(f"Logos 캡처 파일을 찾을 수 없습니다: {capture_path}")

    failures = validate_capture(
        text=capture_path.read_text(encoding="utf-8"),
        min_chars=args.capture_min_chars,
        must_contain=split_terms(args.capture_must_contain),
        must_not_contain=split_terms(args.capture_must_not_contain) or DEFAULT_BAD_PHRASES,
    )
    if failures:
        lines = "\n".join(f"- {failure}" for failure in failures)
        raise RuntimeError(f"Logos 캡처 검증 실패\n{lines}")

    print(f"Logos 캡처 검증 통과: {capture_path}")


def response_text(data: dict) -> str:
    direct = data.get("output_text")
    if isinstance(direct, str) and direct.strip():
        return direct

    chunks: list[str] = []
    for item in data.get("output", []):
        if not isinstance(item, dict):
            continue
        for content in item.get("content", []):
            if not isinstance(content, dict):
                continue
            text = content.get("text")
            if isinstance(text, str):
                chunks.append(text)
    return "\n".join(chunks).strip()


def require_api_key() -> str:
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise EnvironmentError(
            "OPENAI_API_KEY 환경변수가 설정되지 않았습니다.\n"
            "PowerShell에서 OPENAI_API_KEY 환경변수를 설정하세요."
        )
    return api_key


def request_json(url: str, payload: dict | None = None) -> dict:
    api_key = require_api_key()
    body = None if payload is None else json.dumps(payload, ensure_ascii=False).encode("utf-8")
    method = "GET" if payload is None else "POST"
    request = urllib.request.Request(
        url,
        data=body,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method=method,
    )

    try:
        with urllib.request.urlopen(request, timeout=300) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"OpenAI API 호출 실패: HTTP {exc.code}\n{detail}") from exc


def check_model_access(model: str) -> None:
    encoded_model = urllib.parse.quote(model, safe="")
    data = request_json(f"{MODELS_URL}/{encoded_model}")
    print(f"OpenAI 모델 접근 확인 완료: {data.get('id', model)}")


def call_openai(prompt: str, model: str, max_output_tokens: int) -> tuple[str, dict]:
    payload = {
        "model": model,
        "instructions": GPT_INSTRUCTIONS,
        "input": prompt,
        "max_output_tokens": max_output_tokens,
    }
    data = request_json(RESPONSES_URL, payload=payload)
    text = response_text(data)
    if not text:
        raise RuntimeError("OpenAI 응답에서 텍스트를 추출하지 못했습니다.")
    return text, data


def backup_path_for(output_path: Path) -> Path:
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    return output_path.with_name(f"{output_path.name}.{stamp}.bak")


def save_text(
    text: str,
    output_path: Path,
    force: bool,
    backup: bool,
    output_temp_then_replace: bool,
    check_before_replace: bool = False,
) -> None:
    exists = output_path.exists()
    if exists and not force:
        raise FileExistsError(
            f"출력 파일이 이미 있습니다. 기존 파일을 보존하려면 다른 --output을 쓰고, "
            f"교체가 필요하면 --force와 함께 --backup 또는 --output-temp-then-replace를 명시하세요: {output_path}"
        )
    if exists and force and not output_temp_then_replace:
        raise FileExistsError(
            f"기존 파일 직접 덮어쓰기는 막혀 있습니다. --output-temp-then-replace를 함께 사용하세요: {output_path}"
        )

    output_path.parent.mkdir(parents=True, exist_ok=True)

    if exists and backup:
        backup_path = backup_path_for(output_path)
        shutil.copy2(output_path, backup_path)
        print(f"기존 연구 파일 백업 생성: {backup_path}")

    if output_temp_then_replace:
        temp_path = output_path.with_name(f".{output_path.name}.tmp")
        temp_path.write_text(text, encoding="utf-8")
        if check_before_replace:
            run_checked([sys.executable, "scripts/check_research_file.py", "--input", str(temp_path), "--min-bullets", "7"])
        try:
            temp_path.replace(output_path)
        except PermissionError:
            if exists and not backup:
                raise
            if output_path.exists():
                output_path.unlink()
            temp_path.replace(output_path)
    else:
        output_path.write_text(text, encoding="utf-8")

    print(f"GPT 연구 파일 저장: {output_path}")


def run_checked(command: list[str]) -> None:
    print("실행:", " ".join(command))
    subprocess.run(command, check=True)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="OpenAI GPT Responses API로 심층 설교 연구 파일을 생성합니다.")
    parser.add_argument("--prompt", default=None, help="이미 생성된 심층 연구 프롬프트 파일")
    parser.add_argument("--passage", default=None, help="연구할 본문. 예: 요한복음 13:14")
    parser.add_argument("--outline", default=None, help="설교 개요 Markdown 파일")
    parser.add_argument("--logos-capture", default=None, help="Logos 캡처 Markdown 파일")
    parser.add_argument("--existing-research", default=None, help="기존 연구 Markdown 파일")
    parser.add_argument("--template", default=str(DEFAULT_TEMPLATE), help="프롬프트 템플릿 경로")
    parser.add_argument("--output", default=None, help="연구 파일 저장 경로")
    parser.add_argument("--model", default=DEFAULT_MODEL, help="OpenAI 모델명. 기본: OPENAI_MODEL 또는 gpt-5")
    parser.add_argument("--max-output-tokens", type=int, default=12000, help="최대 출력 토큰")
    parser.add_argument("--force", action="store_true", help="기존 출력 파일 교체 허용. 기존 파일이 있으면 --output-temp-then-replace도 필요합니다.")
    parser.add_argument("--backup", action="store_true", help="기존 출력 파일을 타임스탬프 .bak 파일로 백업한 뒤 교체")
    parser.add_argument("--output-temp-then-replace", action="store_true", help="임시 파일에 먼저 쓰고 최종 경로로 교체")
    parser.add_argument("--dry-run", action="store_true", help="API를 호출하지 않고 입력 검증과 실행 계획만 출력")
    parser.add_argument("--check-model", action="store_true", help="GPT 호출 전 모델 접근 가능 여부 확인")
    parser.add_argument("--validate-capture", action="store_true", help="GPT 호출 전 Logos 캡처 품질 검사")
    parser.add_argument("--capture-min-chars", type=int, default=2000, help="캡처 최소 글자 수")
    parser.add_argument(
        "--capture-must-contain",
        action="append",
        default=[],
        help="캡처에 반드시 포함되어야 할 문자열. 여러 번 지정할 수 있고, | 로 나눈 값도 모두 필수입니다.",
    )
    parser.add_argument(
        "--capture-must-not-contain",
        action="append",
        default=[],
        help="캡처에 포함되면 실패할 문자열. 여러 개는 | 로 구분합니다.",
    )
    parser.add_argument("--check", action="store_true", help="저장 후 check_research_file.py 실행")
    parser.add_argument("--run-all", action="store_true", help="저장 후 run_all.py 실행")
    parser.add_argument("--output-dir", default="output", help="run_all.py 출력 폴더")
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    validate_capture_if_requested(args)
    prompt = load_prompt(args)
    passage_for_slug = args.passage or "passage"
    output_path = Path(args.output) if args.output else Path("input/research") / f"{slugify(passage_for_slug)}-research.md"

    if args.dry_run:
        print("Dry run: GPT API 호출 생략")
        print(f"- model: {args.model}")
        print(f"- prompt chars: {len(prompt)}")
        print(f"- output: {output_path}")
        print(f"- force: {args.force}")
        print(f"- backup: {args.backup}")
        print(f"- output_temp_then_replace: {args.output_temp_then_replace}")
        print(f"- capture_min_chars: {args.capture_min_chars}")
        print(f"- check: {args.check}")
        print(f"- run_all: {args.run_all}")
        return 0

    if args.check_model:
        check_model_access(args.model)

    print(f"OpenAI GPT 연구 실행: model={args.model}")
    text, _raw = call_openai(
        prompt=prompt,
        model=args.model,
        max_output_tokens=args.max_output_tokens,
    )
    save_text(
        text=text,
        output_path=output_path,
        force=args.force,
        backup=args.backup,
        output_temp_then_replace=args.output_temp_then_replace,
        check_before_replace=args.check,
    )

    if args.check and not args.output_temp_then_replace:
        run_checked([sys.executable, "scripts/check_research_file.py", "--input", str(output_path), "--min-bullets", "7"])

    if args.run_all:
        if not args.outline:
            raise ValueError("--run-all을 사용하려면 --outline이 필요합니다.")
        run_checked(
            [
                sys.executable,
                "scripts/run_all.py",
                "--input",
                args.outline,
                "--research",
                str(output_path),
                "--output-dir",
                args.output_dir,
            ]
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
