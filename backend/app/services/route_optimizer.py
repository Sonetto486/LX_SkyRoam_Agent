"""
路线优化服务
使用最近邻算法优化景点访问顺序
"""

from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from loguru import logger
import math

from app.models.travel_plan import TravelPlan, TravelPlanItem
from app.tools.amap_rest_client import amap_rest_client


class RouteOptimizer:
    """路线优化服务"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def optimize_single_day_route(
        self,
        plan_id: int,
        date_str: str,
        start_point: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        优化单日路线

        Args:
            plan_id: 旅行计划ID
            date_str: 日期字符串 (YYYY-MM-DD格式)
            start_point: 自定义起点（包含name和coordinates）

        Returns:
            优化结果
        """
        # 获取旅行计划
        plan = await self._get_plan(plan_id)
        if not plan:
            return {
                "success": False,
                "message": "旅行计划不存在",
                "route_segments": []
            }

        # 获取指定日期的景点
        items_by_date = await self._group_items_by_date(plan)
        attractions = items_by_date.get(date_str, [])

        if not attractions:
            return {
                "success": False,
                "message": f"日期 {date_str} 没有景点数据",
                "route_segments": []
            }

        if len(attractions) < 2:
            logger.info(f"日期 {date_str} 只有 {len(attractions)} 个景点，无需优化")
            return {
                "success": True,
                "message": "景点数量不足，无需优化",
                "route_segments": []
            }

        logger.info(f"开始优化日期 {date_str} 的路线，共 {len(attractions)} 个景点")

        # 如果提供了自定义起点，创建一个虚拟景点作为起点
        if start_point and start_point.get("coordinates"):
            start_attraction = TravelPlanItem(
                id=-1,  # 临时ID
                title=start_point.get("name", "起点"),
                coordinates=start_point["coordinates"],
                item_type="attraction"
            )
            # 将起点添加到景点列表开头
            all_attractions = [start_attraction] + attractions
        else:
            all_attractions = attractions

        # 检查所有景点是否都有坐标
        valid_attractions = [
            a for a in all_attractions
            if a.coordinates and a.coordinates.get('lat') and a.coordinates.get('lng')
        ]

        if len(valid_attractions) < 2:
            logger.warning(f"日期 {date_str} 有效坐标景点不足2个")
            return {
                "success": False,
                "message": "有效坐标景点不足",
                "route_segments": []
            }

        # 使用最近邻算法排序
        ordered_attractions = self._nearest_neighbor_algorithm(valid_attractions)

        # 获取相邻景点间的路线信息
        route_segments = await self._get_route_segments(ordered_attractions)

        # 如果有自定义起点，移除起点相关的段
        if start_point and start_point.get("coordinates"):
            # 移除从起点到第一个景点的段（保留在返回结果中用于显示）
            # 但不更新数据库中的景点顺序
            pass
        else:
            # 更新数据库中的景点顺序（排除虚拟起点）
            actual_attractions = [a for a in ordered_attractions if a.id != -1]
            if actual_attractions:
                await self._update_attractions_order(actual_attractions, date_str)

        # 新增：同步景点顺序到JSON字段
        await self._sync_attractions_order_to_json(plan, date_str, ordered_attractions)

        # 计算总距离和时间
        total_distance = sum(seg.get("distance", 0) for seg in route_segments)
        total_duration = sum(seg.get("duration", 0) for seg in route_segments)

        return {
            "success": True,
            "date": date_str,
            "message": f"路线优化完成，共 {len(route_segments)} 个路段",
            "route_segments": route_segments,
            "total_distance": round(total_distance, 2),
            "total_duration": round(total_duration, 0),
            "ordered_items": [
                {
                    "id": item.id,
                    "title": item.title,
                    "coordinates": item.coordinates
                }
                for item in ordered_attractions if item.id != -1
            ]
        }

    async def optimize_route(self, plan_id: int) -> Dict[str, Any]:
        """
        优化整个行程的所有天路线

        Args:
            plan_id: 旅行计划ID

        Returns:
            优化结果
        """
        # 获取旅行计划
        plan = await self._get_plan(plan_id)
        if not plan:
            return {
                "success": False,
                "message": "旅行计划不存在",
                "optimized_days": []
            }

        # 按日期分组景点
        items_by_date = await self._group_items_by_date(plan)

        if not items_by_date:
            return {
                "success": False,
                "message": "无景点数据",
                "optimized_days": []
            }

        # 检查是否已经优化过
        if await self._is_already_optimized(plan):
            return {
                "success": True,
                "already_optimized": True,
                "message": "路线已经是最优，无需优化",
                "optimized_days": [],
                "stats": {
                    "total_distance": 0,
                    "total_duration": 0,
                    "days_optimized": 0
                }
            }

        optimized_days = []
        total_distance = 0
        total_duration = 0

        try:
            # 优化每一天的路线
            for date_str, attractions in items_by_date.items():
                if len(attractions) < 2:
                    logger.info(f"日期 {date_str} 只有 {len(attractions)} 个景点，无需优化")
                    continue

                logger.info(f"开始优化日期 {date_str} 的路线，共 {len(attractions)} 个景点")

                # 优化单日路线
                day_result = await self._optimize_day_route(date_str, attractions)

                if day_result["success"]:
                    optimized_days.append(day_result)
                    total_distance += day_result.get("total_distance", 0)
                    total_duration += day_result.get("total_duration", 0)

            if not optimized_days:
                return {
                    "success": False,
                    "message": "没有需要优化的路线",
                    "optimized_days": []
                }

            # 标记为已优化
            await self._mark_as_optimized(plan)

            return {
                "success": True,
                "already_optimized": False,
                "message": f"路线优化完成，共优化 {len(optimized_days)} 天",
                "optimized_days": optimized_days,
                "stats": {
                    "total_distance": round(total_distance, 2),
                    "total_duration": round(total_duration, 0),
                    "days_optimized": len(optimized_days)
                }
            }

        except Exception as e:
            logger.error(f"路线优化失败: {e}")
            return {
                "success": False,
                "message": f"优化失败: {str(e)}",
                "optimized_days": []
            }

    async def _optimize_day_route(
        self,
        date_str: str,
        attractions: List[TravelPlanItem]
    ) -> Dict[str, Any]:
        """
        优化单日路线

        Args:
            date_str: 日期字符串
            attractions: 景点列表

        Returns:
            优化结果
        """
        # 检查所有景点是否都有坐标
        valid_attractions = [
            a for a in attractions
            if a.coordinates and a.coordinates.get('lat') and a.coordinates.get('lng')
        ]

        if len(valid_attractions) < 2:
            logger.warning(f"日期 {date_str} 有效坐标景点不足2个，尝试自动填充坐标")

            # 自动调用一键优化填充坐标
            from app.services.itinerary_optimizer import ItineraryOptimizer
            optimizer = ItineraryOptimizer(self.db)

            # 只填充坐标，不均衡行程
            fill_result = await optimizer.fill_missing_coordinates(plan)

            if fill_result.get("coordinates_filled", 0) > 0:
                logger.info(f"自动填充了 {fill_result['coordinates_filled']} 个景点坐标")

                # 刷新plan对象，重新获取坐标
                await self.db.refresh(plan)

                # 重新获取景点列表
                items_by_date = await self._group_items_by_date(plan)
                attractions = items_by_date.get(date_str, [])

                # 重新检查坐标
                valid_attractions = [
                    a for a in attractions
                    if a.coordinates and a.coordinates.get('lat') and a.coordinates.get('lng')
                ]

                if len(valid_attractions) < 2:
                    logger.error(f"填充坐标后仍然不足2个景点")
                    return {
                        "success": False,
                        "message": "有效坐标景点不足，无法优化",
                        "date": date_str
                    }
            else:
                return {
                    "success": False,
                    "message": "无法自动填充景点坐标",
                    "date": date_str
                }

        # 使用最近邻算法排序
        ordered_attractions = self._nearest_neighbor_algorithm(valid_attractions)

        # 获取相邻景点间的路线信息
        route_segments = await self._get_route_segments(ordered_attractions)

        # 计算总距离和时间
        total_distance = sum(seg.get("distance", 0) for seg in route_segments)
        total_duration = sum(seg.get("duration", 0) for seg in route_segments)

        # 更新数据库中的景点顺序
        await self._update_attractions_order(ordered_attractions, date_str)

        return {
            "success": True,
            "date": date_str,
            "ordered_items": [
                {
                    "id": item.id,
                    "title": item.title,
                    "coordinates": item.coordinates
                }
                for item in ordered_attractions
            ],
            "route_segments": route_segments,
            "total_distance": total_distance,
            "total_duration": total_duration
        }

    def _nearest_neighbor_algorithm(
        self,
        attractions: List[TravelPlanItem]
    ) -> List[TravelPlanItem]:
        """
        最近邻算法 - 从第一个景点开始，每次选择最近的未访问景点

        Args:
            attractions: 景点列表（第一个景点作为起点）

        Returns:
            排序后的景点列表
        """
        if not attractions:
            return []

        ordered = [attractions[0]]  # 第一个景点作为起点
        remaining = attractions[1:]

        while remaining:
            current = ordered[-1]
            current_coords = current.coordinates

            # 找到距离当前景点最近的未访问景点
            nearest_idx = 0
            min_distance = float('inf')

            for i, attraction in enumerate(remaining):
                if not attraction.coordinates:
                    continue

                distance = self._calculate_distance(
                    current_coords['lat'],
                    current_coords['lng'],
                    attraction.coordinates['lat'],
                    attraction.coordinates['lng']
                )

                if distance < min_distance:
                    min_distance = distance
                    nearest_idx = i

            # 将最近的景点加入有序列表
            ordered.append(remaining.pop(nearest_idx))

        logger.info(f"最近邻算法完成，访问顺序: {[a.title for a in ordered]}")
        return ordered

    async def _get_route_segments(
        self,
        ordered_attractions: List[TravelPlanItem]
    ) -> List[Dict[str, Any]]:
        """
        获取相邻景点间的路线信息（包含多种出行方案）

        Args:
            ordered_attractions: 排序后的景点列表

        Returns:
            路线段信息列表
        """
        segments = []

        for i in range(len(ordered_attractions) - 1):
            from_attr = ordered_attractions[i]
            to_attr = ordered_attractions[i + 1]

            # 计算直线距离
            straight_distance = self._calculate_distance(
                from_attr.coordinates['lat'],
                from_attr.coordinates['lng'],
                to_attr.coordinates['lat'],
                to_attr.coordinates['lng']
            )

            # 根据距离确定主要出行方式
            mode = self._determine_travel_mode(straight_distance)

            # 计算多种出行方案
            alternatives = self._calculate_all_travel_modes(straight_distance)

            # 尝试调用地图API获取实际路线
            try:
                origin = f"{from_attr.coordinates['lng']},{from_attr.coordinates['lat']}"
                destination = f"{to_attr.coordinates['lng']},{to_attr.coordinates['lat']}"

                # 根据出行方式选择API
                api_mode = "driving" if mode == "driving" else "transit"

                # 获取城市名称（从第一个景点的位置推断，或使用默认值）
                city_name = "三亚"  # 默认城市
                # 尝试从景点地址中提取城市
                if from_attr.address:
                    # 简单的城市提取逻辑
                    for known_city in ["三亚", "北京", "上海", "广州", "深圳", "成都", "杭州", "西安", "重庆", "武汉"]:
                        if known_city in from_attr.address:
                            city_name = known_city
                            break

                routes = await amap_rest_client.get_directions(origin, destination, api_mode, city_name)

                if routes and len(routes) > 0:
                    # 使用API返回的实际距离和时间
                    route = routes[0]
                    actual_distance = route.get("distance", straight_distance)
                    actual_duration = route.get("duration", 0)

                    # 提取路线的详细路径点
                    path_points = []
                    if route.get("route"):
                        # 从路线步骤中提取路径点
                        for step in route.get("route", []):
                            if step.get("path"):
                                for point in step["path"]:
                                    path_points.append({
                                        "lng": point.get("lng") or point[0],
                                        "lat": point.get("lat") or point[1]
                                    })

                    segments.append({
                        "from": from_attr.title,
                        "to": to_attr.title,
                        "from_id": from_attr.id,
                        "to_id": to_attr.id,
                        "distance": actual_distance,
                        "duration": actual_duration,
                        "mode": mode,
                        "mode_label": self._get_mode_label(mode),
                        "path": path_points,  # 添加路径点
                        "alternatives": alternatives  # 添加多种出行方案
                    })
                else:
                    # API失败，使用直线距离估算
                    estimated_duration = self._estimate_duration(straight_distance, mode)
                    segments.append({
                        "from": from_attr.title,
                        "to": to_attr.title,
                        "from_id": from_attr.id,
                        "to_id": to_attr.id,
                        "distance": round(straight_distance, 2),
                        "duration": estimated_duration,
                        "mode": mode,
                        "mode_label": self._get_mode_label(mode),
                        "path": [],  # 没有路径点
                        "alternatives": alternatives
                    })

            except Exception as e:
                logger.warning(f"获取路线信息失败: {e}, 使用估算值")
                estimated_duration = self._estimate_duration(straight_distance, mode)
                segments.append({
                    "from": from_attr.title,
                    "to": to_attr.title,
                    "from_id": from_attr.id,
                    "to_id": to_attr.id,
                    "distance": round(straight_distance, 2),
                    "duration": estimated_duration,
                    "mode": mode,
                    "mode_label": self._get_mode_label(mode),
                    "path": [],  # 没有路径点
                    "alternatives": alternatives
                })

        return segments

    def _calculate_all_travel_modes(self, distance: float) -> List[Dict[str, Any]]:
        """
        计算所有出行方式的时间和距离

        Args:
            distance: 距离（km）

        Returns:
            多种出行方案列表
        """
        modes = ["walking", "transit", "driving"]
        alternatives = []

        for mode in modes:
            duration = self._estimate_duration(distance, mode)
            mode_label = self._get_mode_label(mode)
            alternatives.append({
                "mode": mode,
                "mode_label": mode_label,
                "duration": duration,
                "distance": round(distance, 2)
            })

        return alternatives

    def _determine_travel_mode(self, distance: float) -> str:
        """
        根据距离确定出行方式

        Args:
            distance: 距离（km）

        Returns:
            出行方式: walking, transit, driving
        """
        if distance < 1:
            return "walking"
        elif distance <= 5:
            return "transit"
        else:
            return "driving"

    def _get_mode_label(self, mode: str) -> str:
        """获取出行方式的中文标签"""
        labels = {
            "walking": "步行",
            "transit": "公交/骑行",
            "driving": "驾车"
        }
        return labels.get(mode, "未知")

    def _estimate_duration(self, distance: float, mode: str) -> int:
        """
        估算行程时间（分钟）

        Args:
            distance: 距离（km）
            mode: 出行方式

        Returns:
            预估时间（分钟）
        """
        # 平均速度（km/h）
        speeds = {
            "walking": 5,
            "transit": 20,
            "driving": 40
        }

        speed = speeds.get(mode, 20)
        duration_hours = distance / speed
        duration_minutes = int(duration_hours * 60)

        return max(5, duration_minutes)  # 最少5分钟

    def _calculate_distance(
        self,
        lat1: float,
        lng1: float,
        lat2: float,
        lng2: float
    ) -> float:
        """
        计算两点之间的距离（km）
        使用 Haversine 公式

        Args:
            lat1, lng1: 点1坐标
            lat2, lng2: 点2坐标

        Returns:
            距离（km）
        """
        R = 6371  # 地球半径（km）

        lat1_rad = math.radians(lat1)
        lat2_rad = math.radians(lat2)
        delta_lat = math.radians(lat2 - lat1)
        delta_lng = math.radians(lng2 - lng1)

        a = math.sin(delta_lat / 2) ** 2 + \
            math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(delta_lng / 2) ** 2
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

        return R * c

    async def _update_attractions_order(
        self,
        ordered_attractions: List[TravelPlanItem],
        date_str: str
    ):
        """
        更新景点顺序（通过调整 start_time）

        Args:
            ordered_attractions: 排序后的景点列表
            date_str: 日期字符串
        """
        # 基准时间：当天上午9点
        base_hour = 9

        for i, attraction in enumerate(ordered_attractions):
            # 为每个景点分配时间（每小时一个景点）
            new_hour = base_hour + i

            # 解析日期
            date_parts = date_str.split('-')
            year, month, day = int(date_parts[0]), int(date_parts[1]), int(date_parts[2])

            new_start_time = datetime(year, month, day, new_hour, 0, 0)

            # 更新数据库
            await self.db.execute(
                update(TravelPlanItem)
                .where(TravelPlanItem.id == attraction.id)
                .values(start_time=new_start_time)
            )

            # 更新对象属性
            attraction.start_time = new_start_time

        await self.db.commit()
        logger.info(f"已更新 {len(ordered_attractions)} 个景点的时间顺序")

    async def _get_plan(self, plan_id: int) -> Optional[TravelPlan]:
        """获取旅行计划"""
        result = await self.db.execute(
            select(TravelPlan).where(TravelPlan.id == plan_id)
        )
        return result.scalar_one_or_none()

    async def _group_items_by_date(self, plan: TravelPlan) -> Dict[str, List[TravelPlanItem]]:
        """按日期分组景点项目"""
        items_by_date = {}

        for item in plan.items:
            if item.item_type != 'attraction':
                continue

            # 获取日期
            if item.start_time:
                date_str = item.start_time.strftime('%Y-%m-%d')
            else:
                date_str = plan.start_date.strftime('%Y-%m-%d')

            if date_str not in items_by_date:
                items_by_date[date_str] = []

            items_by_date[date_str].append(item)

        # 按日期排序
        items_by_date = dict(sorted(items_by_date.items()))

        return items_by_date

    async def _is_already_optimized(self, plan: TravelPlan) -> bool:
        """
        检查路线是否已经优化过

        通过检查 preferences 中的 route_optimized 标记
        """
        if not plan.preferences:
            return False

        return plan.preferences.get('route_optimized', False)

    async def _mark_as_optimized(self, plan: TravelPlan):
        """
        标记路线为已优化
        """
        if not plan.preferences:
            plan.preferences = {}

        plan.preferences['route_optimized'] = True
        plan.preferences['route_optimized_at'] = datetime.now().isoformat()

        await self.db.commit()
        logger.info(f"行程 {plan.id} 已标记为路线优化完成")

    async def _sync_attractions_order_to_json(
        self,
        plan: TravelPlan,
        date_str: str,
        ordered_attractions: List[TravelPlanItem]
    ):
        """
        同步景点顺序到JSON字段（selected_plan 和 generated_plans）

        Args:
            plan: 旅行计划对象
            date_str: 日期字符串
            ordered_attractions: 排序后的景点列表
        """
        # 过滤掉虚拟起点（id=-1）
        actual_attractions = [a for a in ordered_attractions if a.id != -1]

        if not actual_attractions:
            return

        updated = False

        # 更新 selected_plan
        if plan.selected_plan and plan.selected_plan.get('daily_itineraries'):
            for day_itinerary in plan.selected_plan['daily_itineraries']:
                if day_itinerary.get('date') == date_str:
                    # 按新顺序重建 attractions 数组
                    day_itinerary['attractions'] = [
                        {
                            'name': item.title,
                            'address': item.address,
                            'coordinates': item.coordinates,
                            'type': item.details.get('type') if item.details else None,
                            'score': item.details.get('score') if item.details else None,
                            'description': item.description
                        }
                        for item in actual_attractions
                    ]
                    updated = True
                    logger.info(f"已同步 selected_plan 中 {date_str} 的景点顺序")
                    break

            # 触发字段更新
            if updated:
                plan.selected_plan = dict(plan.selected_plan)
                logger.info("已触发 selected_plan 字段更新")

        # 更新 generated_plans
        if plan.generated_plans:
            for generated_plan in plan.generated_plans:
                if generated_plan.get('daily_itineraries'):
                    for day_itinerary in generated_plan['daily_itineraries']:
                        if day_itinerary.get('date') == date_str:
                            day_itinerary['attractions'] = [
                                {
                                    'name': item.title,
                                    'address': item.address,
                                    'coordinates': item.coordinates,
                                    'type': item.details.get('type') if item.details else None,
                                    'score': item.details.get('score') if item.details else None,
                                    'description': item.description
                                }
                                for item in actual_attractions
                            ]
                            updated = True
                            logger.info(f"已同步 generated_plans 中 {date_str} 的景点顺序")
                            break

            # 触发字段更新
            if updated:
                plan.generated_plans = list(plan.generated_plans)
                logger.info("已触发 generated_plans 字段更新")

        if updated:
            await self.db.commit()
            logger.info("景点顺序JSON同步完成")
