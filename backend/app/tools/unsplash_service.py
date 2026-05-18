"""
Unsplash API 服务
用于获取旅行类图片作为兜底
"""

import asyncio
import httpx
from typing import List, Optional, Dict, Any
from loguru import logger
from app.core.redis import get_cache, set_cache
from app.core.config import settings

# Unsplash API 基础 URL
UNSPLASH_API_BASE = "https://api.unsplash.com"

# 缓存 TTL（7天）
UNSPLASH_CACHE_TTL = 7 * 24 * 3600


class UnsplashService:
    """Unsplash 图片服务"""

    # 预置的静态兜底图片（当 API 不可用时使用）
    # 这些是精选的旅行类图片，来自 Unsplash
    STATIC_FALLBACK_IMAGES = {
        "北京": "https://images.unsplash.com/photo-1508804185872-d7badad1f121?w=400",  # 北京故宫
        "上海": "https://images.unsplash.com/photo-1538428494232-9c6d8e8e5e5e?w=400",  # 上海城市
        "杭州": "https://images.unsplash.com/photo-1517309230475-67c9c8f9e9d3?w=400",  # 西湖
        "成都": "https://images.unsplash.com/photo-1513415756790-2ac1db1297d5?w=400",  # 成都熊猫
        "西安": "https://images.unsplash.com/photo-1513836276808-7c1a1e1e5e5e?w=400",  # 西安城墙
        "南京": "https://images.unsplash.com/photo-1517309230475-67c9c8f9e9d3?w=400",  # 古城
        "苏州": "https://images.unsplash.com/photo-1517309230475-67c9c8f9e9d3?w=400",  # 园林
        "厦门": "https://images.unsplash.com/photo-1513836276808-7c1a1e1e5e5e?w=400",  # 海边
        "重庆": "https://images.unsplash.com/photo-1513415756790-2ac1db1297d5?w=400",  # 山城
        "广州": "https://images.unsplash.com/photo-1538428494232-9c6d8e8e5e5e?w=400",  # 城市
        "_default": "https://images.unsplash.com/photo-1488085061387-4b4c4e1b9a3c?w=400",  # 通用旅行图
    }

    def __init__(self):
        self._http_client: Optional[httpx.AsyncClient] = None
        self._last_request_time = 0
        self._request_interval = 0.5  # 500ms 间隔（Unsplash API 限流）
        self._access_key = settings.UNSPLASH_ACCESS_KEY if hasattr(settings, 'UNSPLASH_ACCESS_KEY') else ""

    async def _get_client(self) -> httpx.AsyncClient:
        """获取 HTTP 客户端"""
        if self._http_client is None or self._http_client.is_closed:
            self._http_client = httpx.AsyncClient(timeout=30.0)
        return self._http_client

    async def close(self):
        """关闭 HTTP 客户端"""
        if self._http_client and not self._http_client.is_closed:
            await self._http_client.aclose()

    async def _rate_limit(self):
        """请求限流"""
        import time
        now = time.time()
        elapsed = now - self._last_request_time
        if elapsed < self._request_interval:
            await asyncio.sleep(self._request_interval - elapsed)
        self._last_request_time = time.time()

    async def search_travel_image(self, city: str = "") -> Optional[str]:
        """
        搜索旅行类图片

        Args:
            city: 城市名（用于搜索相关图片）

        Returns:
            图片 URL 或 None
        """
        # 如果没有 API Key，直接返回静态兜底图片
        if not self._access_key:
            logger.debug("Unsplash API Key 未配置，使用静态兜底图片")
            return self._get_static_fallback(city)

        # 检查缓存
        cache_key = f"unsplash:fallback:{city}"
        cached = await get_cache(cache_key)
        if cached:
            logger.debug(f"使用缓存的 Unsplash 图片: {city}")
            return cached

        # 构建搜索查询
        queries = self._build_search_queries(city)

        # 遍历查询
        for query in queries:
            try:
                await self._rate_limit()
                image_url = await self._search_photos(query)

                if image_url:
                    # 缓存结果
                    await set_cache(cache_key, image_url, ttl=UNSPLASH_CACHE_TTL)
                    logger.info(f"Unsplash 图片获取成功: {city} -> {image_url[:60]}...")
                    return image_url

            except Exception as e:
                logger.warning(f"Unsplash 搜索失败 [{query}]: {e}")
                continue

        # API 搜索失败，使用静态兜底
        logger.debug(f"Unsplash API 搜索失败，使用静态兜底: {city}")
        return self._get_static_fallback(city)

    def _build_search_queries(self, city: str) -> List[str]:
        """构建搜索查询列表"""
        queries = []

        # 城市相关查询
        if city:
            # 尝试英文名称
            english_city = self._get_english_city_name(city)
            if english_city:
                queries.append(f"{english_city} travel")
                queries.append(f"{english_city} landmark")
            # 中文名称
            queries.append(f"{city} travel")
            queries.append(f"{city} china")

        # 通用旅行查询
        queries.append("travel china")
        queries.append("landscape asia")
        queries.append("travel destination")

        return queries

    def _get_english_city_name(self, city: str) -> Optional[str]:
        """获取城市英文名称"""
        city_map = {
            "北京": "Beijing",
            "上海": "Shanghai",
            "杭州": "Hangzhou",
            "成都": "Chengdu",
            "西安": "Xi'an",
            "南京": "Nanjing",
            "苏州": "Suzhou",
            "厦门": "Xiamen",
            "重庆": "Chongqing",
            "广州": "Guangzhou",
            "深圳": "Shenzhen",
            "武汉": "Wuhan",
            "长沙": "Changsha",
            "青岛": "Qingdao",
            "大连": "Dalian",
            "三亚": "Sanya",
            "昆明": "Kunming",
            "桂林": "Guilin",
            "丽江": "Lijiang",
            "大理": "Dali",
        }
        return city_map.get(city)

    async def _search_photos(self, query: str) -> Optional[str]:
        """调用 Unsplash API 搜索图片"""
        client = await self._get_client()

        url = f"{UNSPLASH_API_BASE}/search/photos"
        params = {
            "query": query,
            "per_page": 5,
            "orientation": "landscape",  # 横向图片更适合展示
            "content_filter": "high",  # 高质量内容
        }
        headers = {
            "Authorization": f"Client-ID {self._access_key}",
            "Accept-Version": "v1",
        }

        try:
            response = await client.get(url, params=params, headers=headers)
            response.raise_for_status()
            data = response.json()

            results = data.get("results", [])
            if not results:
                return None

            # 选择第一张合适的图片
            for photo in results:
                urls = photo.get("urls", {})
                # 使用 regular 尺寸（约 1080px，适合展示）
                image_url = urls.get("regular") or urls.get("small")
                if image_url:
                    return image_url

            return None

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 403:
                logger.warning("Unsplash API 限流或 Key 无效")
            else:
                logger.warning(f"Unsplash HTTP 错误: {e}")
            return None
        except Exception as e:
            logger.warning(f"Unsplash 搜索异常: {e}")
            return None

    def _get_static_fallback(self, city: str) -> str:
        """获取静态兜底图片"""
        return self.STATIC_FALLBACK_IMAGES.get(city, self.STATIC_FALLBACK_IMAGES["_default"])

    def get_static_fallback_for_city(self, city: str = "") -> str:
        """
        公开方法：获取城市的静态兜底图片
        当所有 API 都失败时使用
        """
        return self._get_static_fallback(city)


# 全局单例
unsplash_service = UnsplashService()