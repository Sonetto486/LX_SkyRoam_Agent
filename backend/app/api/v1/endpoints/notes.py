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
    page: int = Query(1, description="Page number"),
    is_random: bool = Query(False, description="Whether to return random notes")
) -> Any:
    """
    Get travel notes from the xhs_notes table.
    """
    try:
        # Base count query
        count_query = "SELECT COUNT(*) FROM xhs_notes"
        count_params = {}
        if keyword:
            count_query += " WHERE destination LIKE :keyword OR must_visit_spots LIKE :keyword OR travel_feelings LIKE :keyword"
            count_params["keyword"] = f"%{keyword}%"
        
        count_result = await db.execute(text(count_query), count_params)
        total_count = count_result.scalar()

        # Base query using raw SQL
        query_str = "SELECT id, destination, transport_info, accommodation_info, must_visit_spots, food_recommendations, practical_tips, travel_feelings FROM xhs_notes"
        params = {}
        
        if keyword:
            query_str += " WHERE destination LIKE :keyword OR must_visit_spots LIKE :keyword OR travel_feelings LIKE :keyword"
            params["keyword"] = f"%{keyword}%"
            
        if is_random:
            query_str += " ORDER BY RANDOM()"
        else:
            query_str += " ORDER BY id DESC"
            
        # Add Pagination
        skip = (page - 1) * limit
        query_str += f" LIMIT :limit OFFSET :offset"
        params["limit"] = limit
        params["offset"] = skip
        
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
            "total": total_count,
            "page": page,
            "limit": limit,
            "items": notes_list
        }
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Failed to fetch notes: {str(e)}")

@router.get("/{note_id}", response_model=Any)
async def get_note_detail(
    note_id: int,
    db: AsyncSession = Depends(get_async_db)
) -> Any:
    """
    Get a single travel note detail by ID.
    """
    try:
        query_str = "SELECT id, destination, transport_info, accommodation_info, must_visit_spots, food_recommendations, practical_tips, travel_feelings FROM xhs_notes WHERE id = :id"
        result = await db.execute(text(query_str), {"id": note_id})
        row = result.fetchone()
        
        if not row:
            raise HTTPException(status_code=404, detail="Note not found")
            
        return {
            "id": row.id,
            "destination": row.destination,
            "transport_info": row.transport_info,
            "accommodation_info": row.accommodation_info,
            "must_visit_spots": row.must_visit_spots,
            "food_recommendations": row.food_recommendations,
            "practical_tips": row.practical_tips,
            "travel_feelings": row.travel_feelings,
            "image_url": f"https://picsum.photos/seed/note_{row.id}/800/600",
            "title": f"【{row.destination}】{str(row.must_visit_spots)[:30]}..." if row.must_visit_spots else f"{row.destination}游记"
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch note detail: {str(e)}")
