# Logos Coverage Report - 요한복음 13:14

- 감사 시각: 2026-05-27 11:35:26
- 캡처 파일 수: 6
- 통합 텍스트 길이: 16,787자

## Coverage Score

### 70 / 100점

- status: `review_required`
- 판정: 보강 필요. deep research는 보류를 권장합니다.

## 사용한 캡처 파일

- `tmp\logos-capture\raw\jn-13-14-uia-passage-workflow.md` (4,580 bytes)
- `tmp\logos-capture\raw\john-13-1-17-passage-guide-20260521.md` (5,997 bytes)
- `tmp\logos-capture\raw\john-13-1-17-word-study-20260521.md` (7,167 bytes)
- `tmp\logos-capture\raw\john-13-1-bible-encyclopedia-20260521.md` (3,586 bytes)
- `tmp\logos-capture\raw\john-13-14-passage-guide-20260521.md` (3,893 bytes)
- `tmp\logos-capture\raw\structure-discourse.md` (6,238 bytes)

## 항목별 점수

| 항목 | 배점 | 획득 | 상태 |
|---|---:|---:|---|
| R-01 본문 범위·문맥 확인 | 10 | 10 | 통과 |
| R-02 번역 비교 | 10 | 10 | 통과 |
| R-03 원어·문법 | 15 | 15 | 통과 |
| R-04 구조·담화 | 10 | 10 | 통과 |
| R-05 교차본문 | 10 | 0 | 누락 |
| R-06 주석 비교 | 15 | 15 | 통과 |
| R-07 성경신학 | 10 | 0 | 누락 |
| R-08 조직신학 | 5 | 5 | 통과 |
| R-09 역사·문화 배경 | 5 | 0 | 누락 |
| R-10 설교 자료 | 5 | 5 | 통과 |
| R-11 목회·적용 | 5 | 0 | 누락 |
| **합계** | **100** | **70** | |

## 누락 자료군

### R-05 - 교차본문 (0/10점)
- 발견 키워드: 2개 / 필요: 2개
- 해당 Logos 자료군을 실제로 확인하고 raw capture에 요약하십시오.

### R-07 - 성경신학 (0/10점)
- 발견 키워드: 2개 / 필요: 2개
- 해당 Logos 자료군을 실제로 확인하고 raw capture에 요약하십시오.

### R-09 - 역사·문화 배경 (0/5점)
- 발견 키워드: 5개 / 필요: 2개
- 해당 Logos 자료군을 실제로 확인하고 raw capture에 요약하십시오.

### R-11 - 목회·적용 (0/5점)
- 발견 키워드: 2개 / 필요: 2개
- 해당 Logos 자료군을 실제로 확인하고 raw capture에 요약하십시오.


## 통과 자료군

- R-01 본문 범위·문맥 확인 (10/10점)
- R-02 번역 비교 (10/10점)
- R-03 원어·문법 (15/15점)
- R-04 구조·담화 (10/10점)
- R-06 주석 비교 (15/15점)
- R-08 조직신학 (5/5점)
- R-10 설교 자료 (5/5점)

## 다음 단계

Coverage는 자료군 존재 여부만 평가합니다. 이어서 Capture Quality를 확인하십시오.

```powershell
python scripts/audit_capture_quality.py --passage docs\john\13-14\00-passage.yaml
python scripts/gate_deep_research.py --passage docs\john\13-14\00-passage.yaml
```