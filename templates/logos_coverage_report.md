# Logos Coverage Report — {{BOOK_KO}} {{PASSAGE}}

**감사일**: {{DATE}}  
**캡처 파일 수**: {{FILE_COUNT}}개  
**총 텍스트**: {{TEXT_SIZE}}자

---

## 종합 점수

### {{SCORE}} / 100점

**상태**: `{{STATUS}}`  
**판정**: {{STATUS_LABEL}}

---

## 항목별 점수

| 항목 | 배점 | 획득 | 상태 |
|------|------|------|------|
| 본문 범위·문맥 확인 | 10 | {{R01}} | {{R01_STATUS}} |
| 번역 비교 | 10 | {{R02}} | {{R02_STATUS}} |
| 원어·문법 | 15 | {{R03}} | {{R03_STATUS}} |
| 구조·담화 | 10 | {{R04}} | {{R04_STATUS}} |
| 교차본문 | 10 | {{R05}} | {{R05_STATUS}} |
| 주석 비교 | 15 | {{R06}} | {{R06_STATUS}} |
| 성경신학 | 10 | {{R07}} | {{R07_STATUS}} |
| 조직신학 | 5 | {{R08}} | {{R08_STATUS}} |
| 역사·문화 배경 | 5 | {{R09}} | {{R09_STATUS}} |
| 설교 자료 | 5 | {{R10}} | {{R10_STATUS}} |
| 목회·적용 자료 | 5 | {{R11}} | {{R11_STATUS}} |
| **합계** | **100** | **{{SCORE}}** | |

---

## 누락 항목 (캡처 필요)

{{MISSING_ITEMS}}

---

## 완료된 항목

{{PASSED_ITEMS}}

---

## 다음 단계

```powershell
# 보강 후 재감사
python scripts/audit_logos_coverage.py --passage {{PASSAGE_YAML_PATH}}

# 통과 시 게이트 확인
python scripts/gate_deep_research.py --passage {{PASSAGE_YAML_PATH}}

# 심층 연구
python scripts/run_logos_max_research.py --passage "{{BOOK_KO}} {{PASSAGE}}"
```
