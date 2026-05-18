from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from app.tools.smart_planner import SmartPlanner
from app.core.security import get_current_user
from app.models.user import User

router = APIRouter()

class LocationInput(BaseModel):
    id: int
    name: str
    lat: float
    lng: float
    type: str
    estimated_duration: Optional[float] = Field(default=1.0)
    address: Optional[str] = Field(default="")

class SmartPlanRequest(BaseModel):
    locations: List[LocationInput]
    days: int = Field(ge=1, le=14)
    return_to_hotel: Optional[bool] = Field(default=True)

class AccommodationRecommendation(BaseModel):
    center_lat: float
    center_lng: float
    average_distance_km: float
    nearby_attractions: List[Dict[str, Any]]
    message: str

class SmartPlanResponse(BaseModel):
    success: bool
    daily_plans: List[Dict[str, Any]]
    warnings: List[str]
    use_virtual_hotel: bool
    total_locations: int
    days: int
    accommodation_recommendation: AccommodationRecommendation

@router.post("/smart-plan", response_model=SmartPlanResponse)
async def smart_plan(
    request: SmartPlanRequest,
    current_user: User = Depends(get_current_user)
):
    """
    智能规划接口：根据用户勾选的地点自动生成合理的每日行程安排
    
    算法说明：
    1. 预处理：分离酒店、计算交通时间矩阵、设置默认游览时长
    2. 天分组：使用K-Means聚类将地点分配到各天
    3. 每天内排序：使用最近邻算法+2-opt优化生成最优路径
    4. 餐饮插入：根据时间窗口自动插入午餐和晚餐
    5. 交通时间：调用高德API获取步行、驾车、公交等真实交通时间
    
    参数：
    - locations: 用户勾选的地点列表
    - days: 计划天数
    - return_to_hotel: 是否返回酒店（默认True）
    """
    if not request.locations:
        raise HTTPException(status_code=400, detail="至少需要选择一个地点")
    
    if request.days < 1:
        raise HTTPException(status_code=400, detail="天数必须大于0")
    
    try:
        planner = SmartPlanner()
        
        # Convert to dict list
        locations = [loc.dict() for loc in request.locations]
        
        # Execute async planning with real traffic data from Amap
        result = await planner.plan_async(locations, request.days, request.return_to_hotel)
        
        return SmartPlanResponse(
            success=True,
            **result
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"规划失败: {str(e)}")