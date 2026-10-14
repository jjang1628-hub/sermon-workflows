---
name: markitdown
description: PDF, DOCX, PPTX, XLSX, HTML, CSV, 이미지, 오디오 등 비-Markdown 파일을 Markdown으로 변환한다. 목사님이 올린 설교문·원고·주석 PDF·워드·PPT·엑셀 자료를 읽거나 분석하기 전에 텍스트로 바꿔야 할 때 사용한다. 
---

# MarkItDown 변환 스킬

Microsoft MarkItDown으로 문서를 Markdown 텍스트로 바꿔 분석 가능한 상태로 만든다.

## 언제 쓰나
- 사용자가 PDF/DOCX/PPTX/XLSX/HTML/CSV 자료를 주고 "읽어줘·요약·분석·정리"를 요청할 때
- 변환 결과를 `tmp/logos-capture/raw/` 같은 입력 단계로 넘기기 전 텍스트화가 필요할 때

## 사용법
```bash
python scripts/md_convert.py <입력파일>                 # → tmp/markitdown/<파일명>.md
python scripts/md_convert.py <입력파일> -o <출력.md>    # 출력 경로 지정
# 또는 CLI 직접:
markitdown <입력파일> -o <출력.md>
```
설치가 안 되어 있으면: `pip install -r requirements.txt`

## 규칙
- 변환본은 **원자료의 기계적 텍스트화**일 뿐이다. 표·각주·한글 서식이 깨질 수 있으니 중요한 인용은 원본과 대조한다.
- 원본 파일은 수정하지 않는다. 기존 출력 파일을 덮어쓸 때는 `.bak` 백업이 자동 생성된다.
- 변환 결과에 없는 내용을 추측해서 채우지 않는다. 스캔 PDF처럼 텍스트가 비면 "텍스트 추출 실패(OCR 필요)"로 보고한다.
- Logos 유료 자료의 대량 변환·스크래핑 금지 (CLAUDE.md 보안 규칙 준수). 공식 Copy/Export로 확보한 자료만 변환한다.
- 개인정보가 담긴 문서는 익명화 전 변환 결과를 공유·커밋하지 않는다.
