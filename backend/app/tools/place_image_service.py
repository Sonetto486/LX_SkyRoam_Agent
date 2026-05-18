import asyncio
import time
from typing import List, Optional, Dict, Any, Union
from loguru import logger
from app.tools.amap_rest_client import amap_rest_client
import Levenshtein

MAX_RETRIES = 3
RETRY_DELAY = 1.0
DEFAULT_IMAGE = "https://picsum.photos/400/300"


class PlaceImageService:
    # 别名映射：将口语化名称转换为标准POI名称
    ALIAS_MAP = {
        "陆家嘴三件套": "上海环球金融中心",
        "东方明珠": "东方明珠广播电视塔",
        "外滩钟楼": "外滩海关大楼",
        "万国建筑群": "外滩万国建筑博览群",
        "故宫": "故宫博物院",
        "天安门": "天安门广场",
        "西湖": "杭州西湖风景名胜区",
        "兵马俑": "秦始皇兵马俑博物馆",
        "长城": "八达岭长城",
        "鸟巢": "国家体育场",
        "水立方": "国家游泳中心",
        "小蛮腰": "广州塔",
        "天府广场": "成都天府广场",
        "春熙路": "成都春熙路步行街",
        "夫子庙": "南京夫子庙",
        "中山陵": "南京中山陵",
        "黄鹤楼": "武汉黄鹤楼",
        "大雁塔": "西安大雁塔",
        "回民街": "西安回民街",
        "洪崖洞": "重庆洪崖洞",
        "解放碑": "重庆解放碑步行街",
        "鼓浪屿": "厦门鼓浪屿",
        "曾厝垵": "厦门曾厝垵",
        "宽窄巷子": "成都宽窄巷子",
        "锦里": "成都锦里古街",
        "南锣鼓巷": "北京南锣鼓巷",
        "三里屯": "北京三里屯",
        "太古里": "成都太古里",
        "豫园": "上海豫园",
        "城隍庙": "上海城隍庙",
        "外滩": "上海外滩",
        "南京路": "上海南京路步行街",
        "人民广场": "上海人民广场",
    }

    # 高德POI分类代码映射
    TYPE_MAP = {
        "景点": "110000|140000",  # 风景名胜|国家级景点
        "酒店": "100000",          # 住宿服务
        "餐饮": "050000",          # 餐饮服务
        "交通": "150000",          # 交通设施服务
    }

    # 城市关键词，用于从名称/地址中推断城市
    CITY_KEYWORDS = [
        "北京", "上海", "广州", "深圳", "杭州", "成都", "南京", "武汉", "西安", "重庆",
        "苏州", "无锡", "宁波", "青岛", "大连", "厦门", "长沙", "郑州", "合肥", "福州",
        "天津", "沈阳", "济南", "哈尔滨", "长春", "昆明", "南宁", "贵阳", "兰州", "太原",
        "南昌", "海口", "石家庄", "乌鲁木齐", "拉萨", "银川", "西宁", "呼和浩特"
    ]

    # 通用/枢纽地址标记：这些地址不应用于 geocode 其他无关地点
    GENERIC_ADDRESS_MARKERS = ["火车站", "高铁站", "机场", "地铁站", "客运中心", "枢纽"]

    def __init__(self):
        self.request_count = 0
        self._last_request_time = 0
        self._request_interval = 0.3  # 300ms间隔，更保守的限流策略

    async def _rate_limit_wait(self):
        """请求间隔控制，防止QPS限流"""
        now = time.time()
        elapsed = now - self._last_request_time
        if elapsed < self._request_interval:
            await asyncio.sleep(self._request_interval - elapsed)
        self._last_request_time = time.time()

    async def get_place_images(self, search_query: str, city_limit: str = "") -> List[str]:
        """获取地点图片"""
        for attempt in range(MAX_RETRIES):
            try:
                await self._rate_limit_wait()
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
        """获取地点坐标（结合geocode和POI搜索）"""
        await self._rate_limit_wait()
        
        # 优先使用POI搜索获取精确坐标
        try:
            places = await amap_rest_client.search_places(
                query=search_query,
                city=city_limit,
                category="景点"
            )
            if places:
                # 增加城市校验，防止跨城误匹配
                best = self._pick_best_match(search_query, places, city_limit)
                if best:
                    location = best.get("location", "")
                    if "," in location:
                        lng_str, lat_str = location.split(",", 1)
                        return {"lat": float(lat_str.strip()), "lng": float(lng_str.strip())}
        except Exception as e:
            logger.warning(f"POI搜索获取坐标失败: {e}")

        # 降级使用geocode
        try:
            geocode_result = await amap_rest_client.geocode(search_query, city_limit)
            if geocode_result:
                return {"lat": geocode_result.get("lat"), "lng": geocode_result.get("lng")}
        except Exception as e:
            logger.warning(f"地理编码获取坐标失败: {e}")

        return {"lat": None, "lng": None}

    async def get_geocode_info(self, address: str, city: str = "") -> Optional[Dict[str, Any]]:
        """获取完整的地理编码信息"""
        await self._rate_limit_wait()
        try:
            return await amap_rest_client.geocode(address, city)
        except Exception as e:
            logger.error(f"获取地理编码信息失败: {e}")
            return None

    def _infer_city(self, raw_name: str, address: str, default_city: str = "", lat: Optional[float] = None, lng: Optional[float] = None) -> str:
        """推断地点所属城市。优先级: default_city > 名称关键词 > 地址关键词 > 坐标范围"""
        if default_city:
            return default_city

        # 从名称推断
        for keyword in self.CITY_KEYWORDS:
            if keyword in raw_name:
                return keyword

        # 从地址推断
        if address and address not in ["地址未知", "未知", "无"]:
            for keyword in self.CITY_KEYWORDS:
                if keyword in address:
                    return keyword

        # 坐标范围推断（上海示例，可扩展）
        if lat and lng:
            if 30.6 < lat < 31.6 and 120.8 < lng < 122.0:
                logger.info(f"📍 坐标坐落上海，自动设置城市为上海")
                return "上海"

        return ""

    def _is_valid_specific_address(self, address: str, place_name: str) -> bool:
        """
        判断 address 是否是该地点的有效特定地址。
        如果 address 是"上海站"这类通用枢纽，而 place_name 是"东方明珠"，
        则该地址不应被用于 geocode 东方明珠。
        """
        if not address or address in ["地址未知", "未知", "无"]:
            return False

        # 如果地址包含通用枢纽标记，但地点名称本身不包含这些标记，视为通用地址
        for marker in self.GENERIC_ADDRESS_MARKERS:
            if marker in address and marker not in place_name:
                return False

        # 有效地址应包含具体街道/区域信息
        has_detail = any(marker in address for marker in ["路", "街", "巷", "号", "大道", "胡同", "区", "镇", "村"])
        return has_detail

    def _is_city_match(self, place: Dict, expected_city: str) -> bool:
        """验证 POI 结果的城市是否与预期一致"""
        if not expected_city:
            return True
        poi_city = place.get("cityname", "") or place.get("city", "") or place.get("pname", "")
        if not poi_city:
            return True  # 无法验证时放行，避免过度拦截

        expected = expected_city.replace("市", "").replace("省", "")
        actual = poi_city.replace("市", "").replace("省", "")
        return expected in actual or actual in expected

    def _pick_best_match(self, target_name: str, candidates: List[Dict], expected_city: str = "") -> Optional[Dict]:
        """从候选列表中选出名称最相似且城市匹配的POI"""
        best = None
        best_score = 9999

        for place in candidates:
            name = place.get("name", "")
            if not name:
                continue

            # 【关键修复】城市不匹配直接丢弃，防止"外滩"匹配到惠州
            if expected_city and not self._is_city_match(place, expected_city):
                continue

            clean_name = name.split("(")[0].split("（")[0].strip()
            score = min(
                Levenshtein.distance(target_name.lower(), name.lower()),
                Levenshtein.distance(target_name.lower(), clean_name.lower())
            )

            # 名称完全包含目标时给予额外奖励
            if target_name.lower() in name.lower():
                score -= 1

            if score < best_score:
                best_score = score
                best = place

        # 【关键修复】收紧阈值，短名称必须更严格
        threshold = max(2, len(target_name) * 0.4)
        if best and best_score <= threshold:
            return best
        return None

    async def _search_around_with_loose_match(
        self, lat: float, lng: float, raw_name: str, radius: int = 1000, poi_types: str = "110000", expected_city: str = ""
    ) -> Optional[Dict]:
        """周边搜索，增加城市验证"""
        try:
            await self._rate_limit_wait()
            nearby_places = await amap_rest_client.search_places_around(
                location=f"{lng},{lat}",
                radius=radius,
                keywords="",
                types=poi_types
            )
            if nearby_places:
                best = self._pick_best_match(raw_name, nearby_places, expected_city)
                if best:
                    return best
        except Exception as e:
            logger.warning(f"周边放宽搜索失败: {e}")
        return None

    async def _try_alternative_queries(
        self, raw_name: str, city: str, poi_types: str = "110000", lat: Optional[float] = None, lng: Optional[float] = None, expected_city: str = ""
    ) -> Optional[Dict]:
        """多级降级搜索：原名 → 去除修饰词 → 城市+核心词"""
        queries = [raw_name]
        if "·" in raw_name:
            queries.append(raw_name.split("·")[0])
        if "（" in raw_name:
            queries.append(raw_name.split("（")[0])
        if "、" in raw_name:
            queries.append(raw_name.split("、")[0])

        # 短名称优先使用"城市+名称"组合，避免全国范围误匹配
        if expected_city and expected_city not in raw_name and len(raw_name) <= 6:
            queries.insert(0, f"{expected_city}{raw_name}")

        for q in queries:
            try:
                await self._rate_limit_wait()
                places = await amap_rest_client.search_places(
                    query=q, city=city or expected_city, category="景点"
                )
                if places:
                    best = self._pick_best_match(raw_name, places, expected_city or city)
                    if best:
                        return best
            except Exception as e:
                logger.warning(f"降级搜索 {q} 失败: {e}")
                continue
        return None

    async def enrich_location_with_image(self, location: Dict[str, Any], default_city: str = "") -> Dict[str, Any]:
        """
        增强地点信息：同时使用geocode和POI搜索，获取精确坐标和图片
        返回结果包含：经纬度、格式化地址、省市区、图片URL等
        """
        raw_name = location.get("name", "").strip()
        address = location.get("address", "").strip()
        lat = location.get("lat")
        lng = location.get("lng")
        place_type = location.get("type", "景点")

        poi_types = self.TYPE_MAP.get(place_type, "110000")

        # 初始化增强字段
        location.setdefault("formatted_address", "")
        location.setdefault("province", "")
        location.setdefault("city", "")
        location.setdefault("district", "")
        location.setdefault("adcode", "")
        location.setdefault("level", "")

        # 【关键修复】统一推断城市，default_city 拥有最高优先级
        city_context = self._infer_city(raw_name, address, default_city, lat, lng)
        if default_city:
            city_context = default_city

        # Step 1: Geocode 获取精确坐标和地址信息
        geocode_result = None
        geocode_used = False

        # 【关键修复】判断地址是否有效且特定于该地点，防止"上海站"污染所有地点
        use_address = self._is_valid_specific_address(address, raw_name)

        # 构建 geocode 查询队列：优先使用特定地址，否则使用"城市+名称"
        geocode_queries = []
        if use_address:
            geocode_queries.append(address)

        name_query = raw_name
        if city_context and city_context not in raw_name:
            name_query = f"{city_context}{raw_name}"
        geocode_queries.append(name_query)

        for query in geocode_queries:
            if not query:
                continue
            try:
                await self._rate_limit_wait()
                geocode_result = await amap_rest_client.geocode(query, city_context)
                if geocode_result:
                    geocode_used = True
                    location["lng"] = geocode_result.get("lng")
                    location["lat"] = geocode_result.get("lat")
                    location["formatted_address"] = geocode_result.get("formatted_address", "")
                    location["province"] = geocode_result.get("province", "")
                    location["city"] = geocode_result.get("city", "")
                    location["district"] = geocode_result.get("district", "")
                    location["adcode"] = geocode_result.get("adcode", "")
                    location["level"] = geocode_result.get("level", "")
                    lat = location["lat"]
                    lng = location["lng"]
                    logger.info(f"✅ 地理编码成功 [{query}]: ({lat}, {lng})")
                    break
            except Exception as e:
                logger.warning(f"地理编码失败 [{query}]: {e}")
                continue

        # Step 2: 使用坐标进行周边 POI 搜索（优先精确匹配）
        poi_found = False
        if lat is not None and lng is not None:
            try:
                await self._rate_limit_wait()
                nearby = await amap_rest_client.search_places_around(
                    location=f"{lng},{lat}",
                    radius=500,
                    keywords=raw_name,
                    types=poi_types
                )
                if nearby:
                    best_match = self._pick_best_match(raw_name, nearby, city_context)
                    if best_match:
                        poi_found = True
                        result = self._populate_from_poi(location, best_match, city_context)
                        self._merge_geocode_info(result, location)
                        return result
            except Exception as e:
                logger.warning(f"严格周边搜索异常: {e}")

            # 放宽周边搜索范围
            best = await self._search_around_with_loose_match(
                lat, lng, raw_name, radius=1000, poi_types=poi_types, expected_city=city_context
            )
            if best:
                poi_found = True
                result = self._populate_from_poi(location, best, city_context)
                self._merge_geocode_info(result, location)
                return result

        # Step 3: 文本搜索（带城市上下文增强）
        enhanced = raw_name
        if city_context and city_context not in raw_name:
            enhanced = f"{city_context}{raw_name}"

        logger.info(f"🔍 文本搜索: [{raw_name}] -> [{enhanced}] (城市: {city_context}, 类型: {place_type})")

        try:
            await self._rate_limit_wait()
            places = await amap_rest_client.search_places(
                query=enhanced, city=city_context, category="景点"
            )
            if places:
                best = self._pick_best_match(raw_name, places, city_context)
                if best:
                    poi_found = True
                    result = self._populate_from_poi(location, best, city_context)
                    await self._enrich_poi_address(result, best, city_context)
                    return result

            # 降级搜索
            best = await self._try_alternative_queries(
                raw_name, city_context or "", poi_types, lat, lng, city_context
            )
            if best:
                poi_found = True
                result = self._populate_from_poi(location, best, city_context)
                await self._enrich_poi_address(result, best, city_context)
                return result

        except Exception as e:
            logger.error(f"文本搜索异常: {e}")

        # Step 4: 当所有搜索都失败时，使用 geocode 结果更新地址
        if geocode_result and not poi_found:
            geo_addr = geocode_result.get("formatted_address", "")
            if geo_addr:
                if "区" in geo_addr or "路" in geo_addr or "街" in geo_addr:
                    location["address"] = geo_addr
                elif address and not use_address:
                    # 原始地址是通用地址，直接用 geocode 结果覆盖
                    location["address"] = geo_addr
                elif address and address not in ["地址未知", "未知", "无"]:
                    location["address"] = f"{geo_addr}（{address}）" if geo_addr else address
                else:
                    location["address"] = geo_addr or "地址待确认"
            
            location["images"] = [DEFAULT_IMAGE]
            location["image_url"] = DEFAULT_IMAGE
            return location

        # Step 5: 最终兜底
        if not poi_found and not geocode_used:
            if city_context:
                fallback_addr = f"{city_context}{raw_name}附近"
            else:
                fallback_addr = f"{raw_name}（地址待确认）"
            location["address"] = fallback_addr
            logger.info(f"📌 使用兜底地址: {fallback_addr}")

        location["images"] = [DEFAULT_IMAGE]
        location["image_url"] = DEFAULT_IMAGE
        return location

    def _merge_geocode_info(self, result: Dict, location: Dict):
        """将 geocode 信息合并到 POI 结果中"""
        if location.get("formatted_address"):
            result.update({
                "formatted_address": location["formatted_address"],
                "province": location["province"],
                "city": location["city"],
                "district": location["district"],
                "adcode": location["adcode"],
                "level": location["level"]
            })

    async def _enrich_poi_address(self, result: Dict, poi: Dict, city_context: str):
        """对 POI 地址进行 geocode 补充详细信息"""
        poi_address = poi.get("address", "")
        if poi_address and not result.get("formatted_address"):
            try:
                await self._rate_limit_wait()
                gc_result = await amap_rest_client.geocode(poi_address, city_context)
                if gc_result:
                    result.update({
                        "formatted_address": gc_result.get("formatted_address", ""),
                        "province": gc_result.get("province", ""),
                        "city": gc_result.get("city", ""),
                        "district": gc_result.get("district", ""),
                        "adcode": gc_result.get("adcode", ""),
                        "level": gc_result.get("level", "")
                    })
            except Exception as e:
                logger.warning(f"POI地址地理编码失败: {e}")

    def _populate_from_poi(self, location: Dict[str, Any], poi: Dict[str, Any], expected_city: str = "") -> Dict[str, Any]:
        """用POI数据填充location，增加城市校验防止地址污染"""
        photos = poi.get("photos", [])
        image_urls = [p.get("url") for p in photos if p.get("url")]
        
        if image_urls:
            location["images"] = image_urls[:3]
            location["image_url"] = image_urls[0]
        else:
            location["images"] = [DEFAULT_IMAGE]
            location["image_url"] = DEFAULT_IMAGE
        
        loc_str = poi.get("location", "")
        if "," in loc_str:
            lng_str, lat_str = loc_str.split(",", 1)
            location["lng"] = float(lng_str)
            location["lat"] = float(lat_str)
        
        # 补充POI中的定位信息
        location["poi_name"] = poi.get("name", "")
        location["poi_address"] = poi.get("address", "")
        location["poi_category"] = poi.get("category", "")
        location["poi_rating"] = poi.get("rating", 0)
        location["poi_price"] = poi.get("price", "")
        
        # 【关键修复】POI 城市校验：不匹配时使用预期城市
        poi_city = poi.get("cityname", "") or poi.get("city", "")
        if expected_city and not self._is_city_match(poi, expected_city):
            location["poi_cityname"] = expected_city
            location["city"] = expected_city
            logger.warning(f"POI城市不匹配: 预期{expected_city}, 实际{poi_city}, 使用预期城市")
        else:
            location["poi_cityname"] = poi_city
            location["city"] = poi_city or location.get("city", "")
        
        location["poi_adname"] = poi.get("adname", "")
        location["poi_tags"] = poi.get("tags", [])
        location["poi_distance"] = poi.get("distance", "")
        
        # 【关键修复】使用POI地址更新主地址字段时，必须城市匹配
        poi_address = poi.get("address", "")
        if poi_address:
            if expected_city and self._is_city_match(poi, expected_city):
                if "区" in poi_address or "路" in poi_address or "街" in poi_address:
                    location["address"] = poi_address
            elif not expected_city:
                if "区" in poi_address or "路" in poi_address or "街" in poi_address:
                    location["address"] = poi_address
        
        return location

    async def get_location_detail(self, name: str, address: str = "", city: str = "", place_type: str = "景点") -> Dict[str, Any]:
        """
        获取完整的地点详情：同时包含geocode和POI信息
        返回：经纬度、格式化地址、省市区、图片、评分、价格等
        """
        result = {
            "name": name,
            "address": address,
            "lat": None,
            "lng": None,
            "formatted_address": "",
            "province": "",
            "city": "",
            "district": "",
            "adcode": "",
            "level": "",
            "images": [],
            "image_url": DEFAULT_IMAGE,
            "poi_name": "",
            "poi_rating": 0,
            "poi_price": "",
            "poi_category": "",
            "poi_tags": [],
            "source": ""
        }

        poi_types = self.TYPE_MAP.get(place_type, "110000")
        
        # 【关键修复】统一推断城市
        inferred_city = self._infer_city(name, address, city)
        if city:
            inferred_city = city

        # Step 1: 使用 geocode 获取精确坐标和地址信息
        geocode_queries = []
        if self._is_valid_specific_address(address, name):
            geocode_queries.append(address)
        
        name_query = name
        if inferred_city and inferred_city not in name:
            name_query = f"{inferred_city}{name}"
        geocode_queries.append(name_query)
        
        for query in geocode_queries:
            if not query:
                continue
            try:
                gc_result = await self.get_geocode_info(query, inferred_city)
                if gc_result:
                    result.update({
                        "lat": gc_result["lat"],
                        "lng": gc_result["lng"],
                        "formatted_address": gc_result.get("formatted_address", ""),
                        "province": gc_result.get("province", ""),
                        "city": gc_result.get("city", ""),
                        "district": gc_result.get("district", ""),
                        "adcode": gc_result.get("adcode", ""),
                        "level": gc_result.get("level", ""),
                        "source": "geocode"
                    })
                    break
            except Exception as e:
                logger.warning(f"geocode查询失败 [{query}]: {e}")

        # Step 2: 使用 POI 搜索获取图片和详细信息
        search_query = name
        if inferred_city and inferred_city not in name:
            search_query = f"{inferred_city}{name}"
        
        try:
            await self._rate_limit_wait()
            places = await amap_rest_client.search_places(
                query=search_query, city=inferred_city, category="景点"
            )
            
            if places:
                best_match = self._pick_best_match(name, places, inferred_city)
                if best_match:
                    photos = best_match.get("photos", [])
                    result["images"] = [p["url"] for p in photos if p.get("url")][:3] or [DEFAULT_IMAGE]
                    result["image_url"] = next((p["url"] for p in photos if p.get("url")), DEFAULT_IMAGE)
                    result["poi_name"] = best_match.get("name", "")
                    result["poi_rating"] = best_match.get("rating", 0)
                    result["poi_price"] = best_match.get("price", "")
                    result["poi_category"] = best_match.get("category", "")
                    result["poi_tags"] = best_match.get("tags", [])
                    result["source"] = "poi"
                    
                    # 如果POI有更精确的坐标，使用POI坐标
                    if best_match.get("location"):
                        loc_str = best_match["location"]
                        if "," in loc_str:
                            lng_str, lat_str = loc_str.split(",", 1)
                            result["lng"] = float(lng_str)
                            result["lat"] = float(lat_str)
                    
                    # 如果之前没有 geocode 结果，尝试对 POI 地址进行 geocode
                    if not result["formatted_address"] and best_match.get("address"):
                        gc_result = await self.get_geocode_info(best_match["address"], inferred_city)
                        if gc_result:
                            result.update({
                                "formatted_address": gc_result.get("formatted_address", ""),
                                "province": gc_result.get("province", ""),
                                "city": gc_result.get("city", ""),
                                "district": gc_result.get("district", ""),
                                "adcode": gc_result.get("adcode", ""),
                                "level": gc_result.get("level", "")
                            })
        except Exception as e:
            logger.error(f"POI搜索失败: {e}")

        # 如果还没有坐标，尝试对名称进行 geocode
        if result["lat"] is None and name:
            try:
                gc_result = await self.get_geocode_info(name_query, inferred_city)
                if gc_result:
                    result.update({
                        "lat": gc_result["lat"],
                        "lng": gc_result["lng"],
                        "formatted_address": gc_result.get("formatted_address", ""),
                        "province": gc_result.get("province", ""),
                        "city": gc_result.get("city", ""),
                        "district": gc_result.get("district", ""),
                        "adcode": gc_result.get("adcode", ""),
                        "level": gc_result.get("level", ""),
                        "source": "geocode_name"
                    })
            except Exception as e:
                logger.warning(f"名称geocode失败: {e}")

        if not result["images"]:
            result["images"] = [DEFAULT_IMAGE]

        return result


place_image_service = PlaceImageService()