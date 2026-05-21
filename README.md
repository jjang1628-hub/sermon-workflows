# sermon-workflows

설교 개요를 반복 가능한 사역 문서로 바꾸기 위한 작은 도구 모음입니다.

현재 포함된 첫 도구:

- `scripts/outline_to_small_group.py`
  - 설교 개요 Markdown 파일을 읽어서 목장 나눔지 Markdown 초안을 생성합니다.
  - 출력 구조는 기본적으로 `관찰 -> 해석 -> 적용`을 따릅니다.
  - 원본 파일은 수정하지 않습니다.

## 프로젝트 구조

```text
sermon-workflows/
├─ README.md
├─ scripts/
│  └─ outline_to_small_group.py
├─ templates/
│  └─ small_group_guide_template.md
└─ examples/
   ├─ sample_outline.md
   └─ sample_small_group_guide.md
```

## 빠른 실행

PowerShell 예시:

```powershell
python .\scripts\outline_to_small_group.py `
  --input .\examples\sample_outline.md `
  --output .\examples\sample_small_group_guide.generated.md
```

출력 파일을 열어 바로 수정하면 됩니다.

## 입력 가정

- 입력 파일은 Markdown(`.md`)입니다.
- 다음 정보가 있으면 더 좋은 초안을 만듭니다.
  - 제목
  - 본문 또는 성구
  - 핵심 포인트 2~4개
- 완성 원고 수준의 해석 자동화가 아니라, 사람이 검토하기 쉬운 초안 생성에 집중합니다.

## 다음 확장 후보

- YAML front matter 지원
- 발표용 PPT 초안 텍스트 생성
- 공지문 패키지(KakaoTalk / 주보 / SMS) 생성
