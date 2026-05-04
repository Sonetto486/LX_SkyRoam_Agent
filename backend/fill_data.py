import asyncio
from app.core.database import AsyncSessionLocal
from app.models.travel_plan import TravelPlan, TravelPlanItem
from app.models.destination import Topic
from sqlalchemy import select

async def fill():
    async with AsyncSessionLocal() as db:
        try:
            # Topic 2
            topic = await db.get(Topic, 2)
            if topic:
                topic.intro = '这里是京都古寺巡礼的详细描述。包含了清水寺、金阁寺等著名寺庙的详细游览路线和历史背景介绍。这是一个专注于日本历史与佛教文化的深度体验专题。'
                print("Updated topic 2")
                
            # Plan 7
            plan = await db.get(TravelPlan, 7)
            if plan:
                plan.description = '这是一个丰富多彩的华东5日经典连线游。包含所有的交通、住宿与景点安排。'
                plan.is_public = True
                plan.status = 'completed'
                print("Updated plan 7")
                
                # Check if it has items
                res = await db.execute(select(TravelPlanItem).where(TravelPlanItem.travel_plan_id == 7))
                items = res.scalars().all()
                if not items:
                    db.add(TravelPlanItem(travel_plan_id=7, title='第一天：到达与休整', item_type='transport'))
                    db.add(TravelPlanItem(travel_plan_id=7, title='第二天：城市观光', item_type='attraction'))
                    print("Added items for plan 7")
            
            await db.commit()
            print("Done!")
        except Exception as e:
            print("Failed:", e)
            await db.rollback()

if __name__ == "__main__":
    asyncio.run(fill())