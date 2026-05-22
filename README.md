# sermon-workflows

**Logos-first, AI-assisted, Pastor-finalized Sermon Research System**

이 프로젝트는 설교문 자동 생성기가 아닙니다.
Logos 연구를 먼저 충분히 수행하도록 강제하는 설교 연구 자동화 시스템입니다.

핵심 원칙:

1. Scripture first - 본문이 최종 기준입니다.
2. Logos research second - Logos 자료는 본문 아래 증인입니다.
3. AI synthesis third - AI는 정리, 비교, 통합, 경고를 돕습니다.
4. Pastor finalization last - 최종 설교 문장과 적용은 목회자가 확정합니다.

## Logos-Max v2.1 Workflow

v2.1은 두 점수를 분리합니다.

- **Coverage Score**: 필요한 Logos 자료군이 있는가?
- **Capture Quality Score**: 그 자료가 본문 연구와 설교 방향에 실제로 기여하는가?

Coverage가 높아도 Quality가 낮으면 deep research로 넘어가지 않습니다.

### 1. 새 본문 시작

```powershell
python scripts/run_logos_max.py `
  --book John `
  --passage 13:14 `
  --context 13:1-17 `
  --genre gospel_farewell_discourse `
  --step setup
```

### 2. Logos 연구 레시피와 캡처 체크리스트 생성

```powershell
python scripts/run_logos_max.py `
  --passage docs/john/13-14/00-passage.yaml `
  --step recipe
```

생성 파일:

- `docs/john/13-14/01-logos-recipe.md`
- `docs/john/13-14/02-logos-capture-checklist.md`

### 3. Logos에서 자료 캡처

허용:

- Logos 공식 UI
- Copy / Export / Print
- 사용자가 볼 수 있는 패널 내용 캡처
- `tmp/logos-capture/raw/` 저장

금지:

- Logos 내부 DB 접근
- 설치 폴더 리소스 직접 추출
- 유료 리소스 대량 추출
- 라이선스 우회

Actual-use 원칙:

- AI 예시는 Logos 캡처의 대체물이 아닙니다.
- Logos에서 실제 확인한 자료만 raw capture로 인정합니다.
- 템플릿 파일은 `capture_status: template` 상태에서는 Coverage/Quality 감사에서 제외됩니다.
- 템플릿을 실제 캡처로 사용하려면 Logos Sources Checked를 채우고 `capture_status: actual`로 바꾸십시오.

### 4. Coverage + Quality 감사

```powershell
python scripts/run_logos_max.py `
  --passage docs/john/13-14/00-passage.yaml `
  --step audit
```

생성 파일:

- `docs/john/13-14/03-logos-coverage-report.md`
- `docs/john/13-14/04-capture-quality-report.md`

### 5. Combined Gate 확인

```powershell
python scripts/run_logos_max.py `
  --passage docs/john/13-14/00-passage.yaml `
  --step gate
```

Gate 기준:

| Coverage | Quality | 판정 |
|---:|---:|---|
| 90+ | 80+ | `logos_max_deep_eligible` |
| 75+ | 70+ | `deep_eligible` |
| 75+ | 60-69 | `review_required` |
| 60-74 | any | `capture_incomplete` |
| <60 | any | `gate_blocked` |
| 75+ | <60 | `quality_blocked` |

### 6. 기준 통과 후 Deep Research

```powershell
python scripts/run_logos_max.py `
  --passage docs/john/13-14/00-passage.yaml `
  --step deep
```

Gate를 강제로 넘겨야 할 때는 반드시 사유를 남겨야 합니다.

```powershell
python scripts/run_logos_max.py `
  --passage docs/john/13-14/00-passage.yaml `
  --step deep `
  --force-deep `
  --force-reason "수요설교 준비 시간이 제한되어 제한적 분석으로 진행"
```

생성 파일:

- `docs/john/13-14/force-override-log.md`

운영 원칙:

- deep research는 Coverage와 Quality Gate 통과 후 실행합니다.
- `--force`는 테스트 또는 예외 상황에서만 사용합니다.
- Gate 통과 후에도 `05-logos-integration-summary.md`가 없으면 deep research로 바로 가지 않습니다.
- Integration Summary는 Logos 연구 통찰을 설교 방향으로 넘기기 전의 마지막 분별 기록입니다.

## 설치

```powershell
git clone https://github.com/jjang1628-hub/sermon-workflows.git
cd sermon-workflows

python -m venv .venv
.\.venv\Scripts\activate

pip install -r requirements.txt
ollama pull qwen3:1.7b
```

Claude deep research를 사용할 때만 API 키를 환경 변수로 설정합니다.

```powershell
$env:ANTHROPIC_API_KEY = "sk-ant-..."
```

`.env`, API 키, 토큰은 커밋하지 않습니다.

## 주요 파일 구조

```text
sermon-workflows/
├─ config/
│  ├─ logos_tool_categories.yaml
│  ├─ logos_capture_checklist.yaml
│  ├─ logos_resource_priorities.yaml
│  ├─ logos_coverage_rubric.yaml
│  ├─ logos_capture_quality_rules.yaml
│  └─ genre_recipes.yaml
├─ scripts/
│  ├─ create_passage.py
│  ├─ build_logos_recipe.py
│  ├─ audit_logos_coverage.py
│  ├─ audit_capture_quality.py
│  ├─ gate_deep_research.py
│  ├─ run_logos_max.py
│  └─ run_logos_max_research.py
├─ tmp/logos-capture/raw/
└─ docs/{book}/{passage}/
   ├─ 00-passage.yaml
   ├─ 01-logos-recipe.md
   ├─ 02-logos-capture-checklist.md
   ├─ 03-logos-coverage-report.md
   ├─ 04-capture-quality-report.md
   ├─ deep-research.md
   ├─ final-direction.md
   ├─ sermon-final.md
   ├─ sermon-delivery-compression.md
   ├─ ppt-outline-preaching.md
   ├─ small-group-guide-member.md
   └─ rehearsal-guide.md
```

## 보안과 보존 원칙

- `output/`은 자동 생성물이며 Git에서 제외합니다.
- 보존할 최종 연구 자산은 `docs/` 아래에 둡니다.
- Logos 원문 자료를 대량 복제하지 않습니다.
- AI 결과는 최종 신학 판단이 아닙니다.
- 설교자는 본문과 실제 Logos 자료를 다시 확인합니다.

## 동기화

```powershell
git status
git add .
git commit -m "작업 내용 요약"
git push
```

다른 컴퓨터에서는:

```powershell
git pull
```

## 참고 문서

- `docs/troubleshooting.md`
- `docs/logos_max_workflow.md`
- `SETUP.md`
