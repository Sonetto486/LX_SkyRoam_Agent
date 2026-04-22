import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy import text
from sqlalchemy.orm import sessionmaker
import sys
import os

# 使用容器内部的数据库连接 URL
DATABASE_URL = "postgresql+asyncpg://postgres:123456@postgres:5432/skyroam"

engine = create_async_engine(DATABASE_URL, echo=False)
AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

async def seed_topics():
    async with AsyncSessionLocal() as session:
        print("开始清理并插入 Topic 数据...")
        # 清理旧数据，重启自增ID
        await session.execute(text("TRUNCATE TABLE topic_place RESTART IDENTITY CASCADE;"))
        await session.execute(text("TRUNCATE TABLE topic RESTART IDENTITY CASCADE;"))
        
        # 1. 插入专题 (Topic) - 完美复刻你在前端页面看到的那四张卡片
        topics = [
            {
                "name": "东京樱花季", 
                "intro": "东京最佳樱花观赏地点和时间推荐", 
                "cover_url": "https://picsum.photos/seed/tokyo1/800/600", 
                "region": "日本"
            },
            {
                "name": "京都古寺巡礼", 
                "intro": "探索京都最著名的寺庙和神社", 
                "cover_url": "https://picsum.photos/seed/kyoto/800/600", 
                "region": "日本"
            },
            {
                "name": "北海道美食之旅", 
                "intro": "品尝北海道特色美食和温泉体验", 
                "cover_url": "https://picsum.photos/seed/hokkaido/800/600", 
                "region": "日本"
            },
            {
                "name": "大阪环球影城", 
                "intro": "环球影城游玩攻略和快速通行证使用技巧", 
                "cover_url": "https://picsum.photos/seed/usj/800/600", 
                "region": "日本"
            }
        ]
        
        for t in topics:
            await session.execute(text("""
                INSERT INTO topic (name, intro, cover_url, region)
                VALUES (:name, :intro, :cover_url, :region)
            """), t)
        
        # 2. 获取刚刚插入的专题ID
        result = await session.execute(text("SELECT id, name FROM topic"))
        topic_records = result.fetchall()
        
        # 3. 插入专题地点关联 (Topic Place) - 制造关联数据
        # 注意：这里 related_id=1,2 等我们借用了初始化 SQL 里的“北京、上海、天安门、故宫”的ID作为假数据来打通流程。
        for idx, r in enumerate(topic_records):
            topic_id = r.id
            places = [
                {
                    "topic_id": topic_id, 
                    "related_type": "destinations", 
                    "related_id": 1, 
                    "is_key_point": True, 
                    "highlight_info": f"【核心精选】这是《{r.name}》行程绝对不能错过的首选区域！", 
                    "order_index": 1
                },
                {
                    "topic_id": topic_id, 
                    "related_type": "attractions", 
                    "related_id": 2, 
                    "is_key_point": False, 
                    "highlight_info": f"非常适合打卡拍照的宝藏地点，可以安排在下午。", 
                    "order_index": 2
                }
            ]
            for p in places:
                await session.execute(text("""
                    INSERT INTO topic_place (topic_id, related_type, related_id, is_key_point, highlight_info, order_index)
                    VALUES (:topic_id, :related_type, :related_id, :is_key_point, :highlight_info, :order_index)
                """), p)
                
        await session.commit()

if __name__ == "__main__":
    asyncio.run(seed_topics())
