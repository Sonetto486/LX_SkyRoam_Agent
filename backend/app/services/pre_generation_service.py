"""
预生成核心服务
负责生成热门城市的预生成行程方案
"""

from typing import List, Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, delete
from loguru import logger
from datetime import datetime, timedelta
import asyncio
import json

from app.core.config import settings
from app.core.database import async_session
from app.models.pre_generated_plan import PreGeneratedPlan
from app.models.hot_destination import HotDestination
from app.services.plan_generator import PlanGenerator
from app.services.data_collector import DataCollector


class PreGenerationService:
    """预生成服务"""

    def __init__(self):
        self.plan_generator = PlanGenerator()
        self.data_collector = DataCollector()

    async def generate_for_destination(
        self,
        destination: str,
        force: bool = False,
        duration_configs: List[Dict[str, int]] = None,
        budget_levels: List[str] = None,
        preference_combos: List[List[str]] = None
    ) -> Dict[str, Any]:
        """
        为单个目的地生成预生成方案

        Args:
            destination: 目的地城市名
            force: 是否强制重新生成（忽略缓存）
            duration_configs: 天数配置列表
            budget_levels: 预算等级列表
            preference_combos: 偏好组合列表

        Returns:
            生成结果统计
        """
        # 默认配置
        if duration_configs is None:
            duration_configs = [
                {"min": 1, "max": 3, "default": 2},
                {"min": 4, "max": 7, "default": 5},
                {"min": 8, "max": 14, "default": 10},
            ]

        if budget_levels is None:
            budget_levels = ["economy", "comfortable", "luxury"]

        if preference_combos is None:
            preference_combos = [
                ["culture"],
                ["nature"],
                ["food"],
                ["culture", "nature"],
                ["food", "shopping"],
                ["relaxation"],
            ]

        results = []
        errors = []

        async with async_session() as db:
            db: AsyncSession = db

            for duration_config in duration_configs:
                for budget in budget_levels:
                    for prefs in preference_combos:
                        try:
                            # 检查是否已存在且未过期
                            if not force:
                                existing = await self._check_existing(
                                    db, destination, duration_config["default"], budget, prefs
                                )
                                if existing:
                                    logger.debug(f"跳过已存在的方案: {destination}, {duration_config['default']}天, {budget}")
                                    continue

                            # 生成方案
                            plan_data = await self._generate_single_plan(
                                destination=destination,
                                duration_days=duration_config["default"],
                                budget_level=budget,
                                preferences=prefs
                            )

                            if plan_data:
                                await self._save_pre_generated_plan(
                                    db=db,
                                    destination=destination,
                                    plan_data=plan_data,
                                    duration_days=duration_config["default"],
                                    budget_level=budget,
                                    preferences=prefs
                                )
                                results.append({
                                    "duration": duration_config["default"],
                                    "budget": budget,
                                    "preferences": prefs,
                                    "status": "success"
                                })
                            else:
                                errors.append({
                                    "duration": duration_config["default"],
                                    "budget": budget,
                                    "preferences": prefs,
                                    "error": "生成失败"
                                })

                        except Exception as e:
                            logger.error(f"生成方案失败: {destination}, {duration_config['default']}天, {budget} - {e}")
                            errors.append({
                                "duration": duration_config["default"],
                                "budget": budget,
                                "preferences": prefs,
                                "error": str(e)
                            })

                            # 限制并发，避免API限流
                            await asyncio.sleep(2)

            # 更新热门城市状态
            await self._update_hot_destination_status(db, destination, len(results))

        return {
            "destination": destination,
            "generated_count": len(results),
            "error_count": len(errors),
            "results": results,
            "errors": errors
        }

    async def generate_all_hot_destinations(
        self,
        force: bool = False,
        limit: int = None
    ) -> Dict[str, Any]:
        """
        批量生成所有热门城市的预生成方案

        Args:
            force: 是否强制重新生成
            limit: 限制处理的城市数量（用于测试）

        Returns:
            批量生成结果统计
        """
        async with async_session() as db:
            db: AsyncSession = db

            # 获取启用的热门城市，按优先级排序
            query = select(HotDestination).where(
                HotDestination.is_enabled == True,
                HotDestination.is_active == True
            ).order_by(HotDestination.priority.asc())

            if limit:
                query = query.limit(limit)

            result = await db.execute(query)
            destinations = result.scalars().all()

        total = len(destinations)
        success_count = 0
        error_count = 0
        results = []

        # 分批处理，避免并发过高
        batch_size = settings.PRE_GENERATION_BATCH_SIZE

        for i in range(0, total, batch_size):
            batch = destinations[i:i + batch_size]
            logger.info(f"处理批次 {i // batch_size + 1}/{(total + batch_size - 1) // batch_size}")

            # 并发生成（限制并发数）
            semaphore = asyncio.Semaphore(settings.PRE_GENERATION_CONCURRENT_LIMIT)

            async def generate_with_limit(dest):
                async with semaphore:
                    try:
                        result = await self.generate_for_destination(
                            destination=dest.city_name,
                            force=force
                        )
                        return result
                    except Exception as e:
                        logger.error(f"生成 {dest.city_name} 失败: {e}")
                        return {"destination": dest.city_name, "error": str(e)}

            batch_results = await asyncio.gather(*[generate_with_limit(dest) for dest in batch])

            for r in batch_results:
                if "error" in r:
                    error_count += 1
                else:
                    success_count += 1
                results.append(r)

            # 批次间休息
            if i + batch_size < total:
                await asyncio.sleep(10)

        return {
            "total_destinations": total,
            "success_count": success_count,
            "error_count": error_count,
            "results": results
        }

    async def _generate_single_plan(
        self,
        destination: str,
        duration_days: int,
        budget_level: str,
        preferences: List[str]
    ) -> Optional[Dict[str, Any]]:
        """
        生成单个方案（调用现有生成流程）
        """
        try:
            # 构建模拟的旅行计划数据
            start_date = datetime.now() + timedelta(days=7)
            end_date = start_date + timedelta(days=duration_days - 1)

            # 构建偏好数据
            pref_data = {
                "travelPreferences": preferences,
                "budgetLevel": budget_level,
            }

            # 收集数据
            raw_data = await self.data_collector.collect_attraction_data(
                destination=destination,
                start_date=start_date,
                end_date=end_date
            )

            if not raw_data:
                logger.warning(f"未收集到景点数据: {destination}")
                return None

            # 生成简化的方案模板
            plan_template = {
                "destination": destination,
                "duration_days": duration_days,
                "budget_level": budget_level,
                "preferences": preferences,
                "attractions": raw_data[:duration_days * 4],  # 每天4个景点
                "generated_at": datetime.utcnow().isoformat(),
            }

            return plan_template

        except Exception as e:
            logger.error(f"生成方案失败: {destination} - {e}")
            return None

    async def _save_pre_generated_plan(
        self,
        db: AsyncSession,
        destination: str,
        plan_data: Dict[str, Any],
        duration_days: int,
        budget_level: str,
        preferences: List[str]
    ):
        """保存预生成方案"""
        expires_at = datetime.utcnow() + timedelta(days=settings.PRE_GENERATION_EXPIRE_DAYS)

        plan = PreGeneratedPlan(
            destination_name=destination,
            plan_template=plan_data,
            duration_days=duration_days,
            budget_level=budget_level,
            travel_preferences=preferences,
            status="active",
            expires_at=expires_at,
            generation_version="1.0",
            data_sources={"poi": True, "amap": True}
        )

        db.add(plan)
        await db.commit()
        logger.info(f"保存预生成方案: {destination}, {duration_days}天, {budget_level}")

    async def _check_existing(
        self,
        db: AsyncSession,
        destination: str,
        duration_days: int,
        budget_level: str,
        preferences: List[str]
    ) -> bool:
        """检查是否已存在有效的预生成方案"""
        query = select(PreGeneratedPlan).where(
            and_(
                PreGeneratedPlan.destination_name == destination,
                PreGeneratedPlan.duration_days == duration_days,
                PreGeneratedPlan.budget_level == budget_level,
                PreGeneratedPlan.status == "active",
                or_(
                    PreGeneratedPlan.expires_at.is_(None),
                    PreGeneratedPlan.expires_at > datetime.utcnow()
                )
            )
        )

        result = await db.execute(query)
        return result.scalar_one_or_none() is not None

    async def _update_hot_destination_status(
        self,
        db: AsyncSession,
        destination: str,
        generated_count: int
    ):
        """更新热门城市状态"""
        query = select(HotDestination).where(HotDestination.city_name == destination)
        result = await db.execute(query)
        hot_dest = result.scalar_one_or_none()

        if hot_dest:
            hot_dest.pre_generated_count += generated_count
            hot_dest.last_pre_generated_at = datetime.utcnow()
            await db.commit()

    async def cleanup_expired_plans(self) -> Dict[str, int]:
        """清理过期的预生成方案"""
        async with async_session() as db:
            db: AsyncSession = db

            # 查找过期方案
            query = select(PreGeneratedPlan).where(
                and_(
                    PreGeneratedPlan.expires_at < datetime.utcnow(),
                    PreGeneratedPlan.status == "active"
                )
            )

            result = await db.execute(query)
            expired_plans = result.scalars().all()

            # 标记为过期
            count = 0
            for plan in expired_plans:
                plan.status = "deprecated"
                count += 1

            await db.commit()

        logger.info(f"清理过期方案: {count} 个")
        return {"expired_count": count}

    async def get_status(self) -> Dict[str, Any]:
        """获取预生成状态"""
        async with async_session() as db:
            db: AsyncSession = db

            # 统计热门城市
            total_destinations = await db.execute(
                select(HotDestination).where(HotDestination.is_enabled == True)
            )
            total_destinations_count = len(total_destinations.scalars().all())

            # 统计已生成城市
            generated_result = await db.execute(
                select(PreGeneratedPlan.destination_name).distinct()
            )
            generated_destinations = len(generated_result.scalars().all())

            # 统计方案数量
            total_plans = await db.execute(
                select(PreGeneratedPlan)
            )
            total_plans_count = len(total_plans.scalars().all())

            active_plans = await db.execute(
                select(PreGeneratedPlan).where(PreGeneratedPlan.status == "active")
            )
            active_plans_count = len(active_plans.scalars().all())

            expired_plans = await db.execute(
                select(PreGeneratedPlan).where(PreGeneratedPlan.status == "deprecated")
            )
            expired_plans_count = len(expired_plans.scalars().all())

            # 最近生成时间
            last_gen = await db.execute(
                select(HotDestination.last_pre_generated_at)
                .where(HotDestination.last_pre_generated_at.isnot(None))
                .order_by(HotDestination.last_pre_generated_at.desc())
                .limit(1)
            )
            last_generation_time = last_gen.scalar_one_or_none()

        return {
            "total_destinations": total_destinations_count,
            "generated_destinations": generated_destinations,
            "total_plans": total_plans_count,
            "active_plans": active_plans_count,
            "expired_plans": expired_plans_count,
            "last_generation_time": last_generation_time,
            "is_generating": False
        }


# 单例实例
pre_generation_service = PreGenerationService()
