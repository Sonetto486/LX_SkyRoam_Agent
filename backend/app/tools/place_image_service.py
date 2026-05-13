import asyncio
from typing import List, Optional, Dict, Any, Union
from loguru import logger
from app.tools.amap_rest_client import amap_rest_client
import Levenshtein

MAX_RETRIES = 3
RETRY_DELAY = 1.0
DEFAULT_IMAGE = "https://picsum.photos/400/300"


class PlaceImageService:
    def __init__(self):
        self.request_count = 0

    async def get_place_images(self, search_query: str, city_limit: str = "") -> List[str]:
        for attempt in range(MAX_RETRIES):
            try:
                logger.debug(f"开始获取地点图片(第{attempt+1}次尝试): {search_query}")

                if self.request_count > 0:
                    await asyncio.sleep(RETRY_DELAY)
                self.request_count += 1

                places = await amap_rest_client.search_places(
                    query=search_query,
                    city=city_limit,
                    category="景点"
                )

                if places:
                    logger.debug(f"找到地点: {places[0].get('name')} (区域: {places[0].get('adname', '未知')})")
                    photos = places[0].get("photos", [])
                    image_urls = [photo.get("url") for photo in photos if photo.get("url")]
                    if image_urls:
                        logger.debug(f"获取到 {len(image_urls)} 张图片")
                        return image_urls[:3]
            except Exception as e:
                if "CUQPS_HAS_EXCEEDED_THE_LIMIT" in str(e):
                    logger.warning(f"QPS超限，重试: {search_query}")
                    await asyncio.sleep(RETRY_DELAY * (attempt + 1))
                    continue
                logger.error(f"获取图片失败: {e}")
                break

        logger.debug(f"未找到 {search_query} 图片，使用兜底图")
        return [DEFAULT_IMAGE]

    async def get_place_coordinate(self, search_query: str, city_limit: str = "") -> Dict[str, Optional[float]]:
        try:
            places = await amap_rest_client.search_places(
                query=search_query,
                city=city_limit,
                category="景点"
            )
            if not places:
                return {"lat": None, "lng": None}

            location = places[0].get("location", "")
            if "," in location:
                lng_str, lat_str = location.split(",", 1)
                return {"lat": float(lat_str.strip()), "lng": float(lng_str.strip())}
        except Exception as e:
            logger.warning(f"解析经纬度失败: {e}")

        return {"lat": None, "lng": None}

    def _pick_best_match(self, target_name: str, candidates: List[Dict]) -> Optional[Dict]:
        """从候选列表中选出名称最相似的POI，相似度过低则丢弃"""
        best = None
        best_score = 9999
        for place in candidates:
            name = place.get("name", "")
            if not name:
                continue
            clean_name = name.split("(")[0].strip()
            score = min(
                Levenshtein.distance(target_name.lower(), name.lower()),
                Levenshtein.distance(target_name.lower(), clean_name.lower())
            )
            if score < best_score:
                best_score = score
                best = place
        if best and best_score <= max(3, len(target_name) * 0.6):
            return best
        return None

    async def _search_around_with_loose_match(
        self, lat: float, lng: float, raw_name: str, radius: int = 1000
    ) -> Optional[Dict]:
        """周边搜索，不依赖高德keywords，而是拉取周边POI后本地模糊匹配"""
        try:
            nearby_places = await amap_rest_client.search_places_around(
                location=f"{lng},{lat}",
                radius=radius,
                keywords="",
                types="风景名胜"
            )
            if nearby_places:
                best = self._pick_best_match(raw_name, nearby_places)
                if best:
                    return best
        except Exception as e:
            logger.warning(f"周边放宽搜索失败: {e}")
        return None

    async def _try_alternative_queries(
        self, raw_name: str, city: str, lat: Optional[float] = None, lng: Optional[float] = None
    ) -> Optional[Dict]:
        """多级降级搜索：原名 → 去除修饰词 → 仅核心词"""
        queries = [raw_name]
        if "·" in raw_name:
            queries.append(raw_name.split("·")[0])
        if "（" in raw_name:
            queries.append(raw_name.split("（")[0])
        if len(raw_name) > 4:
            queries.append(raw_name[:6])

        for q in queries:
            try:
                places = await amap_rest_client.search_places(
                    query=q, city=city, category="景点"
                )
                if places:
                    best = self._pick_best_match(raw_name, places)
                    if best:
                        return best
            except Exception as e:
                logger.warning(f"降级搜索 {q} 失败: {e}")
                continue
        return None

    async def enrich_location_with_image(self, location: Dict[str, Any], default_city: str = "") -> Dict[str, Any]:
        raw_name = location.get("name", "").strip()
        address = location.get("address", "").strip()
        lat = location.get("lat")
        lng = location.get("lng")

        city_context = default_city
        if not city_context and '市' in address:
            city_context = address.split('市')[0]
        if not city_context and lat and lng:
            if 30.6 < lat < 31.6 and 120.8 < lng < 122.0:
                city_context = "上海"
                logger.info(f"📍 坐标坐落上海，自动设置城市为上海")
        if not city_context and "上海" in address:
            city_context = "上海"

        if lat is not None and lng is not None:
            try:
                nearby = await amap_rest_client.search_places_around(
                    location=f"{lng},{lat}",
                    radius=500,
                    keywords=raw_name,
                    types="风景名胜"
                )
                if nearby:
                    best_match = self._pick_best_match(raw_name, nearby)
                    if best_match:
                        return self._populate_from_poi(location, best_match)
            except Exception as e:
                logger.warning(f"严格周边搜索异常: {e}")

            best = await self._search_around_with_loose_match(lat, lng, raw_name, radius=1000)
            if best:
                return self._populate_from_poi(location, best)

        enhanced = raw_name
        if city_context and city_context not in raw_name:
            enhanced = f"{city_context}{raw_name}"

        logger.info(f"🔍 文本搜索: [{raw_name}] -> [{enhanced}] (城市: {city_context})")

        try:
            places = await amap_rest_client.search_places(
                query=enhanced, city=city_context, category="景点"
            )
            if places:
                best = self._pick_best_match(raw_name, places)
                if best:
                    return self._populate_from_poi(location, best)

            best = await self._try_alternative_queries(raw_name, city_context or "", lat, lng)
            if best:
                return self._populate_from_poi(location, best)

        except Exception as e:
            logger.error(f"文本搜索异常: {e}")

        location["images"] = [DEFAULT_IMAGE]
        location["image_url"] = DEFAULT_IMAGE
        return location

    def _populate_from_poi(self, location: Dict[str, Any], poi: Dict[str, Any]) -> Dict[str, Any]:
        """用POI数据填充location"""
        photos = poi.get("photos", [])
        image_urls = [p.get("url") for p in photos if p.get("url")]
        if image_urls:
            location["images"] = image_urls[:3]
            location["image_url"] = image_urls[0]
        loc_str = poi.get("location", "")
        if "," in loc_str:
            lng_str, lat_str = loc_str.split(",", 1)
            location["lat"] = float(lat_str)
            location["lng"] = float(lng_str)
        return location


place_image_service = PlaceImageService()
