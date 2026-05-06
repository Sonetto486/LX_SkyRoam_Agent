"""
专题相关模型
"""

from sqlalchemy import Column, String, Text, Boolean, Integer, ForeignKey
from sqlalchemy.orm import relationship
from app.models.base import BaseModel


class Topic(BaseModel):
    """专题模型"""
    __tablename__ = "topic"

    name = Column(String(100), nullable=False)
    intro = Column(Text, nullable=True)
    cover_url = Column(String(255), nullable=True)
    region = Column(String(100), nullable=True)
    continent = Column(String(50), nullable=True)

    # 关联的地点
    places = relationship("TopicPlace", back_populates="topic", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Topic(name={self.name})>"


class TopicPlace(BaseModel):
    """专题地点关联模型"""
    __tablename__ = "topic_place"

    topic_id = Column(Integer, ForeignKey("topic.id", ondelete="CASCADE"), nullable=False)
    related_type = Column(String(20), nullable=False)  # attractions/restaurants/destinations
    related_id = Column(Integer, nullable=False)
    is_key_point = Column(Boolean, default=False, nullable=False)
    highlight_info = Column(Text, nullable=True)
    order_index = Column(Integer, nullable=False)

    # 关联的专题
    topic = relationship("Topic", back_populates="places")

    def __repr__(self):
        return f"<TopicPlace(topic_id={self.topic_id}, type={self.related_type})>"