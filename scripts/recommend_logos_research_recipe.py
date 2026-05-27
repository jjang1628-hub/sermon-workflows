"""
recommend_logos_research_recipe.py — Logos 연구 레시피 추천기

성경 본문과 운영 모드를 입력받아 어떤 Logos 도구를 어떤 순서로
사용해야 하는지 추천 리포트를 생성한다.

사용법:
    python scripts/recommend_logos_research_recipe.py --passage "요한복음 13:14"
    python scripts/recommend_logos_research_recipe.py --passage "시편 23:1" --mode deep
    python scripts/recommend_logos_research_recipe.py --passage "로마서 8:1" --mode standard --output output/research_packs/ro-8-1-logos-recipe.md
"""

from __future__ import annotations

import argparse
import re
from datetime import datetime
from pathlib import Path


# 장르 감지 규칙
GENRE_MAP = {
    "gospel": ["마태복음", "마가복음", "누가복음", "요한복음", "마 ", "막 ", "눅 ", "요 "],
    "epistle": ["로마서", "고린도전서", "고린도후서", "갈라디아서", "에베소서", "빌립보서",
                "골로새서", "데살로니가전서", "데살로니가후서", "디모데전서", "디모데후서",
                "디도서", "빌레몬서", "히브리서", "야고보서", "베드로전서", "베드로후서",
                "요한일서", "요한이서", "요한삼서", "유다서"],
    "psalm_wisdom": ["시편", "잠언", "전도서", "아가", "욥기"],
    "prophetic_apocalyptic": ["이사야", "예레미야", "예레미야애가", "에스겔", "다니엘",
                               "호세아", "요엘", "아모스", "오바댜", "요나", "미가",
                               "나훔", "하박국", "스바냐", "학개", "스가랴", "말라기",
                               "요한계시록"],
    "law_ritual": ["레위기", "민수기", "신명기"],
    "ot_narrative": ["창세기", "출애굽기", "여호수아", "사사기", "룻기",
                     "사무엘상", "사무엘하", "열왕기상", "열왕기하",
                     "역대상", "역대하", "에스라", "느헤미야", "에스더"],
}

GENRE_LABELS = {
    "gospel": "복음서 (Gospel)",
    "epistle": "서신서 (Epistle)",
    "psalm_wisdom": "시편·지혜 (Psalm/Wisdom)",
    "prophetic_apocalyptic": "예언·묵시 (Prophetic/Apocalyptic)",
    "law_ritual": "율법·의식 (Law/Ritual)",
    "ot_narrative": "구약 내러티브 (OT Narrative)",
}

# 장르별 연구 단계 (tool, focus, time_quick, time_standard, time_deep)
RECIPES = {
    "gospel": [
        ("Passage Guide", "Context, Literary Context 섹션", 5, 10, 15),
        ("Exegetical Guide", "헬라어 핵심 동사·명사 분석", 5, 15, 20),
        ("Bible Word Study", "핵심 단어 1–2개 심층 분석", 0, 10, 15),
        ("Cross-Reference", "구약 반향·인용 확인", 5, 10, 15),
        ("Factbook", "인물·지명·유대 배경", 0, 10, 15),
        ("Commentary (Carson/Keener)", "핵심 주석 2–3종 비교", 0, 10, 20),
    ],
    "epistle": [
        ("Exegetical Guide", "구문 구조 분석 — 주동사·종속절", 5, 15, 20),
        ("Bible Word Study", "신학 용어 집중 분석", 5, 15, 20),
        ("Passage Guide", "서신 논증 구조 파악", 5, 10, 15),
        ("Theology Guide", "교의학 연결 주제", 0, 10, 15),
        ("Cross-Reference", "동일 서신 내 반향·구약 배경", 0, 5, 10),
        ("Commentary (Moo/Schreiner)", "핵심 주석 비교", 0, 10, 20),
    ],
    "psalm_wisdom": [
        ("Exegetical Guide", "히브리어 시 구조 — 평행법·키아즘", 5, 15, 20),
        ("Bible Word Study", "감정·신뢰·하나님 호칭 단어", 5, 10, 15),
        ("Passage Guide", "장르 정보·표제 해설", 5, 10, 15),
        ("Cross-Reference", "신약 인용 확인 (메시아 시편)", 5, 10, 15),
        ("Factbook", "역사적 배경 (표제가 있는 경우)", 0, 5, 10),
    ],
    "prophetic_apocalyptic": [
        ("Cross-Reference", "반향 텍스트 전체 — 구약 내부+신약", 5, 15, 20),
        ("Factbook", "역사적 배경 — 예언 당시 상황", 5, 10, 15),
        ("Exegetical Guide", "상징·이미지 언어 히브리어 분석", 5, 10, 15),
        ("Theology Guide", "종말론·메시아·언약 회복 주제", 0, 10, 15),
        ("Bible Word Study", "핵심 예언 단어", 0, 5, 10),
    ],
    "law_ritual": [
        ("Factbook", "의식·제도·제사장직 배경", 5, 15, 20),
        ("Exegetical Guide", "히브리어 법령·의식 용어", 5, 15, 20),
        ("Theology Guide", "언약 신학 연결 — 율법의 기능", 0, 10, 15),
        ("Cross-Reference", "신약 성취 (히브리서·갈라디아서)", 5, 10, 15),
        ("Bible Word Study", "핵심 법령 단어 의미 변화", 0, 5, 10),
    ],
    "ot_narrative": [
        ("Passage Guide", "서사 흐름과 문맥 — 전후 챕터 관계", 5, 10, 15),
        ("Factbook", "인물·지명·제도·문화 배경", 5, 15, 20),
        ("Bible Word Study", "히브리어 핵심 서사 단어", 0, 10, 15),
        ("Cross-Reference", "신약 인용·반향·성취 확인", 5, 10, 15),
        ("Exegetical Guide", "히브리어 문법 핵심 포인트", 0, 10, 15),
    ],
}

KEY_QUESTIONS = {
    "gospel": [
        "이 사건/말씀이 예수님의 메시아 정체성과 어떻게 연결되는가?",
        "구약의 어떤 주제나 예언이 성취되는가?",
        "제자들 또는 청중의 반응은 무엇을 드러내는가?",
    ],
    "epistle": [
        "저자의 논증의 핵심 전제는 무엇인가?",
        "명령(imperative)의 근거(indicative)는 무엇인가?",
        "이 서신의 교회 상황이 이 구절에 어떻게 영향을 미치는가?",
    ],
    "psalm_wisdom": [
        "이 시의 감정적 궤도는 무엇인가 (탄식→신뢰, 찬양→확신 등)?",
        "신약이 이 시를 어떻게 인용하는가?",
        "오늘 성도의 어떤 감정 상황에서 이 시가 울림을 갖는가?",
    ],
    "prophetic_apocalyptic": [
        "이 예언의 역사적 성취와 종말론적 성취는 어떻게 구분되는가?",
        "이 상징/이미지가 청중에게 어떤 신학적 메시지를 전달하는가?",
        "이 예언이 그리스도의 사역과 어떻게 연결되는가?",
    ],
    "law_ritual": [
        "이 율법/의식이 무엇을 가리키고 있는가?",
        "그리스도 안에서 이 율법은 어떻게 성취되었는가?",
        "이 율법의 영구적 원리는 무엇이며 일시적 형식은 무엇인가?",
    ],
    "ot_narrative": [
        "이 인물의 실패 또는 성공이 인간의 어떤 보편적 문제를 드러내는가?",
        "하나님의 개입이 어떻게 묘사되는가?",
        "이 서사가 신약의 어떤 성취를 가리키는가?",
    ],
}

MODE_TIME = {
    "quick": 0,    # index in tuple
    "standard": 1,
    "deep": 2,
}


def detect_genre(passage: str) -> str:
    for genre, keywords in GENRE_MAP.items():
        if any(kw in passage for kw in keywords):
            return genre
    return "gospel"  # 기본값


def slugify(passage: str) -> str:
    table = {
        "창세기": "ge", "출애굽기": "ex", "레위기": "le", "민수기": "nu",
        "신명기": "dt", "여호수아": "jos", "사사기": "jdg", "룻기": "ru",
        "사무엘상": "1sa", "사무엘하": "2sa", "열왕기상": "1ki", "열왕기하": "2ki",
        "역대상": "1ch", "역대하": "2ch", "에스라": "ezr", "느헤미야": "ne",
        "에스더": "est", "욥기": "job", "시편": "ps", "잠언": "pr",
        "전도서": "ec", "아가": "ss", "이사야": "is", "예레미야": "je",
        "예레미야애가": "la", "에스겔": "eze", "다니엘": "da", "호세아": "ho",
        "요엘": "joe", "아모스": "am", "오바댜": "ob", "요나": "jon",
        "미가": "mic", "나훔": "na", "하박국": "hab", "스바냐": "zep",
        "학개": "hag", "스가랴": "zec", "말라기": "mal",
        "마태복음": "mt", "마가복음": "mk", "누가복음": "lk", "요한복음": "jn",
        "사도행전": "ac", "로마서": "ro", "고린도전서": "1co", "고린도후서": "2co",
        "갈라디아서": "ga", "에베소서": "eph", "빌립보서": "php", "골로새서": "col",
        "데살로니가전서": "1th", "데살로니가후서": "2th", "디모데전서": "1ti",
        "디모데후서": "2ti", "디도서": "tit", "빌레몬서": "phm", "히브리서": "heb",
        "야고보서": "jas", "베드로전서": "1pe", "베드로후서": "2pe",
        "요한일서": "1jn", "요한이서": "2jn", "요한삼서": "3jn",
        "유다서": "jude", "요한계시록": "re",
    }
    slug = passage
    for korean, abbr in table.items():
        if korean in passage:
            slug = passage.replace(korean, abbr)
            break
    slug = re.sub(r"[:\s]+", "-", slug)
    slug = re.sub(r"[^a-zA-Z0-9\-]", "", slug)
    return slug.strip("-").lower() or "passage"


def build_recipe_report(passage: str, genre: str, mode: str) -> str:
    steps = RECIPES.get(genre, RECIPES["gospel"])
    time_idx = MODE_TIME.get(mode, 1)
    questions = KEY_QUESTIONS.get(genre, [])
    genre_label = GENRE_LABELS.get(genre, genre)
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    total_time = sum(s[2 + time_idx] for s in steps)

    lines = [
        f"# Logos 연구 레시피 — {passage}",
        f"",
        f"> 생성일시: {timestamp}  ",
        f"> 운영 모드: {mode.upper()}  ",
        f"> 예상 소요시간: 약 {total_time}분  ",
        f"",
        f"---",
        f"",
        f"## 장르 분류",
        f"",
        f"- **감지된 장르**: {genre_label}",
        f"- **Logos 연구 전략**: {genre_label} 최적화 단계 적용",
        f"",
        f"---",
        f"",
        f"## 연구 단계 ({mode.upper()} 모드)",
        f"",
    ]

    for i, (tool, focus, t_quick, t_std, t_deep) in enumerate(steps, 1):
        time_min = (t_quick, t_std, t_deep)[time_idx]
        if time_min == 0:
            if mode == "quick":
                continue
            time_str = f"{time_min}분 (선택)"
        else:
            time_str = f"{time_min}분"

        lines += [
            f"### {i}단계: {tool} ({time_str})",
            f"- **Logos 도구**: {tool}",
            f"- **집중 포인트**: {focus}",
            f"",
        ]

    lines += [
        f"---",
        f"",
        f"## 핵심 연구 질문",
        f"",
    ]
    for q in questions:
        lines.append(f"- {q}")

    lines += [
        f"",
        f"---",
        f"",
        f"## 캡처 체크리스트",
        f"",
        f"캡처 후 `scripts/validate_logos_capture.py`로 검증:  ",
        f"- [ ] 성경 원문 (개역개정 + 원어 1종)",
        f"- [ ] Passage Guide 핵심 섹션",
        f"- [ ] 주석 1–3종 핵심 부분",
        f"- [ ] 원어 단어 연구 (핵심 1–2개)",
        f"- [ ] 교차 참조",
        f"",
        f"---",
        f"",
        f"## 다음 단계",
        f"",
        f"```powershell",
        f"# 캡처 완료 후 실행:",
        f"python scripts\\validate_logos_capture.py --capture tmp\\logos-capture\\raw\\<파일명>.md",
        f"python scripts\\run_logos_max_research.py --passage \"{passage}\" --mode {mode}",
        f"```",
        f"",
        f"---",
        f"",
        f"⚠️ 이 레시피는 연구 보조 자료입니다. 최종 설교는 목사님이 직접 작성하세요.",
    ]

    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Logos 연구 레시피 추천기")
    parser.add_argument("--passage", required=True, help="성경 본문 (예: 요한복음 13:14)")
    parser.add_argument("--mode", choices=["quick", "standard", "deep", "expert"], default="standard")
    parser.add_argument("--genre", default=None, help="장르 강제 지정 (자동 감지 무시)")
    parser.add_argument("--output", default=None, help="출력 파일 경로")
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    # 장르 감지
    genre = args.genre or detect_genre(args.passage)
    if genre not in RECIPES:
        genre = "gospel"

    print(f"OK 본문: {args.passage}")
    print(f"OK 장르: {GENRE_LABELS.get(genre, genre)}")
    print(f"OK 모드: {args.mode.upper()}")

    # 출력 경로
    if args.output:
        output_path = Path(args.output)
    else:
        slug = slugify(args.passage)
        mode_str = args.mode if args.mode != "expert" else "deep"
        output_path = Path("output/research_packs") / f"{slug}-logos-recipe.md"

    if output_path.exists() and not args.force:
        print(f"NG 출력 파일이 이미 있습니다. --force 사용: {output_path}")
        return 1

    output_path.parent.mkdir(parents=True, exist_ok=True)

    # 레포트 생성
    report = build_recipe_report(args.passage, genre, args.mode)

    import shutil
    if output_path.exists() and args.force:
        backup = output_path.with_suffix(".bak")
        shutil.copy2(output_path, backup)

    temp = output_path.with_suffix(".tmp")
    temp.write_text(report, encoding="utf-8")
    if output_path.exists():
        output_path.unlink()
    temp.rename(output_path)

    print(f"OK 레시피 저장: {output_path}")
    print(f"   크기: {output_path.stat().st_size:,}바이트")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
