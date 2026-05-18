import asyncio
import json
from app.core.database import async_session
from sqlalchemy import text

async def check():
    async with async_session() as session:
        result = await session.execute(text("SELECT id, title, details FROM travel_plan_items WHERE travel_plan_id = 96 AND item_type = 'attraction' LIMIT 3"))
        rows = result.fetchall()
        for row in rows:
            print(f'ID: {row[0]}, Title: {row[1]}')
            details = row[2] if row[2] else {}
            print(f'  Details keys: {list(details.keys())}')
            print(f'  rating: {details.get("rating")}')
            print(f'  category: {details.get("category")}')
            print(f'  photos: {details.get("photos", [])[:2] if details.get("photos") else None}')
            print()

if __name__ == "__main__":
    asyncio.run(check())
