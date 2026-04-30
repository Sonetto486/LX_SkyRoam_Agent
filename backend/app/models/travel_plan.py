"""
旅行计划模型
"""

from sqlalchemy import Column, String, Text, Integer, Float, DateTime, ForeignKey, JSON, Boolean
from sqlalchemy.orm import relationship
from datetime import datetime
from app.models.base import BaseModel


class TravelPlan(BaseModel):
    """旅行计划模型"""
    __tablename__ = "travel_plans"
    
    # 基本信息
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    
    # 旅行参数
    departure = Column(String(100), nullable=True)  # 出发地（可选）
    destination = Column(String(100), nullable=False)
    start_date = Column(DateTime, nullable=False)
    end_date = Column(DateTime, nullable=False)
    duration_days = Column(Integer, nullable=False)
    budget = Column(Float, nullable=True)
    transportation = Column(String(50), nullable=True)  # 出行方式
    
    # 用户偏好
    preferences = Column(JSON, nullable=True)  # 存储用户偏好设置
    requirements = Column(JSON, nullable=True)  # 存储特殊要求
    
    # 方案数据
    generated_plans = Column(JSON, nullable=True)  # 存储生成的多个方案
    selected_plan = Column(JSON, nullable=True)    # 用户选择的最终方案
    
    # 状态
    status = Column(String(20), default="draft", nullable=False)  # draft, generating, completed, archived
    score = Column(Float, nullable=True)  # 方案评分

    # 公开
    is_public = Column(Boolean, default=False, nullable=False)
    public_at = Column(DateTime, nullable=True)

    # 新增：行程扩展信息
    cities = Column(JSON, nullable=True)  # 途经城市列表 ["城市1", "城市2"]
    members = Column(JSON, nullable=True)  # 参与成员 [{"name": "张三", "role": "组织者", "avatar": "url"}]
    packing_list = Column(JSON, nullable=True)  # 物品清单 [{"name": "护照", "category": "证件", "checked": false}]
    travel_mode = Column(String(50), nullable=True)  # 出行方式: flight, train, car, bus, self_drive
    tags = Column(JSON, nullable=True)  # 行程标签 ["蜜月", "亲子", "自驾"]

    # 关联关系
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    user = relationship("User", back_populates="travel_plans")
    
    items = relationship("TravelPlanItem", back_populates="travel_plan", cascade="all, delete-orphan")
    # 新增：用户评分关系
    ratings = relationship("TravelPlanRating", back_populates="travel_plan", cascade="all, delete-orphan")

    @staticmethod
    def _as_dict(value):
        return value if isinstance(value, dict) else {}

    def _get_preference_value(self, key):
        """从preferences中获取指定字段"""
        prefs = self._as_dict(getattr(self, "preferences", None))
        value = prefs.get(key)
        return value if value not in ("", None) else None

    def _get_list_value(self, key):
        value = self._get_preference_value(key)
        if value is None:
            return None
        if isinstance(value, list):
            return value
        if isinstance(value, str):
            return [value]
        return None

    @property
    def travelers(self):
        value = self._get_preference_value("travelers")
        if value is None:
            return 1
        try:
            return int(value)
        except (TypeError, ValueError):
            return 1

    @property
    def ageGroups(self):
        return self._get_list_value("ageGroups")

    @property
    def foodPreferences(self):
        return self._get_list_value("foodPreferences")

    @property
    def dietaryRestrictions(self):
        return self._get_list_value("dietaryRestrictions")
    
    def __repr__(self):
        try:
            # 安全地获取属性，避免触发懒加载
            obj_id = getattr(self, 'id', 'N/A')
            return f"<TravelPlan(id={obj_id})>"
        except Exception:
            return f"<TravelPlan(instance)>"


class TravelPlanItem(BaseModel):
    """旅行计划项目模型"""
    __tablename__ = "travel_plan_items"
    
    # 基本信息
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    item_type = Column(String(50), nullable=False)  # flight, hotel, attraction, restaurant, transport
    
    # 时间安排
    start_time = Column(DateTime, nullable=True)
    end_time = Column(DateTime, nullable=True)
    duration_hours = Column(Float, nullable=True)
    
    # 位置信息
    location = Column(String(200), nullable=True)
    address = Column(Text, nullable=True)
    coordinates = Column(JSON, nullable=True)  # {"lat": 0, "lng": 0}
    
    # 详细信息
    details = Column(JSON, nullable=True)  # 存储具体信息（价格、评分、联系方式等）
    images = Column(JSON, nullable=True)   # 存储图片URL列表

    # 新增：地点扩展信息
    opening_hours = Column(JSON, nullable=True)  # 开放时间 {"weekday": "09:00-18:00", "weekend": "10:00-20:00"}
    phone = Column(String(50), nullable=True)  # 联系电话
    website = Column(String(200), nullable=True)  # 网址
    facilities = Column(JSON, nullable=True)  # 服务设施 ["停车场", "餐厅", "WiFi"]
    priority = Column(String(20), nullable=True)  # 优先级: must(必去), optional(可选), backup(备选)

    # 关联关系
    travel_plan_id = Column(Integer, ForeignKey("travel_plans.id"), nullable=False)
    travel_plan = relationship("TravelPlan", back_populates="items")
    
    def __repr__(self):
        try:
            # 安全地获取属性，避免触发懒加载
            obj_id = getattr(self, 'id', 'N/A')
            return f"<TravelPlanItem(id={obj_id})>"
        except Exception:
            return f"<TravelPlanItem(instance)>"


# 新增：旅行计划评分模型
class TravelPlanRating(BaseModel):
    """旅行计划评分模型"""
    __tablename__ = "travel_plan_ratings"

    # 评分信息
    travel_plan_id = Column(Integer, ForeignKey("travel_plans.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    score = Column(Integer, nullable=False)  # 1-5 星
    comment = Column(Text, nullable=True)

    # 关系
    travel_plan = relationship("TravelPlan", back_populates="ratings")
    # 可选：如果需要从评分查到用户，可后续加反向关系

    def __repr__(self):
        try:
            obj_id = getattr(self, 'id', 'N/A')
            return f"<TravelPlanRating(id={obj_id})>"
        except Exception:
            return f"<TravelPlanRating(instance)>"


# 新增：收藏地点模型
class FavoriteLocation(BaseModel):
    """收藏地点模型"""
    __tablename__ = "favorite_locations"

    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    name = Column(String(200), nullable=False)  # 地点名称
    address = Column(Text, nullable=True)  # 地址
    coordinates = Column(JSON, nullable=True)  # 坐标 {lat, lng}
    category = Column(String(50), nullable=True)  # 分类: attraction, restaurant, hotel
    phone = Column(String(50), nullable=True)  # 电话
    poi_id = Column(String(100), nullable=True)  # 高德/百度 POI ID
    source = Column(String(20), nullable=True)  # 来源: amap, baidu, manual
    notes = Column(Text, nullable=True)  # 备注

    def __repr__(self):
        try:
            obj_id = getattr(self, 'id', 'N/A')
            return f"<FavoriteLocation(id={obj_id})>"
        except Exception:
            return f"<FavoriteLocation(instance)>"
