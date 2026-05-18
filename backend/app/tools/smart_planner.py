from typing import List, Dict, Tuple, Optional, Any
import numpy as np
from math import radians, cos, sin, asin, sqrt
from datetime import datetime
from collections import defaultdict
import asyncio
import logging

logger = logging.getLogger(__name__)

class AmapClient:
    """简易高德地图客户端 - 仅用于获取交通时间"""
    def __init__(self):
        from app.core.config import settings
        self.api_key = settings.AMAP_API_KEY
        self.base_url = "https://restapi.amap.com/v3"
    
    async def get_direction(self, origin_lat: float, origin_lng: float,
                           dest_lat: float, dest_lng: float) -> Optional[Dict[str, Any]]:
        """获取起点到终点的交通时间（步行、驾车、公交）"""
        if not self.api_key:
            return None
        
        origin = f"{origin_lng},{origin_lat}"
        destination = f"{dest_lng},{dest_lat}"
        
        result = {
            "walking": {"duration": 0, "distance": 0},
            "driving": {"duration": 0, "distance": 0},
            "transit": {"duration": 0, "distance": 0}
        }
        
        try:
            import httpx
            async with httpx.AsyncClient(timeout=10.0) as client:
                # 步行路线
                walking_params = {
                    "key": self.api_key,
                    "origin": origin,
                    "destination": destination
                }
                walking_resp = await client.get(
                    f"{self.base_url}/direction/walking",
                    params=walking_params
                )
                walking_data = walking_resp.json()
                if walking_data.get("status") == "1":
                    path = walking_data.get("route", {}).get("paths", [{}])[0]
                    result["walking"] = {
                        "duration": int(path.get("duration", 0)) // 60,
                        "distance": round(int(path.get("distance", 0)) / 1000, 2)
                    }
                
                # 驾车路线
                driving_params = {
                    "key": self.api_key,
                    "origin": origin,
                    "destination": destination,
                    "extensions": "base"
                }
                driving_resp = await client.get(
                    f"{self.base_url}/direction/driving",
                    params=driving_params
                )
                driving_data = driving_resp.json()
                if driving_data.get("status") == "1":
                    path = driving_data.get("route", {}).get("paths", [{}])[0]
                    result["driving"] = {
                        "duration": int(path.get("duration", 0)) // 60,
                        "distance": round(int(path.get("distance", 0)) / 1000, 2)
                    }
                
                # 公交路线
                transit_params = {
                    "key": self.api_key,
                    "origin": origin,
                    "destination": destination,
                    "city": "全国"
                }
                transit_resp = await client.get(
                    f"{self.base_url}/direction/transit/integrated",
                    params=transit_params
                )
                transit_data = transit_resp.json()
                if transit_data.get("status") == "1":
                    transit = transit_data.get("route", {}).get("transits", [{}])[0]
                    result["transit"] = {
                        "duration": int(transit.get("duration", 0)) // 60,
                        "distance": round(int(transit.get("distance", 0)) / 1000, 2)
                    }
                
                return result
        except Exception:
            return None
    
    async def reverse_geocode(self, lat: float, lng: float) -> Optional[Dict[str, Any]]:
        """反向地理编码 - 根据坐标获取行政区划信息"""
        if not self.api_key:
            return None
        
        try:
            import httpx
            async with httpx.AsyncClient(timeout=10.0) as client:
                params = {
                    "key": self.api_key,
                    "location": f"{lng},{lat}",
                    "output": "json",
                    "extensions": "all"
                }
                response = await client.get(
                    f"{self.base_url}/geocode/regeo",
                    params=params
                )
                data = response.json()
                
                if data.get("status") == "1":
                    regeocode = data.get("regeocode", {})
                    address_component = regeocode.get("addressComponent", {})
                    return {
                        "province": address_component.get("province", ""),
                        "city": address_component.get("city", ""),
                        "district": address_component.get("district", ""),
                        "street": address_component.get("street", ""),
                        "street_number": address_component.get("streetNumber", ""),
                        "formatted_address": regeocode.get("formatted_address", "")
                    }
            return None
        except Exception:
            return None

class Location:
    def __init__(self, id: int, name: str, lat: float, lng: float, type: str,
                 estimated_duration: float = 1.0, address: str = ""):
        self.id = id
        self.name = name
        self.lat = lat
        self.lng = lng
        self.type = type
        self.estimated_duration = estimated_duration
        self.address = address

class DailyPlan:
    def __init__(self, day_number: int):
        self.day_number = day_number
        self.locations: List[Dict[str, Any]] = []
        self.start_time = "09:00"
        self.end_time = "18:00"
        self.total_duration = 0.0
        self.warnings: List[str] = []

class SmartPlanner:
    def __init__(self):
        self.WALKING_SPEED = 5
        self.DRIVING_SPEED = 30
        self.LUNCH_WINDOW = (11.5, 13.5)
        self.DINNER_WINDOW = (17.5, 20.0)
        self.MEAL_DURATION = 1.0
        self.DAILY_AVAILABLE_HOURS = 9.0

    def haversine_distance(self, lat1: float, lng1: float, lat2: float, lng2: float) -> float:
        lat1, lng1, lat2, lng2 = map(radians, [lat1, lng1, lat2, lng2])
        dlat = lat2 - lat1
        dlng = lng2 - lng1
        a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlng/2)**2
        c = 2 * asin(sqrt(a))
        r = 6371
        return c * r

    def calculate_travel_time(self, lat1: float, lng1: float, lat2: float, lng2: float,
                             mode: str = "walking") -> float:
        distance = self.haversine_distance(lat1, lng1, lat2, lng2)
        speed = self.WALKING_SPEED if mode == "walking" else self.DRIVING_SPEED
        return distance / speed

    def build_time_matrix(self, locations: List[Location], hotel_loc: Optional[Tuple[float, float]] = None) -> np.ndarray:
        all_points = [(loc.lat, loc.lng) for loc in locations]
        if hotel_loc:
            all_points.insert(0, hotel_loc)

        n = len(all_points)
        matrix = np.zeros((n, n))

        for i in range(n):
            for j in range(n):
                if i != j:
                    matrix[i, j] = self.calculate_travel_time(
                        all_points[i][0], all_points[i][1],
                        all_points[j][0], all_points[j][1]
                    )
        return matrix

    def kmeans_cluster(self, locations: List[Location], days: int) -> List[List[int]]:
        """Pure Python K-Means implementation using numpy."""
        coords = np.array([[loc.lat, loc.lng] for loc in locations])

        if len(locations) <= days:
            return [[i] for i in range(len(locations))]

        np.random.seed(42)
        indices = np.random.choice(len(locations), days, replace=False)
        centroids = coords[indices].copy()

        for _ in range(100):
            distances = np.zeros((len(locations), days))
            for j in range(days):
                diff = coords - centroids[j]
                distances[:, j] = np.sqrt(np.sum(diff ** 2, axis=1))

            labels = np.argmin(distances, axis=1)

            new_centroids = np.zeros_like(centroids)
            for j in range(days):
                mask = labels == j
                if np.sum(mask) > 0:
                    new_centroids[j] = np.mean(coords[mask], axis=0)
                else:
                    new_centroids[j] = centroids[j]

            if np.allclose(centroids, new_centroids):
                break
            centroids = new_centroids

        clusters = defaultdict(list)
        for idx, label in enumerate(labels):
            clusters[label].append(idx)

        return list(clusters.values())

    def nearest_neighbor_tsp(self, time_matrix: np.ndarray, start_idx: int = 0) -> List[int]:
        n = time_matrix.shape[0]
        visited = [False] * n
        path = [start_idx]
        visited[start_idx] = True

        current = start_idx
        for _ in range(n - 1):
            min_time = float('inf')
            next_idx = -1
            for i in range(n):
                if not visited[i] and time_matrix[current, i] < min_time:
                    min_time = time_matrix[current, i]
                    next_idx = i
            if next_idx != -1:
                visited[next_idx] = True
                path.append(next_idx)
                current = next_idx

        return path

    def two_opt(self, path: List[int], time_matrix: np.ndarray) -> List[int]:
        n = len(path)
        improved = True
        best_path = path.copy()
        best_time = self.calculate_path_time(best_path, time_matrix)

        while improved:
            improved = False
            for i in range(1, n - 1):
                for j in range(i + 1, n):
                    new_path = best_path[:i] + best_path[i:j+1][::-1] + best_path[j+1:]
                    new_time = self.calculate_path_time(new_path, time_matrix)
                    if new_time < best_time:
                        best_path = new_path
                        best_time = new_time
                        improved = True

        return best_path

    def calculate_path_time(self, path: List[int], time_matrix: np.ndarray) -> float:
        total = 0.0
        for i in range(len(path) - 1):
            total += time_matrix[path[i], path[i+1]]
        total += time_matrix[path[-1], path[0]]
        return total

    def insert_meals(self, day_plan: List[Dict[str, Any]], restaurants: List[Dict[str, Any]],
                     start_time: float = 9.0) -> Tuple[List[Dict[str, Any]], List[str]]:
        result = []
        warnings = []
        current_time = start_time
        lunch_inserted = False
        dinner_inserted = False
        used_restaurants = set()

        for idx, loc in enumerate(day_plan):
            # 午餐插入：只能在11:30-13:30之间，且必须已经游览至少一个景点
            if not lunch_inserted and idx > 0 and self.LUNCH_WINDOW[0] <= current_time <= self.LUNCH_WINDOW[1]:
                meal = self._select_restaurant(restaurants, loc,
                                               day_plan[idx+1] if idx+1 < len(day_plan) else None,
                                               used_restaurants)
                if meal:
                    result.append({
                        "id": -1,
                        "name": meal["name"],
                        "type": "餐饮",
                        "lat": meal["lat"],
                        "lng": meal["lng"],
                        "estimated_duration": self.MEAL_DURATION,
                        "arrival_time": self._format_time(current_time),
                        "departure_time": self._format_time(current_time + self.MEAL_DURATION),
                        "meal_type": "午餐"
                    })
                    current_time += self.MEAL_DURATION
                    lunch_inserted = True
                    used_restaurants.add(meal["name"])

            # 添加当前地点
            result.append({
                **loc,
                "arrival_time": self._format_time(current_time),
                "departure_time": self._format_time(current_time + loc["estimated_duration"])
            })
            current_time += loc["estimated_duration"]

            # 计算到下一个地点的时间
            if idx + 1 < len(day_plan):
                travel_time = self.calculate_travel_time(
                    loc["lat"], loc["lng"],
                    day_plan[idx+1]["lat"], day_plan[idx+1]["lng"]
                )
                current_time += travel_time

            # 晚餐插入：只能在17:30-20:00之间
            if not dinner_inserted and self.DINNER_WINDOW[0] <= current_time <= self.DINNER_WINDOW[1]:
                meal = self._select_restaurant(restaurants, loc,
                                               day_plan[idx+1] if idx+1 < len(day_plan) else None,
                                               used_restaurants)
                if meal:
                    result.append({
                        "id": -2,
                        "name": meal["name"],
                        "type": "餐饮",
                        "lat": meal["lat"],
                        "lng": meal["lng"],
                        "estimated_duration": self.MEAL_DURATION,
                        "arrival_time": self._format_time(current_time),
                        "departure_time": self._format_time(current_time + self.MEAL_DURATION),
                        "meal_type": "晚餐"
                    })
                    current_time += self.MEAL_DURATION
                    dinner_inserted = True
                    used_restaurants.add(meal["name"])

        # 不要强制添加晚餐，如果时间太晚或行程太短就不添加
        if not dinner_inserted and current_time < self.DINNER_WINDOW[1] and len(day_plan) >= 2:
            last_loc = day_plan[-1] if day_plan else result[-1]
            meal = self._select_restaurant(restaurants, last_loc, None, used_restaurants)
            if meal:
                result.append({
                    "id": -2,
                    "name": meal["name"],
                    "type": "餐饮",
                    "lat": meal["lat"],
                    "lng": meal["lng"],
                    "estimated_duration": self.MEAL_DURATION,
                    "arrival_time": self._format_time(current_time),
                    "departure_time": self._format_time(current_time + self.MEAL_DURATION),
                    "meal_type": "晚餐"
                })

        if current_time > 18.0:
            warnings.append(f"当天行程结束时间预计为 {self._format_time(current_time)}，超过计划结束时间18:00")

        return result, warnings

    async def insert_meals_async(self, day_plan: List[Dict[str, Any]], 
                                  restaurants: List[Dict[str, Any]],
                                  amap_client: AmapClient,
                                  start_time: float = 9.0) -> Tuple[List[Dict[str, Any]], List[str]]:
        """异步版本的insert_meals，使用高德API获取真实交通时间"""
        result = []
        warnings = []
        current_time = start_time
        lunch_inserted = False
        dinner_inserted = False
        used_restaurants = set()

        async def get_travel_info(from_loc: Dict, to_loc: Dict) -> Dict[str, Any]:
            """获取两个地点间的交通时间"""
            direction = await amap_client.get_direction(
                from_loc["lat"], from_loc["lng"],
                to_loc["lat"], to_loc["lng"]
            )
            if direction:
                return direction
            # 如果API失败，返回估算值
            distance = self.haversine_distance(
                from_loc["lat"], from_loc["lng"],
                to_loc["lat"], to_loc["lng"]
            )
            return {
                "walking": {"duration": int(distance / 5 * 60), "distance": round(distance, 2)},
                "driving": {"duration": int(distance / 30 * 60), "distance": round(distance, 2)},
                "transit": {"duration": int(distance / 15 * 60), "distance": round(distance, 2)}
            }

        for idx, loc in enumerate(day_plan):
            # 午餐插入
            if not lunch_inserted and idx > 0 and self.LUNCH_WINDOW[0] <= current_time <= self.LUNCH_WINDOW[1]:
                meal = self._select_restaurant(restaurants, loc,
                                               day_plan[idx+1] if idx+1 < len(day_plan) else None,
                                               used_restaurants)
                if meal:
                    # 获取到餐厅的交通时间
                    travel = await get_travel_info(loc, meal)
                    # 获取餐厅的行政区划信息
                    geo_info = await amap_client.reverse_geocode(meal["lat"], meal["lng"])
                    address = ""
                    if geo_info:
                        district = geo_info.get("district", "")
                        city = geo_info.get("city", "")
                        if district:
                            address = f"{city}{district}" if city else district
                    
                    result.append({
                        "id": -1,
                        "name": meal["name"],
                        "type": "餐饮",
                        "lat": meal["lat"],
                        "lng": meal["lng"],
                        "estimated_duration": self.MEAL_DURATION,
                        "arrival_time": self._format_time(current_time),
                        "departure_time": self._format_time(current_time + self.MEAL_DURATION),
                        "meal_type": "午餐",
                        "address": address,
                        "travel_to": {
                            "walking": f"{travel['walking']['duration']}分钟",
                            "driving": f"{travel['driving']['duration']}分钟",
                            "transit": f"{travel['transit']['duration']}分钟"
                        }
                    })
                    current_time += self.MEAL_DURATION
                    lunch_inserted = True
                    used_restaurants.add(meal["name"])

            # 添加当前地点
            travel_info = None
            if idx + 1 < len(day_plan):
                travel_info = await get_travel_info(loc, day_plan[idx+1])

            result.append({
                **loc,
                "arrival_time": self._format_time(current_time),
                "departure_time": self._format_time(current_time + loc["estimated_duration"])
            })
            current_time += loc["estimated_duration"]

            # 计算到下一个地点的时间
            if idx + 1 < len(day_plan) and travel_info:
                current_time += travel_info["driving"]["duration"] / 60

            # 晚餐插入
            if not dinner_inserted and self.DINNER_WINDOW[0] <= current_time <= self.DINNER_WINDOW[1]:
                meal = self._select_restaurant(restaurants, loc,
                                               day_plan[idx+1] if idx+1 < len(day_plan) else None,
                                               used_restaurants)
                if meal:
                    travel = await get_travel_info(loc, meal)
                    # 获取餐厅的行政区划信息
                    geo_info = await amap_client.reverse_geocode(meal["lat"], meal["lng"])
                    address = ""
                    if geo_info:
                        district = geo_info.get("district", "")
                        city = geo_info.get("city", "")
                        if district:
                            address = f"{city}{district}" if city else district
                    
                    result.append({
                        "id": -2,
                        "name": meal["name"],
                        "type": "餐饮",
                        "lat": meal["lat"],
                        "lng": meal["lng"],
                        "estimated_duration": self.MEAL_DURATION,
                        "arrival_time": self._format_time(current_time),
                        "departure_time": self._format_time(current_time + self.MEAL_DURATION),
                        "meal_type": "晚餐",
                        "address": address,
                        "travel_to": {
                            "walking": f"{travel['walking']['duration']}分钟",
                            "driving": f"{travel['driving']['duration']}分钟",
                            "transit": f"{travel['transit']['duration']}分钟"
                        }
                    })
                    current_time += self.MEAL_DURATION
                    dinner_inserted = True
                    used_restaurants.add(meal["name"])

        # 晚餐兜底
        if not dinner_inserted and current_time < self.DINNER_WINDOW[1] and len(day_plan) >= 2:
            last_loc = day_plan[-1] if day_plan else result[-1]
            meal = self._select_restaurant(restaurants, last_loc, None, used_restaurants)
            if meal:
                # 获取餐厅的行政区划信息
                geo_info = await amap_client.reverse_geocode(meal["lat"], meal["lng"])
                address = ""
                if geo_info:
                    district = geo_info.get("district", "")
                    city = geo_info.get("city", "")
                    if district:
                        address = f"{city}{district}" if city else district
                
                result.append({
                    "id": -2,
                    "name": meal["name"],
                    "type": "餐饮",
                    "lat": meal["lat"],
                    "lng": meal["lng"],
                    "estimated_duration": self.MEAL_DURATION,
                    "arrival_time": self._format_time(current_time),
                    "departure_time": self._format_time(current_time + self.MEAL_DURATION),
                    "meal_type": "晚餐",
                    "address": address
                })

        if current_time > 18.0:
            warnings.append(f"当天行程结束时间预计为 {self._format_time(current_time)}，超过计划结束时间18:00")

        return result, warnings

    def _select_restaurant(self, restaurants: List[Dict[str, Any]],
                          current_loc: Dict[str, Any], next_loc: Optional[Dict[str, Any]],
                          used_restaurants: set = None) -> Optional[Dict[str, Any]]:
        if used_restaurants is None:
            used_restaurants = set()

        # 过滤掉已使用过的餐饮点
        available_restaurants = [r for r in restaurants if r["name"] not in used_restaurants]
        
        if not available_restaurants:
            # 如果没有可用的餐饮点，返回None表示跳过
            return None

        best_score = float('inf')
        best_rest = available_restaurants[0]

        for rest in available_restaurants:
            dist_to_current = self.haversine_distance(current_loc["lat"], current_loc["lng"],
                                                      rest["lat"], rest["lng"])
            if next_loc:
                dist_to_next = self.haversine_distance(rest["lat"], rest["lng"],
                                                      next_loc["lat"], next_loc["lng"])
                score = dist_to_current * 0.6 + dist_to_next * 0.4
            else:
                score = dist_to_current

            if score < best_score:
                best_score = score
                best_rest = rest

        return best_rest

    def _format_time(self, hours: float) -> str:
        h = int(hours)
        m = int((hours - h) * 60)
        return f"{h:02d}:{m:02d}"

    async def recommend_accommodation_area(self, attractions: List[Dict[str, Any]], 
                                          amap_client: AmapClient) -> Dict[str, Any]:
        """
        鲁棒版住宿区域推荐（解决异常值拉偏问题）
        算法：DBSCAN聚类找到主集群 → 中位数中心计算 → 异常值过滤
        """
        if not attractions:
            return {
                "center_lat": 0,
                "center_lng": 0,
                "message": "没有景点数据，无法推荐住宿区域"
            }
        
        # ======================
        # 步骤1：数据清洗与预处理
        # ======================
        valid_attractions = []
        invalid_attractions = []
        
        for att in attractions:
            lat = att.get("lat", 0)
            lng = att.get("lng", 0)
            
            # 过滤明显无效的坐标
            if (lat == 0 and lng == 0) or abs(lat) < 1 or abs(lng) < 1:
                invalid_attractions.append(att["name"])
                continue
            
            # 过滤中国境外坐标（中国范围：北纬18°-54°，东经73°-135°）
            if not (18 <= lat <= 54 and 73 <= lng <= 135):
                invalid_attractions.append(att["name"])
                continue
                
            valid_attractions.append(att)
        
        if not valid_attractions:
            return {
                "center_lat": 0,
                "center_lng": 0,
                "message": "所有景点坐标无效，无法推荐住宿区域",
                "invalid_attractions": invalid_attractions
            }
        
        if invalid_attractions:
            logger.warning(f"⚠️ 发现 {len(invalid_attractions)} 个无效坐标的景点: {invalid_attractions}")
        
        # ======================
        # 步骤2：DBSCAN聚类找到主景点集群
        # ======================
        coords = np.array([[att["lat"], att["lng"]] for att in valid_attractions])
        
        # 使用DBSCAN聚类，eps=0.5度≈55公里，min_samples=2
        from sklearn.cluster import DBSCAN
        clustering = DBSCAN(eps=0.5, min_samples=2).fit(coords)
        labels = clustering.labels_
        
        # 找到最大的集群（主景点区）
        unique_labels, counts = np.unique(labels, return_counts=True)
        main_cluster_label = unique_labels[np.argmax(counts)]
        
        # 只保留主集群内的景点
        main_cluster_indices = np.where(labels == main_cluster_label)[0]
        main_attractions = [valid_attractions[i] for i in main_cluster_indices]
        outlier_attractions = [valid_attractions[i] for i in np.where(labels != main_cluster_label)[0]]
        
        if outlier_attractions:
            logger.info(f"ℹ️ 识别出 {len(outlier_attractions)} 个远离主景区的孤立景点: {[a['name'] for a in outlier_attractions]}")
        
        # ======================
        # 步骤3：计算中位数中心（对异常值不敏感）
        # ======================
        main_coords = np.array([[att["lat"], att["lng"]] for att in main_attractions])
        median_lat = np.median(main_coords[:, 0])
        median_lng = np.median(main_coords[:, 1])
        
        # ======================
        # 步骤4：计算到主中心的平均距离
        # ======================
        avg_distance = sum(
            self.haversine_distance(att["lat"], att["lng"], median_lat, median_lng)
            for att in main_attractions
        ) / len(main_attractions)
        
        # ======================
        # 步骤5：获取行政区划信息
        # ======================
        province = ""
        city = ""
        district = ""
        area_info = ""
        
        try:
            geo_info = await amap_client.reverse_geocode(median_lat, median_lng)
            if geo_info:
                province = geo_info.get("province", "")
                city = geo_info.get("city", "")
                district = geo_info.get("district", "")
                
                if district:
                    area_info = f"{city}{district}" if city else district
                elif city:
                    area_info = city
                elif province:
                    area_info = province
        except Exception as e:
            logger.warning(f"⚠️ 高德API调用失败，使用本地估算: {e}")
        
        # ======================
        # 步骤6：找出距离中心最近的参考景点
        # ======================
        attractions_with_dist = sorted(
            main_attractions,
            key=lambda x: self.haversine_distance(x["lat"], x["lng"], median_lat, median_lng)
        )
        
        nearby_attractions = attractions_with_dist[:3]
        
        # ======================
        # 步骤7：构建推荐消息
        # ======================
        if area_info:
            message = f"建议选择在{area_info}附近的住宿，交通便利且到各景点距离均衡"
        else:
            message = "建议选择在这个中心点附近的住宿，交通便利且到各景点距离均衡"
        
        result = {
            "center_lat": round(median_lat, 4),
            "center_lng": round(median_lng, 4),
            "province": province,
            "city": city,
            "district": district,
            "area_description": area_info,
            "average_distance_km": round(avg_distance, 2),
            "nearby_attractions": [
                {
                    "name": a["name"],
                    "lat": a["lat"],
                    "lng": a["lng"],
                    "distance_km": round(self.haversine_distance(a["lat"], a["lng"], median_lat, median_lng), 2)
                }
                for a in nearby_attractions
            ],
            "message": message
        }
        
        if invalid_attractions:
            result["invalid_attractions"] = invalid_attractions
        if outlier_attractions:
            result["outlier_attractions"] = [a["name"] for a in outlier_attractions]
        
        return result
    
    def recommend_accommodation_area_sync(self, attractions: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        鲁棒版同步住宿区域推荐（不调用高德API）
        """
        if not attractions:
            return {
                "center_lat": 0,
                "center_lng": 0,
                "message": "没有景点数据，无法推荐住宿区域"
            }
        
        # 数据清洗
        valid_attractions = []
        invalid_attractions = []
        
        for att in attractions:
            lat = att.get("lat", 0)
            lng = att.get("lng", 0)
            
            if (lat == 0 and lng == 0) or abs(lat) < 1 or abs(lng) < 1:
                invalid_attractions.append(att["name"])
                continue
            
            if not (18 <= lat <= 54 and 73 <= lng <= 135):
                invalid_attractions.append(att["name"])
                continue
                
            valid_attractions.append(att)
        
        if not valid_attractions:
            return {
                "center_lat": 0,
                "center_lng": 0,
                "message": "所有景点坐标无效，无法推荐住宿区域",
                "invalid_attractions": invalid_attractions
            }
        
        # DBSCAN聚类
        coords = np.array([[att["lat"], att["lng"]] for att in valid_attractions])
        
        try:
            from sklearn.cluster import DBSCAN
            clustering = DBSCAN(eps=0.5, min_samples=2).fit(coords)
            labels = clustering.labels_
            
            unique_labels, counts = np.unique(labels, return_counts=True)
            main_cluster_label = unique_labels[np.argmax(counts)]
            
            main_cluster_indices = np.where(labels == main_cluster_label)[0]
            main_attractions = [valid_attractions[i] for i in main_cluster_indices]
        except ImportError:
            # 如果没有sklearn，降级使用中位数中心
            logger.warning("⚠️ 未安装scikit-learn，降级使用简单中位数中心")
            main_attractions = valid_attractions
        
        # 计算中位数中心
        main_coords = np.array([[att["lat"], att["lng"]] for att in main_attractions])
        median_lat = np.median(main_coords[:, 0])
        median_lng = np.median(main_coords[:, 1])
        
        # 计算平均距离
        avg_distance = sum(
            self.haversine_distance(att["lat"], att["lng"], median_lat, median_lng)
            for att in main_attractions
        ) / len(main_attractions)
        
        # 找出最近的景点
        attractions_with_dist = sorted(
            main_attractions,
            key=lambda x: self.haversine_distance(x["lat"], x["lng"], median_lat, median_lng)
        )
        
        nearby_attractions = attractions_with_dist[:3]
        
        result = {
            "center_lat": round(median_lat, 4),
            "center_lng": round(median_lng, 4),
            "province": "",
            "city": "",
            "district": "",
            "area_description": "",
            "average_distance_km": round(avg_distance, 2),
            "nearby_attractions": [
                {
                    "name": a["name"],
                    "lat": a["lat"],
                    "lng": a["lng"],
                    "distance_km": round(self.haversine_distance(a["lat"], a["lng"], median_lat, median_lng), 2)
                }
                for a in nearby_attractions
            ],
            "message": "建议选择在这个中心点附近的住宿，交通便利且到各景点距离均衡"
        }
        
        if invalid_attractions:
            result["invalid_attractions"] = invalid_attractions
        
        return result

    async def plan_async(self, locations: List[Dict[str, Any]], days: int,
                         return_to_hotel: bool = True) -> Dict[str, Any]:
        hotels = [loc for loc in locations if loc.get("type") == "酒店"]
        restaurants = [loc for loc in locations if loc.get("type") == "餐饮"]
        
        # 聚类只针对景点，排除餐饮和酒店
        attractions = [loc for loc in locations if loc.get("type") not in ("酒店", "餐饮")]

        use_virtual_hotel = False
        hotel_loc = None
        if not hotels:
            use_virtual_hotel = True
            if attractions:
                avg_lat = sum(loc["lat"] for loc in attractions) / len(attractions)
                avg_lng = sum(loc["lng"] for loc in attractions) / len(attractions)
                hotel_loc = (avg_lat, avg_lng)
            elif restaurants:
                avg_lat = sum(loc["lat"] for loc in restaurants) / len(restaurants)
                avg_lng = sum(loc["lng"] for loc in restaurants) / len(restaurants)
                hotel_loc = (avg_lat, avg_lng)

        # 只对景点进行聚类
        loc_objects = [Location(
            id=i,
            name=loc["name"],
            lat=loc["lat"],
            lng=loc["lng"],
            type=loc["type"],
            estimated_duration=loc.get("estimated_duration", 1.0),
            address=loc.get("address", "")
        ) for i, loc in enumerate(attractions)]

        clusters = self.kmeans_cluster(loc_objects, days)

        daily_plans = []
        total_warnings = []

        if use_virtual_hotel:
            total_warnings.append("")

        amap_client = AmapClient()

        for day_idx, cluster in enumerate(clusters):
            day_number = day_idx + 1
            day_locs = [attractions[i] for i in cluster]

            day_coords = [(loc["lat"], loc["lng"]) for loc in day_locs]
            if hotel_loc:
                day_coords.insert(0, hotel_loc)

            n = len(day_coords)
            time_matrix = np.zeros((n, n))
            for i in range(n):
                for j in range(n):
                    if i != j:
                        time_matrix[i, j] = self.calculate_travel_time(
                            day_coords[i][0], day_coords[i][1],
                            day_coords[j][0], day_coords[j][1]
                        )

            initial_path = self.nearest_neighbor_tsp(time_matrix, 0 if hotel_loc else 0)
            optimized_path = self.two_opt(initial_path, time_matrix)

            if hotel_loc:
                optimized_path = [p - 1 for p in optimized_path if p != 0]

            ordered_locs = [day_locs[i] for i in optimized_path if i >= 0 and i < len(day_locs)]

            day_plan, day_warnings = await self.insert_meals_async(ordered_locs, restaurants, amap_client)
            total_warnings.extend(day_warnings)

            daily_plans.append({
                "day_number": day_number,
                "start_time": "09:00",
                "end_time": "18:00",
                "items": day_plan,
                "warnings": day_warnings
            })

        # 推荐住宿区域（精确到区）
        accommodation_recommendation = await self.recommend_accommodation_area(attractions, amap_client)
        
        return {
            "daily_plans": daily_plans,
            "warnings": total_warnings,
            "use_virtual_hotel": use_virtual_hotel,
            "total_locations": len(locations),
            "days": days,
            "accommodation_recommendation": accommodation_recommendation
        }
    
    def plan(self, locations: List[Dict[str, Any]], days: int,
             return_to_hotel: bool = True) -> Dict[str, Any]:
        """同步版本的plan方法（不调用高德API）"""
        hotels = [loc for loc in locations if loc.get("type") == "酒店"]
        restaurants = [loc for loc in locations if loc.get("type") == "餐饮"]
        
        # 聚类只针对景点，排除餐饮和酒店
        attractions = [loc for loc in locations if loc.get("type") not in ("酒店", "餐饮")]

        use_virtual_hotel = False
        hotel_loc = None
        if not hotels:
            use_virtual_hotel = True
            if attractions:
                avg_lat = sum(loc["lat"] for loc in attractions) / len(attractions)
                avg_lng = sum(loc["lng"] for loc in attractions) / len(attractions)
                hotel_loc = (avg_lat, avg_lng)
            elif restaurants:
                avg_lat = sum(loc["lat"] for loc in restaurants)
                avg_lng = sum(loc["lng"] for loc in restaurants)
                hotel_loc = (avg_lat, avg_lng)

        # 只对景点进行聚类
        loc_objects = [Location(
            id=i,
            name=loc["name"],
            lat=loc["lat"],
            lng=loc["lng"],
            type=loc["type"],
            estimated_duration=loc.get("estimated_duration", 1.0),
            address=loc.get("address", "")
        ) for i, loc in enumerate(attractions)]

        clusters = self.kmeans_cluster(loc_objects, days)

        daily_plans = []
        total_warnings = []

        if use_virtual_hotel:
            total_warnings.append("")

        for day_idx, cluster in enumerate(clusters):
            day_number = day_idx + 1
            day_locs = [attractions[i] for i in cluster]

            day_coords = [(loc["lat"], loc["lng"]) for loc in day_locs]
            if hotel_loc:
                day_coords.insert(0, hotel_loc)

            n = len(day_coords)
            time_matrix = np.zeros((n, n))
            for i in range(n):
                for j in range(n):
                    if i != j:
                        time_matrix[i, j] = self.calculate_travel_time(
                            day_coords[i][0], day_coords[i][1],
                            day_coords[j][0], day_coords[j][1]
                        )

            initial_path = self.nearest_neighbor_tsp(time_matrix, 0 if hotel_loc else 0)
            optimized_path = self.two_opt(initial_path, time_matrix)

            if hotel_loc:
                optimized_path = [p - 1 for p in optimized_path if p != 0]

            ordered_locs = [day_locs[i] for i in optimized_path if i >= 0 and i < len(day_locs)]

            day_plan, day_warnings = self.insert_meals(ordered_locs, restaurants)
            total_warnings.extend(day_warnings)

            daily_plans.append({
                "day_number": day_number,
                "start_time": "09:00",
                "end_time": "18:00",
                "items": day_plan,
                "warnings": day_warnings
            })

        # 推荐住宿区域（同步版本，不调用高德API）
        accommodation_recommendation = self.recommend_accommodation_area_sync(attractions)
        
        return {
            "daily_plans": daily_plans,
            "warnings": total_warnings,
            "use_virtual_hotel": use_virtual_hotel,
            "total_locations": len(locations),
            "days": days,
            "accommodation_recommendation": accommodation_recommendation
        }