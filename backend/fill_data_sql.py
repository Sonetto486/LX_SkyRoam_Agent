import asyncio
from app.core.database import AsyncSessionLocal
from sqlalchemy import text

async def fill():
    async with AsyncSessionLocal() as db:
        try:
            await db.execute(text("UPDATE topic SET intro = '这里是京都古寺巡礼的详细描述。包含了清水寺、金阁寺等著名寺庙的详细游览路线和历史背景介绍。这是一个专注于日本历史与佛教文化的深度体验专题。' WHERE id = 2"))
            await db.execute(text("UPDATE travel_plans SET description = '这是一个丰富多彩的华东5日经典连线游。包含所有的交通、住宿与景点安排。', is_public = true, status = 'completed' WHERE id = 7"))
            
            # Use raw SQL, travel_plan_items uses is_active
            await db.execute(text("INSERT INTO travel_plan_items (travel_plan_id, title, item_type, is_active, created_at, updated_at) VALUES (7, '第一天：到达与休整', 'transport', true, NOW(), NOW()) ON CONFLICT DO NOTHING"))
            await db.execute(text("INSERT INTO travel_plan_items (travel_plan_id, title, item_type, is_active, created_at, updated_at) VALUES (7, '第二天：城市观光', 'attraction', true, NOW(), NOW()) ON CONFLICT DO NOTHING"))

            await db.commit()
            print("Successfully populated missing data via SQL!")
        except Exception as e:
            print("Failed:", e)
            await db.rollback()

if __name__ == "__main__":
    asyncio.run(fill())