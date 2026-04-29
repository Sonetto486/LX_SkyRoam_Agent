"""
智能导入API端点（终极防弹版 - 解决非法URL、单位清洗、UI适配及JSON崩溃问题）
"""
from typing import Optional, List, Dict, Any, Union
from datetime import datetime, timedelta
from loguru import logger
from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, Field, ValidationError, field_validator
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
import json
import re

# 根据你的实际项目路径导入
from app.core.database import get_async_db
from app.core.security import get_current_user
from app.models.user import User
from app.services.travel_plan_service import TravelPlanService
from app.schemas.travel_plan import TravelPlanCreate, TravelPlanResponse
from app.core.config import settings
from app.tools.place_image_service import PlaceImageService

router = APIRouter()

# ==========================================
# 1. Pydantic Schema：UI 适配与极强容错的默认值设计
# ==========================================

class ParsedLocation(BaseModel):
    id: int = Field(default=1, description="唯一标识ID，从1开始递增")
    name: str = Field(default="未知地点", description="地点/店铺/景点名称")
    type: str = Field(default="景点", description="类型标签，如：景点 / 餐饮 / 酒店 / 交通")
    address: str = Field(default="地址未知", description="区域或详细地址")
    day: str = Field(default="Day 1", description="所属行程，格式必须为 'Day 1', 'Day 2'")
    excerpt: str = Field(default="无说明", description="原文引用：攻略中对该地点的原话描述")
    selected: bool = Field(default=True, description="前端复选框默认勾选状态")
    image_url: Optional[str] = Field(default=None, description="地点图片URL")
    images: List[str] = Field(default_factory=list, description="地点图片URL列表")

class ScheduleItem(BaseModel):
    time: str = Field(default="全天", description="时间段")
    place: str = Field(default="未知", description="地点名称")
    transport: str = Field(default="步行", description="交通方式")
    distance: float = Field(default=0.0, description="距离")
    duration: float = Field(default=1.0, description="时长")
    ticket_cost: float = Field(default=0.0, description="门票")
    food_cost: float = Field(default=0.0, description="餐饮")
    desc: str = Field(default="", description="描述")

    @field_validator('distance', 'duration', 'ticket_cost', 'food_cost', mode='before')
    @classmethod
    def parse_numeric_string(cls, v):
        """防御性清洗：去除单位字符串，保留纯数字"""
        if isinstance(v, str):
            match = re.search(r'-?\d+\.?\d*', v)
            if match:
                try: return float(match.group())
                except: pass
            return 0.0
        return v if isinstance(v, (int, float)) else 0.0

class DailyScheduleItem(BaseModel):
    day_num: int = Field(default=1, ge=1, description="第几天")
    schedule_items: List[ScheduleItem] = Field(default_factory=list)

class CostBreakdown(BaseModel):
    flights: float = Field(default=0.0)
    hotels: float = Field(default=0.0)
    food: float = Field(default=0.0)
    transport_tickets: float = Field(default=0.0)
    others: float = Field(default=0.0)
    
    @field_validator('*', mode='before')
    @classmethod
    def parse_cost_fields(cls, v):
        if isinstance(v, str):
            match = re.search(r'-?\d+\.?\d*', v)
            if match:
                try: return float(match.group())
                except: pass
            return 0.0
        return v if isinstance(v, (int, float)) else 0.0

class ExtractedTravelData(BaseModel):
    destination: str = Field(default="未知", description="核心目的地")
    transportation: str = Field(default="自驾", description="大交通方式")
    duration_days: int = Field(default=1, description="总天数")
    budget: float = Field(default=0.0, description="总预算")
    start_date: str = Field(default_factory=lambda: datetime.now().strftime("%Y-%m-%d"))
    end_date: str = Field(default_factory=lambda: (datetime.now() + timedelta(days=2)).strftime("%Y-%m-%d"))
    
    # 前端 UI 渲染专用的打平数据源
    parsed_locations: List[ParsedLocation] = Field(default_factory=list, description="用于前端卡片渲染的地点列表")
    
    daily_schedule: List[DailyScheduleItem] = Field(default_factory=list)
    cost_breakdown: CostBreakdown = Field(default_factory=CostBreakdown)
    notes: List[str] = Field(default_factory=lambda: ["无"])
    
    @field_validator('budget', 'duration_days', mode='before')
    @classmethod
    def parse_top_level_numerics(cls, v):
        if isinstance(v, str):
            match = re.search(r'-?\d+\.?\d*', v)
            if match:
                try: return float(match.group()) if '.' in match.group() else int(match.group())
                except: pass
        return v if isinstance(v, (int, float)) else 0

# ==========================================
# 2. 核心逻辑：AI 调用提取
# ==========================================
@retry(stop=stop_after_attempt(2), wait=wait_exponential(multiplier=1, min=2, max=5), reraise=True)
async def _call_llm_with_retry(prompt: str, system_prompt: str) -> str:
    from app.tools.openai_client import openai_client
    return await openai_client.generate_text(
        prompt=prompt,
        system_prompt=system_prompt,
        response_format={"type": "json_object"},
        temperature=0.1
    )

async def _extract_text_logic(text: str) -> ExtractedTravelData:
    """文本提取核心算法（增强容错版）"""
    try:
        today = datetime.now().strftime("%Y-%m-%d")
        prompt = f"""
        # 角色
        你是专业的旅行信息提取与标准化工程师。

        # 任务
        从用户提供的旅游文本中100%精准提取信息。
        如果原文很短（如只有简单的行程罗列），请直接提取其中的地点并合理拆分天数。

        # 核心铁律（违反直接失败）
        - 严格输出纯JSON，不要包含```json等markdown标签，不加任何解释。
        - 所有的数字字段必须是纯数字，绝对禁止带有单位（如km、元等）。
        - 无对应信息时，字符串填"未知"或"无"，数字填0。
        
        # 必须严格遵循以下JSON输出结构，必须包含所有字段：
        {{
            "destination": "核心目的地，如黄山",
            "transportation": "大交通方式",
            "duration_days": 4,
            "budget": 1000,
            "start_date": "{today}",
            "end_date": "YYYY-MM-DD",
            "notes": ["注意事项"],
            "daily_schedule": [
                {{
                    "day_num": 1,
                    "schedule_items": [
                        {{
                            "time": "全天",
                            "place": "地点名称",
                            "transport": "交通方式",
                            "distance": 0,
                            "duration": 1,
                            "ticket_cost": 0,
                            "food_cost": 0,
                            "desc": "行程描述"
                        }}
                    ]
                }}
            ],
            "cost_breakdown": {{
                "flights": 0, "hotels": 0, "food": 0, "transport_tickets": 0, "others": 0
            }},
            "parsed_locations": [
                {{
                    "id": 1,
                    "name": "提取出的具体地点",
                    "type": "必须是 景点/餐饮/酒店/交通 之一",
                    "address": "地址或未知",
                    "day": "Day 1",
                    "excerpt": "原文中对该地的描述或原话",
                    "selected": true
                }}
            ]
        }}

        # 针对 parsed_locations 的特别提取说明 (专供UI卡片渲染)
        - 原文中提到的每一个具体地点（如：屯溪、碧山村、某某餐厅等），都必须单独作为一个对象放入 parsed_locations 数组中！即使只有一句话带过也要提取。
        - id: 从1开始递增的整数
        - day: 格式必须严格为 "Day 1", "Day 2", "Day 3" 这种格式
        - excerpt: 必须填入原文原话（如："超级喜欢，文艺古村"）
        - selected: 必须全部固定为 true

        待处理文本：
        {text}
        """
        
        raw_content = await _call_llm_with_retry(prompt, "你是一个纯JSON输出机器，绝对不输出markdown代码块或废话。")
        
        # 🔥 强行截取第一对 {} 之间的内容，避免 LLM 废话导致 JSONDecodeError
        json_str = raw_content.strip()
        match = re.search(r'\{[\s\S]*\}', json_str)
        if match:
            json_str = match.group(0)

        # 增加更细致的错误捕捉，方便查看日志
        try:
            json_data = json.loads(json_str)
            validated_data = ExtractedTravelData(**json_data)
            logger.info(f"✅ AI提取成功：找到了 {len(validated_data.parsed_locations)} 个地点。")
            return validated_data
            
        except ValidationError as ve:
            logger.error(f"❌ Pydantic数据结构验证失败: {ve}\n【AI原始输出】: {json_str}")
            return ExtractedTravelData()
            
        except json.JSONDecodeError as je:
            logger.error(f"❌ JSON解析失败(AI输出格式有误): {je}\n【AI原始输出】: {json_str}")
            return ExtractedTravelData()

    except Exception as e:
        logger.error(f"❌ AI调用未知网络异常: {e}")
        return ExtractedTravelData()

# ==========================================
# 3. 辅助函数
# ==========================================
def _safe_parse_date(date_str: Optional[str], default_date: datetime) -> datetime:
    if not date_str: return default_date
    try: return datetime.strptime(date_str, "%Y-%m-%d")
    except: return default_date

# ==========================================
# 4. API 端点
# ==========================================
@router.post("/import")
async def import_travel_plan(
    textInput: str = Body(None),
    linkInput: str = Body(None),
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user),
):
    try:
        service = TravelPlanService(db)
        extracted_info: Optional[ExtractedTravelData] = None
        source_note = ""

        # 1. 优先处理小红书链接
        if linkInput and "xiaohongshu.com" in linkInput:
            # 🔥 提取纯净 URL，防干扰
            url_match = re.search(r'(https?://[^\s]+)', linkInput)
            if not url_match:
                logger.warning(f"未能从输入中提取有效链接: {linkInput}")
            else:
                real_url = url_match.group(1)
                try:
                    from app.platforms.xhs.real_crawler import get_crawler_instance
                    crawler = get_crawler_instance()
                    
                    if not crawler.is_started: 
                        await crawler.start()
                    await crawler.ensure_logged_in()

                    context = crawler.playwright_crawler._get_context()
                    page = await context.new_page()
                    
                    try:
                        logger.info(f"正在导航至: {real_url}")
                        await page.goto(real_url, timeout=15000)
                        await page.wait_for_timeout(2000)
                        
                        title_el = await page.query_selector('.title, #detail-title, [class*="title"]')
                        title_text = await title_el.inner_text() if title_el else ""

                        desc_selectors = ['#detail-desc', '.note-detail-desc', '.detail-desc', '[id*="detail"] span']
                        detailed_desc = ""
                        for s in desc_selectors:
                            el = await page.query_selector(s)
                            if el:
                                txt = await el.inner_text()
                                if len(txt.strip()) > 10:
                                    detailed_desc = txt.strip()
                                    break
                        
                        if not detailed_desc:
                            detailed_desc = await page.evaluate('document.body.innerText')

                        combined_text = f"标题: {title_text}\n\n内容: {detailed_desc}"
                        source_note = f"来源链接：{real_url}"
                        extracted_info = await _extract_text_logic(combined_text)
                        
                    finally:
                        await page.close()
                except Exception as e:
                    logger.error(f"小红书爬虫抓取异常: {e}")

        # 2. 兜底解析纯文本
        if not extracted_info and textInput:
            logger.info("使用纯文本模式解析")
            extracted_info = await _extract_text_logic(textInput)

        # 这里不抛出400异常，因为模型如果彻底崩了会返回全默认值的结构
        # 前端会渲染出 0个地点 0天行程 的空状态，方便用户感知并手动添加
        if not extracted_info:
            extracted_info = ExtractedTravelData()

        # 3. 补充备注与处理日期
        if source_note and source_note not in extracted_info.notes: 
            extracted_info.notes.append(source_note)
            
        # 4. 为地点添加图片信息
        image_service = PlaceImageService()
        enriched_locations = []
        for location in extracted_info.parsed_locations:
            # 为每个地点添加图片
            enriched_location = await image_service.enrich_location_with_image(location.model_dump())
            enriched_locations.append(ParsedLocation(**enriched_location))
        
        extracted_info.parsed_locations = enriched_locations
        
        start_date = _safe_parse_date(extracted_info.start_date, datetime.now())
        end_date = _safe_parse_date(extracted_info.end_date, start_date + timedelta(days=extracted_info.duration_days))

        # 4. 存入数据库 (状态设为 draft 草稿)
        plan_data = {
            "title": f"{extracted_info.destination} 行程草案" if extracted_info.destination != "未知" else "未命名行程草案",
            "destination": extracted_info.destination,
            "description": "通过智能导入解析的待确认行程",
            "user_id": current_user.id,
            "start_date": start_date,
            "end_date": end_date,
            "duration_days": extracted_info.duration_days,
            "budget": extracted_info.budget,
            "transportation": extracted_info.transportation,
            "status": "draft", 
            "preferences": extracted_info.model_dump()
        }
        
        plan = await service.create_travel_plan(TravelPlanCreate(**plan_data))
        
        return {
            "success": True,
            "data": TravelPlanResponse.model_validate(plan).model_dump(),
            "message": "解析完成，请确认提取的地点"
        }
        
    except HTTPException: 
        raise
    except Exception as e:
        logger.error(f"系统严重异常: {e}")
        raise HTTPException(status_code=500, detail="服务器内部错误")