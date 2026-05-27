# Claude 심층 연구 워크플로우

## 개요

Claude는 Logos-Max 시스템에서 20-Pass Multi-Pass Deep Research를 수행한다.
각 Pass는 이전 Pass의 결과를 바탕으로 더 깊은 분석을 진행한다.

---

## 20-Pass 프로토콜 상세

### Phase 1: 본문 기초 (Pass 1–7)

| Pass | 이름 | 핵심 질문 |
|------|------|-----------|
| Pass 1 | 본문 경계 확인 | 이 본문은 어디서 시작하고 끝나는가? |
| Pass 2 | 문학 장르 분류 | 복음서/서신/시편/예언/내러티브 중 어느 것인가? |
| Pass 3 | 본문 구조 분석 | 문단 구조, 키아즘, 평행법은 무엇인가? |
| Pass 4 | 핵심 단어 식별 | 반복되거나 신학적으로 중요한 단어는? |
| Pass 5 | 원어 심층 분석 | 헬라어/히브리어 핵심 단어의 의미와 용례는? |
| Pass 6 | 역사·문화 배경 | 1세기 독자가 이 본문을 어떻게 이해했을까? |
| Pass 7 | 문학적 흐름 | 저자의 논증 전개 방식은 무엇인가? |

### Phase 2: 저자·독자·구속사 (Pass 8–11)

| Pass | 이름 | 핵심 질문 |
|------|------|-----------|
| Pass 8 | 저자 의도 | 저자가 이 구절을 통해 무엇을 말하려 했는가? |
| Pass 9 | 원독자 상황 | 최초 독자의 구체적 상황은 무엇인가? |
| Pass 10 | 구속사적 위치 | 창조-타락-구속-새창조 흐름에서 이 본문의 위치는? |
| Pass 11 | 그리스도 연결 | 본문이 십자가와 부활을 어떻게 가리키는가? |

### Phase 3: 주석·신학 (Pass 12–15)

| Pass | 이름 | 핵심 질문 |
|------|------|-----------|
| Pass 12 | 주석 비교 | 3종 이상의 주석이 어떻게 다른 관점을 보이는가? |
| Pass 13 | 신학 주제 | 개혁주의 관점에서 핵심 신학 주제는? |
| Pass 14 | 교리적 함의 | 이 본문이 교의학적으로 어떤 의미를 갖는가? |
| Pass 15 | 교차 참조 | 연결되는 성경 본문 3–5개는? |

### Phase 4: 반론 (Pass 16)

| Pass | 이름 | 핵심 질문 |
|------|------|-----------|
| Pass 16 | 반론 및 대안 해석 | 최소 2개의 대안 해석은 무엇인가? |

### Phase 5: 설교 설계 (Pass 17–19)

| Pass | 이름 | 핵심 질문 |
|------|------|-----------|
| Pass 17 | 현대 적용 원리 | 오늘 성도의 삶에서 어떻게 적용되는가? |
| Pass 18 | 설교 Big Idea | 한 문장으로 설교 전체를 표현하면? |
| Pass 19 | 적용 구조화 | 복음→동기→순종 순서로 적용을 구체화하면? |

### Phase 6: 통합 검토 (Pass 20)

| Pass | 이름 | 핵심 질문 |
|------|------|-----------|
| Pass 20 | 통합 검토 | 분석의 약점, 주의사항, 추가 연구 권장사항은? |

---

## 신뢰도 레이블 체계

모든 주장에 의무적으로 신뢰도 레이블을 붙인다:

| 레이블 | 조건 |
|--------|------|
| 🔵 높음 | 원어 + 주석 2종 이상 + 교차 참조로 확인 |
| 🟡 중간 | 주석 1종 또는 일반적 학문 합의 |
| 🔴 낮음 | 추론이나 가능성 수준 |
| ⚪ 확인필요 | Logos에서 직접 확인 필요 |

---

## 실행 방법

### 기본 실행
```powershell
$env:ANTHROPIC_API_KEY = "<ANTHROPIC_API_KEY>"
python scripts\run_deep_research_with_claude.py `
  --passage "요한복음 13:14" `
  --mode standard
```

### 연구 팩 포함
```powershell
python scripts\run_deep_research_with_claude.py `
  --passage "요한복음 13:14" `
  --mode deep `
  --research-pack output\research_packs\jn-13-14-research-pack.md
```

### Logos 캡처 직접 입력
```powershell
python scripts\run_deep_research_with_claude.py `
  --passage "요한복음 13:14" `
  --logos-capture tmp\logos-capture\raw\john-13-14-passage-guide-20260521.md
```

---

## 감사 3종 세트

Claude 심층 연구 이후 반드시 실행:

```
심층 연구 보고서
       ↓
  Evidence Ledger ──→ 모든 주장에 출처 기록
       ↓
   Claim Audit ──→ 12문항으로 품질 검사
       ↓
 Counter-Reading ──→ 8관점으로 반론 생성
```

---

## 금지 사항

Claude는 다음을 하지 않는다:
- "이것이 유일한 해석입니다" 단언
- 설교 최종 결론 확정
- 인물 영웅화
- 출처 없는 원어 주장
- 율법적 적용 (복음 기반 없이 "~해야 합니다")

---

## 출력 파일

| 파일 | 경로 |
|------|------|
| 심층 연구 보고서 | `output/deep_research/{slug}-deep-research.md` |
| Evidence Ledger | `output/evidence_ledgers/{slug}-evidence-ledger.md` |
| Claim Audit | `output/claim_audits/{slug}-claim-audit.md` |
| Counter-Reading | `output/deep_research/{slug}-counter-reading.md` |

