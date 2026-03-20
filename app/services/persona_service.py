import json
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.persona import Persona


async def get_personas_by_project(db: AsyncSession, project_id: int) -> list[Persona]:
    result = await db.execute(select(Persona).where(Persona.project_id == project_id))
    return list(result.scalars().all())


def load_personas_from_json() -> list[dict]:
    path = Path(settings.PERSONAS_JSON_PATH)
    if not path.exists():
        return []
    with path.open(encoding="utf-8") as file:
        return json.load(file)


async def seed_personas_from_json(db: AsyncSession, project_id: int) -> int:
    existing = await get_personas_by_project(db, project_id)
    if existing:
        return len(existing)

    personas_data = load_personas_from_json()
    for p in personas_data:
        db.add(Persona(
            project_id=project_id,
            cluster_id=p["cluster_id"],
            persona_name=p["persona_name"],
            persona_name_en=p["persona_name_en"],
            age_range=p["age_range"],
            description=p["description"],
            key_characteristics=p["key_characteristics"],
            keywords=p["keywords"],
            interests=p["interests"],
            segment_tags=p["segment_tags"],
            preferred_channel=p["preferred_channel"],
            purchase_intent=p["purchase_intent"],
            brand_attitude=p["brand_attitude"],
            marketing_acceptance=p["marketing_acceptance"],
            future_value=p["future_value"],
            churn_risk=p["churn_risk"],
            size=p["size"],
        ))
    await db.commit()
    return len(personas_data)
