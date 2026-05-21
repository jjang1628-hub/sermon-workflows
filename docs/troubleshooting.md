# Logos-Max 트러블슈팅 가이드

> 발생한 실제 버그와 해결책을 기록합니다.  
> 새 문제 발생 시 이 파일에 추가하세요.

---

## BUG-001 — Ollama qwen3 0바이트 출력

**발생 환경**  
- Ollama 0.5+, qwen3:1.7b / qwen3:8b  
- 오케스트레이터(`run_logos_max_research.py`)에서 서브프로세스로 실행 시  
- 단독 실행(`python scripts/run_local_research_with_ollama.py`)에서도 재현 가능

**증상**
```
OK 저장 완료: output\local_research\jn-13-14-local-research.md
   크기: 0바이트
```

**원인**

Ollama 0.5+에서 qwen3 계열 모델은 **thinking 모드**를 기본 활성화합니다.  
thinking 모드에서 응답 토큰은 `chunk["thinking"]` 필드에 들어가고,  
기존 코드가 읽던 `chunk["response"]` 필드는 **비어 있습니다.**

```python
# 문제 코드
token = chunk.get("response", "")   # thinking 모드에서는 항상 빈 문자열
full_response.append(token)          # 빈 문자열만 쌓임
```

qwen3가 `num_predict` 예산을 thinking에 소진하면  
`full_response = []` 상태로 파일이 0바이트가 됩니다.

**해결책**

`run_local_research_with_ollama.py`의 `run_ollama_generate()`:

```python
is_qwen3 = "qwen3" in model.lower()
payload_dict = { ... }
if is_qwen3:
    payload_dict["think"] = False   # thinking 모드 비활성화
```

- qwen3 모델 감지 시 `"think": False`를 Ollama API 페이로드에 추가
- `num_predict` 3000 → 4096으로 증가 (응답 공간 확보)

**Regression 테스트**
```
1. qwen3 모델 실행 후 출력 파일 크기 > 0바이트
2. output/local_research/{slug}-local-research.md 존재 및 비어 있지 않음
```

**Fallback 보호**  
빈 결과가 나와도 0바이트 파일 생성 방지:

```python
if not result.strip():
    result = "# Logos 연구 자료 (로컬 분석 — 모델 응답 없음)\n\n..."
output_path.write_text(result, encoding="utf-8")
```

---

## BUG-002 — Windows cp949 UnicodeEncodeError

**발생 환경**  
- Windows, PowerShell 기본 인코딩 cp949  
- `run_logos_max_research.py` 오케스트레이터 실행 시

**증상**
```
UnicodeEncodeError: 'cp949' codec can't encode character '–' in position 6
  File "scripts/run_logos_max_research.py", line 85, in run_step
    print(f"   {line}")
```

en-dash (`–`, U+2013) 등 한글·특수문자가 서브프로세스 stdout에 포함되면  
오케스트레이터의 `print()` 호출이 cp949 인코딩 오류로 충돌합니다.

**원인**

1. 서브프로세스 stdout을 `capture_output=True, encoding="utf-8"`로 캡처
2. 캡처된 UTF-8 문자열을 `print(f"   {line}")` 로 출력
3. 오케스트레이터 자체 stdout이 cp949이면 인코딩 불가 문자에서 충돌

**해결책**

`run_logos_max_research.py` 상단:

```python
# Windows cp949 콘솔에서 한글/특수문자 출력 깨짐 방지
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
```

`run_step()` 내부:

```python
sub_env = dict(os.environ, PYTHONUTF8="1")
result = subprocess.run(
    cmd, capture_output=True, text=True,
    encoding="utf-8", errors="replace",
    env=sub_env,           # 서브프로세스도 UTF-8 모드
)
```

`run_local_research_with_ollama.py` 스트리밍 print:

```python
try:
    print(token, end="", flush=True)
except UnicodeEncodeError:
    print("?", end="", flush=True)   # 인코딩 불가 문자는 ?로 대체
```

**Regression 테스트**
```
1. 한글/특수문자 포함 파이프라인 실행 시 UnicodeEncodeError 없음
2. 오케스트레이터 8단계 EXIT:0 완료
3. 출력 로그에 한글 정상 표시
```

---

## BUG-003 — Windows `FileExistsError: [WinError 183]`

**발생 환경**  
- Windows, Python 3.x  
- 여러 스크립트의 `temp.rename(output_path)` 호출 시

**증상**
```
FileExistsError: [WinError 183] 파일이 이미 있으므로 만들 수 없습니다
```

**원인**

Linux와 달리 Windows의 `Path.rename()`은 대상 파일이 이미 존재하면 실패합니다.

**해결책**

모든 스크립트에 적용된 패턴:

```python
temp = output_path.with_suffix(".tmp")
temp.write_text(content, encoding="utf-8")
if output_path.exists():          # Windows 호환: 먼저 삭제
    output_path.unlink()
temp.rename(output_path)
```

**적용된 파일**  
`classify_logos_library.py`, `run_deep_research_with_claude.py`,  
`run_counter_reading.py`, `audit_research_claims.py`,  
`build_evidence_ledger.py`, `prepare_research_pack.py`,  
`validate_logos_capture.py`, `recommend_logos_research_recipe.py`

---

## Ollama Output Quality Gate v2 가이드

Ollama 실행 후 자동으로 생성되는 `output/local_research/{slug}-quality-gate.md`를 확인하세요.

Quality Gate v2는 **Keyword Gate [K]** + **Logic Gate [L]** 2층 구조입니다.
- **[K]**: 해당 단어/구절이 텍스트에 존재하는가? (단어 수준)
- **[L]**: 해당 개념이 올바른 해석 맥락과 함께 사용되는가? (논리 수준, ±300자 근접 확인)

### QG 항목별 의미

| ID | 층 | 항목 | 통과 조건 | 실패 시 의미 |
|----|----|----|----------|------------|
| QG-CAP | — | 캡처 충분성 | ≥2,000자 | 자료 부족 — 추가 캡처 권장 |
| QG-01 | K | 본문 문맥 반영 | 앞뒤 1개 이상 절 번호 언급 | 캡처 자료 부족 또는 모델이 문맥 무시 |
| QG-02 | K | 핵심 구절 반영 | 본문 핵심 단어 2개 이상 | 본문을 제대로 분석하지 않음 |
| QG-03 | L | 은혜→순종 구조 | 은혜+순종 언급 또는 선행-응답 논리 | 섬김 윤리로 축소됐을 가능성 |
| QG-04 | K | 그리스도 중심 연결 | 십자가·구속·그리스도 등 1개 이상 | 도덕주의적 설교 위험 |
| QG-05 | — | 환각 자료 감지 | 알려진 환각 패턴 없음 | 허위 주석명 포함 — 직접 사용 금지 |
| QG-ETH | L | 섬김 윤리 축소 경고 | 윤리 단독 or 복음 균형 | 윤리 언어만 있고 복음 연결 없음 |
| QG-06 | — | 종합 판정 | 자동 | 아래 판정 기준 참조 |
| QG-J131-K | K | 요 13:1 언급 | "13:1" 또는 "끝까지 사랑" | 세족 액자 누락 |
| QG-J131-L | L | 요 13:1 해석 액자 | 13:1이 세족 해석의 토대로 사용 | 13:1 언급만 있고 해석 연결 없음 |
| QG-J133-K | K | 요 13:3 언급 | "13:3" 또는 "아버지께로 가심" | 자발적 낮아짐 근거 누락 |
| QG-J138-K | K | 요 13:8 언급 | "13:8" 또는 "씻어 주지 않으면" | 구원론적 씻김 누락 |
| QG-J138-L | L | 요 13:8 구원론적 연결 | 씻김이 관계/정결/구원과 연결 | 단순 세족 행위로만 해석 |
| QG-J1414-L | L | 13:14 선행 은혜 구조 | "씻었으니 → 너희도" 은혜 선행 | 명령 중심 설교 위험 |

### verdict_code 및 판정 기준

| verdict_code | 판정 | 조건 | 오케스트레이터 동작 |
|---|---|---|---|
| `draft_usable` | 초안 사용 가능 | QG-01~05 모두 통과 | Claude 보강 권장 |
| `claude_required` | Claude 필수 | QG-01~04 중 1~2개 실패 or QG-ETH 실패 | `--ollama-critique` 전달 |
| `recapture_required` | 재캡처 권장 | QG-01~04 중 3개+ 실패 or QG-CAP=quick_only | 강력 재캡처 권고 |
| `direct_use_forbidden` | 직접 사용 금지 | QG-05 실패 (환각) | `--skip-deep` 시 🚨 경고 차단 |

**`direct_use_forbidden` + `--skip-deep` 조합**: 오케스트레이터가 최종 보고에 경고 메시지를 출력합니다. Claude 심층 분석 없이 이 초안을 설교에 사용하지 마십시오.

### QG-CAP 캡처 등급

| 등급 | 기준 | 의미 |
|------|------|------|
| quick_only | < 2,000자 | Standard/Deep 분석 불가 |
| standard_limited | 2,000~6,000자 | Standard 가능하나 주석 추가 권장 |
| standard_ok | 6,000~15,000자 | Standard 정상, Deep 제한 |
| deep_eligible | ≥ 15,000자 | 모든 모드 가능 |

### QG-05 환각 감지 패턴

현재 등록된 고위험 패턴:
- `고신총회` — qwen3:1.7b가 자주 생성하는 허위 출판사
- `IBT 신학` — 허위 시리즈명
- `CLC 신약 주석 시리즈` — CLC는 실존하지만 해당 시리즈로 출판 안 됨
- `신약의 구약사용 주석` — 실제 Beale & Carson 책 제목이 다름
- `대한예수교장로회 고신` — 주석서 출판 주체로 잘못 사용
- `기독교문서선교회 주석` — 허위 시리즈명
- `합신대학원 주석` — 허위 시리즈명

패턴 추가: `scripts/run_local_research_with_ollama.py`의 `_HALLUCINATION_INDICATOR_PATTERNS` 리스트에 추가

저자명 자동 감지도 동작합니다: `저자명 (연도)` 패턴으로 추출된 저자가 Logos 캡처에 없으면 `저자?:이름` 형태로 경고합니다.

---

## BUG-004 — Ollama 캡처 4,000자 잘림으로 QG 실패

**발생 환경**
- `run_local_research_with_ollama.py` 모든 버전
- 연구팩이 4,000자 이상일 때

**증상**
```
NG [QG-J133-K] 요 13:3 언급 [K]: 누락: 아버지께로 가심
NG [QG-J138-K] 요 13:8 언급 [K]: 누락: 씻어 주지 않으면
NG [QG-J138-L] 요 13:8 구원론적 연결 [L]: 누락
NG [QG-J1414-L] 13:14 선행 은혜→응답 [L]: 누락
```
캡처 파일에 키워드가 분명히 존재하지만 QG가 실패함.

**원인**

`run_local_research_with_ollama.py` 라인 599:
```python
capture_content = raw[:4000] + (...)   # 4,000자 이후 잘림
```
연구팩의 신학 분석 내용(요 13:8 구원론, 13:14 은혜→순종 등)이 4,000자 이후에 위치해 잘림.

실제 측정:
- `'13:8'` → 위치 4,091자 (4,000 제한에 딱 걸림)
- `'씻어 주지'` → 위치 4,162자
- `'구원론'` → 위치 4,100자
- `'13:3'` → 위치 6,367자
- `'아버지께로'` → 위치 6,455자

**해결책**

```python
# 수정 전
capture_content = raw[:4000] + ("\n\n[... 이하 생략 ...]" if len(raw) > 4000 else "")

# 수정 후
capture_content = raw[:8000] + ("\n\n[... 이하 생략 ...]" if len(raw) > 8000 else "")
```

**함께 적용: `prepare_research_pack.py` 파일 발견 로직 확장**

`find_capture_files()` 함수가 `jn` 접두사만 인식하여 `john-13-*` 파일을 누락.

```python
# 추가된 alias
_prefix_aliases = {
    "jn": ["john", "jn"],
    "mt": ["matt", "matthew", "mt"],
    ...
}
# S05, S06에 추가된 키워드
"S05": ["word-study", ..., "text-study", "bible-text"],
"S06": ["commentary", ..., "encyclopedia", "encycl"],
```

---

## 일반 진단 명령

```powershell
# Ollama 서버 상태
ollama list
ollama ps

# qwen3 단독 동작 확인
ollama run qwen3:1.7b "안녕"

# 파이프라인 단계별 실행 확인
cd C:\Users\my\Documents\sermon-workflows

# Ollama 단독
C:\Python314\python.exe scripts/run_local_research_with_ollama.py `
  --passage "요한복음 13:14" --model qwen3:1.7b `
  --logos-capture tmp\logos-capture\raw\john-13-14-passage-guide-20260521.md `
  --force

# 출력 파일 확인 (크기 > 0이어야 함)
Get-Item output\local_research\jn-13-14-local-research.md | Select-Object Name, Length

# 전체 파이프라인 (--skip-deep: Claude API 없이 실행)
C:\Python314\python.exe scripts/run_logos_max_research.py `
  --passage "요한복음 13:14" --mode standard `
  --capture tmp\logos-capture\raw\john-13-14-passage-guide-20260521.md `
  --skip-deep --force
```

---

## Ollama 결과물 신학 품질 기준

qwen3:1.7b는 **4단계 초안 역할**입니다. 아래 기준으로 판단하세요:

| 항목 | 기대 수준 | 실제 성능 |
|------|----------|----------|
| 구조 섹션 완성 | 필수 | ✅ 통과 |
| 핵심 문맥 포착 (앞뒤 5절) | 권장 | ⚠️ 약함 |
| Big Idea (본문 논리 기반) | 권장 | ⚠️ 템플릿 경향 |
| 주석 인용 정확도 | 보조 | ❌ 환각 주의 |
| 십자가 방향 연결 | 5단계에서 보완 | ❌ 1.7b 한계 |

**주석 인용 환각 주의**: qwen3:1.7b는 Logos 캡처에 없는 책을 스스로 만들어 낼 수 있습니다.  
Logos 캡처 파일이 풍부할수록 (3,000자+) 환각이 줄어듭니다.  
캡처 부족 시 `--skip-ollama`로 건너뛰고 바로 5단계 Claude 심층 연구를 사용하세요.

---

⚠️ 이 자료는 연구 보조 자료입니다. 최종 설교는 목사님이 직접 작성하세요.
