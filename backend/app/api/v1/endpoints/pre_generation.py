"""
预生成方案管理 API
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional

from app.core.database import get_async_db
from app.core.security import get_current_user
from app.models.user import User
from app.schemas.pre_generated_plan import (
    PreGenerationStatus,
    PreGeneratedPlanMatch,
    HotDestinationResponse,
    HotDestinationCreate
)
from app.services.pre_generation_service import pre_generation_service
from app.services.pre_plan_matcher import pre_plan_matcher
from app.tasks.pre_generation_tasks import (
    pre_generate_plans_task,
    pre_generate_single_city_task,
    cleanup_expired_pre_plans_task
)
from loguru import logger

router = APIRouter()


@router.get("/status", response_model=PreGenerationStatus)
async def get_pre_generation_status(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db)
):
    """获取预生成状态概览"""
    status = await pre_generation_service.get_status()
    return PreGenerationStatus(**status)


@router.post("/trigger")
async def trigger_pre_generation(
    destination_name: Optional[str] = Query(None, description="指定城市名，为空则生成所有热门城市"),
    force: bool = Query(False, description="是否强制重新生成"),
    current_user: User = Depends(get_current_user)
):
    """手动触发预生成任务（需要登录）"""
    # 检查权限（可选：添加管理员权限检查）
    # if not current_user.is_admin:
    #     raise HTTPException(status_code=403, detail="需要管理员权限")

    try:
        if destination_name:
            async_result = pre_generate_single_city_task.delay(destination_name, force)
        else:
            async_result = pre_generate_plans_task.delay(None, force)

        return {
            "message": "预生成任务已启动",
            "task_id": async_result.id,
            "destination": destination_name or "所有热门城市"
        }
    except Exception as e:
        logger.error(f"触发预生成任务失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/cleanup")
async def trigger_cleanup(
    current_user: User = Depends(get_current_user)
):
    """手动触发过期清理任务"""
    try:
        async_result = cleanup_expired_pre_plans_task.delay()
        return {
            "message": "清理任务已启动",
            "task_id": async_result.id
        }
    except Exception as e:
        logger.error(f"触发清理任务失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/match", response_model=PreGeneratedPlanMatch)
async def match_pre_generated_plan(
    destination: str = Query(..., description="目的地城市名"),
    duration_days: int = Query(..., ge=1, le=30, description="行程天数"),
    budget: Optional[float] = Query(None, description="预算金额"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db)
):
    """
    匹配预生成方案

    用于测试预生成方案的匹配效果
    """
    preferences = None
    if current_user.preferences:
        try:
            import json
            preferences = json.loads(current_user.preferences)
        except Exception:
            pass

    plan_data, score = await pre_plan_matcher.find_best_match(
        db, destination, duration_days, budget, preferences
    )

    match_level = pre_plan_matcher.get_match_level(score)

    result = {
        "plan": plan_data,
        "match_score": score,
        "source": "pre_generated" if plan_data else "real_time",
        "can_customize": match_level in ["good", "acceptable"],
    }

    if match_level == "good":
        result["suggestion"] = "此方案基于您的偏好预生成，您可以进一步自定义"
    elif match_level == "acceptable":
        result["suggestion"] = "将基于预生成方案框架，补充您的个性化需求"
    elif match_level == "poor":
        result["suggestion"] = "正在为您生成专属方案"

    return PreGeneratedPlanMatch(**result)


@router.get("/destinations")
async def list_hot_destinations(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_async_db)
):
    """获取热门城市列表"""
    from sqlalchemy import select
    from app.models.hot_destination import HotDestination

    query = select(HotDestination).where(
        HotDestination.is_enabled == True,
        HotDestination.is_active == True
    ).order_by(HotDestination.priority.asc()).offset(offset).limit(limit)

    result = await db.execute(query)
    destinations = result.scalars().all()

    return [HotDestinationResponse(**d.to_dict()) for d in destinations]


@router.post("/destinations")
async def add_hot_destination(
    data: HotDestinationCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db)
):
    """添加热门城市"""
    from app.models.hot_destination import HotDestination

    # 检查是否已存在
    from sqlalchemy import select
    query = select(HotDestination).where(HotDestination.city_name == data.city_name)
    result = await db.execute(query)
    existing = result.scalar_one_or_none()

    if existing:
        raise HTTPException(status_code=400, detail="城市已存在")

    hot_dest = HotDestination(
        city_name=data.city_name,
        province=data.province,
        region=data.region,
        priority=data.priority,
        is_enabled=data.is_enabled,
        popularity_score=data.popularity_score,
        tags=data.tags,
        monthly_visitors=data.monthly_visitors,
        search_volume=data.search_volume,
        latitude=data.latitude,
        longitude=data.longitude
    )

    db.add(hot_dest)
    await db.commit()

    return {"message": "城市添加成功", "city_name": data.city_name}