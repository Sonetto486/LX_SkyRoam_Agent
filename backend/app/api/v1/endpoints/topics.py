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
