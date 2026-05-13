"""
天气API端点
"""

from fastapi import APIRouter, HTTPException, Query
from typing import Optional
from datetime import datetime, timedelta
from loguru import logger
from app.tools.amap_rest_client import amap_rest_client
from app.core.redis import get_cache, set_cache

router = APIRouter()

# 天气数据缓存TTL（1小时）
WEATHER_CACHE_TTL = 60 * 60


def should_use_travel_date(travel_date_str: str) -> tuple[bool, str]:
    """
    判断是否应该使用旅行日期的天气

    Args:
        travel_date_str: 旅行日期字符串 (YYYY-MM-DD 或 ISO格式)

    Returns:
        (should_use_travel_date, reason): 是否使用旅行日期，以及原因说明
    """
    try:
        # 解析旅行日期
        travel_date_str = travel_date_str.split('T')[0]  # 处理ISO格式
        travel_date = datetime.strptime(travel_date_str, '%Y-%m-%d').date()
        today = datetime.now().date()

        # 计算日期差
        days_diff = (travel_date - today).days

        # 过去的日期
        if days_diff < 0:
            return False, f"旅行日期已过去 {abs(days_diff)} 天"

        # 未来两周后（超过14天）
        if days_diff > 14:
            return False, f"旅行日期在 {days_diff} 天后（超过两周）"

        # 在附近（今天到未来两周内）
        return True, f"旅行日期在 {days_diff} 天后"

    except Exception as e:
        logger.warning(f"解析旅行日期失败: {e}")
        return False, "日期解析失败"


@router.get("")
async def get_weather(
    city: str = Query(..., description="城市名称或adcode"),
    days: int = Query(7, ge=1, le=15, description="预报天数，1-15天"),
    travel_date: Optional[str] = Query(None, description="旅行日期(YYYY-MM-DD)，用于智能判断显示哪天的天气")
):
    """
    获取城市天气预报

    - **city**: 城市名称（如"北京"）或行政区划代码
    - **days**: 预报天数，默认7天，最多15天
    - **travel_date**: 旅行日期，如果提供则智能判断：
        - 过去的日期或未来两周后：返回最近一周天气
        - 附近日期（今天到未来两周内）：返回从旅行日期开始的天气

    返回实时天气和未来天气预报
    """
    try:
        # 规范化城市名
        city_norm = city.strip()

        # 确保至少7天
        min_days = max(7, days)

        # 判断是否使用旅行日期
        use_travel_date = True
        reason = ""
        if travel_date:
            use_travel_date, reason = should_use_travel_date(travel_date)
            logger.info(f"旅行日期判断: {travel_date} -> {use_travel_date}, {reason}")

        # 构建缓存键
        cache_key = f"weather:{city_norm}:{min_days}:{travel_date or 'current'}"
        cached = await get_cache(cache_key)
        if cached:
            logger.debug(f"天气数据命中缓存: {city_norm}")
            return cached

        # 调用高德地图天气API
        # extensions=all 获取预报天气，extensions=base 获取实况天气
        weather_data = await amap_rest_client.get_weather(city_norm, extensions="all")

        if not weather_data:
            raise HTTPException(status_code=404, detail=f"未找到城市 {city_norm} 的天气数据")

        # 添加判断信息
        weather_data["date_mode"] = "travel_date" if use_travel_date else "current"
        weather_data["date_reason"] = reason
        weather_data["travel_date"] = travel_date

        # 处理预报数据
        if "forecast" in weather_data and weather_data["forecast"]:
            today_str = datetime.now().strftime('%Y-%m-%d')

            if use_travel_date and travel_date:
                # 从旅行日期开始筛选
                travel_date_clean = travel_date.split('T')[0]
                filtered = [f for f in weather_data["forecast"] if f.get("date", "") >= travel_date_clean]

                # 如果筛选后数据不足，补充从今天开始的数据
                if len(filtered) < min_days:
                    filtered = weather_data["forecast"][:min_days]
                else:
                    filtered = filtered[:min_days]

                weather_data["forecast"] = filtered
            else:
                # 使用最近一周（从今天开始）
                weather_data["forecast"] = weather_data["forecast"][:min_days]

        # 缓存结果
        await set_cache(cache_key, weather_data, ttl=WEATHER_CACHE_TTL)

        return weather_data

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取天气数据失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取天气数据失败: {str(e)}")


@router.get("/current")
async def get_current_weather(
    city: str = Query(..., description="城市名称或adcode")
):
    """
    获取城市实时天气（不含预报）

    - **city**: 城市名称（如"北京"）或行政区划代码
    """
    try:
        city_norm = city.strip()

        # 缓存实况天气（较短TTL，15分钟）
        cache_key = f"weather:current:{city_norm}"
        cached = await get_cache(cache_key)
        if cached:
            return cached

        # 调用高德地图天气API，只获取实况
        weather_data = await amap_rest_client.get_weather(city_norm, extensions="base")

        if not weather_data:
            raise HTTPException(status_code=404, detail=f"未找到城市 {city_norm} 的天气数据")

        # 只返回实况数据
        result = {
            "city": weather_data.get("city", city_norm),
            "current": weather_data.get("current", {})
        }

        # 缓存15分钟
        await set_cache(cache_key, result, ttl=15 * 60)

        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取实时天气失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取实时天气失败: {str(e)}")
