"""
预生成方案数据模型
用于存储热门城市的预生成行程方案模板
"""

from sqlalchemy import Column, Integer, String, Float, DateTime, Text, Boolean
from sqlalchemy.dialects.postgresql import JSONB
from datetime import datetime
from app.models.base import BaseModel


class PreGeneratedPlan(BaseModel):
    """预生成方案模型"""
    __tablename__ = "pre_generated_plans"

    # 目的地信息
    destination_id = Column(Integer, nullable=True)  # 关联 destinations 表
    destination_name = Column(String(100), nullable=False, index=True)

    # 预生成方案核心数据
    plan_template = Column(JSONB, nullable=False)  # 完整的方案模板（不含具体日期）

    # 匹配维度（用于快速检索）
    duration_days = Column(Integer, nullable=False, index=True)  # 行程天数: 1-3, 4-7, 8-14
    budget_level = Column(String(20), nullable=False, index=True)  # economy, comfortable, luxury
    travel_preferences = Column(JSONB, nullable=True)  # ["culture", "nature", "food", ...]
    age_groups = Column(JSONB, nullable=True)  # ["adult", "child", ...]
    food_preferences = Column(JSONB, nullable=True)  # ["spicy", "local", ...]
    transportation_mode = Column(String(50), nullable=True)  # flight, train, car, ...

    # 元数据
    popularity_score = Column(Float, default=0.0)  # 目的地热度分数
    generation_version = Column(String(20), nullable=True)  # 方案版本号
    data_sources = Column(JSONB, nullable=True)  # {"poi": true, "amap": true, ...}

    # 状态管理
    status = Column(String(20), default="active", index=True)  # active, deprecated, updating
    last_updated_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=True, index=True)  # 过期时间

    # 统计信息
    match_count = Column(Integer, default=0)  # 匹配次数
    usage_count = Column(Integer, default=0)  # 实际使用次数
    avg_rating = Column(Float, nullable=True)  # 平均评分

    def to_dict(self):
        """转换为字典"""
        result = super().to_dict()
        # 确保 JSONB 字段正确序列化
        if self.plan_template:
            result["plan_template"] = self.plan_template
        if self.travel_preferences:
            result["travel_preferences"] = self.travel_preferences
        if self.age_groups:
            result["age_groups"] = self.age_groups
        if self.food_preferences:
            result["food_preferences"] = self.food_preferences
        if self.data_sources:
            result["data_sources"] = self.data_sources
        return result