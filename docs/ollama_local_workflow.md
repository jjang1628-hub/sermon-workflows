# Ollama 로컬 LLM 워크플로우

## 역할

Ollama는 Logos-Max 시스템에서 **1차 분석 초안**을 담당한다.
Claude API 키 없이도 기본 분석이 가능하다.
단, 결과는 반드시 "1차 분석 초안" 레이블을 포함해야 한다.

---

## 설치 및 설정

### Ollama 설치
```powershell
winget install Ollama.Ollama
# 설치 후 PATH 재로드
$env:PATH = [System.Environment]::GetEnvironmentVariable("PATH","Machine") + ";" + $env:PATH
```

### 모델 설치
```powershell
# RAM 8GB 이상 권장
ollama pull qwen3:8b

# RAM 4GB (최소 2.7GB 여유)
ollama pull qwen3:1.7b

# RAM 2GB (초경량)
ollama pull qwen3:0.6b
```

### 서버 상태 확인
```powershell
python scripts\run_local_research_with_ollama.py --check-ollama --model qwen3:1.7b
```

---

## RAM 요구사항

| 모델 | 모델 크기 | 필요 RAM | 권장 RAM |
|------|----------|----------|----------|
| qwen3:0.6b | ~400MB | 1GB | 2GB |
| qwen3:1.7b | ~1.1GB | 2GB | 4GB |
| qwen3:8b | ~5.5GB | 6GB | 8GB |

**시스템 RAM이 7.7GB인 경우**: qwen3:1.7b 권장 (qwen3:8b는 메모리 부족 오류 가능)

---

## 실행 방법

### 기본 실행
```powershell
python scripts\run_local_research_with_ollama.py `
  --passage "요한복음 13:14" `
  --logos-capture tmp\logos-capture\raw\john-13-14-passage-guide-20260521.md `
  --model qwen3:1.7b
```

### 전체 옵션
```powershell
python scripts\run_local_research_with_ollama.py `
  --passage "요한복음 13:14" `
  --logos-capture <캡처파일> `
  --output output\local_research\jn-13-14-local-research.md `
  --model qwen3:1.7b `
  --research-mode quick `
  --force
```

### 캡처 파일 없이 실행
```powershell
python scripts\run_local_research_with_ollama.py `
  --passage "요한복음 13:14" `
  --model qwen3:1.7b
```

---

## 문제 해결

### HTTP 500 오류 (메모리 부족)
```
NG 생성 실패: Ollama API 오류: HTTP Error 500: Internal Server Error
```
**원인**: 모델이 사용 가능한 RAM보다 큼  
**해결**: 더 작은 모델 사용
```powershell
# qwen3:8b → qwen3:1.7b로 변경
python scripts\run_local_research_with_ollama.py --model qwen3:1.7b ...
```

### qwen3 0바이트 출력 (Ollama 0.5+)

**증상**: 실행 성공인데 `크기: 0바이트`  
**원인**: Ollama 0.5+에서 qwen3의 thinking 토큰이 `chunk["thinking"]`으로 분리됨.  
`chunk["response"]`가 비어 있어 전체 응답이 빈 문자열이 됨.  
**해결**: 스크립트 내부에서 qwen3 감지 시 `"think": False` 자동 적용 (이미 수정됨)  
**확인**:
```powershell
Get-Item output\local_research\{slug}-local-research.md | Select-Object Length
# Length > 0 이어야 함
```
→ 여전히 0바이트라면 `docs/troubleshooting.md` BUG-001 참조

### 한글 깨짐 / UnicodeEncodeError

**증상**: `UnicodeEncodeError: 'cp949' codec can't encode character`  
**원인**: 오케스트레이터 stdout이 Windows cp949인데 한글·특수문자 출력 시 충돌  
**해결**: 스크립트 내부에서 `sys.stdout.reconfigure(encoding="utf-8")` 자동 적용 (이미 수정됨)  
**수동 실행 시**:
```powershell
chcp 65001
$env:PYTHONUTF8 = "1"
python scripts\run_local_research_with_ollama.py ...
```
→ `docs/troubleshooting.md` BUG-002 참조

### Ollama 서버 미실행
```powershell
# Ollama 앱 실행 또는:
ollama serve
```

### 모델 미설치
```powershell
ollama pull qwen3:1.7b
```

---

## 출력 형식

Ollama 결과는 항상 다음 레이블을 포함:

```markdown
> ⚠️ 1차 분석 초안 — 목사님 검토 필요
> 이 분석은 로컬 LLM(qwen3:1.7b) 출력입니다.
> 원어·주석을 실제 Logos에서 반드시 확인하세요.
```

---

## Ollama vs Claude 비교

| 항목 | Ollama (로컬) | Claude (API) |
|------|--------------|--------------|
| 비용 | 무료 | 유료 (API) |
| 속도 | RAM 의존 | 빠름 |
| 품질 | 1차 초안 수준 | 심층 분석 수준 |
| 오프라인 | 가능 | 불가 |
| 신학 깊이 | 중간 | 높음 |
| 권장 용도 | 빠른 초안, 아이디어 탐색 | 심층 설교 연구 |

---

## 출력 파일

| 파일 | 경로 |
|------|------|
| 1차 분석 초안 | `output/local_research/{slug}-local-research.md` |
