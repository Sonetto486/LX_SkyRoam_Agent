"""检查数据库中的景点图片数据"""
import asyncio
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.database import get_async_session_local
from sqlalchemy import text

async def check():
    async_session = get_async_session_local()
    async with async_session() as db:
        # 检查野生动物园和迪士尼相关
        result = await db.execute(text("""
            SELECT name, city, image_url, image_source
            FROM attraction_details
            WHERE name LIKE '%野生动物%' OR name LIKE '%迪士尼%' OR name LIKE '%迪士尼%'
        """))
        rows = result.fetchall()
        print("=" * 100)
        print("野生动物园和迪士尼相关景点")
        print("=" * 100)
        for r in rows:
            print(f"景点: {r[0]}, 城市: {r[1]}")
            print(f"图片来源: {r[3]}")
            print(f"图片URL: {r[2][:80] if r[2] else 'None'}...")
            print("-" * 80)

if __name__ == "__main__":
    asyncio.run(check())
