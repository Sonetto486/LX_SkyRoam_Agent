from typing import Any, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from app.core.database import get_async_db
import random

router = APIRouter()

@router.get("/", response_model=Any)
async def get_notes(
    db: AsyncSession = Depends(get_async_db),
    keyword: Optional[str] = Query(None, description="Search destination keyword"),
    limit: int = Query(24, description="Number of notes to return"),
    is_random: bool = Query(False, description="Whether to return random notes")
) -> Any:
    """
    Get travel notes from the xhs_notes table.
    """
    try:
        # Base query using raw SQL
        query_str = "SELECT id, destination, transport_info, accommodation_info, must_visit_spots, food_recommendations, practical_tips, travel_feelings FROM xhs_notes"
        params = {}
        
        if keyword:
            query_str += " WHERE destination LIKE :keyword OR must_visit_spots LIKE :keyword"
            params["keyword"] = f"%{keyword}%"
            
        if is_random:
            query_str += " ORDER BY RANDOM()"
        else:
            query_str += " ORDER BY id DESC"
            
        query_str += f" LIMIT :limit"
        params["limit"] = limit
        
        result = await db.execute(text(query_str), params)
        rows = result.fetchall()
        
        notes_list = []
        for row in rows:
            notes_list.append({
                "id": row.id,
                "destination": row.destination,
                "transport_info": row.transport_info,
                "accommodation_info": row.accommodation_info,
                "must_visit_spots": row.must_visit_spots,
                "food_recommendations": row.food_recommendations,
                "practical_tips": row.practical_tips,
                "travel_feelings": row.travel_feelings,
                # Random image seed based on ID for UI placeholder
                "image_url": f"https://picsum.photos/seed/note_{row.id}/800/600",
                # Create a concise title from destination and spots
                "title": f"【{row.destination}】{str(row.must_visit_spots)[:20]}..." if row.must_visit_spots else f"{row.destination}游记"
            })
            
        return {
            "total": len(notes_list),
            "items": notes_list
        }
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Failed to fetch notes: {str(e)}")
