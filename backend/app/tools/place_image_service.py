"""
地点图片服务
专门负责获取地点的图片信息
"""

import asyncio
from typing import List, Optional, Dict, Any
from loguru import logger
from app.tools.amap_rest_client import amap_rest_client

# 重试配置
MAX_RETRIES = 3
RETRY_DELAY = 1.0  # 秒


class PlaceImageService:
    """地点图片服务"""

    def __init__(self):
        self.request_count = 0

    async def get_place_images(self, keywords: str, address: str = "") -> List[str]:
        """
        获取地点图片

        Args:
            keywords: 地点名称
            address: 地点地址（可选）

        Returns:
            图片URL列表
        """
        for attempt in range(MAX_RETRIES):
            try:
                logger.debug(f"开始获取地点图片(第{attempt+1}次尝试): {keywords}")

                # 添加请求间隔，避免QPS超限
                if self.request_count > 0:
                    await asyncio.sleep(RETRY_DELAY)
                self.request_count += 1

                # 1. 搜索地点
                # 优先使用带地址的搜索
                if address:
                    places = await amap_rest_client.search_places(
                        query=keywords,
                        city=address.split('市')[0] if '市' in address else "",
                        category="景点"
                    )
                else:
                    # 如果没有地址，使用周边搜索（全国范围）
                    places = await amap_rest_client.search_places_around(
                        location="",  # 空字符串表示全国搜索
                        keywords=keywords,
                        radius=5000,
                        offset=1
                    )
                
                if places:
                    logger.debug(f"找到地点: {places[0].get('name')}")
                    
                    # 2. 提取图片
                    photos = places[0].get("photos", [])
                    if photos:
                        image_urls = [photo.get("url") for photo in photos if photo.get("url")]
                        logger.debug(f"获取到 {len(image_urls)} 张图片")
                        return image_urls[:3]  # 最多返回3张图片
            
            except Exception as e:
                error_msg = str(e)
                # 如果是QPS超限错误，进行重试
                if "CUQPS_HAS_EXCEEDED_THE_LIMIT" in error_msg:
                    logger.warning(f"QPS超限，等待后重试(第{attempt+1}次): {keywords}")
                    await asyncio.sleep(RETRY_DELAY * (attempt + 1))
                    continue
                logger.error(f"获取地点图片失败: {e}")
                break
        
        logger.debug(f"未找到地点 {keywords} 的图片")
        return []
    
    async def get_place_image(self, keywords: str, address: str = "") -> Optional[str]:
        """
        获取地点的第一张图片
        
        Args:
            keywords: 地点名称
            address: 地点地址（可选）
            
        Returns:
            第一张图片的URL，如果没有则返回None
        """
        images = await self.get_place_images(keywords, address)
        return images[0] if images else None
    
    async def enrich_location_with_image(self, location: Dict[str, Any]) -> Dict[str, Any]:
        """
        为地点添加图片信息
        
        Args:
            location: 地点信息
            
        Returns:
            添加了图片信息的地点
        """
        keywords = location.get("name", "")
        address = location.get("address", "")
        
        images = await self.get_place_images(keywords, address)
        
        if images:
            location["images"] = images
            location["image_url"] = images[0]  # 主图片
        
        return location
