"""
旅行计划API端点
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional, Any, Dict
from datetime import datetime, date
from pydantic import BaseModel, Field

from app.core.database import get_async_db
from app.schemas.travel_plan import (
    TravelPlanCreate,
    TravelPlanCreateRequest,
    TravelPlanUpdate,
    TravelPlanResponse,
    TravelPlanGenerateRequest,
    TravelPlanBatchDeleteRequest
)
from app.services.travel_plan_service import TravelPlanService
from app.services.agent_service import AgentService
from app.services.plan_generator import PlanGenerator
from loguru import logger
from fastapi.responses import HTMLResponse, JSONResponse, Response, PlainTextResponse, StreamingResponse
import asyncio, time, json
from app.core.config import settings
from fastapi.encoders import jsonable_encoder
from app.core.redis import get_cache, set_cache

# 新增导入
from app.core.security import get_current_user, get_current_user_optional, is_admin
from app.services.attraction_detail_service import AttractionDetailService
from app.models.attraction_detail import AttractionDetail
from app.models.user import User
from sqlalchemy import select
from app.tasks.travel_plan_tasks import (
    generate_travel_plans_task as celery_generate_travel_plans_task,
    refine_travel_plan_task as celery_refine_travel_plan_task,
    export_travel_plan_task as celery_export_travel_plan_task,
)
from celery.result import AsyncResult

router = APIRouter()


@router.post("/", response_model=TravelPlanResponse)
async def create_travel_plan(
    plan_data: TravelPlanCreateRequest,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user),
):
    """创建新的旅行计划(绑定到当前用户)"""
    service = TravelPlanService(db)
    data = plan_data.dict()
    data["user_id"] = current_user.id
    return await service.create_travel_plan(TravelPlanCreate(**data))


@router.get("/")
async def get_travel_plans(
    skip: int = 0,
    limit: int = 100,
    user_id: Optional[int] = None,
    status: Optional[str] = None,
    keyword: Optional[str] = None,
    min_score: Optional[float] = None,
    max_score: Optional[float] = None,
    created_from: Optional[datetime] = Query(None, description="创建时间(ISO8601,支持Z)"),
    created_to: Optional[datetime] = Query(None, description="创建时间(ISO8601,支持Z)"),
    travel_from: Optional[date] = Query(None, description="出行日期(YYYY-MM-DD)"),
    travel_to: Optional[date] = Query(None, description="出行日期(YYYY-MM-DD)"),
    plan_source: Optional[str] = Query(
        None,
        description="方案来源过滤: private(仅私有), public(仅公开), 未传表示全部",
        regex="^(private|public)$"
    ),
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user),
):
    """获取旅行计划列表(普通用户仅能查看自己的,管理员可查看所有)"""
    service = TravelPlanService(db)
    # 非管理员强制限定为当前用户
    effective_user_id = user_id if is_admin(current_user) else current_user.id
    plans, total = await service.get_travel_plans_with_total(
        skip=skip,
        limit=limit,
        user_id=effective_user_id,
        status=status,
        keyword=keyword,
        min_score=min_score,
        max_score=max_score,
        created_from=created_from,
        created_to=created_to,
        travel_from=travel_from,
        travel_to=travel_to,
        plan_source=plan_source,
    )
    return {
        "plans": plans,
        "total": total,
        "skip": skip,
        "limit": limit,
    }

# =============== 公开访问相关端点 ===============
@router.get("/public")
async def list_public_travel_plans(
    skip: int = 0,
    limit: int = 100,
    destination: Optional[str] = None,
    keyword: Optional[str] = None,
    min_score: Optional[float] = None,
    travel_from: Optional[date] = Query(None, description="出行日期(YYYY-MM-DD)"),
    travel_to: Optional[date] = Query(None, description="出行日期(YYYY-MM-DD)"),
    db: AsyncSession = Depends(get_async_db),
):
    """公开列表:无需登录,支持目的地,关键词,评分与出行日期检查"""
    service = TravelPlanService(db)
    plans, total = await service.get_public_travel_plans_with_total(
        skip=skip,
        limit=limit,
        destination=destination,
        keyword=keyword,
        min_score=min_score,
        travel_from=travel_from,
        travel_to=travel_to,
    )
    return {
        "plans": plans,
        "total": total,
        "skip": skip,
        "limit": limit,
    }

@router.get("/public/{plan_id}", response_model=TravelPlanResponse)
async def get_public_travel_plan(
    plan_id: int,
    db: AsyncSession = Depends(get_async_db),
):
    """公开详情:无需登录,仅公开计划可访问"""
    service = TravelPlanService(db)
    plan = await service.get_public_travel_plan(plan_id)
    if not plan:
        raise HTTPException(status_code=404, detail="公开旅行计划不存在")
    plan_data = TravelPlanResponse.from_orm(plan).dict()
    plan_data = await _enrich_plan_with_attraction_details(plan_data, db)
    return plan_data

@router.put("/{plan_id}/publish")
async def publish_travel_plan(
    plan_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user),
):
    """发布为公开方案(需拥有或管理员权限)"""
    service = TravelPlanService(db)
    plan = await service.get_travel_plan(plan_id)
    if not plan:
        raise HTTPException(status_code=404, detail="旅行计划不存在")
    if not (is_admin(current_user) or plan.user_id == current_user.id):
        raise HTTPException(status_code=403, detail="无权发布该计划")
    await service.set_public_status(plan_id, True)
    plan = await service.get_travel_plan(plan_id)
    return TravelPlanResponse.from_orm(plan)

@router.put("/{plan_id}/unpublish")
async def unpublish_travel_plan(
    plan_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user),
):
    """取消公开(需拥有或管理员权限)"""
    service = TravelPlanService(db)
    plan = await service.get_travel_plan(plan_id)
    if not plan:
        raise HTTPException(status_code=404, detail="旅行计划不存在")
    if not (is_admin(current_user) or plan.user_id == current_user.id):
        raise HTTPException(status_code=403, detail="无权取消公开该计划")
    await service.set_public_status(plan_id, False)
    plan = await service.get_travel_plan(plan_id)
    return TravelPlanResponse.from_orm(plan)


@router.get("/{plan_id}", response_model=TravelPlanResponse)
async def get_travel_plan(
    plan_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user),
):
    """获取单个旅行计划(需拥有或管理员权限)"""
    service = TravelPlanService(db)
    plan = await service.get_travel_plan(plan_id)
    if not plan:
        raise HTTPException(status_code=404, detail="旅行计划不存在")
    if not (is_admin(current_user) or plan.user_id == current_user.id):
        raise HTTPException(status_code=403, detail="无权访问该计划")
    plan_data = TravelPlanResponse.from_orm(plan).dict()
    plan_data = await _enrich_plan_with_attraction_details(plan_data, db)
    return plan_data


async def _enrich_plan_with_attraction_details(plan_data: dict, db: AsyncSession) -> dict:
    """为生成的方案补充手动维护的景点详细信息，减少对LLM输出的依赖"""
    try:
        destination = plan_data.get("destination")
        if not destination:
            return plan_data

        # 批量加载该目的地的景点详情，按名称建立索引（小写去空格）
        result = await db.execute(
            select(AttractionDetail).where(AttractionDetail.destination == destination)
        )
        details = result.scalars().all()
        if not details:
            return plan_data

        detail_map = {d.name.strip().lower(): d for d in details if d.name}

        def merge_one(attraction: Any) -> Any:
            if attraction is None:
                return attraction
            if isinstance(attraction, str):
                base = {"name": attraction}
            elif isinstance(attraction, dict):
                base = dict(attraction)
            else:
                return attraction

            name = (base.get("name") or "").strip().lower()
            if not name:
                return base

            detail = detail_map.get(name)
            if not detail:
                return base

            return AttractionDetailService.merge_detail_into_attraction(base, detail)

        # 遍历 generated_plans -> daily_itineraries -> attractions
        generated_plans = plan_data.get("generated_plans")
        if isinstance(generated_plans, list):
            for plan in generated_plans:
                if not isinstance(plan, dict):
                    continue
                daily_list = plan.get("daily_itineraries")
                if not isinstance(daily_list, list):
                    continue
                for day in daily_list:
                    if not isinstance(day, dict):
                        continue
                    attractions = day.get("attractions")
                    if isinstance(attractions, list):
                        merged = [merge_one(a) for a in attractions]
                        day["attractions"] = merged

        # 同步 selected_plan(如果有且与 generated_plans 对应)
        selected_plan = plan_data.get("selected_plan")
        if isinstance(selected_plan, dict) and isinstance(generated_plans, list):
            try:
                # 通过 title/type 找到对应索引
                sel_title = selected_plan.get("title")
                sel_type = selected_plan.get("type")
                idx = next(
                    (i for i, p in enumerate(generated_plans)
                     if isinstance(p, dict)
                     and p.get("title") == sel_title
                     and p.get("type") == sel_type),
                    None
                )
                if idx is not None and isinstance(generated_plans[idx], dict):
                    plan_data["selected_plan"] = generated_plans[idx]
            except Exception:
                pass

        return plan_data
    except Exception as e:
        logger.warning(f"补充景点详细信息失败(忽略，不阻塞主流程): {e}")
        return plan_data


@router.put("/{plan_id}", response_model=TravelPlanResponse)
async def update_travel_plan(
    plan_id: int,
    plan_data: TravelPlanUpdate,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user),
):
    """更新旅行计划(需拥有或管理员权限)"""
    service = TravelPlanService(db)
    plan = await service.get_travel_plan(plan_id)
    if not plan:
        raise HTTPException(status_code=404, detail="旅行计划不存在")
    if not (is_admin(current_user) or plan.user_id == current_user.id):
        raise HTTPException(status_code=403, detail="无权更新该计划")
    plan = await service.update_travel_plan(plan_id, plan_data)
    return plan


@router.delete("/{plan_id}")
async def delete_travel_plan(
    plan_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user),
):
    """删除旅行计划(需拥有或管理员权限)"""
    service = TravelPlanService(db)
    plan = await service.get_travel_plan(plan_id)
    if not plan:
        raise HTTPException(status_code=404, detail="旅行计划不存在")
    if not (is_admin(current_user) or plan.user_id == current_user.id):
        raise HTTPException(status_code=403, detail="无权删除该计划")
    success = await service.delete_travel_plan(plan_id)
    if not success:
        raise HTTPException(status_code=404, detail="旅行计划不存在")
    return {"message": "旅行计划已删除"}


@router.post("/batch-delete")
async def batch_delete_travel_plans(
    payload: TravelPlanBatchDeleteRequest,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user),
):
    """批量删除旅行计划(仅管理员)"""
    if not is_admin(current_user):
        raise HTTPException(status_code=403, detail="仅管理员可批量删除")
    service = TravelPlanService(db)
    deleted_count = await service.delete_travel_plans(payload.ids)
    return {"deleted": deleted_count}


@router.post("/{plan_id}/generate")
async def generate_travel_plans(
    plan_id: int,
    request: TravelPlanGenerateRequest,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user),
):
    """生成旅行方案(需拥有或管理员权限)"""
    service = TravelPlanService(db)
    agent_service = AgentService(db)
    plan = await service.get_travel_plan(plan_id)
    if not plan:
        raise HTTPException(status_code=404, detail="旅行计划不存在")
    if not (is_admin(current_user) or plan.user_id == current_user.id):
        raise HTTPException(status_code=403, detail="无权生成该计划")
    # 防止重复触发生成任务
    if plan.status == "generating":
        raise HTTPException(status_code=409, detail="该计划正在生成中，请稍后")
    # 先更新状态为生成中并加锁，避免并发竞争
    await agent_service._update_plan_status(plan_id, "generating")
    async_result = celery_generate_travel_plans_task.delay(
        plan_id,
        request.preferences,
        request.requirements,
    )
    return {
        "message": "旅行方案生成任务已启动",
        "plan_id": plan_id,
        "status": "generating",
        "task_id": async_result.id,
    }


@router.post("/{plan_id}/refine")
async def refine_travel_plan_async(
    plan_id: int,
    request_data: dict,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user),
):
    """细化旅行方案(Celery异步,需拥有或管理员权限)"""
    service = TravelPlanService(db)
    plan = await service.get_travel_plan(plan_id)
    if not plan:
        raise HTTPException(status_code=404, detail="旅行计划不存在")
    if not (is_admin(current_user) or plan.user_id == current_user.id):
        raise HTTPException(status_code=403, detail="无权细化该计划")
    plan_index = request_data.get("plan_index")
    refinements = request_data.get("refinements") or {}
    if plan_index is None:
        raise HTTPException(status_code=400, detail="缺少plan_index参数")
    async_result = celery_refine_travel_plan_task.delay(plan_id, plan_index, refinements)
    return {
        "message": "方案细化任务已启动",
        "plan_id": plan_id,
        "task_id": async_result.id,
    }


@router.get("/tasks/status/{task_id}")
async def get_task_status(task_id: str, current_user: User = Depends(get_current_user)):
    """查询Celery任务状态(需登录)"""
    try:
        task_result = AsyncResult(task_id)
        state = task_result.state
        if state == "PENDING":
            return {"task_id": task_id, "status": "pending", "message": "任务等待执行"}
        if state == "PROGRESS":
            info = task_result.info or {}
            return {
                "task_id": task_id,
                "status": "progress",
                "current": info.get("current", 0),
                "total": info.get("total", 100),
                "message": info.get("status", "执行中"),
            }
        if state == "SUCCESS":
            return {"task_id": task_id, "status": "success", "result": task_result.result}
        # FAILURE 或其他状态
        return {"task_id": task_id, "status": "failed", "message": str(task_result.info)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取任务状态失败: {str(e)}")


@router.delete("/tasks/cancel/{task_id}")
async def cancel_task(task_id: str, current_user: User = Depends(get_current_user)):
    """取消Celery任务(需登录)"""
    try:
        task_result = AsyncResult(task_id)
        task_result.revoke(terminate=True)
        return {"task_id": task_id, "status": "cancelled"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"取消任务失败: {str(e)}")


@router.get("/{plan_id}/status")
async def get_generation_status(
    plan_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user),
):
    """获取方案生成状态(需拥有或管理员权限)"""
    service = TravelPlanService(db)
    plan = await service.get_travel_plan(plan_id)
    if not plan:
        raise HTTPException(status_code=404, detail="旅行计划不存在")
    if not (is_admin(current_user) or plan.user_id == current_user.id):
        raise HTTPException(status_code=403, detail="无权查看该计划状态")
    return {
        "plan_id": plan_id,
        "status": plan.status,
        "generated_plans": plan.generated_plans,
        "selected_plan": plan.selected_plan,
    }


@router.get("/{plan_id}/status/stream")
async def stream_generation_status(
    plan_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user),
):
    """SSE流式返回方案生成状态(需拥有或管理员权限)"""
    service = TravelPlanService(db)
    plan = await service.get_travel_plan(plan_id)
    if not plan:
        raise HTTPException(status_code=404, detail="旅行计划不存在")
    if not (is_admin(current_user) or plan.user_id == current_user.id):
        raise HTTPException(status_code=403, detail="无权查看该计划状态")

    start_ts = time.time()
    max_seconds = settings.PLAN_STATUS_STREAM_MAX_SECONDS

    async def event_generator():
        last_status = None
        while True:
            try:
                current_plan = await service.get_travel_plan(plan_id)
                if current_plan is not None:
                    await db.refresh(current_plan)
                status = current_plan.status
                elapsed = time.time() - start_ts
                base_progress = min(90, 10 + (elapsed / max_seconds) * 80)
                progress = 100 if status == "completed" else (0 if status == "failed" else round(base_progress, 2))

                payload = {
                    "plan_id": plan_id,
                    "status": status,
                    "progress": progress,
                    "preview": None,
                }

                try:
                    gp = current_plan.generated_plans or []
                    if isinstance(gp, list):
                        for p in gp:
                            if p and p.get("is_preview") and p.get("preview_type") == "raw_data_preview":
                                payload["preview"] = p
                                break
                except Exception:
                    payload["preview"] = None

                yield f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"

                if status in ("completed", "failed"):
                    break
                if elapsed >= max_seconds:
                    timeout_payload = {
                        "plan_id": plan_id,
                        "status": "timeout",
                        "progress": round(base_progress, 2),
                    }
                    yield f"data: {json.dumps(timeout_payload, ensure_ascii=False)}\n\n"
                    break

                await asyncio.sleep(settings.PLAN_STATUS_STREAM_INTERVAL)
            except asyncio.CancelledError:
                break
            except Exception as e:
                err_payload = {"plan_id": plan_id, "status": "error", "message": str(e)}
                yield f"data: {json.dumps(err_payload, ensure_ascii=False)}\n\n"
                break

    return StreamingResponse(event_generator(), media_type="text/event-stream", headers={"Cache-Control": "no-cache"})


@router.post("/{plan_id}/select-plan")
async def select_travel_plan(
    plan_id: int,
    request_data: dict,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user),
):
    """选择最终旅行方案(需拥有或管理员权限)"""
    service = TravelPlanService(db)
    plan = await service.get_travel_plan(plan_id)
    if not plan:
        raise HTTPException(status_code=404, detail="旅行计划不存在")
    if not (is_admin(current_user) or plan.user_id == current_user.id):
        raise HTTPException(status_code=403, detail="无权选择该计划方案")
    plan_index = request_data.get("plan_index")
    if plan_index is None:
        raise HTTPException(status_code=400, detail="缺少plan_index参数")
    success = await service.select_plan(plan_id, plan_index)
    if not success:
        raise HTTPException(status_code=400, detail="选择方案失败")
    return {"message": "方案选择成功"}


@router.post("/{plan_id}/export-async")
async def export_travel_plan_async(
    plan_id: int,
    format: str = "pdf",  # pdf, json, html
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user),
):
    """导出旅行计划(Celery异步,需拥有或管理员权限)"""
    allowed = {"json", "html", "pdf"}
    if format not in allowed:
        raise HTTPException(status_code=400, detail=f"不支持的导出格式: {format}")
    service = TravelPlanService(db)
    plan = await service.get_travel_plan(plan_id)
    if not plan:
        raise HTTPException(status_code=404, detail="旅行计划不存在")
    if not (is_admin(current_user) or plan.user_id == current_user.id):
        raise HTTPException(status_code=403, detail="无权导出该计划")
    async_result = celery_export_travel_plan_task.delay(plan_id, format)
    return {
        "message": "导出任务已启动",
        "plan_id": plan_id,
        "format": format,
        "task_id": async_result.id,
    }

# =============== 评分相关端点 ===============
from app.schemas.travel_plan import (
    TravelPlanRatingCreate,
    TravelPlanRatingResponse,
    TravelPlanRatingSummary,
)

@router.post("/{plan_id}/ratings")
async def rate_travel_plan(
    plan_id: int,
    payload: TravelPlanRatingCreate,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user),
):
    """对旅行计划进行评分(任何登录用户可评分)"""
    service = TravelPlanService(db)
    plan = await service.get_travel_plan(plan_id)
    if not plan:
        raise HTTPException(status_code=404, detail="旅行计划不存在")
    # 允许任意登录用户评分，无需拥有权限
    avg, cnt = await service.upsert_rating(plan_id, current_user.id, payload.score, payload.comment)
    return {"message": "评分已提交", "summary": {"average": avg, "count": cnt}}

@router.get("/{plan_id}/ratings", response_model=List[TravelPlanRatingResponse])
async def list_plan_ratings(
    plan_id: int,
    skip: int = 0,
    limit: int = 10,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user),
):
    """获取旅行计划的评分列表(登录用户可查看)"""
    service = TravelPlanService(db)
    plan = await service.get_travel_plan(plan_id)
    if not plan:
        raise HTTPException(status_code=404, detail="旅行计划不存在")
    ratings = await service.get_ratings(plan_id, skip=skip, limit=limit)
    return ratings

@router.get("/{plan_id}/ratings/summary", response_model=TravelPlanRatingSummary)
async def get_plan_rating_summary(
    plan_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user),
):
    """获取评分汇总(平均分,数量)"""
    service = TravelPlanService(db)
    plan = await service.get_travel_plan(plan_id)
    if not plan:
        raise HTTPException(status_code=404, detail="旅行计划不存在")
    avg, cnt = await service.get_rating_summary(plan_id)
    return {"average": avg, "count": cnt}

@router.get("/{plan_id}/ratings/me", response_model=Optional[TravelPlanRatingResponse])
async def get_my_plan_rating(
    plan_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user),
):
    """获取当前用户对该计划的评分(用于前端回填)"""
    service = TravelPlanService(db)
    plan = await service.get_travel_plan(plan_id)
    if not plan:
        raise HTTPException(status_code=404, detail="旅行计划不存在")
    rating = await service.get_rating_by_user(plan_id, current_user.id)
    return rating

@router.get("/{plan_id}/text-plan")
async def get_text_plan(
    plan_id: int,
    max_chars: int = Query(2000, ge=500, le=5000, description="最大字符数限制"),
    db: AsyncSession = Depends(get_async_db),
    current_user: Optional[User] = Depends(get_current_user_optional),
):
    """获取纯文本旅行方案(LLM直接生成,不依赖爬取数据)
    
    注意:此方案基于LLM知识库生成,可能有滞后性,但主要景点信息通常是准确的。
    适用于快速概览目的地玩法。
    
    结果会缓存到Redis 1小时。
    """
    try:
        # 尝试从缓存获取
        cache_key = f"text_plan:{plan_id}:{max_chars}"
        cached_result = await get_cache(cache_key)
        if cached_result:
            logger.info(f"从缓存获取纯文本方案: plan_id={plan_id}")
            return cached_result
        
        service = TravelPlanService(db)
        # 尝试获取计划(私有或公开)
        plan = None
        is_public = False
        
        # 先尝试私有计划
        if current_user:
            plan = await service.get_travel_plan(plan_id)
            if plan and (is_admin(current_user) or plan.user_id == current_user.id):
                pass  # 有权限访问
            else:
                plan = None
        
        # 如果私有计划不可访问，尝试公开计划
        if not plan:
            plan = await service.get_public_travel_plan(plan_id)
            if plan:
                is_public = True
        
        if not plan:
            raise HTTPException(status_code=404, detail="旅行计划不存在或无权限访问")
        
        # 获取用户偏好(如果有)
        preferences = {}
        if hasattr(plan, 'preferences') and plan.preferences:
            try:
                if isinstance(plan.preferences, str):
                    preferences = json.loads(plan.preferences)
                elif isinstance(plan.preferences, dict):
                    preferences = plan.preferences
            except:
                preferences = {}
        
        # 生成纯文本方案
        generator = PlanGenerator()
        text_plan = await generator.generate_text_plan(
            plan=plan,
            preferences=preferences,
            max_chars=max_chars
        )
        
        result = {
            "plan_id": plan_id,
            "text_plan": text_plan,
            "destination": plan.destination,
            "duration_days": plan.duration_days,
            "generated_at": datetime.utcnow().isoformat(),
            "note": "此方案基于LLM知识库生成，可能有滞后性，但主要景点信息通常是准确的。"
        }
        
        # 缓存结果1小时 = 3600秒
        await set_cache(cache_key, result, ttl=3600)
        logger.info(f"纯文本方案已缓存: plan_id={plan_id}")
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取纯文本方案失败: {e}")
        raise HTTPException(status_code=500, detail=f"生成纯文本方案失败: {str(e)}")

def _render_plan_html(plan_data: dict) -> str:
    title = plan_data.get("title") or f"旅行方案 #{plan_data.get('id', '')}"
    destination = plan_data.get("destination", "")
    description = plan_data.get("description", "")
    score = plan_data.get("score")
    duration_days = plan_data.get("duration_days")
    selected_plan = plan_data.get("selected_plan") or {}
    items = plan_data.get("items") or []
    
    def safe(v):
        return v if v is not None else ""
    
    html = f"""
    <!doctype html>
    <html lang=\"zh\">
    <head>
      <meta charset=\"utf-8\" />
      <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\" />
      <title>{safe(title)}</title>
      <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, 'Noto Sans', 'Liberation Sans', sans-serif; margin: 24px; color: #222; }}
        h1 {{ margin: 0 0 8px; font-size: 24px; }}
        .meta {{ color: #666; margin-bottom: 16px; }}
        .section {{ margin: 16px 0; }}
        .item {{ border: 1px solid #eee; border-radius: 6px; padding: 12px; margin: 8px 0; }}
        .item-title {{ font-weight: 600; margin-bottom: 6px; }}
        .item-desc {{ color: #555; }}
        table {{ border-collapse: collapse; width: 100%; }}
        th, td {{ border: 1px solid #eee; padding: 8px; text-align: left; }}
      </style>
    </head>
    <body>
      <h1>{safe(title)}</h1>
      <div class=\"meta\">目的地：{safe(destination)} | 天数：{safe(duration_days)} | 评分：{safe(score)}</div>
      <div class=\"section\">
        <h2>方案简介</h2>
        <p class=\"item-desc\">{safe(description)}</p>
      </div>
      <div class=\"section\">
        <h2>最终选择的方案</h2>
        <pre style=\"white-space: pre-wrap; background: #fafafa; border: 1px solid #eee; padding: 12px; border-radius: 6px;\">{safe(str(selected_plan))}</pre>
      </div>
      <div class=\"section\">
        <h2>行程项目</h2>
        {''.join([
          f"<div class='item'><div class='item-title'>{safe(i.get('title'))}</div>"
          f"<div class='item-desc'>{safe(i.get('description'))}</div>"
          f"<div>类型：{safe(i.get('item_type'))}</div>"
          f"<div>位置：{safe(i.get('location'))}</div>"
          f"<div>地址：{safe(i.get('address'))}</div>"
          f"</div>" for i in items
        ])}
      </div>
    </body>
    </html>
    """
    return html

@router.get("/{plan_id}/export")
async def export_travel_plan(
    plan_id: int,
    format: str = "pdf",  # pdf, json, html
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user),
):
    """导出旅行计划(需拥有或管理员权限)"""
    allowed = {"json", "html", "pdf"}
    if format not in allowed:
        raise HTTPException(status_code=400, detail=f"不支持的导出格式: {format}")
    service = TravelPlanService(db)
    plan = await service.get_travel_plan(plan_id)
    if not plan:
        raise HTTPException(status_code=404, detail="旅行计划不存在")
    if not (is_admin(current_user) or plan.user_id == current_user.id):
        raise HTTPException(status_code=403, detail="无权导出该计划")
    plan_data = TravelPlanResponse.from_orm(plan).dict()
    if format == "json":
        return JSONResponse(content=jsonable_encoder(plan_data))
    elif format == "html":
        html = _render_plan_html(plan_data)
        return HTMLResponse(content=html)
    else:  # pdf
        return PlainTextResponse(content="PDF 导出暂未实现", status_code=501)

@router.post("/{plan_id}/export")
async def export_travel_plan_post(
    plan_id: int,
    format: str = "pdf",  # pdf, json, html
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user),
):
    """导出旅行计划(POST,同步返回,与GET一致)"""
    return await export_travel_plan(plan_id=plan_id, format=format, db=db, current_user=current_user)

# =============== 快速生成相关端点(简化版) ===============
from app.schemas.travel_plan import QuickGenerateRequest, QuickGenerateResponse
from typing import Dict, Any, List

@router.post("/quick-generate", response_model=QuickGenerateResponse)
async def quick_generate_travel_plan(
    request: QuickGenerateRequest,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user),
):
    """一键生成旅行计划(使用LLM快速生成,不保存到数据库)"""
    try:
        from datetime import datetime, timedelta
        import uuid
        
        # 解析日期
        start_date = datetime.strptime(request.start_date, "%Y-%m-%d")
        end_date = datetime.strptime(request.end_date, "%Y-%m-%d")
        days = (end_date - start_date).days + 1
        
        # 生成计划ID(临时)
        plan_id = str(uuid.uuid4())
        
        # 构建偏好
        preferences = request.preferences or {}
        preferences.update({
            "travelers": request.people,
            "budget": request.budget,
            "departure": request.departure
        })
        
        # 使用PlanGenerator生成文本计划
        generator = PlanGenerator()
        
        # 创建临时计划对象
        class TempPlan:
            def __init__(self, destination, duration_days, preferences):
                self.destination = destination
                self.duration_days = duration_days
                self.preferences = preferences
        
        temp_plan = TempPlan(request.destination, days, preferences)
        
        # 生成文本计划作为基础
        text_plan = await generator.generate_text_plan(
            plan=temp_plan,
            preferences=preferences,
            max_chars=3000
        )
        
        # 将文本计划解析为结构化行程
        daily_itineraries = await _parse_text_to_itineraries(text_plan, request.destination, days, start_date)
        
        # 为每个景点添加坐标
        daily_itineraries = await _add_coordinates_to_itineraries(daily_itineraries, db)
        
        # 添加路线信息
        daily_itineraries = await _add_routes_to_itineraries(daily_itineraries)
        
        response = QuickGenerateResponse(
            plan_id=plan_id,
            title=f"{request.destination} {days}天旅行计划",
            destination=request.destination,
            days=days,
            people=request.people,
            budget=request.budget,
            start_date=request.start_date,
            end_date=request.end_date,
            daily_itineraries=daily_itineraries,
            generated_at=datetime.utcnow().isoformat()
        )
        
        return response
        
    except Exception as e:
        logger.error(f"一键生成旅行计划失败: {e}")
        raise HTTPException(status_code=500, detail=f"生成失败: {str(e)}")

async def _parse_text_to_itineraries(text_plan: str, destination: str, days: int, start_date: datetime) -> List[Dict[str, Any]]:
    """将文本计划解析为结构化行程"""
    try:
        import re
        from datetime import datetime, timedelta
        
        itineraries = []
        
        # 使用正则表达式提取文本中的天数和活动
        # 匹配格式 "Day 1:", "第一天:", "D1:" 等
        day_patterns = [
            r'(?:第(\d+)天|Day\s*(\d+)|D(\d+)|day\s*(\d+))[:\s]*',
            r'(\d+)月(\d+)日[:\s]*'  # 日期格式
        ]
        
        # 按行分割文本
        lines = text_plan.split('\n')
        current_day = 0
        current_activities = []
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            # 检查是否是新的天数
            day_match = None
            for pattern in day_patterns:
                match = re.search(pattern, line, re.IGNORECASE)
                if match:
                    # 保存前一天的内容
                    if current_activities and current_day > 0:
                        itinerary = _create_day_itinerary(current_day, start_date, destination, current_activities)
                        itineraries.append(itinerary)
                    
                    # 获取天数
                    day_num = 0
                    for group in match.groups():
                        if group and group.isdigit():
                            day_num = int(group)
                            break
                    
                    current_day = day_num
                    current_activities = []
                    break
            
            # 如果是活动行，解析活动
            if current_day > 0 and not day_match:
                activity = _parse_activity_line(line)
                if activity:
                    current_activities.append(activity)
        
        # 最后一天
        if current_activities and current_day > 0:
            itinerary = _create_day_itinerary(current_day, start_date, destination, current_activities)
            itineraries.append(itinerary)
        
        # 如果没有解析出任何行程，生成默认行程
        if not itineraries:
            for day in range(1, days + 1):
                itinerary = _create_default_day_itinerary(day, start_date, destination)
                itineraries.append(itinerary)
        
        # 按天数排序
        itineraries.sort(key=lambda x: x['day'])
        
        return itineraries
        
    except Exception as e:
        logger.error(f"解析文本计划失败: {e}")
        # 返回默认行程
        itineraries = []
        for day in range(1, days + 1):
            itinerary = _create_default_day_itinerary(day, start_date, destination)
            itineraries.append(itinerary)
        return itineraries

def _parse_activity_line(line: str) -> Optional[Dict[str, Any]]:
    """解析活动行"""
    try:
        # 匹配时间格式: "09:00-12:00", "上午9点", "9:00" 等
        time_patterns = [
            r'(\d{1,2}:\d{2})\s*[-~]\s*(\d{1,2}:\d{2})',  # 09:00-12:00
            r'(\d{1,2}:\d{2})',  # 09:00
            r'(上午|下午|晚上)\s*(\d{1,2})\s*点(?:\s*-\s*(\d{1,2})\s*点)?',  # 上午9点
        ]
        
        time_match = None
        time_str = ""
        for pattern in time_patterns:
            match = re.search(pattern, line)
            if match:
                if len(match.groups()) >= 2 and match.group(2):
                    # 时间范围
                    start_time = match.group(1)
                    end_time = match.group(2)
                    time_str = f"{start_time}-{end_time}"
                else:
                    # 单一时间点
                    time_str = match.group(1)
                time_match = match
                break
        
        # 移除时间部分，获取活动名称
        activity_text = line
        if time_match:
            activity_text = line[:time_match.start()].strip() + " " + line[time_match.end():].strip()
        
        activity_text = activity_text.strip()
        
        if not activity_text:
            return None
            
        # 简单的活动对象
        return {
            "name": activity_text[:20],  # 活动名称
            "time": time_str or "全天",
            "activity": "参观",
            "location": activity_text,
            "description": activity_text,
            "estimated_cost": 0.0
        }
        
    except Exception as e:
        logger.warning(f"解析活动行失败: {line}, 错误: {e}")
        return None

def _create_day_itinerary(day: int, start_date: datetime, destination: str, activities: List[Dict[str, Any]]) -> Dict[str, Any]:
    """创建一天的行程"""
    current_date = start_date + timedelta(days=day-1)
    
    # 如果没有活动，添加默认活动
    if not activities:
        activities = [
            {
                "name": f"{destination}自由活动",
                "time": "09:00-18:00",
                "activity": "自由活动",
                "location": f"{destination}市区",
                "description": f"在{destination}自由探索",
                "estimated_cost": 0.0
            }
        ]
    
    return {
        "day": day,
        "date": current_date.strftime("%Y-%m-%d"),
        "theme": f"第{day}天 - {destination}探索",
        "activities": activities,
        "routes": [],  # 稍后填充
        "meals": [
            {
                "type": "早餐",
                "time": "08:00",
                "location": f"{destination}酒店",
                "suggestion": "酒店自助早餐"
            },
            {
                "type": "午餐", 
                "time": "12:30",
                "location": f"{destination}市区",
                "suggestion": "品尝当地特色美食"
            },
            {
                "type": "晚餐",
                "time": "18:30", 
                "location": f"{destination}市区",
                "suggestion": "特色餐厅"
            }
        ]
    }

def _create_default_day_itinerary(day: int, start_date: datetime, destination: str) -> Dict[str, Any]:
    """创建默认的一天行程"""
    current_date = start_date + timedelta(days=day-1)
    
    return {
        "day": day,
        "date": current_date.strftime("%Y-%m-%d"),
        "theme": f"第{day}天 - {destination}探索",
        "activities": [
            {
                "name": f"{destination}主要景点",
                "time": "09:00-12:00",
                "activity": "参观",
                "location": f"{destination}核心景区",
                "description": f"参观{destination}最著名的景点",
                "estimated_cost": 50.0
            },
            {
                "name": f"{destination}文化体验", 
                "time": "14:00-17:00",
                "activity": "体验",
                "location": f"{destination}文化区",
                "description": f"体验{destination}的当地文化",
                "estimated_cost": 30.0
            }
        ],
        "routes": [],
        "meals": [
            {
                "type": "早餐",
                "time": "08:00",
                "location": f"{destination}酒店",
                "suggestion": "酒店自助早餐"
            },
            {
                "type": "午餐", 
                "time": "12:30",
                "location": f"{destination}市区",
                "suggestion": "当地特色美食"
            },
            {
                "type": "晚餐",
                "time": "18:30", 
                "location": f"{destination}市区",
                "suggestion": "特色餐厅"
            }
        ]
    }

async def _add_coordinates_to_itineraries(itineraries: List[Dict[str, Any]], db: AsyncSession) -> List[Dict[str, Any]]:
    """为行程中的景点添加经纬度坐标"""
    # 简单实现：返回原数据，实际项目中可调用地理编码API
    # 这里暂时不做坐标补充，避免依赖外部服务
    return itineraries

async def _add_routes_to_itineraries(itineraries: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """为行程添加路线规划信息"""
    # 简单实现：返回原数据，实际项目中可调用路线规划API
    return itineraries


# =============== 行程项目(Item)相关端点 ===============
from app.schemas.travel_plan import TravelPlanItemResponse, TravelPlanItemCreate, TravelPlanItemUpdate


class ReorderItemsRequest(BaseModel):
    """重排序请求"""
    item_ids: List[int] = Field(..., description="按新顺序排列的项目ID列表")


@router.post("/{plan_id}/items", response_model=TravelPlanItemResponse)
async def add_travel_plan_item(
    plan_id: int,
    item_data: TravelPlanItemCreate,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user),
):
    """添加行程项目(需拥有或管理员权限)"""
    service = TravelPlanService(db)
    plan = await service.get_travel_plan(plan_id)
    if not plan:
        raise HTTPException(status_code=404, detail="旅行计划不存在")
    if not (is_admin(current_user) or plan.user_id == current_user.id):
        raise HTTPException(status_code=403, detail="无权添加行程项目")

    item = await service.add_item(plan_id, item_data.model_dump())
    if not item:
        raise HTTPException(status_code=500, detail="添加行程项目失败")
    return TravelPlanItemResponse.from_orm(item)


@router.get("/{plan_id}/items", response_model=List[TravelPlanItemResponse])
async def get_travel_plan_items(
    plan_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user),
):
    """获取行程的所有项目(需拥有或管理员权限)"""
    service = TravelPlanService(db)
    plan = await service.get_travel_plan(plan_id)
    if not plan:
        raise HTTPException(status_code=404, detail="旅行计划不存在")
    if not (is_admin(current_user) or plan.user_id == current_user.id):
        raise HTTPException(status_code=403, detail="无权查看行程项目")

    items = await service.get_items_by_plan(plan_id)
    return [TravelPlanItemResponse.from_orm(item) for item in items]


@router.get("/{plan_id}/items/{item_id}", response_model=TravelPlanItemResponse)
async def get_travel_plan_item(
    plan_id: int,
    item_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user),
):
    """获取单个行程项目(需拥有或管理员权限)"""
    service = TravelPlanService(db)
    plan = await service.get_travel_plan(plan_id)
    if not plan:
        raise HTTPException(status_code=404, detail="旅行计划不存在")
    if not (is_admin(current_user) or plan.user_id == current_user.id):
        raise HTTPException(status_code=403, detail="无权查看行程项目")

    item = await service.get_item(item_id)
    if not item or item.travel_plan_id != plan_id:
        raise HTTPException(status_code=404, detail="行程项目不存在")
    return TravelPlanItemResponse.from_orm(item)


@router.put("/{plan_id}/items/{item_id}", response_model=TravelPlanItemResponse)
async def update_travel_plan_item(
    plan_id: int,
    item_id: int,
    item_data: TravelPlanItemUpdate,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user),
):
    """更新行程项目(需拥有或管理员权限)"""
    service = TravelPlanService(db)
    plan = await service.get_travel_plan(plan_id)
    if not plan:
        raise HTTPException(status_code=404, detail="旅行计划不存在")
    if not (is_admin(current_user) or plan.user_id == current_user.id):
        raise HTTPException(status_code=403, detail="无权更新行程项目")

    item = await service.get_item(item_id)
    if not item or item.travel_plan_id != plan_id:
        raise HTTPException(status_code=404, detail="行程项目不存在")

    updated_item = await service.update_item(item_id, item_data.model_dump(exclude_unset=True))
    return TravelPlanItemResponse.from_orm(updated_item)


@router.delete("/{plan_id}/items/{item_id}")
async def delete_travel_plan_item(
    plan_id: int,
    item_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user),
):
    """删除行程项目(需拥有或管理员权限)"""
    service = TravelPlanService(db)
    plan = await service.get_travel_plan(plan_id)
    if not plan:
        raise HTTPException(status_code=404, detail="旅行计划不存在")
    if not (is_admin(current_user) or plan.user_id == current_user.id):
        raise HTTPException(status_code=403, detail="无权删除行程项目")

    item = await service.get_item(item_id)
    if not item or item.travel_plan_id != plan_id:
        raise HTTPException(status_code=404, detail="行程项目不存在")

    success = await service.delete_item(item_id)
    if not success:
        raise HTTPException(status_code=500, detail="删除行程项目失败")
    return {"message": "行程项目已删除"}


@router.put("/{plan_id}/items/reorder")
async def reorder_travel_plan_items(
    plan_id: int,
    request_data: ReorderItemsRequest,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user),
):
    """重排序行程项目(需拥有或管理员权限)"""
    service = TravelPlanService(db)
    plan = await service.get_travel_plan(plan_id)
    if not plan:
        raise HTTPException(status_code=404, detail="旅行计划不存在")
    if not (is_admin(current_user) or plan.user_id == current_user.id):
        raise HTTPException(status_code=403, detail="无权重排序行程项目")

    success = await service.reorder_items(plan_id, request_data.item_ids)
    if not success:
        raise HTTPException(status_code=400, detail="重排序失败，请检查项目ID是否正确")
    return {"message": "行程项目已重新排序"}