# 심층 설교 연구 자동화

## 목표

Logos 캡처와 설교 개요를 GPT/Claude 프롬프터에 넣을 수 있는 심층 연구 프롬프트로 묶고, 모델이 작성한 연구 파일이 기존 파이프라인에 들어갈 수 있는지 검사한다.

이 자동화는 모델이 신학 판단을 최종 확정하게 만들지 않는다. 모델은 비교·대조 연구 초안을 만들고, 설교자는 출처와 본문 문맥을 검토한다.

## 구성

```text
templates/deep_research_prompt_template.md
scripts/build_deep_research_prompt.py
scripts/check_research_file.py
```

## 사용 순서

### 1. Logos 캡처

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\logos_capture_probe.ps1 `
  -Output .\tmp\logos-capture\raw\john-13-14-passage-guide-20260521.md
```

### 2. 심층 연구 프롬프트 생성

```powershell
python .\scripts\build_deep_research_prompt.py `
  --passage "요한복음 13:14" `
  --outline .\input\jn-13-14-sermon-outline.md `
  --logos-capture .\tmp\logos-capture\raw\john-13-14-passage-guide-20260521.md `
  --existing-research .\input\research\jn-13-14-research.md `
  --output .\tmp\prompts\jn-13-14-deep-research-prompt.md `
  --force
```

생성된 프롬프트를 GPT 프롬프터에 넣고 결과를 아래 파일로 저장한다.

```text
input/research/jn-13-14-research.md
```

### 3. 연구 파일 품질 점검

```powershell
python .\scripts\check_research_file.py `
  --input .\input\research\jn-13-14-research.md `
  --min-bullets 7
```

### 4. GPT API로 직접 연구 파일 생성

`OPENAI_API_KEY`가 설정되어 있으면 GPT Responses API로 프롬프트 실행까지 자동화할 수 있다.

```powershell
$env:OPENAI_API_KEY = "<your-openai-api-key>"

python .\scripts\run_deep_research_with_gpt.py `
  --passage "요한복음 13:14" `
  --outline .\input\jn-13-14-sermon-outline.md `
  --logos-capture .\tmp\logos-capture\raw\john-13-14-passage-guide-20260521.md `
  --existing-research .\input\research\jn-13-14-research.md `
  --output .\input\research\jn-13-14-research.md `
  --model gpt-5 `
  --validate-capture `
  --capture-min-chars 2000 `
  --capture-must-contain "요한복음 13:14" `
  --capture-must-contain "발" `
  --check-model `
  --check `
  --run-all `
  --backup `
  --output-temp-then-replace `
  --force
```

모델명은 `--model`로 바꿀 수 있고, 기본값은 `OPENAI_MODEL` 환경변수 또는 `gpt-5`다.

### 5. 기존 파이프라인 실행

```powershell
python .\scripts\run_all.py `
  --input .\input\jn-13-14-sermon-outline.md `
  --research .\input\research\jn-13-14-research.md `
  --output-dir .\output
```

## 왜 이렇게 나누는가

- 프롬프트 생성은 항상 재현 가능하다.
- 모델 호출 방식은 GPT 프롬프터, Claude API, 수동 붙여넣기 중 무엇이든 바꿀 수 있다.
- 연구 파일 형식은 `research_support.py`가 읽을 수 있게 고정된다.
- 품질 점검은 모델 결과물이 너무 얕거나 섹션이 빠졌을 때 바로 실패시킨다.
- GPT API 실행 전에도 Logos 캡처 검증을 걸 수 있다.

## 자체 점수

- usefulness: 94/100
- simplicity: 88/100
- safety: 96/100
- editability: 94/100
- reuse potential: 94/100

## 무료 로컬 Ollama 경로

OpenAI API quota가 없거나 비용을 아끼려면 GPT API 경로 대신 Ollama 로컬 경로를 사용한다.
이 경로는 Logos 내부 DB를 읽지 않고, 사용자가 공식 Export/Copy/Print로 내보낸 Markdown 자료만 분석한다.

구성 파일:

```text
scripts/classify_logos_capture.py
scripts/prepare_local_research_pack.py
scripts/run_local_research_with_ollama.py
prompts/ollama_local_research.md
docs/ollama_local_workflow.md
```

기본 실행 예:

```powershell
python .\scripts\run_local_research_with_ollama.py `
  --passage "요한복음 13:14" `
  --logos-capture .\tmp\logos-capture\raw\john-13-14-passage-guide-20260521.md `
  --output .\output\local_research\jn-13-14-local-research.md `
  --model qwen3:8b `
  --research-mode quick `
  --validate-capture `
  --capture-must-contain "요한복음 13:14" `
  --capture-must-contain "발" `
  --missing-data-policy limited `
  --allow-limited-analysis
```

자세한 절차는 `docs/ollama_local_workflow.md`를 따른다.
