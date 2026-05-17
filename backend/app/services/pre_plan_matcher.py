"""
预生成方案匹配服务
负责根据用户偏好快速匹配最合适的预生成方案
"""

from typing import List, Dict, Any, Optional, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_
from loguru import logger
from datetime import datetime
import json
import hashlib

from app.models.pre_generated_plan import PreGeneratedPlan
from app.core.redis import get_cache, set_cache
from app.core.config import settings


class PrePlanMatcher:
    """预生成方案匹配器"""

    # 匹配权重配置
    MATCH_WEIGHTS = {
        "destination": 10.0,  # 目的地必须匹配
        "duration": 3.0,      # 天数匹配
        "budget": 2.0,        # 预算等级
        "preferences": 1.5,   # 旅行偏好
        "age_groups": 1.0,    # 年龄组
        "food": 0.5,          # 饮食偏好
    }

    @property
    def duration_tolerance(self) -> int:
        """天数容差"""
        return settings.PRE_GENERATION_DURATION_TOLERANCE

    async def find_best_match(
        self,
        db: AsyncSession,
        destination: str,
        duration_days: int,
        budget: Optional[float] = None,
        preferences: Optional[Dict[str, Any]] = None,
    ) -> Tuple[Optional[Dict[str, Any]], float]:
        """
        查找最佳匹配的预生成方案

        Args:
            db: 数据库会话
            destination: 目的地城市名
            duration_days: 行程天数
            budget: 预算金额
            preferences: 用户偏好字典

        Returns:
            Tuple[方案数据, 匹配分数]
        """
        if not settings.PRE_GENERATION_ENABLED:
            return None, 0.0

        # 1. 构建缓存键
        cache_key = self._build_cache_key(destination, duration_days, budget, preferences)

        # 2. 尝试从Redis缓存获取
        cached = await get_cache(cache_key)
        if cached:
            logger.info(f"从缓存获取预生成方案: {cache_key}")
            return cached.get("plan"), cached.get("score", 0.0)

        # 3. 数据库查询
        query = self._build_query(destination, duration_days, budget, preferences)
        result = await db.execute(query)
        candidates = result.scalars().all()

        if not candidates:
            logger.warning(f"未找到匹配的预生成方案: {destination}, {duration_days}天")
            return None, 0.0

        # 4. 计算匹配分数并排序
        scored_candidates = []
        for plan in candidates:
            score = self._calculate_match_score(plan, destination, duration_days, budget, preferences)
            scored_candidates.append((plan, score))

        scored_candidates.sort(key=lambda x: x[1], reverse=True)
        best_plan, best_score = scored_candidates[0]

        # 5. 转换为可返回的格式
        plan_data = self._convert_to_response(best_plan)

        # 6. 缓存结果（5分钟）
        await set_cache(cache_key, {"plan": plan_data, "score": best_score}, ttl=300)

        # 7. 更新匹配计数
        await self._increment_match_count(db, best_plan.id)

        return plan_data, best_score

    def _build_cache_key(
        self,
        destination: str,
        duration_days: int,
        budget: Optional[float],
        preferences: Optional[Dict[str, Any]]
    ) -> str:
        """构建缓存键"""
        budget_level = self._infer_budget_level(budget) if budget else "any"
        pref_hash = self._hash_preferences(preferences) if preferences else "none"
        return f"pre_plan:{destination}:{duration_days}:{budget_level}:{pref_hash}"

    def _hash_preferences(self, preferences: Dict[str, Any]) -> str:
        """对偏好进行哈希，生成简短标识"""
        pref_str = json.dumps(preferences, sort_keys=True, ensure_ascii=False)
        return hashlib.md5(pref_str.encode()).hexdigest()[:8]

    def _build_query(
        self,
        destination: str,
        duration_days: int,
        budget: Optional[float],
        preferences: Optional[Dict[str, Any]]
    ):
        """构建数据库查询"""
        budget_level = self._infer_budget_level(budget) if budget else None

        conditions = [
            PreGeneratedPlan.destination_name == destination,
            PreGeneratedPlan.status == 'active',
            or_(
                PreGeneratedPlan.expires_at.is_(None),
                PreGeneratedPlan.expires_at > datetime.utcnow()
            ),
        ]

        # 天数范围查询（允许容差）
        min_days = max(1, duration_days - self.duration_tolerance)
        max_days = duration_days + self.duration_tolerance
        conditions.append(PreGeneratedPlan.duration_days.between(min_days, max_days))

        # 预算等级（可选）
        if budget_level:
            conditions.append(
                or_(
                    PreGeneratedPlan.budget_level == budget_level,
                    PreGeneratedPlan.budget_level == 'any'
                )
            )

        return select(PreGeneratedPlan).where(and_(*conditions))

    def _calculate_match_score(
        self,
        plan: PreGeneratedPlan,
        destination: str,
        duration_days: int,
        budget: Optional[float],
        preferences: Optional[Dict[str, Any]]
    ) -> float:
        """计算匹配分数"""
        score = 0.0

        # 目的地精确匹配（已由查询保证）
        score += self.MATCH_WEIGHTS["destination"]

        # 天数匹配
        duration_diff = abs(plan.duration_days - duration_days)
        if duration_diff == 0:
            score += self.MATCH_WEIGHTS["duration"]
        elif duration_diff <= self.duration_tolerance:
            score += self.MATCH_WEIGHTS["duration"] * (1 - duration_diff / (self.duration_tolerance + 1))

        # 预算等级匹配
        if budget:
            plan_budget = plan.budget_level
            user_budget = self._infer_budget_level(budget)
            if plan_budget == user_budget:
                score += self.MATCH_WEIGHTS["budget"]

        # 旅行偏好匹配
        if preferences and plan.travel_preferences:
            pref_score = self._calculate_preference_overlap(
                preferences.get("travelPreferences", []),
                plan.travel_preferences
            )
            score += pref_score * self.MATCH_WEIGHTS["preferences"]

        # 年龄组匹配
        if preferences and plan.age_groups:
            age_score = self._calculate_list_overlap(
                preferences.get("ageGroups", []),
                plan.age_groups
            )
            score += age_score * self.MATCH_WEIGHTS["age_groups"]

        # 饮食偏好匹配
        if preferences and plan.food_preferences:
            food_score = self._calculate_list_overlap(
                preferences.get("foodPreferences", []),
                plan.food_preferences
            )
            score += food_score * self.MATCH_WEIGHTS["food"]

        # 热度加权
        score += (plan.popularity_score or 0) * 0.1

        return score

    def _calculate_preference_overlap(self, user_prefs: List, plan_prefs: List) -> float:
        """计算偏好重叠度"""
        if not user_prefs or not plan_prefs:
            return 0.0

        user_set = set(user_prefs)
        plan_set = set(plan_prefs)

        intersection = len(user_set & plan_set)
        union = len(user_set | plan_set)

        return intersection / union if union > 0 else 0.0

    def _calculate_list_overlap(self, user_list: List, plan_list: List) -> float:
        """计算列表重叠度"""
        if not user_list or not plan_list:
            return 0.0

        user_set = set(user_list)
        plan_set = set(plan_list)

        intersection = len(user_set & plan_set)
        return intersection / len(user_set) if user_set else 0.0

    def _infer_budget_level(self, budget: float) -> str:
        """根据预算金额推断预算等级（按天计算）"""
        # 假设预算是总预算，按天平均
        daily_budget = budget
        if daily_budget < 300:
            return "economy"
        elif daily_budget < 800:
            return "comfortable"
        else:
            return "luxury"

    def _convert_to_response(self, plan: PreGeneratedPlan) -> Dict[str, Any]:
        """转换为响应格式"""
        return {
            "id": plan.id,
            "destination_name": plan.destination_name,
            "duration_days": plan.duration_days,
            "budget_level": plan.budget_level,
            "plan_template": plan.plan_template,
            "travel_preferences": plan.travel_preferences,
            "age_groups": plan.age_groups,
            "food_preferences": plan.food_preferences,
            "transportation_mode": plan.transportation_mode,
            "popularity_score": plan.popularity_score,
            "avg_rating": plan.avg_rating,
        }

    async def _increment_match_count(self, db: AsyncSession, plan_id: int):
        """增加匹配计数"""
        try:
            # 异步更新，不阻塞主流程
            await db.execute(
                f"UPDATE pre_generated_plans SET match_count = match_count + 1 WHERE id = {plan_id}"
            )
            await db.commit()
        except Exception as e:
            logger.warning(f"更新匹配计数失败: {e}")

    def get_match_level(self, score: float) -> str:
        """根据分数判断匹配等级"""
        if score >= settings.PRE_GENERATION_PERFECT_MATCH_SCORE:
            return "perfect"
        elif score >= settings.PRE_GENERATION_GOOD_MATCH_SCORE:
            return "good"
        elif score >= settings.PRE_GENERATION_MIN_MATCH_SCORE:
            return "acceptable"
        else:
            return "poor"


# 单例实例
pre_plan_matcher = PrePlanMatcher()
