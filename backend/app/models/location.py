from sqlalchemy import Column, Integer, String, Text, Numeric, Boolean, JSON, DECIMAL
from app.models.base import Base

class Location(Base):
    __tablename__ = "location"
    
    location_id = Column(Integer, primary_key=True, autoincrement=True, comment="地点ID")
    location_name = Column(String(100), nullable=False, index=True, comment="地点名称")
    address = Column(String(255), nullable=True, comment="地址")
    
    latitude = Column(DECIMAL(10, 7), nullable=True, comment="纬度")
    longitude = Column(DECIMAL(10, 7), nullable=True, comment="经度")
    
    description = Column(Text, nullable=True, comment="地点简介")
    location_type = Column(String(50), nullable=True, comment="地点类型")
    open_time = Column(String(100), nullable=True, comment="开放时间")
    phone = Column(String(20), nullable=True, comment="电话")
    website = Column(String(255), nullable=True, comment="网址")
    
    is_favorite = Column(Boolean, default=False, index=True)
    is_highlight = Column(Boolean, default=False, index=True)
    added_by = Column(String(50), nullable=True)
    
    media_images = Column(JSON, nullable=True)
    facilities = Column(JSON, nullable=True)

    def to_dict(self):
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}
