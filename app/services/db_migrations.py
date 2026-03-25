from __future__ import annotations

import sqlite3
from pathlib import Path


PERSONA_COLUMN_DEFS: dict[str, str] = {
    "occupation_category": "VARCHAR DEFAULT ''",
    "region": "VARCHAR DEFAULT ''",
    "household_type": "VARCHAR DEFAULT ''",
    "buy_channel": "VARCHAR DEFAULT ''",
    "product_group": "VARCHAR DEFAULT ''",
}

SURVEY_QUESTION_COLUMN_DEFS: dict[str, str] = {
    "generation_source": "VARCHAR DEFAULT ''",
    "ai_rationale": "TEXT DEFAULT ''",
    "ai_evidence": "JSON DEFAULT '[]'",
}


def _derive_occupation_category(occupation: str, age: int) -> str:
    occupation_lower = (occupation or "").lower()
    if age <= 24:
        return "학생"
    if any(keyword in occupation_lower for keyword in ("개발", "디자인", "연구", "컨설턴트", "architect")):
        return "전문직"
    if any(keyword in occupation_lower for keyword in ("사업", "자영업", "대표")):
        return "자영업자"
    if any(keyword in occupation_lower for keyword in ("프리랜서", "유튜버", "크리에이터")):
        return "프리랜서"
    return "직장인"


def _derive_region(age: int, segment: str) -> str:
    if "비즈니스" in segment or age >= 40:
        return "대한민국"
    if "게이밍" in segment:
        return "일본"
    if "프리미엄" in segment:
        return "미국"
    return "대한민국"


def _derive_household_type(age: int, segment: str) -> str:
    if age <= 24:
        return "1인 가구"
    if "실용 중시 가족형" in segment:
        return "3인 이상"
    if age >= 38:
        return "2인 가구"
    return "1인 가구"


def _derive_buy_channel(preferred_channel: str) -> str:
    channel_map = {
        "YouTube": "자급제",
        "Instagram": "공식몰",
        "TikTok": "통신사 대리점",
        "LinkedIn": "오프라인 유통",
    }
    return channel_map.get(preferred_channel, "공식몰")


def _derive_product_group(purchase_history: str) -> str:
    device = (purchase_history or "").lower()
    if "fold" in device:
        return "Galaxy Z Fold"
    if "flip" in device:
        return "Galaxy Z Flip"
    if "ultra" in device:
        return "Galaxy S Ultra"
    if "s24+" in device or "s23+" in device:
        return "Galaxy S Plus"
    if "a55" in device or "a34" in device or "a35" in device:
        return "Galaxy A"
    return "Galaxy S"


def ensure_sqlite_persona_dimensions(db_path: str | Path) -> bool:
    path = Path(db_path)
    if not path.exists():
        return False

    with sqlite3.connect(path) as conn:
        cursor = conn.cursor()
        columns = {
            row[1]
            for row in cursor.execute("PRAGMA table_info(personas)").fetchall()
        }
        if not columns:
            return False

        added = False
        for column_name, definition in PERSONA_COLUMN_DEFS.items():
            if column_name not in columns:
                cursor.execute(f"ALTER TABLE personas ADD COLUMN {column_name} {definition}")
                added = True

        rows = cursor.execute(
            """
            SELECT id, age, occupation, segment, preferred_channel, purchase_history,
                   occupation_category, region, household_type, buy_channel, product_group
            FROM personas
            """
        ).fetchall()

        for row in rows:
            persona_id, age, occupation, segment, preferred_channel, purchase_history, occupation_category, region, household_type, buy_channel, product_group = row
            purchase_history_text = purchase_history or ""
            if not occupation_category:
                cursor.execute(
                    "UPDATE personas SET occupation_category = ? WHERE id = ?",
                    (_derive_occupation_category(occupation or "", age or 0), persona_id),
                )
            if not region:
                cursor.execute(
                    "UPDATE personas SET region = ? WHERE id = ?",
                    (_derive_region(age or 0, segment or ""), persona_id),
                )
            if not household_type:
                cursor.execute(
                    "UPDATE personas SET household_type = ? WHERE id = ?",
                    (_derive_household_type(age or 0, segment or ""), persona_id),
                )
            if not buy_channel:
                cursor.execute(
                    "UPDATE personas SET buy_channel = ? WHERE id = ?",
                    (_derive_buy_channel(preferred_channel or ""), persona_id),
                )
            if not product_group:
                cursor.execute(
                    "UPDATE personas SET product_group = ? WHERE id = ?",
                    (_derive_product_group(purchase_history_text), persona_id),
                )

        conn.commit()
        return added or bool(rows)


def ensure_sqlite_survey_question_metadata(db_path: str | Path) -> bool:
    path = Path(db_path)
    if not path.exists():
        return False

    with sqlite3.connect(path) as conn:
        cursor = conn.cursor()
        columns = {
            row[1]
            for row in cursor.execute("PRAGMA table_info(survey_questions)").fetchall()
        }
        if not columns:
            return False

        added = False
        for column_name, definition in SURVEY_QUESTION_COLUMN_DEFS.items():
            if column_name not in columns:
                cursor.execute(f"ALTER TABLE survey_questions ADD COLUMN {column_name} {definition}")
                added = True

        conn.commit()
        return added
