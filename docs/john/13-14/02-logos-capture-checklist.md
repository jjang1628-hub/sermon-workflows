# Logos 캡처 체크리스트 — 요한복음 13:14

**본문**: 요한복음 13:1-17  
**장르**: gospel  
**생성일**: 2026-05-22

> 아래 항목을 Logos에서 순서대로 실행하십시오.
> 각 항목 완료 후 `[x]`로 표시하고, 캡처 파일명을 기록하십시오.

---

## 필수 캡처 (모든 항목 완료 후 다음 단계 진행)

- [ ] **C-01** 본문 범위 확정 (Passage Guide)
  - 캡처 파일: ___
  - 확정 범위: ___

- [ ] **C-02** 번역 비교 (Text Comparison)
  - 캡처 파일: ___
  - 비교 번역본: ___

- [ ] **C-03** 원어 핵심 단어 (Exegetical Guide / Bible Word Study)
  - 캡처 파일: ___
  - 확인한 단어: ___

- [ ] **C-04** 교차본문 (Cross References)
  - 캡처 파일: ___
  - 선택한 교차본문 수: ___

- [ ] **C-05** 주석 비교 (Commentaries)
  - 캡처 파일: ___
  - 확인한 주석: ___

---

## 권장 캡처 (장르: gospel)

- [ ] **C-06** 구조·담화 분석 (Passage Analysis)
  - 캡처 파일: ___

- [ ] **C-07** 역사·문화 배경 (Factbook)
  - 캡처 파일: ___

- [ ] **C-08** 성경신학 테마 (Biblical Theology)
  - 캡처 파일: ___

- [ ] **C-09** 설교 자료 (Sermon Starter Guide)
  - 캡처 파일: ___

---

## 캡처 파일 명명 규칙

```
tmp/logos-capture/raw/{book-slug}-{passage-slug}-{tool}-{YYYYMMDD}.md

예시:
  tmp/logos-capture/raw/jn-13-14-passage-guide-20260522.md
  tmp/logos-capture/raw/jn-13-14-word-study-20260522.md
```

---

## 모든 필수 항목 완료 후

```powershell
python scripts/audit_logos_coverage.py --passage docs\john\13-14\00-passage.yaml
```