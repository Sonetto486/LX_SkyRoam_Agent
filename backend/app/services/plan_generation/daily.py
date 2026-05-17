"""Shared helpers for modular travel plan generation."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any, Awaitable, Callable, Dict, List, Optional, Tuple
import copy
import math
import re

from loguru import logger

LLMRequester = Callable[..., Awaitable[Optional[Any]]]
PromptBuilder = Callable[[int, str, Optional[float]], Tuple[str, str, int, float]]
FallbackBuilder = Callable[[int, str], Dict[str, Any]]
DayEntryExtractor = Callable[[Any, int, str], Optional[Dict[str, Any]]]


def _ensure_attraction_description(attr: Dict[str, Any]) -> str:
    """确保景点有有效的简介，过滤经纬度等不必要信息

    POI 数据库没有 description 字段，chunk_text 可能是地址或其他文本。
    此函数检查描述是否有效，如果无效则生成一个简单的简介。
    """
    desc = attr.get("description", "")
    # 检查描述是否有效（长度>10且不是地址且不包含坐标）
    exclude_keywords = ["地址", "address", "纬度", "经度", "坐标", "location", "latitude", "longitude", "地理位置"]
    if desc and len(desc) > 10:
        # 过滤掉包含坐标等不必要信息的简介
        if not any(kw in desc.lower() for kw in exclude_keywords):
            return desc

    # 生成简洁简介
    name = attr.get("name", "景点")
    city = attr.get("city", "")
    labels = attr.get("labels", [])
    label_str = labels[0] if labels else "风景名胜"

    if city:
        return f"{name}是{city}著名的{label_str}，值得一游。"
    return f"{name}是热门的{label_str}景点，值得一游。"


def calculate_date(start_date: Optional[Any], days_offset: int) -> str:
    """Return YYYY-MM-DD string for ``start_date`` plus ``days_offset`` days."""
    if not start_date:
        return ""
    base: Optional[datetime] = None
    if isinstance(start_date, datetime):
        base = start_date
    else:
        value = str(start_date).strip()
        if not value:
            return ""
        try:
            base = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            try:
                base = datetime.strptime(value.split("T")[0], "%Y-%m-%d")
            except ValueError:
                return value
    target = base + timedelta(days=days_offset)
    return target.strftime("%Y-%m-%d")


def extract_day_entry(parsed: Any, day: int, date_str: str) -> Optional[Dict[str, Any]]:
    """Normalize the structure returned by the LLM into a per-day dictionary."""
    day_plan: Optional[Dict[str, Any]] = None
    if isinstance(parsed, dict):
        day_plan = parsed
    elif isinstance(parsed, list) and parsed:
        if isinstance(parsed[0], dict):
            day_plan = parsed[0]
    if not isinstance(day_plan, dict):
        return None
    day_plan.setdefault("day", day)
    if date_str:
        day_plan.setdefault("date", date_str)
    return day_plan


async def generate_daily_entries(
    *,
    module_name: str,
    total_days: int,
    start_date: Optional[Any],
    per_day_budget: Optional[float],
    build_prompts: PromptBuilder,
    llm_requester: LLMRequester,
    fallback_builder: FallbackBuilder,
    post_process: Optional[Callable[[Dict[str, Any], int, str], Dict[str, Any]]] = None,
    day_entry_extractor: Optional[DayEntryExtractor] = None,
) -> List[Dict[str, Any]]:
    """Generate structured daily entries with graceful fallback handling."""
    extractor = day_entry_extractor or extract_day_entry
    results: List[Dict[str, Any]] = []
    for day in range(1, max(total_days, 0) + 1):
        date_str = calculate_date(start_date, day - 1)
        try:
            system_prompt, user_prompt, max_tokens, temperature = build_prompts(
                day, date_str, per_day_budget
            )
            parsed = await llm_requester(
                system_prompt,
                user_prompt,
                max_tokens=max_tokens,
                temperature=temperature,
                log_context=f"{module_name} 第{day}天",
            )
            if parsed is not None:
                day_plan = extractor(parsed, day, date_str)
                if day_plan:
                    if post_process:
                        day_plan = post_process(day_plan, day, date_str)
                    results.append(day_plan)
                    continue
            logger.warning(f"{module_name} 第{day}天LLM返回无效，启用降级方案")
        except Exception as exc:  # pragma: no cover - defensive log only
            logger.error(f"{module_name} 第{day}天生成异常: {exc}")
        results.append(fallback_builder(day, date_str))
    logger.info(f"{module_name} 按天生成完成，共 {len(results)} 天")
    return results


def get_day_entry_from_list(entries: Optional[List[Dict[str, Any]]], day: int) -> Optional[Dict[str, Any]]:
    """Return the first entry whose ``day`` matches the provided value."""
    if not entries:
        return None
    for entry in entries:
        if entry.get("day") == day:
            return entry
    return None


def extract_price_value(entry: Dict[str, Any]) -> float:
    """Extract numeric price information from a loosely structured payload."""
    price_candidates = [entry.get("price"), entry.get("average_price"), entry.get("cost")]
    for candidate in price_candidates:
        if candidate is None:
            continue
        if isinstance(candidate, (int, float)):
            return float(candidate)
        try:
            match = re.search(r"(\d+(\.\d+)?)", str(candidate))
            if match:
                return float(match.group(1))
        except Exception:
            continue
    price_range = entry.get("price_range")
    if price_range:
        try:
            match = re.search(r"(\d+(\.\d+)?)", str(price_range))
            if match:
                return float(match.group(1))
        except Exception:
            pass
    return float("inf")


def _finite_price(value: float) -> float:
    return value if math.isfinite(value) else 0.0


def build_simple_attraction_plan(
    day: int,
    date_str: str,
    attractions_data: List[Dict[str, Any]],
    min_attractions: int = 3,
    max_attractions: int = 4,
    must_visit_attractions: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """Fallback attraction plan when the LLM response is unusable.

    Args:
        day: Day number
        date_str: Date string
        attractions_data: List of attraction data
        min_attractions: Minimum attractions per day (default 3)
        max_attractions: Maximum attractions per day (default 4)
        must_visit_attractions: List of must-visit attraction names
    """
    # 全天景点关键词
    full_day_keywords = ["迪士尼", "欢乐谷", "长隆", "主题乐园", "游乐园",
                         "野生动物园", "海洋公园", "环球影城", "方特"]

    # 排除关键词：这些不是全天景点
    exclude_keywords = ["豫园", "拙政园", "留园", "狮子林", "公园", "花园", "植物园", "盆景园"]

    # 识别全天景点
    full_day_attractions = []
    for attr in attractions_data:
        name = attr.get("name", "")
        # 排除普通园林
        if any(ex in name for ex in exclude_keywords):
            continue
        if any(kw in name for kw in full_day_keywords):
            full_day_attractions.append(attr)

    # 识别必去景点（非全天）
    must_visit_non_full_day = []
    for attr in attractions_data:
        name = attr.get("name", "")
        if attr.get("is_must_visit") or name in (must_visit_attractions or []):
            if attr not in full_day_attractions:
                must_visit_non_full_day.append(attr)

    # 计算必去景点应该安排在哪一天
    # 必去景点优先安排在第一个非全天景点日期
    must_visit_day = len(full_day_attractions) + 1 if full_day_attractions else 1

    # 如果当天是全天景点日期
    for i, attr in enumerate(full_day_attractions):
        assigned_day = i + 1
        if assigned_day == day:
            return _build_full_day_plan(day, date_str, attr)

    # 获取非全天景点列表
    non_full_day = [a for a in attractions_data if a not in full_day_attractions]

    # 按热度排序（popularity_rank 越小越热门）
    non_full_day_sorted = sorted(
        non_full_day,
        key=lambda x: x.get("popularity_rank", 9999)
    )

    selection: List[Dict[str, Any]] = []

    # 如果当天是必去景点日期，优先安排必去景点
    if day == must_visit_day and must_visit_non_full_day:
        selection.extend(must_visit_non_full_day)

    # 从非必去景点中选择，填充到 min_attractions
    added_names = {a.get("name") for a in selection}
    other_attractions = [a for a in non_full_day_sorted if a.get("name") not in added_names]

    # 计算还需要多少景点
    remaining_slots = max_attractions - len(selection)
    if remaining_slots > 0 and other_attractions:
        # 轮流分配：确保景点均匀分布到每一天
        # 计算非全天景物的天数
        non_full_day_count = max(1, 1)  # 至少1天

        for i, attr in enumerate(other_attractions):
            if len(selection) >= max_attractions:
                break
            # 计算这个景点应该分配到哪一天
            # 使用热度排序后的索引，确保热门景点优先分配
            assigned_day_for_attr = ((i + len(selection)) // min_attractions) + must_visit_day
            if assigned_day_for_attr > day and len(selection) >= min_attractions:
                # 已经有足够的景点，停止分配
                break
            if assigned_day_for_attr == day or len(selection) < min_attractions:
                selection.append(attr)

    # 如果景点数量不足 min_attractions，从所有非全天景点中补充
    if len(selection) < min_attractions:
        added_names = {a.get("name") for a in selection}
        for attr in non_full_day_sorted:
            if attr.get("name") not in added_names:
                selection.append(attr)
                added_names.add(attr.get("name"))
                if len(selection) >= min_attractions:
                    break

    selection = [copy.deepcopy(attr) for attr in selection]

    # 确保每个景点都有有效的简介
    for attr in selection:
        if not attr.get("description") or len(attr.get("description", "")) <= 10:
            attr["description"] = _ensure_attraction_description(attr)

    schedule: List[Dict[str, Any]] = []
    total_cost = 0.0
    for idx, attr in enumerate(selection):
        start_hour = 9 + idx * 3
        end_hour = start_hour + 3
        cost = attr.get("price") or 0
        try:
            total_cost += float(cost)
        except (TypeError, ValueError):
            pass
        # 确保景点有有效的简介
        description = _ensure_attraction_description(attr)
        schedule.append(
            {
                "time": f"{start_hour:02d}:00-{end_hour:02d}:00",
                "activity": "景点游览",
                "location": attr.get("name", "景点"),
                "description": description,
                "cost": cost or 0,
                "tips": "根据景点建议合理安排行程，提前预约可减少排队时间。",
            }
        )

    daily_tips = ["建议根据天气和人流灵活调整行程", "提前确认景点开放时间和购票方式"]
    return {
        "day": day,
        "date": date_str,
        "schedule": schedule,
        "attractions": selection,
        "estimated_cost": total_cost,
        "daily_tips": daily_tips,
    }


def _build_full_day_plan(day: int, date_str: str, attraction: Dict[str, Any]) -> Dict[str, Any]:
    """构建全天景点的单日方案"""
    attr = copy.deepcopy(attraction)
    # 确保景点有有效的简介
    description = _ensure_attraction_description(attr)
    attr["description"] = description
    return {
        "day": day,
        "date": date_str,
        "schedule": [{
            "time": "09:00-18:00",
            "activity": "全天游览",
            "location": attr.get("name", "景点"),
            "description": description,
            "cost": attr.get("price") or 0,
            "tips": "建议提前购票，合理安排游玩时间",
        }],
        "attractions": [attr],
        "estimated_cost": attr.get("price") or 0,
        "daily_tips": ["全天游览，建议早到晚归", "提前查看园区地图和演出时间"],
    }


def build_simple_dining_plan(
    day: int,
    date_str: str,
    restaurants_data: List[Dict[str, Any]],
) -> Dict[str, Any]:
    meal_types = [("早餐", 8), ("午餐", 12), ("晚餐", 18)]
    start = (day - 1) * len(meal_types)
    selection = restaurants_data[start : start + len(meal_types)]
    if len(selection) < len(meal_types):
        selection.extend(restaurants_data[: len(meal_types) - len(selection)])
    meals: List[Dict[str, Any]] = []
    total_cost = 0.0
    iterable = selection if selection else [{} for _ in meal_types]
    for (meal_type, base_hour), restaurant in zip(meal_types, iterable):
        rest = copy.deepcopy(restaurant) if isinstance(restaurant, dict) else {}
        price_value = _finite_price(extract_price_value(rest)) if rest else 0.0
        meals.append(
            {
                "type": meal_type,
                "time": f"{base_hour:02d}:00-{base_hour + 1:02d}:00",
                "restaurant_name": rest.get("name", "当地餐厅"),
                "cuisine": rest.get("cuisine", "当地特色"),
                "recommended_dishes": [
                    {
                        "name": dish,
                        "description": "当地特色菜品",
                        "price": price_value or "依据菜单",
                        "taste": "口味适中",
                    }
                    for dish in rest.get("specialties", [])[:2]
                ]
                or [
                    {
                        "name": "招牌菜",
                        "description": "当地招牌菜品",
                        "price": price_value or "依据菜单",
                        "taste": "风味独特",
                    }
                ],
                "atmosphere": rest.get("atmosphere", "环境舒适"),
                "estimated_cost": price_value,
                "booking_tips": "高峰时段建议提前到店",
                "address": rest.get("address", ""),
            }
        )
        total_cost += price_value

    return {
        "day": day,
        "date": date_str,
        "meals": meals,
        "daily_food_cost": total_cost,
        "food_highlights": [
            meal["restaurant_name"] for meal in meals if meal.get("restaurant_name")
        ],
    }


def build_simple_transportation_plan(
    day: int,
    date_str: str,
    transportation_data: List[Dict[str, Any]],
    *,
    stage: str = "local",
    origin: str = "出发地",
    destination: str = "目的地",
) -> Dict[str, Any]:
    """阶段化的交通fallback，避免每天重复跨城交通"""
    stage = stage or "local"
    origin = origin or "出发地"
    destination = destination or "目的地"

    primary_routes: List[Dict[str, Any]] = []
    template = transportation_data[0] if transportation_data else {}

    if stage == "departure":
        primary_routes.append(_build_intercity_route(origin, destination, template))
    elif stage == "return":
        primary_routes.append(_build_intercity_route(destination, origin, template))
    elif stage == "full_trip":
        primary_routes.append(_build_intercity_route(origin, destination, template))
        primary_routes.append(_build_intercity_route(destination, origin, template))
    else:
        primary_routes.append(_build_local_commute_route(destination, day))

    total_cost = 0.0
    aggregated_tips: List[str] = []
    for route in primary_routes:
        price = route.get("price") or route.get("cost") or 0
        try:
            total_cost += float(price)
        except (TypeError, ValueError):
            pass
        route_tips = route.get("usage_tips") or route.get("tips") or []
        if isinstance(route_tips, list):
            aggregated_tips.extend(route_tips)
        elif route_tips:
            aggregated_tips.append(str(route_tips))

    return {
        "day": day,
        "date": date_str,
        "primary_routes": primary_routes,
        "backup_routes": [],
        "daily_transport_cost": total_cost,
        "tips": aggregated_tips or ["使用默认交通建议"],
    }


def build_simple_accommodation_day(
    day: int,
    date_str: str,
    hotels_data: List[Dict[str, Any]],
) -> Dict[str, Any]:
    hotel: Dict[str, Any] = {}
    if hotels_data:
        index = (day - 1) % len(hotels_data)
        hotel = copy.deepcopy(hotels_data[index])
    price_value = _finite_price(extract_price_value(hotel)) if hotel else 0.0
    return {
        "day": day,
        "date": date_str,
        "flight": {},
        "hotel": hotel
        or {
            "name": "待定酒店",
            "address": "",
            "price_per_night": 0,
            "rating": 4.0,
            "amenities": [],
            "location_advantage": "待定",
        },
        "daily_cost": price_value,
        "accommodation_highlights": ["位置优越，交通便利"],
        "notes": ["使用默认住宿建议"],
    }


def _build_intercity_route(
    origin: str,
    destination: str,
    template: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """根据模板构建跨城交通"""
    template = template or {}
    transport_type = template.get("type") or "交通"
    template_price = template.get("price") or template.get("cost") or 0
    template_duration = template.get("duration") or template.get("time") or 0
    template_distance = template.get("distance") or 0
    usage_tips = template.get("usage_tips") or ["提前抵达车站/机场，预留检票与安检时间"]
    route_label = f"{origin}→{destination}"
    default_name = f"{route_label}{transport_type}"
    name = default_name
    template_name = template.get("name")
    if template_name:
        normalized = template_name
        if "→" in template_name:
            parts = template_name.split("→")
            if len(parts) >= 2:
                normalized = f"{origin}→{destination}{''.join(parts[2:])}" if len(parts) > 2 else f"{origin}→{destination}"
        if origin not in normalized or destination not in normalized:
            normalized = f"{route_label}-{template_name}"
        name = normalized
    route_info = {
        "type": transport_type,
        "name": name,
        "route": route_label,
        "duration": template_duration,
        "distance": template_distance,
        "price": template_price,
        "usage_tips": usage_tips,
    }
    return route_info


def _build_local_commute_route(destination: str, day: int) -> Dict[str, Any]:
    """构建目的地内的默认通勤路线"""
    base_distance = 8 + (day % 3) * 4
    base_duration = 25 + (day % 2) * 10
    price = 8 + (day % 3) * 2
    return {
        "type": "地铁/公交",
        "name": f"{destination}市区通勤",
        "route": f"{destination}市区 → 当日主要景点",
        "duration": base_duration,
        "distance": base_distance,
        "price": price,
        "usage_tips": ["根据实时路况适当提前出发", "可使用本地交通卡享受折扣"],
    }
