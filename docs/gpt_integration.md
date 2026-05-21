# GPT 연동

## 목적

심층 연구 프롬프트를 OpenAI GPT Responses API로 실행해 `input/research/*.md` 연구 파일을 자동 생성한다.

이 단계는 Logos 캡처를 그대로 신뢰하지 않는다. 필요한 경우 GPT 호출 전에 캡처 검증을 먼저 수행한다.

## 준비

PowerShell:

```powershell
$env:OPENAI_API_KEY = "<your-openai-api-key>"
```

선택:

```powershell
$env:OPENAI_MODEL = "gpt-5"
```

## 한 번에 실행

```powershell
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

실제 API 호출 전에 계획만 확인하려면 `--dry-run`을 붙인다.

```powershell
python .\scripts\run_deep_research_with_gpt.py `
  --passage "요한복음 13:14" `
  --outline .\input\jn-13-14-sermon-outline.md `
  --logos-capture .\tmp\logos-capture\raw\john-13-14-passage-guide-20260521.md `
  --existing-research .\input\research\jn-13-14-research.md `
  --output .\input\research\jn-13-14-research.md `
  --validate-capture `
  --capture-must-contain "요한복음 13:14" `
  --capture-must-contain "발" `
  --dry-run
```

## 이미 만든 프롬프트 사용

```powershell
python .\scripts\run_deep_research_with_gpt.py `
  --prompt .\tmp\prompts\jn-13-14-deep-research-prompt.md `
  --passage "요한복음 13:14" `
  --outline .\input\jn-13-14-sermon-outline.md `
  --output .\input\research\jn-13-14-research.md `
  --check `
  --run-all `
  --backup `
  --output-temp-then-replace `
  --force
```

## 안전 장치

- `OPENAI_API_KEY`가 없으면 실행하지 않는다.
- 출력 파일은 `--force` 없이는 교체하지 않는다.
- 기존 파일이 있을 때 `--force`만으로는 직접 덮어쓰지 않는다. `--output-temp-then-replace`가 필요하며, `--backup`을 함께 쓰면 교체 전 백업을 만든다.
- `--validate-capture`를 켜면 캡처가 너무 짧거나 필수 문자열이 없을 때 GPT 호출 전에 중단한다.
- `--capture-must-contain`은 여러 번 지정할 수 있고 모든 항목이 포함되어야 통과한다.
- `--check-model`을 켜면 GPT 호출 전 모델 접근 가능 여부를 확인한다.
- `--check`를 켜면 연구 파일의 필수 섹션과 후보 bullet 수를 검사한다.
- `--run-all`은 연구 파일 생성과 검사를 통과한 뒤 기존 산출물을 만든다.

## 캡처 최소 글자 수 기준

기본 `--capture-min-chars`는 2000자다.

검토 결과:

- 500자는 너무 낮다. Logos UI 메뉴나 일부 짧은 오류 화면도 통과할 수 있다.
- 요한복음 13:14 기존 캡처는 약 2141자로, 2000자 기준을 간신히 통과한다.
- Passage Guide나 주석 목록 연구에는 2000자 이상이 적절하다.
- 단일 성경 본문만 캡처하는 워크플로에는 2000자가 과할 수 있으므로, 그 경우 명령에서 명시적으로 낮춘다.

권장:

- 연구 길잡이, 주석, 설교 준비 자료: 2000자 이상
- 단일 본문 패널: 300-800자
- 여러 섹션이 필요한 심층 연구: 3000자 이상

## 자체 점수

- usefulness: 93/100
- simplicity: 86/100
- safety: 94/100
- editability: 92/100
- reuse potential: 93/100
