from fastapi import APIRouter, Depends, Query, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_
from typing import List, Optional
import httpx
import logging

from app.core.database import get_async_db
from app.core.config import settings
from app.core.security import get_current_user
from app.models.location import Location
from app.models.travel_plan import FavoriteLocation
from app.models.user import User
from app.schemas.travel_plan import (
    FavoriteLocationCreate,
    FavoriteLocationUpdate,
    FavoriteLocationResponse,
    LocationSearchRequest,
    LocationSearchResponse,
    LocationSearchResult,
)

router = APIRouter()
logger = logging.getLogger(__name__)


# =============== 地点搜索相关 ===============

@router.get("/batch")
async def get_locations_batch(
    ids: str = Query(..., description="逗号分隔的地点ID列表，如 1,2,3"),
    db: AsyncSession = Depends(get_async_db)
):
    """
    批量获取地点信息，含经纬度
    """
    try:
        location_ids = [int(id_str.strip()) for id_str in ids.split(",") if id_str.strip().isdigit()]
    except ValueError:
        return []

    if not location_ids:
        return []

    result = await db.execute(select(Location).where(Location.location_id.in_(location_ids)))
    locations = result.scalars().all()

    return [
        {
            "id": loc.location_id,
            "name": loc.location_name,
            "latitude": float(loc.latitude) if loc.latitude else None,
            "longitude": float(loc.longitude) if loc.longitude else None,
        }
        for loc in locations
    ]


@router.post("/search", response_model=LocationSearchResponse)
async def search_locations(
    request: LocationSearchRequest,
    db: AsyncSession = Depends(get_async_db)
):
    """
    地点搜索 - 接入高德地图API
    """
    try:
        # 高德地图 POI 搜索 API
        amap_url = "https://restapi.amap.com/v3/place/text"

        params = {
            "key": settings.AMAP_API_KEY,
            "keywords": request.keyword,
            "offset": request.page_size,
            "page": request.page,
            "extensions": "all",  # 返回详细信息
        }

        # 添加城市限定
        if request.city:
            params["city"] = request.city

        # 添加类型过滤
        if request.category:
            # 高德类型编码映射
            category_map = {
                "attraction": "110000",  # 风景名胜
                "restaurant": "050000",  # 餐饮服务
                "hotel": "100000",       # 住宿服务
            }
            if request.category in category_map:
                params["types"] = category_map[request.category]

        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(amap_url, params=params)
            data = response.json()

        if data.get("status") != "1":
            logger.error(f"高德地图搜索失败: {data.get('info')}")
            return LocationSearchResponse(results=[], total=0, page=request.page, page_size=request.page_size)

        pois = data.get("pois", [])
        results = []

        for poi in pois:
            location = None
            if poi.get("location"):
                lng, lat = poi["location"].split(",")
                location = {"lat": float(lat), "lng": float(lng)}

            results.append(LocationSearchResult(
                id=poi.get("id"),
                name=poi.get("name", ""),
                address=poi.get("address"),
                location=location,
                category=_get_category_from_type(poi.get("typecode", "")),
                distance=float(poi.get("distance", 0)) if poi.get("distance") else None,
                tel=poi.get("tel"),
                rating=float(poi.get("biz_ext", {}).get("rating", 0)) if poi.get("biz_ext", {}).get("rating") else None,
                cost=float(poi.get("biz_ext", {}).get("cost", 0)) if poi.get("biz_ext", {}).get("cost") else None,
                type=poi.get("typecode"),
            ))

        total = int(data.get("count", 0))

        return LocationSearchResponse(
            results=results,
            total=total,
            page=request.page,
            page_size=request.page_size
        )

    except httpx.TimeoutException:
        logger.error("高德地图搜索超时")
        raise HTTPException(status_code=504, detail="地图服务超时")
    except Exception as e:
        logger.error(f"地点搜索失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"搜索失败: {str(e)}")


@router.post("/search/nearby", response_model=LocationSearchResponse)
async def search_nearby_locations(
    request: LocationSearchRequest,
    db: AsyncSession = Depends(get_async_db)
):
    """
    周边搜索 - 根据中心点坐标搜索附近地点
    """
    if not request.location:
        raise HTTPException(status_code=400, detail="周边搜索需要提供中心点坐标")

    try:
        amap_url = "https://restapi.amap.com/v3/place/around"

        params = {
            "key": settings.AMAP_API_KEY,
            "keywords": request.keyword,
            "location": f"{request.location['lng']},{request.location['lat']}",
            "radius": request.radius or 3000,  # 默认3公里
            "offset": request.page_size,
            "page": request.page,
            "extensions": "all",
        }

        if request.category:
            category_map = {
                "attraction": "110000",
                "restaurant": "050000",
                "hotel": "100000",
            }
            if request.category in category_map:
                params["types"] = category_map[request.category]

        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(amap_url, params=params)
            data = response.json()

        if data.get("status") != "1":
            logger.error(f"高德地图周边搜索失败: {data.get('info')}")
            return LocationSearchResponse(results=[], total=0, page=request.page, page_size=request.page_size)

        pois = data.get("pois", [])
        results = []

        for poi in pois:
            location = None
            if poi.get("location"):
                lng, lat = poi["location"].split(",")
                location = {"lat": float(lat), "lng": float(lng)}

            results.append(LocationSearchResult(
                id=poi.get("id"),
                name=poi.get("name", ""),
                address=poi.get("address"),
                location=location,
                category=_get_category_from_type(poi.get("typecode", "")),
                distance=float(poi.get("distance", 0)) if poi.get("distance") else None,
                tel=poi.get("tel"),
                rating=float(poi.get("biz_ext", {}).get("rating", 0)) if poi.get("biz_ext", {}).get("rating") else None,
                cost=float(poi.get("biz_ext", {}).get("cost", 0)) if poi.get("biz_ext", {}).get("cost") else None,
                type=poi.get("typecode"),
            ))

        total = int(data.get("count", 0))

        return LocationSearchResponse(
            results=results,
            total=total,
            page=request.page,
            page_size=request.page_size
        )

    except httpx.TimeoutException:
        logger.error("高德地图周边搜索超时")
        raise HTTPException(status_code=504, detail="地图服务超时")
    except Exception as e:
        logger.error(f"周边搜索失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"搜索失败: {str(e)}")


def _get_category_from_type(typecode: str) -> Optional[str]:
    """根据高德类型编码映射到应用分类"""
    if not typecode:
        return None

    # 高德类型编码前缀映射
    if typecode.startswith("05"):  # 餐饮服务
        return "restaurant"
    elif typecode.startswith("10"):  # 住宿服务
        return "hotel"
    elif typecode.startswith("11"):  # 风景名胜
        return "attraction"
    elif typecode.startswith("06"):  # 购物服务
        return "shopping"
    elif typecode.startswith("01"):  # 餐饮服务
        return "restaurant"

    return None


# =============== 收藏地点相关 ===============

@router.get("/favorites", response_model=List[FavoriteLocationResponse])
async def get_favorite_locations(
    category: Optional[str] = Query(None, description="按分类筛选"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db)
):
    """
    获取用户收藏的地点列表
    """
    query = select(FavoriteLocation).where(FavoriteLocation.user_id == current_user.id)

    if category:
        query = query.where(FavoriteLocation.category == category)

    query = query.order_by(FavoriteLocation.updated_at.desc())

    result = await db.execute(query)
    favorites = result.scalars().all()

    return favorites


@router.post("/favorites", response_model=FavoriteLocationResponse)
async def add_favorite_location(
    location: FavoriteLocationCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db)
):
    """
    添加收藏地点
    """
    # 检查是否已收藏（同一POI）
    if location.poi_id:
        existing = await db.execute(
            select(FavoriteLocation).where(
                and_(
                    FavoriteLocation.user_id == current_user.id,
                    FavoriteLocation.poi_id == location.poi_id
                )
            )
        )
        if existing.scalar_one_or_none():
            raise HTTPException(status_code=400, detail="该地点已收藏")

    favorite = FavoriteLocation(
        user_id=current_user.id,
        name=location.name,
        address=location.address,
        coordinates=location.coordinates,
        category=location.category,
        phone=location.phone,
        poi_id=location.poi_id,
        source=location.source or "manual",
        notes=location.notes,
    )

    db.add(favorite)
    await db.commit()
    await db.refresh(favorite)

    return favorite


@router.put("/favorites/{favorite_id}", response_model=FavoriteLocationResponse)
async def update_favorite_location(
    favorite_id: int,
    location: FavoriteLocationUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db)
):
    """
    更新收藏地点
    """
    result = await db.execute(
        select(FavoriteLocation).where(
            and_(
                FavoriteLocation.id == favorite_id,
                FavoriteLocation.user_id == current_user.id
            )
        )
    )
    favorite = result.scalar_one_or_none()

    if not favorite:
        raise HTTPException(status_code=404, detail="收藏地点不存在")

    update_data = location.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(favorite, key, value)

    await db.commit()
    await db.refresh(favorite)

    return favorite


@router.delete("/favorites/{favorite_id}")
async def delete_favorite_location(
    favorite_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db)
):
    """
    删除收藏地点
    """
    result = await db.execute(
        select(FavoriteLocation).where(
            and_(
                FavoriteLocation.id == favorite_id,
                FavoriteLocation.user_id == current_user.id
            )
        )
    )
    favorite = result.scalar_one_or_none()

    if not favorite:
        raise HTTPException(status_code=404, detail="收藏地点不存在")

    await db.delete(favorite)
    await db.commit()

    return {"message": "删除成功"}


@router.get("/favorites/check")
async def check_favorite(
    poi_id: str = Query(..., description="POI ID"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db)
):
    """
    检查地点是否已收藏
    """
    result = await db.execute(
        select(FavoriteLocation).where(
            and_(
                FavoriteLocation.user_id == current_user.id,
                FavoriteLocation.poi_id == poi_id
            )
        )
    )
    favorite = result.scalar_one_or_none()

    return {
        "is_favorite": favorite is not None,
        "favorite_id": favorite.id if favorite else None
    }
