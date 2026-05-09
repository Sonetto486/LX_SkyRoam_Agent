"""
行程优化服务
提供景点坐标填充和行程均衡功能
"""

from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from loguru import logger
import math

from app.models.travel_plan import TravelPlan, TravelPlanItem
from app.models.attraction_detail import AttractionDetail
from app.tools.unified_map_service import UnifiedMapService


class ItineraryOptimizer:
    """行程优化服务"""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.map_service = UnifiedMapService()

    async def optimize(
        self,
        plan_id: int,
        fill_coordinates: bool = True,
        balance_schedule: bool = True
    ) -> Dict[str, Any]:
        """
        优化行程

        Args:
            plan_id: 旅行计划ID
            fill_coordinates: 是否填充缺失的坐标
            balance_schedule: 是否均衡行程

        Returns:
            优化结果统计
        """
        # 获取旅行计划
        plan = await self._get_plan(plan_id)
        if not plan:
            return {
                "success": False,
                "message": "旅行计划不存在",
                "stats": {}
            }

        stats = {
            "coordinates_filled": 0,
            "items_moved": 0,
            "days_balanced": False
        }

        try:
            # 1. 填充缺失的坐标
            if fill_coordinates:
                coord_result = await self.fill_missing_coordinates(plan)
                stats["coordinates_filled"] = coord_result.get("coordinates_filled", 0)

            # 2. 均衡行程
            if balance_schedule:
                balance_result = await self.balance_schedule(plan)
                stats["items_moved"] = balance_result.get("items_moved", 0)
                stats["days_balanced"] = balance_result.get("days_balanced", False)

            # 刷新计划数据
            await self.db.refresh(plan)

            return {
                "success": True,
                "message": "优化完成",
                "stats": stats
            }

        except Exception as e:
            logger.error(f"优化行程失败: {e}")
            return {
                "success": False,
                "message": f"优化失败: {str(e)}",
                "stats": stats
            }

    async def fill_missing_coordinates(self, plan: TravelPlan) -> Dict[str, Any]:
        """
        填充缺失的景点坐标

        Args:
            plan: 旅行计划对象

        Returns:
            填充统计
        """
        filled_count = 0

        # 获取所有景点类型的行程项目
        items = [item for item in plan.items if item.item_type == 'attraction']

        for item in items:
            # 检查是否已有坐标
            if item.coordinates and item.coordinates.get('lat') and item.coordinates.get('lng'):
                logger.debug(f"景点 {item.title} 已有坐标，跳过")
                continue

            logger.info(f"开始填充景点坐标: {item.title}")

            # 1. 尝试从 AttractionDetail 表匹配
            detail = await self._find_attraction_detail(item.title, plan.destination)
            if detail and detail.latitude and detail.longitude:
                item.coordinates = {
                    'lat': detail.latitude,
                    'lng': detail.longitude
                }
                if not item.address and detail.address:
                    item.address = detail.address
                filled_count += 1
                logger.info(f"从数据库填充坐标: {item.title} -> ({detail.latitude}, {detail.longitude})")
                continue

            # 2. 使用地图服务地理编码
            search_query = f"{plan.destination} {item.title}"
            try:
                geocode_result = await self.map_service.geocode(search_query, plan.destination)
                if geocode_result:
                    item.coordinates = {
                        'lat': geocode_result['latitude'],
                        'lng': geocode_result['longitude']
                    }
                    if not item.address:
                        item.address = geocode_result.get('formatted_address', '')
                    filled_count += 1
                    logger.info(f"从地图服务填充坐标: {item.title} -> ({geocode_result['latitude']}, {geocode_result['longitude']})")
                else:
                    logger.warning(f"无法找到景点坐标: {item.title}")
            except Exception as e:
                logger.error(f"地理编码失败: {item.title}, 错误: {e}")

        if filled_count > 0:
            await self.db.commit()
            logger.info(f"坐标填充完成，共填充 {filled_count} 个景点")

        return {"coordinates_filled": filled_count}

    async def balance_schedule(self, plan: TravelPlan) -> Dict[str, Any]:
        """
        均衡每日行程

        Args:
            plan: 旅行计划对象

        Returns:
            均衡统计
        """
        # 按日期分组景点
        items_by_date = await self._group_items_by_date(plan)

        if not items_by_date:
            return {"items_moved": 0, "days_balanced": False, "message": "无行程数据"}

        # 计算统计数据
        total_items = sum(len(items) for items in items_by_date.values())
        total_days = len(items_by_date)

        if total_days <= 1:
            return {"items_moved": 0, "days_balanced": False, "message": "只有一天行程，无需均衡"}

        # 计算理想每天景点数
        ideal_per_day = total_items / total_days
        threshold_high = math.ceil(ideal_per_day + 1)
        threshold_low = max(1, math.floor(ideal_per_day - 1))

        logger.info(f"行程均衡: 总景点={total_items}, 总天数={total_days}, 理想每天={ideal_per_day:.1f}, 上限={threshold_high}, 下限={threshold_low}")

        moved_count = 0

        # 识别过载天和空闲天
        overloaded = []
        underloaded = []

        for date, items in sorted(items_by_date.items()):
            item_count = len(items)
            if item_count > threshold_high:
                overloaded.append((date, items))
                logger.info(f"过载天: {date}, 景点数={item_count}")
            elif item_count < threshold_low:
                underloaded.append((date, items))
                logger.info(f"空闲天: {date}, 景点数={item_count}")

        if not overloaded or not underloaded:
            logger.info("行程已均衡，无需调整")
            return {"items_moved": 0, "days_balanced": True, "message": "行程已均衡"}

        # 执行均衡操作
        for over_date, over_items in overloaded:
            # 按优先级排序，优先移动 optional 和 backup
            movable_items = sorted(over_items, key=lambda x: self._priority_score(x))

            while len(over_items) > threshold_high and underloaded:
                # 找到最合适的空闲天
                target_date, target_items = self._find_best_target_date(
                    over_date, underloaded, movable_items[0]
                )

                if target_date:
                    item_to_move = movable_items.pop(0)
                    over_items.remove(item_to_move)

                    # 更新项目的日期
                    await self._move_item_to_date(item_to_move, target_date)
                    moved_count += 1

                    logger.info(f"移动景点: {item_to_move.title} 从 {over_date} 到 {target_date}")

                    # 更新空闲天列表
                    target_items.append(item_to_move)
                    if len(target_items) >= threshold_low:
                        underloaded = [(d, items) for d, items in underloaded if d != target_date]

                    # 更新过载天列表
                    if len(over_items) <= threshold_high:
                        break

        if moved_count > 0:
            await self.db.commit()
            logger.info(f"行程均衡完成，共移动 {moved_count} 个景点")

        return {
            "items_moved": moved_count,
            "days_balanced": True,
            "message": f"已移动 {moved_count} 个景点"
        }

    async def _get_plan(self, plan_id: int) -> Optional[TravelPlan]:
        """获取旅行计划"""
        result = await self.db.execute(
            select(TravelPlan).where(TravelPlan.id == plan_id)
        )
        return result.scalar_one_or_none()

    async def _find_attraction_detail(self, name: str, destination: str) -> Optional[AttractionDetail]:
        """从数据库查找景点详情"""
        # 先精确匹配
        result = await self.db.execute(
            select(AttractionDetail)
            .where(AttractionDetail.name == name)
            .where(AttractionDetail.destination == destination)
        )
        detail = result.scalar_one_or_none()

        if detail:
            return detail

        # 模糊匹配（去除空格和大小写）
        result = await self.db.execute(
            select(AttractionDetail)
            .where(AttractionDetail.destination == destination)
        )
        all_details = result.scalars().all()

        for d in all_details:
            if d.name and name:
                if d.name.strip().lower() == name.strip().lower():
                    return d

        return None

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

        return items_by_date

    def _priority_score(self, item: TravelPlanItem) -> int:
        """
        计算景点优先级分数（分数越低越优先移动）

        Args:
            item: 行程项目

        Returns:
            优先级分数
        """
        priority = item.priority or 'optional'

        priority_map = {
            'backup': 1,    # 备选景点最优先移动
            'optional': 2,  # 可选景点次优先
            'must': 3       # 必去景点最后移动
        }

        return priority_map.get(priority, 2)

    def _find_best_target_date(
        self,
        source_date: str,
        underloaded: List[Tuple[str, List[TravelPlanItem]]],
        item_to_move: TravelPlanItem
    ) -> Tuple[Optional[str], Optional[List[TravelPlanItem]]]:
        """
        找到最合适的目标日期

        Args:
            source_date: 源日期
            underloaded: 空闲天列表
            item_to_move: 要移动的项目

        Returns:
            (目标日期, 目标日期的项目列表)
        """
        if not underloaded:
            return None, None

        # 如果项目有坐标，优先选择地理位置相近的日期
        if item_to_move.coordinates and item_to_move.coordinates.get('lat'):
            best_date = None
            best_items = None
            min_distance = float('inf')

            for date, items in underloaded:
                # 计算该天所有景点的中心点
                center_lat, center_lng = self._calculate_center(items)

                if center_lat and center_lng:
                    # 计算距离
                    distance = self._calculate_distance(
                        item_to_move.coordinates['lat'],
                        item_to_move.coordinates['lng'],
                        center_lat,
                        center_lng
                    )

                    if distance < min_distance:
                        min_distance = distance
                        best_date = date
                        best_items = items

            if best_date:
                return best_date, best_items

        # 如果没有坐标信息，选择日期最接近的空闲天
        source_dt = datetime.strptime(source_date, '%Y-%m-%d')

        best_date = None
        best_items = None
        min_diff = float('inf')

        for date, items in underloaded:
            target_dt = datetime.strptime(date, '%Y-%m-%d')
            diff = abs((target_dt - source_dt).days)

            if diff < min_diff:
                min_diff = diff
                best_date = date
                best_items = items

        return best_date, best_items

    def _calculate_center(self, items: List[TravelPlanItem]) -> Tuple[Optional[float], Optional[float]]:
        """计算景点组的地理中心"""
        lats = []
        lngs = []

        for item in items:
            if item.coordinates and item.coordinates.get('lat') and item.coordinates.get('lng'):
                lats.append(item.coordinates['lat'])
                lngs.append(item.coordinates['lng'])

        if lats and lngs:
            return sum(lats) / len(lats), sum(lngs) / len(lngs)

        return None, None

    def _calculate_distance(self, lat1: float, lng1: float, lat2: float, lng2: float) -> float:
        """
        计算两点之间的距离（km）
        使用 Haversine 公式
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

    async def _move_item_to_date(self, item: TravelPlanItem, target_date: str):
        """
        移动项目到指定日期

        Args:
            item: 行程项目
            target_date: 目标日期 (YYYY-MM-DD)
        """
        # 解析目标日期
        target_dt = datetime.strptime(target_date, '%Y-%m-%d')

        # 保持原有的时间部分（如果有）
        if item.start_time:
            new_start_time = target_dt.replace(
                hour=item.start_time.hour,
                minute=item.start_time.minute,
                second=item.start_time.second
            )
        else:
            new_start_time = target_dt

        # 更新数据库
        await self.db.execute(
            update(TravelPlanItem)
            .where(TravelPlanItem.id == item.id)
            .values(start_time=new_start_time)
        )

        # 更新对象属性
        item.start_time = new_start_time
