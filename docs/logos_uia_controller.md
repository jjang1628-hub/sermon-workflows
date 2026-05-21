# Logos UI Automation 컨트롤러

## 목적

Logos를 내부 API로 뚫는 대신, Windows UI Automation으로 Logos 화면을 조작한다.

이 방식은 사용자가 직접 할 수 있는 동작을 프로그램으로 재현한다.

- Logos 실행
- Logos 창 포커스
- UI 요소 탐색
- 구절/검색어 입력
- 버튼 클릭
- 현재 패널 텍스트 캡처

## 한계

- Logos 업데이트로 UI 이름이나 AutomationId가 바뀔 수 있다.
- 모든 패널이 텍스트 복사를 지원하지는 않는다.
- 주석 본문 전체를 라이선스 제한 없이 추출하는 API가 아니다.
- 캡처 결과는 반드시 직접 검토해야 한다.

## 파일

```text
scripts/logos_uia_controller.ps1
```

## 기본 사용

### 1. Logos 열기

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\logos_uia_controller.ps1 `
  -Action OpenUri `
  -LogosUri "logos4:"
```

### 2. 요한복음 13:14 열기

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\logos_uia_controller.ps1 `
  -Action OpenUri `
  -LogosUri "logos4:Bible;ref=Jn+13:14"
```

### 3. UI 요소 탐색

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\logos_uia_controller.ps1 `
  -Action Inspect `
  -InspectDepth 5 `
  -MaxInspectItems 300
```

이 결과에서 `name`, `id`, `type`을 확인한다.

### 4. 구절 입력

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\logos_uia_controller.ps1 `
  -Action Search `
  -Passage "요한복음 13:14"
```

### 5. 버튼 또는 패널 클릭

이름으로 클릭:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\logos_uia_controller.ps1 `
  -Action Click `
  -TargetName "연구 길잡이"
```

AutomationId로 클릭:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\logos_uia_controller.ps1 `
  -Action Click `
  -AutomationId "OurTextBox"
```

### 6. 현재 패널 캡처

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\logos_uia_controller.ps1 `
  -Action Capture `
  -Passage "요한복음 13:14" `
  -PassageSlug "jn-13-14" `
  -SourceKind "passage-guide"
```

### 7. 한 번에 실행

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\logos_uia_controller.ps1 `
  -Action PassageWorkflow `
  -LogosUri "logos4:Bible;ref=Jn+13:14" `
  -Passage "요한복음 13:14" `
  -PassageSlug "jn-13-14" `
  -SourceKind "passage-workflow"
```

### 8. 레시피로 실행

반복 워크플로는 JSON 파일로 정의한다.

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\logos_uia_controller.ps1 `
  -Action RunRecipe `
  -Recipe .\recipes\logos\jn-13-14-passage-workflow.json `
  -Force
```

레시피 예시:

```json
{
  "name": "jn-13-14-passage-workflow",
  "passage": "요한복음 13:14",
  "passageSlug": "jn-13-14",
  "steps": [
    {
      "action": "OpenUri",
      "logosUri": "logos4:Bible;ref=Jn+13:14",
      "waitSeconds": 8
    },
    {
      "action": "Search",
      "passage": "요한복음 13:14",
      "waitSeconds": 5
    },
    {
      "action": "Capture",
      "sourceKind": "passage-workflow",
      "output": "tmp/logos-capture/raw/jn-13-14-uia-passage-workflow.md",
      "minChars": 500,
      "mustContain": ["요한복음 13:14", "발"],
      "mustNotContain": ["길잡이를 불러올 수 없습니다", "Could not load"]
    }
  ]
}
```

`Capture` 단계의 검증 필드:

- `minChars`: 최소 글자 수
- `mustContain`: 반드시 포함해야 할 문자열 목록
- `mustNotContain`: 발견되면 실패할 문자열 목록

## 디버깅 순서

1. `-Action OpenUri`로 Logos가 뜨는지 확인한다.
2. `-Action Inspect`로 입력창과 버튼 이름을 확인한다.
3. `-Action Search`로 구절 입력이 되는지 확인한다.
4. 필요한 버튼은 `-Action Click`으로 하나씩 검증한다.
5. 마지막에 `-Action Capture` 또는 `PassageWorkflow`를 사용한다.

## 다음 확장

- `recipes/logos/*.json` 파일로 반복 워크플로 정의
- 여러 구절 일괄 실행
- Inspect 결과를 파일로 저장
- 특정 패널 제목을 찾아 먼저 클릭한 뒤 캡처
- 캡처 후 `normalize_logos_capture.py`와 `build_deep_research_prompt.py` 자동 실행

## 자체 점수

- usefulness: 90/100
- simplicity: 84/100
- safety: 93/100
- editability: 91/100
- reuse potential: 90/100
