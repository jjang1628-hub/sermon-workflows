# Logos 캡처 체크리스트 - 요한복음 13:14

- 본문: 요한복음 13:1-17
- 장르: `gospel_farewell_discourse`

체크리스트는 설교문을 빨리 만들기 위한 것이 아니라, 본문 아래 충분히 머물기 위한 장치입니다.

## 필수/권장 캡처

### 1. 본문 확정
- [ ] Logos 도구: Passage Guide, Bible panel, Text Comparison
- [ ] 캡처 파일: `tmp/logos-capture/raw/jn-13-14-text_establishment-20260527.md`
- [ ] 본문 이해에 실제로 기여하는 요약 또는 메모 포함

### 2. 번역 비교
- [ ] Logos 도구: Text Comparison
- [ ] 캡처 파일: `tmp/logos-capture/raw/jn-13-14-translation_comparison-20260527.md`
- [ ] 본문 이해에 실제로 기여하는 요약 또는 메모 포함

### 3. 구조·담화
- [ ] Logos 도구: Passage Analysis, Clause Search, Discourse resources
- [ ] 캡처 파일: `tmp/logos-capture/raw/jn-13-14-structure_discourse-20260527.md`
- [ ] 본문 이해에 실제로 기여하는 요약 또는 메모 포함

### 4. 원어·문법
- [ ] Logos 도구: Exegetical Guide, Bible Word Study, Interlinear
- [ ] 캡처 파일: `tmp/logos-capture/raw/jn-13-14-original_language-20260527.md`
- [ ] 본문 이해에 실제로 기여하는 요약 또는 메모 포함

### 5. 교차본문
- [ ] Logos 도구: Cross References, Important Passages, Treasury of Scripture Knowledge
- [ ] 캡처 파일: `tmp/logos-capture/raw/jn-13-14-cross_references-20260527.md`
- [ ] 본문 이해에 실제로 기여하는 요약 또는 메모 포함

### 6. 주석 비교
- [ ] Logos 도구: Passage Guide > Commentaries
- [ ] 캡처 파일: `tmp/logos-capture/raw/jn-13-14-commentaries-20260527.md`
- [ ] 본문 이해에 실제로 기여하는 요약 또는 메모 포함

### 7. 성경신학
- [ ] Logos 도구: Factbook themes, Biblical Theology resources
- [ ] 캡처 파일: `tmp/logos-capture/raw/jn-13-14-biblical_theology-20260527.md`
- [ ] 본문 이해에 실제로 기여하는 요약 또는 메모 포함

### 8. 목회·적용
- [ ] Logos 도구: Pastoral theology, counseling resources, notes
- [ ] 캡처 파일: `tmp/logos-capture/raw/jn-13-14-application_pastoral-20260527.md`
- [ ] 본문 이해에 실제로 기여하는 요약 또는 메모 포함

### 9. 역사·문화 배경
- [ ] Logos 도구: Factbook, Bible Dictionaries, Atlas
- [ ] 캡처 파일: `tmp/logos-capture/raw/jn-13-14-background-20260527.md`
- [ ] 본문 이해에 실제로 기여하는 요약 또는 메모 포함

## 완료 후 실행

```powershell
python scripts/audit_logos_coverage.py --passage docs\john\13-14\00-passage.yaml
python scripts/audit_capture_quality.py --passage docs\john\13-14\00-passage.yaml
python scripts/gate_deep_research.py --passage docs\john\13-14\00-passage.yaml
```