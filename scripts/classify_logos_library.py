"""
classify_logos_library.py — Logos 자료 분류기

logos_library_inventory.csv를 읽어 장르별·우선순위별로 분류하여
logos_library_classified.csv를 생성한다.

사용법:
    python scripts/classify_logos_library.py
    python scripts/classify_logos_library.py --inventory data/logos_library_inventory.csv
    python scripts/classify_logos_library.py --force
"""

from __future__ import annotations

import argparse
import csv
import shutil
from datetime import datetime
from pathlib import Path


# 자동 분류 규칙
GENRE_RULES = {
    "bibles": {
        "genre_gospel": True,
        "genre_epistle": True,
        "genre_ot_narrative": True,
        "genre_psalm_wisdom": True,
        "genre_prophetic": True,
        "genre_law": True,
    },
    "commentaries": {
        "exegetical": {
            "gospel_keywords": ["Matthew", "Mark", "Luke", "John", "마태", "마가", "누가", "요한"],
            "epistle_keywords": ["Romans", "Corinthians", "Galatians", "Ephesians", "Philippians",
                                 "Colossians", "Thessalonians", "Timothy", "Titus", "Hebrews",
                                 "로마서", "고린도", "갈라디아", "에베소", "빌립보"],
            "ot_keywords": ["Genesis", "Exodus", "Joshua", "Judges", "Samuel", "Kings", "Chronicles",
                             "창세기", "출애굽기", "여호수아", "사사기", "사무엘"],
            "psalm_keywords": ["Psalms", "Proverbs", "Ecclesiastes", "Job", "시편", "잠언"],
            "prophetic_keywords": ["Isaiah", "Jeremiah", "Ezekiel", "Daniel", "Revelation",
                                    "이사야", "예레미야", "에스겔", "다니엘", "요한계시록"],
            "law_keywords": ["Leviticus", "Numbers", "Deuteronomy", "레위기", "민수기", "신명기"],
        }
    },
}

TIER_RULES = {
    "bibles": 1,
    "original_language": 1,
    "commentaries": {
        "exegetical": 1,
        "expository": 2,
        "devotional": 3,
        "korean": 2,
        "classical": 2,
    },
    "biblical_theology": 2,
    "systematic_theology": 1,
    "background": 2,
    "sermon_ministry": 3,
}

PRIORITY_SCORE_BASE = {
    1: 95,
    2: 80,
    3: 65,
}


def classify_row(row: dict) -> dict:
    """단일 자료 행을 분류하여 확장된 딕셔너리 반환."""
    category = row.get("category", "")
    subcategory = row.get("subcategory", "")
    title = row.get("title", "")
    author = row.get("author", "")
    combined = f"{title} {author}".lower()

    # Tier 결정
    tier = 2
    if category in TIER_RULES:
        tier_val = TIER_RULES[category]
        if isinstance(tier_val, dict):
            tier = tier_val.get(subcategory, 2)
        else:
            tier = tier_val

    # 장르 적용 가능성 결정
    genre_gospel = "no"
    genre_epistle = "no"
    genre_ot_narrative = "no"
    genre_psalm_wisdom = "no"
    genre_prophetic = "no"
    genre_law = "no"

    if category == "bibles":
        genre_gospel = "yes"
        genre_epistle = "yes"
        genre_ot_narrative = "yes"
        genre_psalm_wisdom = "yes"
        genre_prophetic = "yes"
        genre_law = "yes"
    elif category in ("original_language", "systematic_theology"):
        genre_gospel = "yes"
        genre_epistle = "yes"
        genre_ot_narrative = "yes"
        genre_psalm_wisdom = "yes"
        genre_prophetic = "yes"
        genre_law = "yes"
    elif category == "biblical_theology":
        genre_gospel = "yes"
        genre_epistle = "yes"
        genre_ot_narrative = "yes"
        genre_psalm_wisdom = "yes"
        genre_prophetic = "yes"
        genre_law = "yes"
    elif category == "background":
        nt_bg = subcategory in ("jewish_context", "greco_roman")
        ot_bg = subcategory in ("archaeology", "geography", "dictionaries")
        if nt_bg:
            genre_gospel = "yes"
            genre_epistle = "yes"
        if ot_bg or subcategory == "dictionaries":
            genre_ot_narrative = "yes"
            genre_psalm_wisdom = "yes"
            genre_prophetic = "yes"
            genre_law = "yes"
    elif category == "commentaries":
        rules = CATEGORY_KEYWORDS = {
            "gospel": ["matthew", "mark", "luke", "john", "gospel", "마태", "마가", "누가", "요한"],
            "epistle": ["romans", "corinthians", "galatians", "ephesians", "philippians",
                        "colossians", "thessalonians", "timothy", "titus", "hebrews", "james",
                        "peter", "로마서", "고린도", "갈라디아", "에베소", "히브리서", "야고보"],
            "ot_narrative": ["genesis", "exodus", "joshua", "judges", "ruth", "samuel", "kings",
                              "chronicles", "ezra", "esther", "창세기", "출애굽기", "사사기"],
            "psalm_wisdom": ["psalm", "proverb", "ecclesiastes", "job", "song", "시편", "잠언"],
            "prophetic": ["isaiah", "jeremiah", "ezekiel", "daniel", "revelation", "apocalyptic",
                           "이사야", "예레미야", "에스겔", "다니엘", "요한계시록"],
            "law": ["leviticus", "numbers", "deuteronomy", "레위기", "민수기", "신명기"],
        }
        for genre_key, keywords in rules.items():
            if any(kw in combined for kw in keywords):
                if genre_key == "gospel":
                    genre_gospel = "yes"
                elif genre_key == "epistle":
                    genre_epistle = "yes"
                elif genre_key == "ot_narrative":
                    genre_ot_narrative = "yes"
                elif genre_key == "psalm_wisdom":
                    genre_psalm_wisdom = "yes"
                elif genre_key == "prophetic":
                    genre_prophetic = "yes"
                elif genre_key == "law":
                    genre_law = "yes"

    # Priority score
    priority_score = PRIORITY_SCORE_BASE.get(tier, 60)

    result = dict(row)
    result.update({
        "tier": tier,
        "genre_gospel": genre_gospel,
        "genre_epistle": genre_epistle,
        "genre_ot_narrative": genre_ot_narrative,
        "genre_psalm_wisdom": genre_psalm_wisdom,
        "genre_prophetic": genre_prophetic,
        "genre_law": genre_law,
        "priority_score": priority_score,
    })
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="Logos 자료 분류기")
    parser.add_argument("--inventory", default="data/logos_library_inventory.csv")
    parser.add_argument("--output", default="data/logos_library_classified.csv")
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    inventory_path = Path(args.inventory)
    output_path = Path(args.output)

    if not inventory_path.exists():
        print(f"NG 인벤토리 파일 없음: {inventory_path}")
        return 1

    if output_path.exists() and not args.force:
        print(f"NG 출력 파일이 이미 있습니다. --force 사용: {output_path}")
        return 1

    # 읽기
    with inventory_path.open(encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
        fieldnames = reader.fieldnames or []

    print(f"OK 인벤토리 로드: {len(rows)}개 자료")

    # 백업
    if output_path.exists() and args.force:
        backup = output_path.with_suffix(".bak")
        shutil.copy2(output_path, backup)
        print(f"OK 백업: {backup}")

    # 분류
    classified = [classify_row(row) for row in rows]

    # 새 컬럼 목록
    new_fields = ["tier", "genre_gospel", "genre_epistle", "genre_ot_narrative",
                  "genre_psalm_wisdom", "genre_prophetic", "genre_law", "priority_score"]
    out_fields = [f for f in fieldnames if f not in new_fields] + new_fields

    # 쓰기
    temp_path = output_path.with_suffix(".tmp")
    with temp_path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=out_fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(classified)

    if output_path.exists():
        output_path.unlink()
    temp_path.rename(output_path)

    print(f"OK 분류 완료: {output_path}")
    print(f"   총 {len(classified)}개 / 1등급: {sum(1 for r in classified if str(r.get('tier')) == '1')}개")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
