# 요한복음 13:14 - Logos-Max v2.1 현재 상태

## 현재 판정

```text
Coverage Score: 70/100
Capture Quality Score: 90/100
Gate Decision: capture_incomplete / review_required
정상 deep research 진행: 보류
```

현재 들어온 Logos 자료의 품질은 좋지만, 필요한 자료군이 아직 충분하지 않습니다.
따라서 `--force` 없이 deep research로 넘어가면 안 됩니다.

## 부족 자료군

1. `cross_references` - 교차본문
2. `biblical_theology` - 성경신학
3. `background` - 역사·문화 배경
4. `application_pastoral` - 목회·적용

## 다음 실행 순서

```powershell
python scripts/audit_logos_coverage.py --passage docs/john/13-14/00-passage.yaml
python scripts/audit_capture_quality.py --passage docs/john/13-14/00-passage.yaml
python scripts/gate_deep_research.py --passage docs/john/13-14/00-passage.yaml
python scripts/status.py --passage docs/john/13-14/00-passage.yaml
```

목표:

```text
Coverage Score: 75+
Capture Quality Score: 70+
Gate Decision: deep_eligible
```

## 보존 구조

- 현재 v2.1 활성 파일은 `00`부터 `05`까지입니다.
- 이전 설교 패키지는 `v1/` 아래에 보존했습니다.
- 강제 실행 또는 시험 산출물은 `archive/forced-20260526/` 아래에 보존했습니다.

## 운영 원칙

- `tmp/logos-capture/raw/*.md` 파일은 실제 Logos 확인 후에만 `capture_status: actual`로 둡니다.
- 빈 템플릿은 점수에 반영되지 않습니다.
- `05-logos-integration-summary.md`는 Gate 통과 후 실제 Logos 통찰을 요약하는 검문소입니다.
- `--force`는 정상 통과가 아니며, 테스트 또는 예외 상황에서만 사용합니다.
