"""
预生成方案 Pydantic Schema
"""

from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime


class PreGeneratedPlanBase(BaseModel):
    """预生成方案基础模型"""
    destination_name: str = Field(..., description="目的地城市名")
    duration_days: int = Field(..., ge=1, le=30, description="行程天数")
    budget_level: str = Field(..., description="预算等级: economy/comfortable/luxury")
    plan_template: Dict[str, Any] = Field(..., description="方案模板数据")
    travel_preferences: Optional[List[str]] = Field(None, description="旅行偏好")
    age_groups: Optional[List[str]] = Field(None, description="年龄组")
    food_preferences: Optional[List[str]] = Field(None, description="饮食偏好")
    transportation_mode: Optional[str] = Field(None, description="交通方式")


class PreGeneratedPlanCreate(PreGeneratedPlanBase):
    """创建预生成方案"""
    destination_id: Optional[int] = None
    popularity_score: Optional[float] = 0.0
    data_sources: Optional[Dict[str, bool]] = None


class PreGeneratedPlanResponse(PreGeneratedPlanBase):
    """预生成方案响应"""
    id: int
    destination_id: Optional[int] = None
    popularity_score: float = 0.0
    generation_version: Optional[str] = None
    status: str = "active"
    match_count: int = 0
    usage_count: int = 0
    avg_rating: Optional[float] = None
    expires_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class PreGeneratedPlanMatch(BaseModel):
    """预生成方案匹配结果"""
    plan: Optional[Dict[str, Any]] = None
    match_score: float = Field(..., description="匹配分数")
    source: str = Field(..., description="来源: pre_generated/real_time")
    can_customize: bool = Field(False, description="是否可自定义")
    suggestion: Optional[str] = Field(None, description="建议信息")


class HotDestinationBase(BaseModel):
    """热门城市基础模型"""
    city_name: str = Field(..., description="城市名称")
    province: Optional[str] = Field(None, description="省份")
    region: Optional[str] = Field(None, description="区域")
    priority: int = Field(100, description="优先级")
    is_enabled: bool = Field(True, description="是否启用")
    popularity_score: float = Field(0.0, description="热度分数")
    tags: Optional[str] = Field(None, description="城市标签")


class HotDestinationCreate(HotDestinationBase):
    """创建热门城市"""
    monthly_visitors: Optional[int] = None
    search_volume: Optional[int] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None


class HotDestinationResponse(HotDestinationBase):
    """热门城市响应"""
    id: int
    monthly_visitors: Optional[int] = None
    search_volume: Optional[int] = None
    pre_generated_count: int = 0
    last_pre_generated_at: Optional[datetime] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class PreGenerationStatus(BaseModel):
    """预生成状态"""
    total_destinations: int = Field(0, description="热门城市总数")
    generated_destinations: int = Field(0, description="已生成城市数")
    total_plans: int = Field(0, description="总方案数")
    active_plans: int = Field(0, description="活跃方案数")
    expired_plans: int = Field(0, description="过期方案数")
    last_generation_time: Optional[datetime] = None
    is_generating: bool = False