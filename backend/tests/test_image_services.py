"""
测试 Wikimedia 和 Unsplash 图片获取功能
"""

import asyncio
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.tools.wikimedia_service import wikimedia_service
from app.tools.unsplash_service import unsplash_service
from app.tools.place_image_service import place_image_service
from loguru import logger


async def test_wikimedia():
    """测试 Wikimedia 图片搜索"""
    logger.info("=" * 50)
    logger.info("测试 Wikimedia Commons API")
    logger.info("=" * 50)

    test_cases = [
        ("故宫博物院", "北京", "Forbidden City"),
        ("外滩", "上海", "The Bund Shanghai"),
        ("西湖风景名胜区", "杭州", "West Lake Hangzhou"),
        ("兵马俑", "西安", "Terracotta Army"),
        ("宽窄巷子", "成都", "Kuanzhai Alley"),
        ("鼓浪屿", "厦门", "Gulangyu Island"),
        ("广州塔", "广州", "Canton Tower"),
    ]

    success_count = 0

    for name, city, english in test_cases:
        logger.info(f"\n搜索: {name} ({city})")

        image_url = await wikimedia_service.search_attraction_image(
            attraction_name=name,
            city=city,
            english_name=english
        )

        if image_url:
            logger.success(f"✅ 找到图片: {image_url[:80]}...")
            success_count += 1
        else:
            logger.warning(f"⚠️ 未找到图片")

    logger.info(f"\nWikimedia 测试完成: {success_count}/{len(test_cases)} 成功")
    return success_count


async def test_unsplash():
    """测试 Unsplash 图片搜索"""
    logger.info("\n" + "=" * 50)
    logger.info("测试 Unsplash API")
    logger.info("=" * 50)

    test_cities = ["北京", "上海", "杭州", "西安", "成都"]

    success_count = 0

    for city in test_cities:
        logger.info(f"\n搜索城市: {city}")

        # 测试静态兜底
        static_url = unsplash_service.get_static_fallback_for_city(city)
        logger.info(f"静态兜底: {static_url}")

        # 测试 API 搜索（如果有 API Key）
        api_url = await unsplash_service.search_travel_image(city)
        if api_url:
            logger.success(f"✅ API 图片: {api_url[:80]}...")
            success_count += 1
        else:
            logger.warning(f"⚠️ API 未返回图片，使用静态兜底")

    logger.info(f"\nUnsplash 测试完成")
    return success_count


async def test_place_image_service():
    """测试 PlaceImageService 的 get_best_image 方法"""
    logger.info("\n" + "=" * 50)
    logger.info("测试 PlaceImageService.get_best_image")
    logger.info("=" * 50)

    test_cases = [
        ("故宫博物院", "北京"),
        ("外滩", "上海"),
        ("西湖", "杭州"),
        ("兵马俑", "西安"),
        ("宽窄巷子", "成都"),
    ]

    for name, city in test_cases:
        logger.info(f"\n获取最佳图片: {name} ({city})")

        image_url = await place_image_service.get_best_image(
            attraction_name=name,
            city=city
        )

        logger.info(f"结果: {image_url[:80]}...")

        # 验证不是 picsum.photos
        if "picsum.photos" in image_url:
            logger.error(f"❌ 仍然使用 picsum.photos!")
        else:
            logger.success(f"✅ 使用真实图片")


async def main():
    """运行所有测试"""
    logger.info("开始测试景点图片获取功能\n")

    # 测试 Wikimedia
    wikimedia_success = await test_wikimedia()

    # 测试 Unsplash
    unsplash_success = await test_unsplash()

    # 测试 PlaceImageService
    await test_place_image_service()

    # 总结
    logger.info("\n" + "=" * 50)
    logger.info("测试总结")
    logger.info("=" * 50)
    logger.info(f"Wikimedia 成功: {wikimedia_success}")
    logger.info(f"Unsplash 成功: {unsplash_success}")

    # 关闭 HTTP 客户端
    await wikimedia_service.close()
    await unsplash_service.close()


if __name__ == "__main__":
    asyncio.run(main())