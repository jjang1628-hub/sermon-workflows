# sermon-workflows 새 컴퓨터 셋업 가이드

## 1. Python 설치

Python 3.11 이상 (3.14 권장)
- https://www.python.org/downloads/

```powershell
python --version   # 확인
```

## 2. 의존성 설치

```powershell
cd sermon-workflows
pip install -r requirements.txt
```

## 3. Ollama 설치 (로컬 LLM, Step 4용)

- https://ollama.com 에서 설치
- 설치 후 모델 다운로드:

```powershell
ollama pull qwen3:1.7b    # 경량 (1.1GB)
ollama pull qwen3:8b      # 고품질 (5.2GB)
```

확인:
```powershell
ollama list
ollama ps
```

## 4. Claude API 키 설정 (Step 5 심층 연구용)

환경 변수 설정 (PowerShell):
```powershell
$env:ANTHROPIC_API_KEY = "<ANTHROPIC_API_KEY>"
```

영구 설정 (Windows 시스템 환경 변수):
1. 제어판 → 시스템 → 고급 시스템 설정 → 환경 변수
2. ANTHROPIC_API_KEY 추가

## 5. Python 경로 조정

`scripts/run_logos_max_research.py` 파이프라인에서 Python 실행 경로를 확인하세요.

기본값은 `C:\Python314\python.exe` — 다른 경로라면:
```powershell
# 실제 경로 확인
(Get-Command python).Source
```

`configs/` 폴더의 설정 파일 확인 후 필요시 수정.

## 6. 저장소 클론

```powershell
git clone https://github.com/<username>/sermon-workflows.git
cd sermon-workflows
```

## 7. 동기화 방법

**이 컴퓨터에서 작업 후:**
```powershell
git add .
git commit -m "캡처 보강: 요 13:1-17"
git push
```

**다른 컴퓨터에서 최신 받기:**
```powershell
git pull
```

## 8. Logos Bible Study

Logos는 라이선스 기반 소프트웨어입니다.
- 동일 라이선스로 다른 컴퓨터에도 설치/로그인 가능합니다.
- Logos에서 캡처한 자료는 `tmp/logos-capture/raw/`에 보관됩니다.
- 이 폴더는 git에 포함되어 있어 양쪽 동기화됩니다.

## 9. 파이프라인 실행 테스트

```powershell
cd sermon-workflows
python scripts/run_logos_max_research.py `
  --passage "요한복음 13:14" `
  --mode standard `
  --capture tmp\logos-capture\raw\john-13-1-17-word-study-20260521.md `
  --skip-deep --force
```

Exit:0 이면 설정 완료.

