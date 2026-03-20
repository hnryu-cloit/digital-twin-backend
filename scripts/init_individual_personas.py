import asyncio
import json
import os
import sys

# Add the app directory to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.database import engine, Base
from app.models.individual_persona import IndividualPersona
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import sessionmaker

JSON_PATH = "../digital-twin-ai/scripts/output/detailed_personas_1000.json"

async def init_db():
    print("Initializing database...")
    async with engine.begin() as conn:
        # Create tables
        await conn.run_sync(Base.metadata.create_all)
    print("Tables created.")

async def load_data():
    if not os.path.exists(JSON_PATH):
        print(f"Error: {JSON_PATH} not found.")
        return

    print(f"Loading data from {JSON_PATH}...")
    with open(JSON_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)

    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as session:
        print(f"Inserting {len(data)} personas...")
        for item in data:
            # Prepare data
            all_data = {k: v for k, v in item.items()}
            
            persona = IndividualPersona(
                index=item["index"],
                name=item.get("name"),
                job=item.get("job"),
                personality=item.get("personality"),
                samsung_experience=item.get("samsung_experience"),
                age=item["usr_age"],
                gender=item["usr_gndr"],
                all_data=all_data
            )
            session.add(persona)
        
        await session.commit()
    print("Data loading completed.")

async def main():
    await init_db()
    await load_data()

if __name__ == "__main__":
    asyncio.run(main())
