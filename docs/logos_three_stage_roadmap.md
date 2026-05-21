# Logos 자동화 3단계 로드맵

## 전제

이 로드맵의 목표는 Logos를 완전히 제어하는 것이 아니다. 목표는 설교자가 Logos에서 이미 확인할 수 있는 자료를 안전하게 캡처하고, 검토 가능한 Markdown 연구 파일로 정리한 뒤, 기존 설교 워크플로에 보조 자료로 연결하는 것이다.

중요한 원칙:

- Logos 캡처 원문은 원자료로 보존한다.
- 정규화 파일은 사람이 검토하기 쉬운 중간 산출물이다.
- 기존 설교 개요 파일은 자동으로 수정하지 않는다.
- Logos 자료는 최종 해석이 아니라 참고 자료로만 들어간다.
- 자동화가 실패해도 기존 `input/`과 `output/` 결과물을 망가뜨리지 않는다.

## 전체 흐름

```text
1단계: 캡처

Logos 화면
  -> scripts/logos_capture_probe.ps1
  -> tmp/logos-capture/raw/*.md

2단계: 정규화

tmp/logos-capture/raw/*.md
  -> scripts/normalize_logos_capture.py
  -> input/research/*.md

3단계: 워크플로 연결

input/*.md
input/research/*.md
  -> scripts/outline_to_small_group.py --research ...
  -> scripts/outline_to_ppt_draft.py --research ...
  -> scripts/outline_to_short_summary.py --research ...
  -> output/*.md
```

## 1단계: 캡처

현재 구현된 파일:

- `scripts/logos_capture_probe.ps1`

역할:

- Logos 창을 앞으로 가져온다.
- 현재 포커스된 Logos 패널에 `Ctrl+A`, `Ctrl+C`를 보낸다.
- 복사된 텍스트를 Markdown 파일로 저장한다.
- 기존 클립보드는 가능한 한 복원한다.
- 빈 캡처는 실패로 처리한다.

권장 출력 위치:

```text
tmp/logos-capture/raw/
```

파일명 규칙:

```text
{passage-slug}-{source-kind}-{yyyyMMdd-HHmmss}.md
```

예시:

```text
tmp/logos-capture/raw/john-3-passage-guide-20260521-143000.md
tmp/logos-capture/raw/john-3-commentary-20260521-143500.md
tmp/logos-capture/raw/john-3-bible-text-20260521-144000.md
```

현재 스크립트는 기본 파일명을 자동 생성한다. 다음 개선에서 `-Passage`, `-SourceKind` 옵션을 추가하면 위 규칙을 자동화할 수 있다.

1단계 성공 기준:

1. Logos에서 본문 또는 자료 패널을 클릭한다.
2. 캡처 스크립트를 실행한다.
3. `tmp/logos-capture/` 아래 새 Markdown 파일이 생긴다.
4. 파일 안에 캡처 일시, 주의 문구, 캡처 내용이 들어 있다.
5. 빈 파일이 생기지 않는다.

1단계 실패 처리:

- 캡처 결과가 비어 있으면 사용자가 직접 패널을 클릭하고 다시 실행한다.
- UI 전체 텍스트가 섞이면 정규화 단계에서 제거한다.
- 같은 문제가 반복되면 해당 Logos 패널은 자동 캡처 대상에서 제외한다.

## 2단계: 정규화

추가할 파일:

- `scripts/normalize_logos_capture.py`

역할:

- 캡처 원문을 읽는다.
- 불필요한 빈 줄과 중복 줄을 줄인다.
- 설교자가 검토하기 쉬운 Markdown 구조로 재배치한다.
- 원문을 요약하거나 신학적으로 단정하지 않는다.
- 자동 추출이 애매한 부분은 `검토 필요`에 남긴다.

명령 형태:

```powershell
python .\scripts\normalize_logos_capture.py `
  --input .\tmp\logos-capture\raw\john-3-passage-guide-20260521-143000.md `
  --output .\input\research\john-3-logos-research.md `
  --passage "요한복음 3장" `
  --source-kind "passage-guide"
```

정규화 출력 형식:

```markdown
# Logos 연구 자료

## 기본 정보

- 본문: 요한복음 3장
- 자료 유형: passage-guide
- 원본 캡처 파일: tmp/logos-capture/raw/john-3-passage-guide-20260521-143000.md
- 정규화 일시: 2026-05-21 14:35:00
- 주의: 이 파일은 설교 준비 참고 자료이며 최종 해석이 아닙니다.

## 빠른 검토

- 캡처 글자 수:
- 제거한 중복 줄 수:
- 자동 분류 신뢰도: 낮음 / 보통 / 높음

## 원문에서 보이는 주요 항목

- ...

## 관찰 후보

- ...

## 해석 참고 후보

- ...

## 적용 아이디어 후보

- ...

## 검토 필요

- 출처와 문맥을 직접 확인하세요.
- 자동 분류가 틀릴 수 있습니다.
- 설교의 최종 신학 판단으로 사용하지 마세요.

## 정리된 원문

...
```

정규화 규칙:

- 원문에서 가져온 문장은 가능한 한 그대로 둔다.
- 자동 분류는 키워드 기반으로만 한다.
- 확신이 낮은 내용은 해석하지 말고 `정리된 원문`에 둔다.
- `관찰`, `해석`, `적용` 섹션은 비어 있어도 된다.
- 출처가 불명확한 문장을 강제로 주석처럼 만들지 않는다.

초기 자동 분류 기준:

```text
관찰 후보:
- 반복되는 단어
- 본문 구조
- 인물, 장소, 시간, 명령, 질문

해석 참고 후보:
- 배경
- 문맥
- 원어
- 주석
- 신학
- 교차 참조

적용 아이디어 후보:
- 적용
- 묵상
- 질문
- 기도
- 삶
- 공동체
```

2단계 성공 기준:

1. 캡처 원문 파일을 덮어쓰지 않는다.
2. `input/research/` 아래 정규화 파일이 생긴다.
3. 정규화 파일 상단에 원본 캡처 파일 경로가 남는다.
4. 설교자가 1분 안에 쓸 만한 내용과 버릴 내용을 구분할 수 있다.
5. 애매한 내용은 단정하지 않고 `검토 필요`에 남긴다.

## 3단계: 기존 워크플로 연결

수정할 파일:

- `scripts/outline_to_small_group.py`
- `scripts/outline_to_ppt_draft.py`
- `scripts/outline_to_short_summary.py`
- 선택: `scripts/run_all.py`

핵심 설계:

기존 `--input`은 설교 개요의 주 입력으로 유지한다. 새 `--research` 옵션은 선택 입력이다.

```powershell
python .\scripts\outline_to_small_group.py `
  --input .\input\john-3-sermon-outline.md `
  --research .\input\research\john-3-logos-research.md `
  --output .\output\john-3-small-group-guide.md
```

동작 원칙:

- `--research`가 없으면 기존과 똑같이 작동한다.
- `--research`가 있으면 참고 섹션을 추가로 읽는다.
- 연구 파일 내용은 질문 생성의 보조 힌트로만 쓴다.
- 연구 파일 내용이 설교 개요의 메인 아이디어를 덮어쓰지 않는다.
- 출력물에는 “Logos 참고 자료 기반 검토 필요” 메모를 남긴다.

소그룹 나눔지 연결 방식:

```text
설교 개요:
- 제목
- 본문
- 메인 아이디어
- 설교 흐름

Logos 연구 파일:
- 관찰 후보 -> 관찰 질문 보강
- 해석 참고 후보 -> 해석 질문 보강
- 적용 아이디어 후보 -> 적용 질문 보강
```

PPT 초안 연결 방식:

```text
설교 개요:
- 슬라이드의 기본 문장과 흐름을 결정

Logos 연구 파일:
- 배경 설명이 필요한 슬라이드의 보조 메모로만 사용
- 슬라이드 본문을 길게 만들지 않음
- 한 슬라이드 = 한 main sentence 원칙 유지
```

짧은 사역 요약 연결 방식:

```text
설교 개요:
- 요약의 중심 내용 결정

Logos 연구 파일:
- 안내자가 확인할 참고 메모로만 사용
- 공지문처럼 단정적인 신학 문장으로 자동 변환하지 않음
```

권장 출력 메모:

```markdown
## 검토 메모

- 이 초안은 설교 개요와 Logos 연구 정리 파일을 함께 참고했습니다.
- Logos 연구 자료는 최종 해석이 아니며 본문 문맥과 설교 흐름에 맞게 직접 검토해야 합니다.
```

3단계 성공 기준:

1. `--research` 없이 기존 명령이 계속 통과한다.
2. `--research`를 넣으면 출력물에 참고 자료가 반영된다.
3. 설교 개요의 제목, 본문, 메인 아이디어가 연구 파일 때문에 바뀌지 않는다.
4. 출력물에 검토 메모가 남는다.
5. 한 번 만든 연구 파일을 소그룹, PPT, 요약 생성에 재사용할 수 있다.

## 구현 순서

### 구현 1: 캡처 파일명 개선

`logos_capture_probe.ps1`에 선택 옵션을 추가한다.

```powershell
-Passage "john-3"
-SourceKind "passage-guide"
```

이 옵션이 있으면 출력 파일명을 더 예측 가능하게 만든다.

### 구현 2: 정규화 스크립트 작성

`normalize_logos_capture.py`를 만든다.

최소 기능:

- 입력 파일 읽기
- 출력 파일 덮어쓰기 방지
- 중복 줄 제거
- 기본 정보 섹션 생성
- 키워드 기반 후보 분류
- 정리된 원문 보존

### 구현 3: `--research` 공통 읽기 함수 추가

반복을 줄이기 위해 작게 시작한다.

후보 파일:

```text
scripts/research_support.py
```

역할:

- 연구 파일 읽기
- 필요한 섹션만 추출
- 출력 메모 생성

### 구현 4: 소그룹 나눔지부터 연결

가장 먼저 `outline_to_small_group.py`에만 `--research`를 붙인다.

이유:

- 관찰, 해석, 적용 구조가 이미 연구 파일 구조와 맞다.
- 효과를 가장 빨리 검증할 수 있다.
- PPT보다 실패 위험이 낮다.

### 구현 5: PPT와 요약 연결

소그룹 나눔지에서 효과가 확인되면 같은 방식으로 확장한다.

## 검증 시나리오

### 시나리오 A: 기존 워크플로 회귀 확인

```powershell
python .\scripts\outline_to_small_group.py `
  --input .\input\john-3-sermon-outline.md `
  --output .\output\john-3-sermon-outline-small-group-guide.md
```

기대:

- 기존처럼 출력된다.
- `--research`가 없어도 실패하지 않는다.

### 시나리오 B: 연구 파일 정규화

```powershell
python .\scripts\normalize_logos_capture.py `
  --input .\tmp\logos-capture\raw\john-3-passage-guide-20260521-143000.md `
  --output .\input\research\john-3-logos-research.md `
  --passage "요한복음 3장" `
  --source-kind "passage-guide"
```

기대:

- `input/research/john-3-logos-research.md`가 생긴다.
- 원본 캡처 경로가 파일 안에 남는다.
- 검토 필요 섹션이 포함된다.

### 시나리오 C: 연구 파일을 소그룹 나눔지에 연결

```powershell
python .\scripts\outline_to_small_group.py `
  --input .\input\john-3-sermon-outline.md `
  --research .\input\research\john-3-logos-research.md `
  --output .\output\john-3-with-research-small-group-guide.md
```

기대:

- 관찰, 해석, 적용 질문이 연구 파일의 후보를 일부 반영한다.
- 설교 개요의 중심 흐름은 유지된다.
- 출력물 하단에 검토 메모가 생긴다.

### 시나리오 D: 전체 실행

```powershell
python .\scripts\run_all.py `
  --input .\input\john-3-sermon-outline.md `
  --research .\input\research\john-3-logos-research.md `
  --output-dir .\output
```

기대:

- 소그룹 나눔지, PPT 초안, 짧은 요약이 모두 생성된다.
- 연구 파일이 모든 출력물에 같은 방식으로 추적된다.
- 기존 원본 파일은 수정되지 않는다.

## 중단 기준

아래 상황이 반복되면 자동화 범위를 줄인다.

- 정규화 결과가 원문보다 검토하기 어렵다.
- Logos 캡처가 패널마다 너무 다르게 나온다.
- 연구 자료가 설교 개요의 중심을 자주 왜곡한다.
- 출력물에서 출처와 자동 생성 여부가 불명확해진다.
- 수동 복사 후 붙여넣기보다 시간이 더 걸린다.

## 가장 작은 다음 작업

다음 구현은 `normalize_logos_capture.py` 하나다.

이유:

- 캡처는 이미 있다.
- 기존 변환 스크립트는 아직 건드리지 않아도 된다.
- 캡처 품질을 먼저 샘플로 검증할 수 있다.
- 정규화 파일 형식이 안정되어야 `--research` 연결도 안정된다.

## 자체 점수

- usefulness: 92/100
- simplicity: 87/100
- safety: 95/100
- editability: 93/100
- reuse potential: 91/100
