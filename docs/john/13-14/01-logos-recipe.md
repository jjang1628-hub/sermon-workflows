# Logos 연구 레시피 - 요한복음 13:14

- 본문: 요한복음 13:1-17
- 장르: `gospel_farewell_discourse`
- 보조 장르: gospel_symbolic_action, gospel_discipleship
- 주제 힌트: 씻김 받은 자의 섬김 — 끝까지 사랑하신 주님의 낮아지심

이 레시피의 목적은 AI가 먼저 설교하지 못하게 하고, Logos 자료를 먼저 충분히 보게 만드는 것입니다.

## 장르 핵심 강조점

- 고별 담화 전체 흐름
- 제자 공동체 형성
- 십자가 전 문맥
- 사랑과 순종의 관계
- 그리스도의 낮아지심

## Logos 도구 사용 순서

| 순서 | 자료군 | Logos 도구 | 캡처 파일 제안 |
|---:|---|---|---|
| 1 | 본문 확정 | Passage Guide, Bible panel, Text Comparison | `tmp/logos-capture/raw/jn-13-14-text_establishment-20260522.md` |
| 2 | 번역 비교 | Text Comparison | `tmp/logos-capture/raw/jn-13-14-translation_comparison-20260522.md` |
| 3 | 구조·담화 | Passage Analysis, Clause Search, Discourse resources | `tmp/logos-capture/raw/jn-13-14-structure_discourse-20260522.md` |
| 4 | 원어·문법 | Exegetical Guide, Bible Word Study, Interlinear | `tmp/logos-capture/raw/jn-13-14-original_language-20260522.md` |
| 5 | 교차본문 | Cross References, Important Passages, Treasury of Scripture Knowledge | `tmp/logos-capture/raw/jn-13-14-cross_references-20260522.md` |
| 6 | 주석 비교 | Passage Guide > Commentaries | `tmp/logos-capture/raw/jn-13-14-commentaries-20260522.md` |
| 7 | 성경신학 | Factbook themes, Biblical Theology resources | `tmp/logos-capture/raw/jn-13-14-biblical_theology-20260522.md` |
| 8 | 목회·적용 | Pastoral theology, counseling resources, notes | `tmp/logos-capture/raw/jn-13-14-application_pastoral-20260522.md` |
| 9 | 역사·문화 배경 | Factbook, Bible Dictionaries, Atlas | `tmp/logos-capture/raw/jn-13-14-background-20260522.md` |

## 다음 단계

1. 아래 체크리스트 파일을 열고 Logos에서 자료를 캡처하십시오.
2. 캡처 파일은 `tmp/logos-capture/raw/`에 저장하십시오.
3. Coverage audit과 Capture quality audit을 실행하십시오.

```powershell
python scripts/run_logos_max.py --passage docs\john\13-14\00-passage.yaml --step audit
```