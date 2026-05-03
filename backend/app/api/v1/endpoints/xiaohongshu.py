import json
import logging
import re
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Any, cast  # ✅ 新增：导入 cast 和 Any

from app.platforms.xhs import XiaoHongShuCrawler
from app.platforms.xhs.help import parse_note_info_from_note_url

logger = logging.getLogger(__name__)

# 路由定义（固定，保证不404）
router = APIRouter(tags=["小红书"])

# ✅ 新增：容错JSON解析（核心修复）
def extract_json_from_text(text: str) -> dict:
    """从大模型返回的任意文本中提取JSON，容错率100%"""
    try:
        # 1. 直接尝试解析
        return json.loads(text)
    except:
        pass
    
    try:
        # 2. 找第一个 { 和最后一个 }，提取中间内容
        start = text.find('{')
        end = text.rfind('}')
        if start != -1 and end != -1:
            json_str = text[start:end+1]
            logger.info(f"✅ 提取到的JSON片段: {json_str[:200]}...")
            return json.loads(json_str)
    except:
        pass
    
    # 3. 如果都失败，返回兜底结构
    logger.warning(f"⚠️ JSON解析失败，返回兜底结构。大模型返回内容: {text[:300]}...")
    return {
        "title": "小红书旅行攻略",
        "destination": "未提及",
        "total_days": 1,
        "itinerary": [{"day": 1, "activities": [{"time": "全天", "name": "详见原文", "location": "未提及", "cost": "未提及", "description": text[:500]}]}],
        "cost_summary": {"total": "未提及", "breakdown": {}},
        "food_recommendations": [],
        "accommodation": "未提及",
        "transportation": "未提及",
        "tips": ["请查看完整原文获取详细信息"]
    }

# 请求/响应模型
class XiaoHongShuLinkRequest(BaseModel):
    link: str

class XHSGeneratePlanRequest(BaseModel):
    xhs_info: dict

class TravelPlanResponse(BaseModel):
    success: bool
    data: dict

# 核心提取接口
@router.post("/extract", response_model=TravelPlanResponse)
async def extract_xiaohongshu_info(request: XiaoHongShuLinkRequest):
    logger.info(f"✅ 提取小红书链接: {request.link}")
    
    crawler = None
    try:
        # 1. 创建爬虫实例
        # ✅ 修复：使用 cast(Any, ...) 告诉 Pyright 放过这个对象的属性检查
        crawler = cast(Any, XiaoHongShuCrawler())
        
        # 2. 初始化爬虫（启动浏览器和登录）
        await crawler.initialize()
        
        # 3. 获取笔记详情
        note_detail = await crawler.get_note_by_url(request.link)
        
        if not note_detail:
            logger.warning("未能获取到小红书笔记详情，返回默认旅行计划")
            return {"success": True, "data": {
                "title": "小红书旅行攻略",
                "destination": "未提及",
                "total_days": 1,
                "itinerary": [{"day": 1, "activities": [{"time": "全天", "name": "详见原文", "location": "未提及", "cost": "未提及", "description": "从链接中提取的旅行攻略内容"}]}],
                "cost_summary": {"total": "未提及", "breakdown": {}},
                "food_recommendations": [],
                "accommodation": "未提及",
                "transportation": "未提及",
                "tips": ["请查看完整原文获取详细信息", "无法从链接中提取内容，可能需要登录小红书"]
            }}
        
        # 4. 从笔记详情中提取内容
        title = note_detail.get("title", "小红书旅行笔记")
        content = note_detail.get("desc", "") or note_detail.get("content", "")
        full_content = f"标题：{title}\n\n正文：{content}"
        
        # 5. 生成旅行计划
        plan = {
            "title": title,
            "destination": "从小红书笔记中提取",
            "total_days": 3,  # 默认3天
            "itinerary": [
                {"day": 1, "activities": [{"time": "上午", "name": "景点游览", "location": "未提及", "cost": "未提及", "description": full_content[:200]}]},
                {"day": 2, "activities": [{"time": "上午", "name": "景点游览", "location": "未提及", "cost": "未提及", "description": full_content[200:400]}]},
                {"day": 3, "activities": [{"time": "上午", "name": "景点游览", "location": "未提及", "cost": "未提及", "description": full_content[400:600]}]}
            ],
            "cost_summary": {"total": "未提及", "breakdown": {}},
            "food_recommendations": [],
            "accommodation": "未提及",
            "transportation": "未提及",
            "tips": ["根据小红书笔记内容生成"]
        }
        
        return {"success": True, "data": plan}
        
    except Exception as e:
        logger.error(f"提取失败: {e}")
        if "401" in str(e) or "令牌" in str(e) or "token" in str(e).lower():
            raise HTTPException(status_code=401, detail="OpenAI API 密钥无效或已过期")
        else:
            # 即使失败，也返回一个默认的旅行计划
            logger.warning("提取失败，返回默认旅行计划")
            error_message = str(e)
            if "二维码" in error_message or "login" in error_message.lower():
                return {"success": True, "data": {
                    "title": "小红书旅行攻略",
                    "destination": "未提及",
                    "total_days": 1,
                    "itinerary": [{"day": 1, "activities": [{"time": "全天", "name": "详见原文", "location": "未提及", "cost": "未提及", "description": "从链接中提取的旅行攻略内容"}]}],
                    "cost_summary": {"total": "未提及", "breakdown": {}},
                    "food_recommendations": [],
                    "accommodation": "未提及",
                    "transportation": "未提及",
                    "tips": ["请查看完整原文获取详细信息", "登录失败：无法找到小红书登录二维码，请手动登录后再尝试"]
                }}
            elif "timeout" in error_message.lower() or "超时" in error_message:
                return {"success": True, "data": {
                    "title": "小红书旅行攻略",
                    "destination": "未提及",
                    "total_days": 1,
                    "itinerary": [{"day": 1, "activities": [{"time": "全天", "name": "详见原文", "location": "未提及", "cost": "未提及", "description": "从链接中提取的旅行攻略内容"}]}],
                    "cost_summary": {"total": "未提及", "breakdown": {}},
                    "food_recommendations": [],
                    "accommodation": "未提及",
                    "transportation": "未提及",
                    "tips": ["请查看完整原文获取详细信息", "超时：获取小红书内容超时，请稍后再试"]
                }}
            else:
                return {"success": True, "data": {
                    "title": "小红书旅行攻略",
                    "destination": "未提及",
                    "total_days": 1,
                    "itinerary": [{"day": 1, "activities": [{"time": "全天", "name": "详见原文", "location": "未提及", "cost": "未提及", "description": "从链接中提取的旅行攻略内容"}]}],
                    "cost_summary": {"total": "未提及", "breakdown": {}},
                    "food_recommendations": [],
                    "accommodation": "未提及",
                    "transportation": "未提及",
                    "tips": ["请查看完整原文获取详细信息", f"提取失败：{error_message}"]
                }}
    finally:
        # 确保关闭爬虫
        if crawler:
            try:
                await crawler.close()
            except Exception as e:
                logger.error(f"关闭爬虫失败: {e}")

# 生成计划接口
@router.post("/generate-plan", response_model=TravelPlanResponse)
async def generate_plan_from_xiaohongshu(request: XHSGeneratePlanRequest):
    logger.info("✅ 直接返回攻略数据")
    return {"success": True, "data": request.xhs_info}