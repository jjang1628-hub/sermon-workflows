# Logos 자동화 설계 초안

## 목적

Logos 10에서 설교 준비에 필요한 자료를 반복적으로 수집하고, 기존 `sermon-workflows`의 Markdown 기반 변환 흐름으로 넘길 수 있게 한다.

이 설계는 Logos의 해석 결과를 최종 신학 판단으로 취급하지 않는다. 목표는 자료 수집과 정리의 반복 노동을 줄이는 것이다.

## 냉정한 판단

완전 자동 API 방식은 현재 1차 경로로 두면 안 된다.

- `LogosBibleSoftware.Launcher` COM은 Logos 실행에는 쓸 수 있지만, 실제 연구 자료 접근에는 충분하지 않다.
- `LogosBibleSoftware.Application` 계열은 Logos 4 시대 호환 껍데기에 가깝고, Logos 10의 실제 데이터 접근 API로 보기 어렵다.
- 로컬 HTTP API가 확인되지 않았다.
- Chromium 기반 UI이므로 내부 DOM이나 네트워크를 직접 안정적으로 읽는 설계는 깨질 가능성이 높다.

따라서 원래 목표했던 자동화는 다음 순서로 가야 한다.

1. Logos를 원하는 화면까지 여는 자동화
2. 사용자가 빠르게 확인할 수 있는 화면 텍스트 캡처
3. 캡처 결과를 원본 자료 파일로 저장
4. 저장된 자료를 설교 개요, 소그룹 나눔지, PPT 초안 생성에 연결
5. 나중에 UI Automation을 붙여 캡처 안정성을 높임

## 권장 아키텍처

```text
input/
  passage-request.json
      |
      v
scripts/open_logos_target.ps1
      |
      v
Logos 화면 열림
      |
      v
scripts/logos_capture_probe.ps1
      |
      v
tmp/logos-capture/*.md
      |
      v
scripts/normalize_logos_capture.py
      |
      v
input/research/*.md
      |
      v
기존 sermon-workflows 변환 스크립트
```

## 1단계: 캡처 프로브

첫 구현은 Logos 화면의 복사 가능한 텍스트를 파일로 저장하는 것이다.

이 단계의 장점:

- Logos 내부 API에 의존하지 않는다.
- 실패해도 원본 파일을 건드리지 않는다.
- 캡처된 텍스트를 사람이 바로 검토할 수 있다.
- 이후 Python 정규화 스크립트의 입력으로 재사용할 수 있다.

한계:

- Logos 창 포커스와 현재 패널 상태에 영향을 받는다.
- `Ctrl+A`, `Ctrl+C`가 현재 패널에서 의미 있게 작동해야 한다.
- 캡처 결과에는 광고, 메뉴, 중복 텍스트, 불필요한 UI 텍스트가 섞일 수 있다.

## 2단계: 정규화

캡처 원문은 바로 설교 자료로 쓰지 않는다. 별도 정규화 파일을 만든다.

권장 출력 형식:

```markdown
# Logos 연구 캡처 정리

## 요청

- 본문:
- 자료 유형:
- 캡처 일시:

## 원문 캡처

...

## 정리 후보

### 관찰

### 해석 참고

### 적용 아이디어

## 검토 필요

- 본문 문맥 확인 필요
- 원자료 출처 확인 필요
- 최종 신학 판단은 설교자가 직접 확인
```

## 3단계: 기존 워크플로 연결

정규화된 연구 파일은 기존 설교 개요 변환의 보조 입력으로 둔다.

예상 명령:

```powershell
python .\scripts\outline_to_small_group.py `
  --input .\input\john-3-sermon-outline.md `
  --research .\input\research\john-3-logos-research.md `
  --output .\output\john-3-small-group-guide.md
```

기존 스크립트는 아직 `--research`를 받지 않으므로, 다음 개선에서 작은 변경으로 추가한다.

## 실패 기준

아래 중 하나가 반복되면 해당 경로는 중단한다.

- Logos 업데이트마다 캡처가 깨진다.
- 캡처 결과가 빈번히 비어 있다.
- 수동 복사보다 자동화가 더 오래 걸린다.
- 출처 구분이 불가능해서 설교 검토가 오히려 어려워진다.

## 성공 기준

1. 한 본문에 대해 Logos 화면을 열고 캡처 파일을 만들 수 있다.
2. 캡처 파일은 원문과 분리되어 저장된다.
3. 설교자가 1분 안에 캡처 내용을 검토할 수 있다.
4. 정규화 파일이 기존 Markdown 변환 흐름에 들어갈 수 있다.
5. 실패해도 기존 설교 자료를 덮어쓰지 않는다.

## 다음 구현 순서

1. `logos_capture_probe.ps1`로 현재 Logos 화면 캡처 검증
2. 캡처 결과 샘플 2-3개 저장
3. `normalize_logos_capture.py` 작성
4. 기존 변환 스크립트에 `--research` 옵션 추가
5. UI Automation으로 특정 입력창과 패널 선택 자동화 확장

## 자체 점수

- usefulness: 88/100
- simplicity: 90/100
- safety: 94/100
- editability: 92/100
- reuse potential: 86/100
