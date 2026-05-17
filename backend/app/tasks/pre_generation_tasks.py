"""
预生成任务模块
负责定时/触发式生成热门城市的行程方案
"""

from celery import current_task
from app.core.celery import celery_app
from loguru import logger
from app.core.async_loop import run_coro
from datetime import datetime
import asyncio


@celery_app.task(bind=True)
def pre_generate_plans_task(self, destination_name: str = None, force: bool = False):
    """
    预生成方案任务

    Args:
        destination_name: 指定目的地，None表示生成所有热门城市
        force: 是否强制重新生成（忽略缓存）
    """
    async def run():
        from app.services.pre_generation_service import pre_generation_service

        if destination_name:
            # 单城市生成
            logger.info(f"开始预生成单城市方案: {destination_name}")
            result = await pre_generation_service.generate_for_destination(destination_name, force=force)
        else:
            # 批量生成所有热门城市
            logger.info("开始批量预生成所有热门城市方案")
            result = await pre_generation_service.generate_all_hot_destinations(force=force)

        logger.info(f"预生成任务完成: {result}")
        return result

    return run_coro(run())


@celery_app.task
def cleanup_expired_pre_plans_task():
    """清理过期的预生成方案"""
    async def run():
        from app.services.pre_generation_service import pre_generation_service
        result = await pre_generation_service.cleanup_expired_plans()
        logger.info(f"过期方案清理完成: {result}")
        return result

    return run_coro(run())


@celery_app.task
def update_pre_plan_statistics_task():
    """更新预生成方案的统计信息"""
    async def run():
        from app.services.pre_generation_service import pre_generation_service
        result = await pre_generation_service.get_status()
        logger.info(f"预生成状态更新: {result}")
        return result

    return run_coro(run())


@celery_app.task
def pre_generate_single_city_task(city_name: str, force: bool = False):
    """
    预生成单个城市方案（用于手动触发）

    Args:
        city_name: 城市名称
        force: 是否强制重新生成
    """
    async def run():
        from app.services.pre_generation_service import pre_generation_service
        logger.info(f"手动触发预生成: {city_name}")
        result = await pre_generation_service.generate_for_destination(city_name, force=force)
        return result

    return run_coro(run())
