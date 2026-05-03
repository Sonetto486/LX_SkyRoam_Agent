"""
高德地图 REST API 客户端
直接调用高德地图 REST API，无需 MCP 服务器
"""

import asyncio
import json
from typing import List, Dict, Any, Optional
from loguru import logger
import httpx
from app.core.config import settings
from app.core.redis import cache_key, get_cache, set_cache

# 高德地图 REST API 基础地址
AMAP_REST_API_BASE = "https://restapi.amap.com/v3"

# 地理编码长期缓存 TTL
GEOCODE_CACHE_TTL = 60 * 60 * 24 * 90  # 90天


class AmapRestClient:
    """高德地图 REST API 客户端 - 直接调用高德地图 API"""

    def __init__(self):
        self.http_client = httpx.AsyncClient(timeout=30.0)
        self.api_key = settings.AMAP_API_KEY

        if self.api_key:
            logger.info(f"高德地图 REST API 客户端初始化成功，API Key: {self.api_key[:8]}...")
        else:
            logger.warning("高德地图 API Key 未配置")

    async def geocode(self, address: str, city: str = "") -> Optional[Dict[str, Any]]:
        """地理编码 - 地址转坐标（带长期缓存）"""
        try:
            # 规范化参数并构造缓存键
            addr_norm = str(address).strip()
            city_norm = str(city or "").strip()
            cache_key_str = cache_key("amap:geocode:rest", addr_norm, city_norm)

            # 命中缓存直接返回
            cached = await get_cache(cache_key_str)
            if cached:
                logger.debug(f"地理编码命中缓存: address={addr_norm}, city={city_norm}")
                return cached

            if not self.api_key:
                logger.warning("高德地图API密钥未配置，且无缓存可用")
                return None

            # 构建请求参数
            params = {
                "key": self.api_key,
                "address": addr_norm,
                "output": "json"
            }
            if city_norm:
                params["city"] = city_norm

            # 直接调用高德地图 REST API
            url = f"{AMAP_REST_API_BASE}/geocode/geo"
            response = await self.http_client.get(url, params=params)
            response.raise_for_status()

            result = response.json()

            # 检查响应状态
            if result.get("status") != "1":
                logger.warning(f"高德地图地理编码失败: {result.get('info', '未知错误')}")
                return None

            # 解析结果
            geocodes = result.get("geocodes", [])
            if not geocodes:
                logger.warning(f"地理编码未返回结果: {addr_norm}")
                return None

            geocode = geocodes[0]
            location = geocode.get("location", "")

            if not location:
                logger.warning("地理编码未返回坐标信息")
                return None

            # 解析坐标
            try:
                lng, lat = location.split(",")
                geocode_result = {
                    "lng": float(lng),
                    "lat": float(lat),
                    "formatted_address": geocode.get("formatted_address", ""),
                    "level": geocode.get("level", ""),
                    "country": geocode.get("country", ""),
                    "province": geocode.get("province", ""),
                    "city": geocode.get("city", ""),
                    "district": geocode.get("district", ""),
                    "adcode": geocode.get("adcode", "")
                }

                # 存入长期缓存
                await set_cache(cache_key_str, geocode_result, ttl=GEOCODE_CACHE_TTL)
                logger.info(f"地理编码成功: {addr_norm} -> {location}")

                return geocode_result

            except (ValueError, IndexError) as e:
                logger.error(f"解析坐标失败: {location}, 错误: {e}")
                return None

        except httpx.HTTPStatusError as e:
            logger.error(f"高德地图 API HTTP 错误: {e}")
            return None
        except Exception as e:
            logger.error(f"高德地图地理编码失败: {e}")
            return None

    async def search_places(
        self,
        query: str,
        city: str,
        category: str = "景点"
    ) -> List[Dict[str, Any]]:
        """搜索地点"""
        try:
            if not self.api_key:
                logger.warning("高德地图API密钥未配置")
                return []

            # 构建请求参数
            params = {
                "key": self.api_key,
                "keywords": query,
                "city": city,
                "types": self._get_place_type(category),
                "output": "json",
                "offset": 20,
                "page": 1,
                "extensions": "all"
            }

            # 直接调用高德地图 REST API
            url = f"{AMAP_REST_API_BASE}/place/text"
            response = await self.http_client.get(url, params=params)
            response.raise_for_status()

            result = response.json()

            # 检查响应状态
            if result.get("status") != "1":
                logger.warning(f"高德地图地点搜索失败: {result.get('info', '未知错误')}")
                return []

            pois = result.get("pois", [])
            logger.info(f"高德地图地点搜索成功: {query} in {city}, 找到 {len(pois)} 个结果")

            return self._parse_places_response(pois)

        except Exception as e:
            logger.error(f"高德地图地点搜索失败: {e}")
            return []

    async def search_places_around(
        self,
        location: str,
        keywords: str = "",
        types: str = "",
        radius: int = 5000,
        offset: int = 20,
        page: int = 1
    ) -> List[Dict[str, Any]]:
        """周边搜索地点"""
        try:
            if not self.api_key:
                logger.warning("高德地图API密钥未配置")
                return []

            # 构建请求参数
            params = {
                "key": self.api_key,
                "location": location,
                "keywords": keywords or "",
                "types": types or "",
                "radius": radius,
                "offset": offset,
                "page": page,
                "output": "json",
                "extensions": "all"
            }

            # 直接调用高德地图 REST API
            url = f"{AMAP_REST_API_BASE}/place/around"
            response = await self.http_client.get(url, params=params)
            response.raise_for_status()

            result = response.json()

            # 检查响应状态
            if result.get("status") != "1":
                logger.warning(f"高德地图周边搜索失败: {result.get('info', '未知错误')}")
                return []

            pois = result.get("pois", [])
            logger.info(f"高德地图周边搜索成功: {keywords} @ {location}, 找到 {len(pois)} 个结果")

            return self._parse_places_response(pois)

        except Exception as e:
            logger.error(f"高德地图周边搜索失败: {e}")
            return []

    def _parse_places_response(self, pois: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """解析地点搜索响应"""
        places = []

        for poi in pois[:10]:  # 取前10个地点
            # 提取基本信息
            location_str = poi.get("location", "")
            coordinates = {}
            if location_str and "," in location_str:
                try:
                    lng, lat = location_str.split(",")
                    coordinates = {
                        "lng": float(lng.strip()),
                        "lat": float(lat.strip())
                    }
                except (ValueError, IndexError) as e:
                    logger.warning(f"坐标解析失败: {location_str}, 错误: {e}")
                    coordinates = {}

            # 提取商业扩展信息（评分、价格等）
            biz_ext = poi.get("biz_ext", {})
            rating = 0.0
            cost = ""
            if biz_ext:
                rating_value = biz_ext.get("rating", 0)
                if isinstance(rating_value, (int, float)):
                    rating = float(rating_value)
                elif isinstance(rating_value, str) and rating_value.replace(".", "").isdigit():
                    rating = float(rating_value)
                elif isinstance(rating_value, list) and rating_value:
                    for item in rating_value:
                        if isinstance(item, (int, float)):
                            rating = float(item)
                            break
                        elif isinstance(item, str) and item.replace(".", "").isdigit():
                            rating = float(item)
                            break

                cost = biz_ext.get("cost", "")

            # 提取图片信息
            photos = []
            photo_list = poi.get("photos", [])
            if photo_list:
                for photo in photo_list[:3]:
                    if isinstance(photo, dict) and photo.get("url"):
                        photos.append({
                            "url": photo.get("url", ""),
                            "title": photo.get("title", "")
                        })

            # 提取标签
            tags = []
            tag_str = poi.get("tag", "")
            if tag_str:
                tags = [tag.strip() for tag in tag_str.split(",") if tag.strip()]

            cost_value = self._parse_cost_value(cost)

            place_item = {
                "id": f"amap_place_{poi.get('id', '')}",
                "name": poi.get("name", ""),
                "category": poi.get("type", ""),
                "description": poi.get("address", ""),
                "address": poi.get("address", ""),
                "rating": rating,
                "price": cost_value,
                "cost": cost,
                "price_range": self._get_price_range(cost),
                "coordinates": coordinates,
                "location": location_str,
                "phone": poi.get("tel", ""),
                "business_area": poi.get("business_area", ""),
                "cityname": poi.get("cityname", ""),
                "adname": poi.get("adname", ""),
                "tags": tags,
                "photos": photos,
                "typecode": poi.get("typecode", ""),
                "distance": poi.get("distance", ""),
                "visit_duration": "1-2小时",
                "website": "",
                "accessibility": "良好",
                "source": "高德地图"
            }
            places.append(place_item)

        return places

    def _parse_cost_value(self, cost: str) -> Optional[float]:
        if not cost:
            return None
        try:
            import re
            match = re.search(r"(\d+(\.\d+)?)", cost)
            if match:
                return float(match.group(1))
        except Exception:
            return None
        return None

    def _get_price_range(self, cost: str) -> str:
        """根据人均消费生成价格描述"""
        value = self._parse_cost_value(cost)
        if value is None:
            return "价格未知"
        return f"约 ¥{int(round(value))}"

    def _get_place_type(self, category: str) -> str:
        """获取高德地图地点类型"""
        type_mapping = {
            "景点": "110000",  # 风景名胜
            "餐厅": "050000",  # 餐饮服务
            "酒店": "100000",  # 住宿服务
            "购物": "060000",  # 购物服务
            "交通": "150000",  # 交通设施服务
        }
        return type_mapping.get(category, "110000")

    async def get_directions(
        self,
        origin: str,
        destination: str,
        mode: str = "transit"
    ) -> List[Dict[str, Any]]:
        """获取路线规划"""
        try:
            if not self.api_key:
                logger.warning("高德地图API密钥未配置")
                return []

            # 根据模式选择 API
            if mode == "transit":
                url = f"{AMAP_REST_API_BASE}/direction/transit/integrated"
                params = {
                    "key": self.api_key,
                    "origin": origin,
                    "destination": destination,
                    "city": "北京",  # 可根据需要动态设置
                    "output": "json"
                }
            else:
                url = f"{AMAP_REST_API_BASE}/direction/driving"
                params = {
                    "key": self.api_key,
                    "origin": origin,
                    "destination": destination,
                    "output": "json",
                    "strategy": 0  # 推荐策略
                }

            response = await self.http_client.get(url, params=params)
            response.raise_for_status()

            result = response.json()

            if result.get("status") != "1":
                logger.warning(f"高德地图路线规划失败: {result.get('info', '未知错误')}")
                return []

            return self._parse_directions_response(result, mode)

        except Exception as e:
            logger.error(f"高德地图路线规划失败: {e}")
            return []

    def _parse_directions_response(self, result: Dict[str, Any], mode: str) -> List[Dict[str, Any]]:
        """解析路线规划响应"""
        transportation = []

        try:
            if mode == "transit":
                # 公交路线
                route = result.get("route", {})
                transits = route.get("transits", [])

                for i, transit in enumerate(transits[:3]):
                    distance = int(transit.get("distance", 0))
                    duration = int(transit.get("duration", 0))

                    # 解析步骤
                    steps = []
                    for step in transit.get("steps", []):
                        step_info = {
                            "instruction": step.get("instruction", ""),
                            "distance": int(step.get("distance", 0)),
                            "duration": int(step.get("duration", 0)),
                            "road": step.get("road", "")
                        }
                        steps.append(step_info)

                    transport_item = {
                        "id": f"amap_route_{i+1}",
                        "type": "公共交通",
                        "name": f"高德路线{i+1}",
                        "description": "高德地图推荐路线",
                        "duration": duration // 60,
                        "distance": distance // 1000,
                        "price": self._estimate_cost(distance, duration),
                        "currency": "CNY",
                        "operating_hours": "06:00-23:00",
                        "frequency": "5-15分钟",
                        "coverage": ["目的地"],
                        "features": ["实时路况", "多方案选择"],
                        "route": steps,
                        "source": "高德地图"
                    }
                    transportation.append(transport_item)
            else:
                # 驾车路线
                route = result.get("route", {})
                paths = route.get("paths", [])

                for i, path in enumerate(paths[:3]):
                    distance = int(path.get("distance", 0))
                    duration = int(path.get("duration", 0))

                    steps = []
                    for step in path.get("steps", []):
                        step_info = {
                            "instruction": step.get("instruction", ""),
                            "distance": int(step.get("distance", 0)),
                            "duration": int(step.get("duration", 0)),
                            "road": step.get("road", "")
                        }
                        steps.append(step_info)

                    transport_item = {
                        "id": f"amap_route_{i+1}",
                        "type": "自驾",
                        "name": f"高德路线{i+1}",
                        "description": "高德地图推荐路线",
                        "duration": duration // 60,
                        "distance": distance // 1000,
                        "price": self._estimate_cost(distance, duration),
                        "currency": "CNY",
                        "operating_hours": "24小时",
                        "frequency": "随时",
                        "coverage": ["目的地"],
                        "features": ["实时路况", "多方案选择"],
                        "route": steps,
                        "source": "高德地图"
                    }
                    transportation.append(transport_item)

            logger.info(f"解析高德地图路线成功: {len(transportation)} 条路线")

        except Exception as e:
            logger.error(f"解析高德地图路线响应失败: {e}")

        return transportation

    def _estimate_cost(self, distance: int, duration: int) -> int:
        """估算费用"""
        distance_km = distance // 1000

        if distance_km < 10:
            return 5
        elif distance_km < 50:
            return 15
        else:
            return 30

    async def get_weather(self, city: str, extensions: str = "all") -> Dict[str, Any]:
        """获取天气信息"""
        try:
            if not self.api_key:
                logger.warning("高德地图API密钥未配置")
                return {}

            # 构建请求参数
            params = {
                "key": self.api_key,
                "city": city,
                "extensions": extensions,
                "output": "json"
            }

            # 直接调用高德地图 REST API
            url = f"{AMAP_REST_API_BASE}/weather/weatherInfo"
            response = await self.http_client.get(url, params=params)
            response.raise_for_status()

            result = response.json()

            if result.get("status") != "1":
                logger.warning(f"高德地图天气查询失败: {result.get('info', '未知错误')}")
                return {}

            return self._parse_weather_response(result)

        except Exception as e:
            logger.error(f"高德地图天气查询失败: {e}")
            return {}

    def _parse_weather_response(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """解析天气响应"""
        weather_data = {
            "location": "",
            "forecast": [],
            "recommendations": []
        }

        try:
            # 解析实况天气
            lives = result.get("lives", [])
            if lives:
                live_weather = lives[0]
                weather_data["location"] = live_weather.get("city", "")
                weather_data["current"] = {
                    "weather": live_weather.get("weather", ""),
                    "temperature": live_weather.get("temperature", ""),
                    "humidity": live_weather.get("humidity", ""),
                    "wind_direction": live_weather.get("winddirection", ""),
                    "wind_power": live_weather.get("windpower", ""),
                    "report_time": live_weather.get("reporttime", "")
                }

            # 解析预报天气
            forecasts = result.get("forecasts", [])
            if forecasts:
                forecast_data = forecasts[0]
                weather_data["location"] = forecast_data.get("city", "")

                casts = forecast_data.get("casts", [])
                for cast in casts:
                    forecast_item = {
                        "date": cast.get("date", ""),
                        "week": cast.get("week", ""),
                        "dayweather": cast.get("dayweather", ""),
                        "nightweather": cast.get("nightweather", ""),
                        "daytemp": cast.get("daytemp", ""),
                        "nighttemp": cast.get("nighttemp", ""),
                        "daywind": cast.get("daywind", ""),
                        "nightwind": cast.get("nightwind", ""),
                        "daypower": cast.get("daypower", ""),
                        "nightpower": cast.get("nightpower", "")
                    }
                    weather_data["forecast"].append(forecast_item)

                if casts:
                    weather_data["recommendations"] = self._generate_weather_recommendations(casts)

            logger.debug(f"解析高德地图天气数据成功: {weather_data['location']}")

        except Exception as e:
            logger.error(f"解析高德地图天气响应失败: {e}")

        return weather_data

    def _generate_weather_recommendations(self, casts: List[Dict[str, Any]]) -> List[str]:
        """根据天气预报生成建议"""
        recommendations = []

        try:
            for cast in casts[:3]:
                day_weather = cast.get("dayweather", "")
                day_temp_str = cast.get("daytemp", "0")
                try:
                    day_temp = int(day_temp_str) if day_temp_str.isdigit() else 0
                except ValueError:
                    day_temp = 0

                if day_temp > 30:
                    recommendations.append("气温较高，建议穿着轻薄透气的衣物，注意防晒")
                elif day_temp < 10:
                    recommendations.append("气温较低，建议穿着保暖衣物")

                if "雨" in day_weather:
                    recommendations.append("有降雨，建议携带雨具")
                elif "雪" in day_weather:
                    recommendations.append("有降雪，注意保暖和路面湿滑")
                elif "晴" in day_weather:
                    recommendations.append("天气晴朗，适合户外活动")

            recommendations = list(set(recommendations))

        except Exception as e:
            logger.warning(f"生成天气建议失败: {e}")

        return recommendations

    async def close(self):
        """关闭HTTP客户端"""
        await self.http_client.aclose()


# 创建全局客户端实例
amap_rest_client = AmapRestClient()