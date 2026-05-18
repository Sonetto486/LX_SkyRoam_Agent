"""
更新景点图片链接脚本

使用方法:
    # 查看某个景点的当前图片
    python scripts/update_attraction_image.py --name "故宫博物院" --city "北京"

    # 更新某个景点的图片链接
    python scripts/update_attraction_image.py --name "故宫博物院" --city "北京" --image-url "https://新的图片链接.jpg"

    # 批量更新（从JSON文件）
    python scripts/update_attraction_image.py --batch updates.json

JSON文件格式示例 (updates.json):
{
    "updates": [
        {
            "name": "故宫博物院",
            "city": "北京",
            "image_url": "https://新的图片链接.jpg"
        },
        {
            "name": "外滩",
            "city": "上海",
            "image_url": "https://新的图片链接.jpg"
        }
    ]
}
"""

import asyncio
import sys
import os
import json

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.database import get_async_session_local
from sqlalchemy import text, select
from loguru import logger
from app.models.attraction_detail import AttractionDetail


async def get_attraction_image(name: str, city: str):
    """查看景点的当前图片"""
    async_session = get_async_session_local()
    async with async_session() as db:
        result = await db.execute(text("""
            SELECT name, city, image_url, image_source
            FROM attraction_details
            WHERE name = :name AND city = :city
        """), {"name": name, "city": city})
        row = result.fetchone()
        if row:
            print("=" * 80)
            print(f"景点: {row[0]}")
            print(f"城市: {row[1]}")
            print(f"图片来源: {row[3]}")
            print(f"图片URL: {row[2]}")
            print("=" * 80)
        else:
            print(f"未找到景点: {name} ({city})")


async def update_attraction_image(name: str, city: str, image_url: str):
    """更新景点的图片链接"""
    async_session = get_async_session_local()
    async with async_session() as db:
        # 先检查是否存在
        query = select(AttractionDetail).where(
            AttractionDetail.name == name,
            AttractionDetail.city == city
        )
        result = await db.execute(query)
        existing = result.scalar_one_or_none()

        if existing:
            # 更新图片
            existing.image_url = image_url
            existing.image_source = "manual"
            await db.commit()
            logger.success(f"✅ 已更新 {name} ({city}) 的图片链接")
            print(f"新图片URL: {image_url}")
        else:
            # 创建新记录（使用 ORM 模型，时间戳自动填充）
            new_detail = AttractionDetail(
                name=name,
                destination=city,
                city=city,
                image_url=image_url,
                image_source="manual",
                source="manual",
                verified="verified",
                match_priority=100
            )
            db.add(new_detail)
            await db.commit()
            logger.success(f"✅ 已创建 {name} ({city}) 并设置图片链接")


async def batch_update(json_file: str):
    """批量更新图片链接"""
    with open(json_file, 'r', encoding='utf-8') as f:
        data = json.load(f)

    updates = data.get("updates", [])
    for item in updates:
        name = item.get("name")
        city = item.get("city")
        image_url = item.get("image_url")
        if name and city and image_url:
            await update_attraction_image(name, city, image_url)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="更新景点图片链接")
    parser.add_argument("--name", type=str, help="景点名称")
    parser.add_argument("--city", type=str, help="城市")
    parser.add_argument("--image-url", type=str, help="新的图片链接")
    parser.add_argument("--batch", type=str, help="批量更新JSON文件路径")

    args = parser.parse_args()

    if args.batch:
        asyncio.run(batch_update(args.batch))
    elif args.name and args.city:
        if args.image_url:
            asyncio.run(update_attraction_image(args.name, args.city, args.image_url))
        else:
            asyncio.run(get_attraction_image(args.name, args.city))
    else:
        parser.print_help()
        print("\n示例:")
        print("  # 查看景点图片")
        print("  python scripts/update_attraction_image.py --name '故宫博物院' --city '北京'")
        print("\n  # 更新景点图片")
        print("  python scripts/update_attraction_image.py --name '故宫博物院' --city '北京' --image-url 'https://新图片.jpg'")