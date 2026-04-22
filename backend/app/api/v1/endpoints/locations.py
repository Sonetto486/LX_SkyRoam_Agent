from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List, Optional

from app.core.database import get_async_db
from app.models.location import Location

router = APIRouter()

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
            "location_name": loc.location_name,
            "latitude": float(loc.latitude) if loc.latitude else None,
            "longitude": float(loc.longitude) if loc.longitude else None,
            "description": loc.description,
            "location_type": loc.location_type,
            "open_time": loc.open_time,
            "phone": loc.phone,
            "website": loc.website,
            "address": loc.address,
            "added_by": loc.added_by,
            "media_images": loc.media_images,
            "facilities": loc.facilities
        }
        for loc in locations
    ]
