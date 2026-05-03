"""
旅行计划数据模式
"""

from pydantic import BaseModel, Field, field_validator
from typing import Optional, List, Dict, Any
from datetime import datetime


class TravelPlanBase(BaseModel):
    """旅行计划基础模式"""
    title: str = Field(..., description="计划标题")
    description: Optional[str] = Field(None, description="计划描述")
    departure: Optional[str] = Field(None, description="出发地")
    destination: str = Field(..., description="目的地")
    start_date: datetime = Field(..., description="开始日期")
    end_date: datetime = Field(..., description="结束日期")

    @field_validator('start_date', 'end_date', mode='before')
    @classmethod
    def parse_datetime(cls, v):
        """解析日期时间，确保无时区信息"""
        if isinstance(v, str):
            # 解析字符串格式的日期时间
            try:
                # 尝试解析带时区的格式
                if 'T' in v or '+' in v or 'Z' in v:
                    dt = datetime.fromisoformat(v.replace('Z', '+00:00'))
                    # 转换为无时区的本地时间
                    return dt.replace(tzinfo=None)
                else:
                    # 解析无时区格式
                    return datetime.fromisoformat(v)
            except ValueError:
                # 如果解析失败，尝试其他格式
                from dateutil import parser
                dt = parser.parse(v)
                return dt.replace(tzinfo=None)
        return v
    duration_days: int = Field(..., description="旅行天数")
    budget: Optional[float] = Field(None, description="预算")
    transportation: Optional[str] = Field(None, description="出行方式")
    preferences: Optional[Dict[str, Any]] = Field(None, description="用户偏好（应包含travelers、ageGroups等信息）")
    requirements: Optional[Dict[str, Any]] = Field(None, description="特殊要求")

    # 新增：行程扩展信息
    cities: Optional[List[str]] = Field(None, description="途经城市列表")
    members: Optional[List[Dict[str, Any]]] = Field(None, description="参与成员")
    packing_list: Optional[List[Dict[str, Any]]] = Field(None, description="物品清单")
    travel_mode: Optional[str] = Field(None, description="出行方式: flight, train, car, bus")
    tags: Optional[List[str]] = Field(None, description="行程标签")


class TravelPlanCreateRequest(TravelPlanBase):
    """创建旅行计划请求体（不含用户ID）"""
    pass


class TravelPlanCreate(TravelPlanBase):
    """创建旅行计划模式"""
    user_id: int = Field(..., description="用户ID")


class TravelPlanUpdate(BaseModel):
    """更新旅行计划模式"""
    title: Optional[str] = None
    description: Optional[str] = None
    destination: Optional[str] = None
    # 新增：支持更新出发地
    departure: Optional[str] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    duration_days: Optional[int] = None
    budget: Optional[float] = None
    transportation: Optional[str] = None
    preferences: Optional[Dict[str, Any]] = None
    requirements: Optional[Dict[str, Any]] = None
    status: Optional[str] = None
    # 新增：行程扩展信息
    cities: Optional[List[str]] = None
    members: Optional[List[Dict[str, Any]]] = None
    packing_list: Optional[List[Dict[str, Any]]] = None
    travel_mode: Optional[str] = None
    tags: Optional[List[str]] = None


class TravelPlanItemResponse(BaseModel):
    """旅行计划项目响应模式"""
    id: int
    title: str
    description: Optional[str] = None
    item_type: str
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    duration_hours: Optional[float] = None
    location: Optional[str] = None
    address: Optional[str] = None
    coordinates: Optional[Dict[str, float]] = None
    details: Optional[Dict[str, Any]] = None
    images: Optional[List[str]] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class TravelPlanResponse(TravelPlanBase):
    """旅行计划响应模式"""
    id: int
    user_id: int
    status: str
    score: Optional[float] = None
    generated_plans: Optional[List[Dict[str, Any]]] = None
    selected_plan: Optional[Dict[str, Any]] = None
    created_at: datetime
    updated_at: datetime
    items: Optional[List[TravelPlanItemResponse]] = None
    # 新增：公开字段
    is_public: bool = False
    public_at: Optional[datetime] = None

    class Config:
        from_attributes = True
        
    @classmethod
    def from_orm(cls, obj):
        """自定义ORM转换"""
        data = {
            'id': obj.id,
            'title': obj.title,
            'description': obj.description,
            'departure': obj.departure,
            'destination': obj.destination,
            'start_date': obj.start_date,
            'end_date': obj.end_date,
            'duration_days': obj.duration_days,
            'budget': obj.budget,
            'transportation': obj.transportation,
            'preferences': obj.preferences,
            'requirements': obj.requirements,
            'user_id': obj.user_id,
            'status': obj.status,
            'score': obj.score,
            'generated_plans': obj.generated_plans,
            'selected_plan': obj.selected_plan,
            'created_at': obj.created_at,
            'updated_at': obj.updated_at,
            'items': [],  # items 由 API 层单独处理
            'is_public': getattr(obj, 'is_public', False),
            'public_at': getattr(obj, 'public_at', None),
            # 新增：行程扩展信息
            'cities': getattr(obj, 'cities', None),
            'members': getattr(obj, 'members', None),
            'packing_list': getattr(obj, 'packing_list', None),
            'travel_mode': getattr(obj, 'travel_mode', None),
            'tags': getattr(obj, 'tags', None),
        }
        return cls(**data)


class TravelPlanGenerateRequest(BaseModel):
    """生成旅行方案请求模式"""
    preferences: Optional[Dict[str, Any]] = Field(None, description="生成偏好")
    requirements: Optional[Dict[str, Any]] = Field(None, description="特殊要求")
    num_plans: int = Field(3, description="生成方案数量", ge=1, le=10)


class TravelPlanListResponse(BaseModel):
    """旅行计划列表响应模式"""
    plans: List[TravelPlanResponse]
    total: int
    page: int
    page_size: int


class TravelPlanExportRequest(BaseModel):
    """导出旅行计划请求模式"""
    format: str = Field("pdf", description="导出格式", pattern="^(pdf|json|html)$")
    include_images: bool = Field(True, description="是否包含图片")
    include_map: bool = Field(True, description="是否包含地图")
    language: str = Field("zh", description="导出语言")


class TravelPlanBatchDeleteRequest(BaseModel):
    """批量删除旅行计划请求体"""
    ids: List[int] = Field(..., description="要删除的旅行计划ID列表", min_length=1)

# =============== 评分相关模式 ===============
class TravelPlanRatingCreate(BaseModel):
    """创建/更新评分请求体"""
    score: int = Field(..., ge=1, le=5, description="评分(1-5)")
    comment: Optional[str] = Field(None, description="评分备注")

class TravelPlanRatingResponse(BaseModel):
    """评分记录响应"""
    id: int
    travel_plan_id: int
    user_id: int
    score: int
    comment: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class TravelPlanRatingSummary(BaseModel):
    """评分汇总响应"""
    average: float
    count: int


# =============== 行程项目相关模式 ===============
class TravelPlanItemBase(BaseModel):
    """行程项目基础模式"""
    title: str = Field(..., description="项目标题")
    description: Optional[str] = Field(None, description="项目描述")
    item_type: str = Field(..., description="项目类型: attraction, restaurant, hotel, transport, shopping, entertainment, other")
    start_time: Optional[datetime] = Field(None, description="开始时间")
    end_time: Optional[datetime] = Field(None, description="结束时间")
    location: Optional[str] = Field(None, description="地点名称")
    address: Optional[str] = Field(None, description="详细地址")
    coordinates: Optional[Dict[str, float]] = Field(None, description="坐标 {lat, lng}")
    details: Optional[Dict[str, Any]] = Field(None, description="详细信息")
    images: Optional[List[str]] = Field(None, description="图片URL列表")
    # 新增：地点扩展信息
    opening_hours: Optional[Dict[str, Any]] = Field(None, description="开放时间")
    phone: Optional[str] = Field(None, description="联系电话")
    website: Optional[str] = Field(None, description="网址")
    facilities: Optional[List[str]] = Field(None, description="服务设施")
    priority: Optional[str] = Field(None, description="优先级: must, optional, backup")

    @field_validator('start_time', 'end_time', mode='before')
    @classmethod
    def parse_datetime(cls, v):
        """解析日期时间字符串"""
        if v is None or isinstance(v, datetime):
            return v
        if isinstance(v, str):
            try:
                # 尝试解析 ISO 格式
                if 'T' in v:
                    dt = datetime.fromisoformat(v.replace('Z', '+00:00'))
                    return dt.replace(tzinfo=None)
                return datetime.fromisoformat(v)
            except ValueError:
                pass
        return v


class TravelPlanItemCreate(TravelPlanItemBase):
    """创建行程项目请求"""
    pass


class TravelPlanItemUpdate(BaseModel):
    """更新行程项目请求"""
    title: Optional[str] = None
    description: Optional[str] = None
    item_type: Optional[str] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    location: Optional[str] = None
    address: Optional[str] = None
    coordinates: Optional[Dict[str, float]] = None
    details: Optional[Dict[str, Any]] = None
    images: Optional[List[str]] = None
    # 新增：地点扩展信息
    opening_hours: Optional[Dict[str, Any]] = None
    phone: Optional[str] = None
    website: Optional[str] = None
    facilities: Optional[List[str]] = None
    priority: Optional[str] = None

    @field_validator('start_time', 'end_time', mode='before')
    @classmethod
    def parse_datetime(cls, v):
        """解析日期时间字符串"""
        if v is None or isinstance(v, datetime):
            return v
        if isinstance(v, str):
            try:
                if 'T' in v:
                    dt = datetime.fromisoformat(v.replace('Z', '+00:00'))
                    return dt.replace(tzinfo=None)
                return datetime.fromisoformat(v)
            except ValueError:
                pass
        return v


class TravelPlanItemResponse(TravelPlanItemBase):
    """行程项目响应"""
    id: int
    travel_plan_id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# =============== 收藏地点相关模式 ===============
class FavoriteLocationBase(BaseModel):
    """收藏地点基础模式"""
    name: str = Field(..., description="地点名称")
    address: Optional[str] = Field(None, description="地址")
    coordinates: Optional[Dict[str, float]] = Field(None, description="坐标 {lat, lng}")
    category: Optional[str] = Field(None, description="分类: attraction, restaurant, hotel")
    phone: Optional[str] = Field(None, description="电话")
    poi_id: Optional[str] = Field(None, description="POI ID")
    source: Optional[str] = Field(None, description="来源: amap, baidu, manual")
    notes: Optional[str] = Field(None, description="备注")


class FavoriteLocationCreate(FavoriteLocationBase):
    """创建收藏地点请求"""
    pass


class FavoriteLocationUpdate(BaseModel):
    """更新收藏地点请求"""
    name: Optional[str] = None
    address: Optional[str] = None
    coordinates: Optional[Dict[str, float]] = None
    category: Optional[str] = None
    phone: Optional[str] = None
    notes: Optional[str] = None


class FavoriteLocationResponse(FavoriteLocationBase):
    """收藏地点响应"""
    id: int
    user_id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# =============== 地点搜索相关模式 ===============
class LocationSearchRequest(BaseModel):
    """地点搜索请求"""
    keyword: str = Field(..., description="搜索关键词", min_length=1)
    city: Optional[str] = Field(None, description="城市名称，用于限定搜索范围")
    location: Optional[Dict[str, float]] = Field(None, description="中心点坐标 {lat, lng}，用于周边搜索")
    radius: Optional[int] = Field(None, description="搜索半径（米），配合location使用")
    category: Optional[str] = Field(None, description="地点类型: attraction, restaurant, hotel")
    page: int = Field(1, ge=1, description="页码")
    page_size: int = Field(20, ge=1, le=50, description="每页数量")


class LocationSearchResult(BaseModel):
    """地点搜索结果"""
    id: Optional[str] = Field(None, description="POI ID")
    name: str = Field(..., description="地点名称")
    address: Optional[str] = Field(None, description="地址")
    location: Optional[Dict[str, float]] = Field(None, description="坐标 {lat, lng}")
    category: Optional[str] = Field(None, description="分类")
    distance: Optional[float] = Field(None, description="距离（米）")
    tel: Optional[str] = Field(None, description="电话")
    rating: Optional[float] = Field(None, description="评分")
    cost: Optional[float] = Field(None, description="人均消费")
    type: Optional[str] = Field(None, description="类型编码")


class LocationSearchResponse(BaseModel):
    """地点搜索响应"""
    results: List[LocationSearchResult] = Field(default_factory=list, description="搜索结果列表")
    total: int = Field(0, description="总数量")
    page: int = Field(1, description="当前页码")
    page_size: int = Field(20, description="每页数量")
