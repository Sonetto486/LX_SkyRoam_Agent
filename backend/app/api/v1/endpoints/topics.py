"""
Topic (专题) API 接口
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from typing import List, Dict, Any, Optional

from fastapi import APIRouter, Depends, HTTPException, status, Response, Query

from app.core.database import get_async_db

router = APIRouter()

@router.get("", summary="获取所有精选专题列表")
async def get_topics(
    response: Response, 
    keyword: Optional[str] = Query(None, description="搜索关键字"),
    continent: Optional[str] = Query("all", description="大洲筛选: all, asia, europe..."),
    db: AsyncSession = Depends(get_async_db)
):
    # 防止浏览器缓存影响我们调试数据更新
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    try:
        # 构建动态 SQL 查询
        query_sql = "SELECT id, name, intro, cover_url, region, continent FROM topic WHERE 1=1"
        params = {}
        
        if keyword:
            query_sql += """ AND (
                name ILIKE :keyword 
                OR intro ILIKE :keyword 
                OR region ILIKE :keyword
                OR EXISTS (
                    SELECT 1 FROM topic_place tp
                    JOIN destinations d ON tp.related_type = 'destinations' AND tp.related_id = d.id
                    WHERE tp.topic_id = topic.id AND (d.name ILIKE :keyword OR d.description ILIKE :keyword)
                )
                OR EXISTS (
                    SELECT 1 FROM topic_place tp
                    JOIN attractions a ON tp.related_type = 'attractions' AND tp.related_id = a.id
                    WHERE tp.topic_id = topic.id AND (a.name ILIKE :keyword OR a.description ILIKE :keyword)
                )
            )"""
            params["keyword"] = f"%{keyword}%"
            
        if continent and continent != "all":
            query_sql += " AND continent = :continent"
            params["continent"] = continent
            
        query_sql += " ORDER BY id ASC"
        
        # 执行原生 SQL 查询
        result = await db.execute(text(query_sql), params)
        topics = result.fetchall()
        
        # 将结果转换为前端需要的 JSON 格式
        response_data = []
        for row in topics:
            response_data.append({
                "id": row.id,
                "title": row.name,
                "image": row.cover_url,
                "tags": [row.region, "精选专题"] if row.region else ["精选专题"],
                "description": row.intro
            })
            
        return response_data
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取专题数据失败: {str(e)}"
        )

@router.get("/{topic_id}", summary="获取单个专题及包含的景点详情")
async def get_topic_detail(topic_id: int, response: Response, db: AsyncSession = Depends(get_async_db)):
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    try:
        # 获取专题基本信息
        topic_result = await db.execute(text("SELECT id, name, intro, cover_url, region FROM topic WHERE id = :id"), {"id": topic_id})
        topic = topic_result.fetchone()
        
        if not topic:
            raise HTTPException(status_code=404, detail="专题未找到")
            
        # 查询属于这个专题的所有的目的地和景点
        # 这里用 Union 来拼接景点和目的地的数据
        places_sql = """
        SELECT 
            tp.id as map_id, 
            tp.related_type, 
            tp.related_id,
            tp.highlight_info,
            tp.order_index,
            tp.is_key_point,
            a.name as place_name,
            a.images as image_url,
            a.rating,
            a.description
        FROM topic_place tp
        INNER JOIN attractions a ON tp.related_type = 'attractions' AND tp.related_id = a.id
        WHERE tp.topic_id = :topic_id
        
        UNION ALL
        
        SELECT 
            tp.id as map_id, 
            tp.related_type, 
            tp.related_id,
            tp.highlight_info,
            tp.order_index,
            tp.is_key_point,
            d.name as place_name,
            '[]' as image_url, -- destinations 暂时没有图片字段
            d.popularity_score as rating,
            d.description
        FROM topic_place tp
        INNER JOIN destinations d ON tp.related_type = 'destinations' AND tp.related_id = d.id
        WHERE tp.topic_id = :topic_id
        
        ORDER BY order_index ASC
        """
        
        places_result = await db.execute(text(places_sql), {"topic_id": topic_id})
        places = places_result.fetchall()
        
        # 组装返回 JSON
        places_data = []
        for p in places:
            import json
            image_str = p.image_url if p.image_url else '[]'
            try:
                images = json.loads(image_str)
                cover_image = images[0] if isinstance(images, list) and len(images) > 0 else f"https://picsum.photos/seed/dest_{p.related_id}/800/600"
            except:
                cover_image = image_str if image_str and not image_str.startswith('[') else f"https://picsum.photos/seed/dest_{p.related_id}/800/600"
                
            places_data.append({
                "id": p.map_id,
                "relatedId": p.related_id,
                "type": p.related_type,
                "name": p.place_name,
                "description": p.description or p.highlight_info,
                "highlight": p.highlight_info,
                "image": cover_image,
                "rating": float(p.rating) if p.rating else 4.5,
                "isKeyPoint": p.is_key_point
            })
            
        return {
            "id": topic.id,
            "title": topic.name,
            "image": topic.cover_url,
            "tags": [topic.region, "精选专题"] if topic.region else ["精选专题"],
            "description": topic.intro,
            "places": places_data
        }
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取专题详情失败: {str(e)}"
        )


@router.get("/places/{place_type}/{place_id}", summary="获取地点更详细信息")
async def get_place_detail(place_type: str, place_id: int, response: Response, db: AsyncSession = Depends(get_async_db)):
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    try:
        import json

        def first_image(raw_value, fallback: str):
            if not raw_value:
                return fallback
            try:
                if isinstance(raw_value, str):
                    parsed = json.loads(raw_value)
                else:
                    parsed = raw_value
                if isinstance(parsed, list) and parsed:
                    return parsed[0]
                if isinstance(parsed, str) and parsed:
                    return parsed
            except Exception:
                if isinstance(raw_value, str) and raw_value.startswith("http"):
                    return raw_value
            return fallback

        if place_type == "destinations":
            dest_result = await db.execute(
                text("""
                    SELECT id, name, country, city, region, latitude, longitude,
                           description, highlights, best_time_to_visit, popularity_score,
                           safety_score, cost_level
                    FROM destinations
                    WHERE id = :id
                """),
                {"id": place_id}
            )
            dest = dest_result.fetchone()
            if not dest:
                raise HTTPException(status_code=404, detail="目的地不存在")

            attraction_result = await db.execute(
                text("""
                    SELECT id, name, category, description, address, latitude, longitude,
                           opening_hours, ticket_price, currency, rating, review_count,
                           features, accessibility, contact_info, images, website
                    FROM attractions
                    WHERE destination_id = :id
                    ORDER BY rating DESC NULLS LAST, review_count DESC NULLS LAST, id ASC
                    LIMIT 6
                """),
                {"id": place_id}
            )
            attractions = attraction_result.fetchall()

            return {
                "type": "destinations",
                "id": dest.id,
                "name": dest.name,
                "coverImage": f"https://picsum.photos/seed/destination_{dest.id}/1600/900",
                "summary": dest.description,
                "destination": {
                    "country": dest.country,
                    "city": dest.city,
                    "region": dest.region,
                    "latitude": float(dest.latitude) if dest.latitude is not None else None,
                    "longitude": float(dest.longitude) if dest.longitude is not None else None,
                    "highlights": dest.highlights or [],
                    "bestTimeToVisit": dest.best_time_to_visit,
                    "popularityScore": float(dest.popularity_score) if dest.popularity_score is not None else 0,
                    "safetyScore": float(dest.safety_score) if dest.safety_score is not None else None,
                    "costLevel": dest.cost_level,
                    "images": [],
                    "videos": [],
                },
                "relatedAttractions": [
                    {
                        "id": row.id,
                        "name": row.name,
                        "category": row.category,
                        "description": row.description,
                        "address": row.address,
                        "rating": float(row.rating) if row.rating is not None else None,
                        "reviewCount": row.review_count,
                        "image": first_image(row.images, f"https://picsum.photos/seed/attr_{row.id}/800/600"),
                    }
                    for row in attractions
                ]
            }

        if place_type == "attractions":
            attr_result = await db.execute(
                text("""
                    SELECT a.id, a.name, a.category, a.description, a.address, a.latitude, a.longitude,
                           a.opening_hours, a.ticket_price, a.currency, a.rating, a.review_count,
                           a.features, a.accessibility, a.contact_info, a.images, a.website,
                           d.id AS destination_id, d.name AS destination_name, d.country, d.city, d.region
                    FROM attractions a
                    LEFT JOIN destinations d ON a.destination_id = d.id
                    WHERE a.id = :id
                """),
                {"id": place_id}
            )
            row = attr_result.fetchone()
            if not row:
                raise HTTPException(status_code=404, detail="景点不存在")

            return {
                "type": "attractions",
                "id": row.id,
                "name": row.name,
                "coverImage": first_image(row.images, f"https://picsum.photos/seed/attr_{row.id}/1600/900"),
                "summary": row.description,
                "attraction": {
                    "category": row.category,
                    "description": row.description,
                    "address": row.address,
                    "latitude": float(row.latitude) if row.latitude is not None else None,
                    "longitude": float(row.longitude) if row.longitude is not None else None,
                    "openingHours": row.opening_hours,
                    "ticketPrice": float(row.ticket_price) if row.ticket_price is not None else None,
                    "currency": row.currency,
                    "rating": float(row.rating) if row.rating is not None else None,
                    "reviewCount": row.review_count,
                    "features": row.features,
                    "accessibility": row.accessibility,
                    "contactInfo": row.contact_info,
                    "website": row.website,
                    "images": json.loads(row.images) if row.images else [],
                },
                "destination": {
                    "id": row.destination_id,
                    "name": row.destination_name,
                    "country": row.country,
                    "city": row.city,
                    "region": row.region,
                }
            }

        raise HTTPException(status_code=400, detail="不支持的地点类型")
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"获取地点详情失败: {str(e)}")
