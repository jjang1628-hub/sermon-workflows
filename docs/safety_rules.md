# 안전 규칙 (Safety Rules) — 불변 원칙

이 문서는 `configs/safety_rules.yaml`의 인간 가독성 버전이다.
모든 스크립트와 자동화 프로세스는 이 규칙을 따른다.

---

## 파일 보호 규칙

### FP-01: 기존 파일 직접 덮어쓰기 금지
- 출력 경로에 파일이 존재하면 **--force 없이 즉시 중단**
- 메시지: `"NG 출력 파일이 이미 있습니다. --force 사용: {경로}"`

### FP-02: --force 사용 시 백업 + temp replace 패턴 필수
```python
# 올바른 패턴
backup = output_path.with_suffix('.bak')
shutil.copy2(output_path, backup)
temp = output_path.with_suffix('.tmp')
write_to(temp)
temp.rename(output_path)
```
- `--force` 단독으로 직접 덮어쓰기 금지
- 백업 없이 `output_path.write_text(...)` 호출 금지

### FP-03: 원본 캡처 파일 수정 금지
- `tmp/logos-capture/raw/` 폴더 파일은 읽기 전용
- 모든 처리 결과는 별도 폴더에 저장

---

## Logos 접근 규칙

### LA-01: Logos 내부 DB 직접 접근 금지
허용: `logos4:` URI 스킴으로 앱 열기, UI를 통한 열람
금지: Logos 설치 경로의 `.db`, `.sqlite`, `.index` 파일 직접 읽기

### LA-02: 설치 폴더 리소스 직접 추출 금지
금지 경로 예시:
- `C:\Program Files (x86)\Logos Bible Software\`
- `%APPDATA%\Logos\`
- `%LOCALAPPDATA%\Logos\`

### LA-03: 유료 자료 대량 스크래핑 금지
- 단일 본문 캡처만 허용
- 자동 반복 캡처 금지

### LA-04: 공식 UI 경로로 확보한 자료만 분석
허용: Ctrl+A → Ctrl+C 복사, File→Export, Print→PDF
금지: 바이너리 파싱, 패킷 캡처, 메모리 덤프

### LA-05: 장문 원문 인용 금지
- 단일 자료에서 최대 500자 인용
- 초과 시 자동 잘림 + 경고 추가

---

## 신학 안전 규칙

### TS-01: Ollama 결과 레이블 필수
```
⚠️ 1차 분석 초안 — 목사님 검토 필요
```
로컬 LLM 결과물에 위 레이블이 없으면 자동으로 추가된다.

### TS-02: 인물 영웅화 감지 시 경고
다음 패턴 감지 시 경고 삽입:
- "모범을 보이셨습니다" (인물 미화)
- "귀감이 됩니다"
- "우리도 이처럼"

### TS-03: 율법적 적용 감지 시 경고
복음 기반 없이 다음 패턴 사용 시 경고:
- "우리는 반드시 ~해야 합니다"
- "~하지 않으면"
- 은혜 언급 없는 명령형 적용

### TS-04: Counter-Reading Pass 생략 불가
Deep/Expert 모드에서 counter-reading 파일이 없으면 완료 보고를 거부한다.

---

## 출력 안전 규칙

### OS-01: 설교 최종본 오인 방지
모든 출력 파일 하단에 다음 푸터 자동 추가:
```
⚠️ 이 자료는 연구 보조 자료입니다. 최종 설교는 목사님이 직접 작성하세요.
```

### OS-02: 민감한 개인정보 출력 금지
- 교인 이름, 개인 상황을 출력 파일에 포함하지 않는다

---

## 실행 안전 규칙

### ES-01: API 키 코드 하드코딩 금지
```python
# 금지
api_key = "sk-ant-api03-..."

# 허용
api_key = os.environ.get("ANTHROPIC_API_KEY", "")
```

### ES-02: Ollama generate 전 서버 확인 필수
```python
ok, msg = check_ollama_available()
if not ok:
    return 1  # 확인 없이 generate 호출 금지
```

### ES-03: 출력 디렉토리 자동 생성
```python
output_path.parent.mkdir(parents=True, exist_ok=True)
```

---

## 위반 심각도

| 수준 | 의미 | 예시 |
|------|------|------|
| 🛑 block | 실행 완전 중단 | Logos DB 직접 접근 시도 |
| ❌ error | 오류 반환 후 중단 | 필수 파일 없음 |
| ⚠️ warning | 경고 후 계속 | 인물 영웅화 패턴 감지 |
| ✏️ auto-fix | 자동 수정 후 계속 | 레이블/푸터 자동 추가 |

---

## 이 규칙을 바꾸려면

`configs/safety_rules.yaml`을 수정하고 이 문서를 함께 업데이트한다.
규칙 완화는 신중하게 검토한다. "편의"를 위해 안전을 타협하지 않는다.
