"""
热门城市数据模型
管理国内前100热门旅游城市
"""

from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean
from datetime import datetime
from app.models.base import BaseModel


class HotDestination(BaseModel):
    """热门城市模型"""
    __tablename__ = "hot_destinations"

    # 基本信息
    city_name = Column(String(100), nullable=False, unique=True, index=True)
    province = Column(String(50), nullable=True)
    region = Column(String(50), nullable=True)  # 华东、华南、华北、西南、西北、东北

    # 热度指标
    popularity_score = Column(Float, default=0.0)
    monthly_visitors = Column(Integer, nullable=True)  # 月访问量
    search_volume = Column(Integer, nullable=True)  # 搜索量

    # 配置
    priority = Column(Integer, default=100)  # 预生成优先级（越小越优先）
    is_enabled = Column(Boolean, default=True)  # 是否启用预生成

    # 预生成状态
    pre_generated_count = Column(Integer, default=0)  # 已预生成方案数
    last_pre_generated_at = Column(DateTime, nullable=True)

    # 城市坐标（用于地图展示）
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)

    # 城市特色标签
    tags = Column(String(200), nullable=True)  # 如 "历史文化,美食之都,自然风光"

    def to_dict(self):
        """转换为字典"""
        return {
            "id": self.id,
            "city_name": self.city_name,
            "province": self.province,
            "region": self.region,
            "popularity_score": self.popularity_score,
            "monthly_visitors": self.monthly_visitors,
            "search_volume": self.search_volume,
            "priority": self.priority,
            "is_enabled": self.is_enabled,
            "pre_generated_count": self.pre_generated_count,
            "last_pre_generated_at": self.last_pre_generated_at,
            "latitude": self.latitude,
            "longitude": self.longitude,
            "tags": self.tags,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "is_active": self.is_active
        }