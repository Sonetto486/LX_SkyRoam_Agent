"""
图片导入API端点 - 通过百度OCR识别图片中的旅游攻略文字
独立模块，不影响现有smart_import.py代码
"""
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
from loguru import logger
from fastapi import APIRouter, Depends, HTTPException, File, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, Field
import base64
import json
import re

# 根据项目路径导入
from app.core.database import get_async_db
from app.core.security import get_current_user
from app.models.user import User
from app.services.travel_plan_service import TravelPlanService
from app.schemas.travel_plan import TravelPlanCreate, TravelPlanResponse
from app.core.config import settings
from app.tools.place_image_service import PlaceImageService
from app.tools.baidu_ocr_service import ocr_service

router = APIRouter(tags=["图片导入"])

# ==========================================
# 数据模型（复用smart_import的结构）
# ==========================================
class ParsedLocation(BaseModel):
    id: int = Field(default=1, description="唯一标识ID，从1开始递增")
    name: str = Field(default="未知地点", description="地点/店铺/景点名称")
    type: str = Field(default="景点", description="类型标签")
    address: str = Field(default="地址未知", description="区域或详细地址")
    day: str = Field(default="Day 1", description="所属行程")
    excerpt: str = Field(default="无说明", description="原文引用")
    selected: bool = Field(default=True, description="默认勾选状态")
    image_url: Optional[str] = Field(default=None, description="地点图片URL")
    images: List[str] = Field(default_factory=list, description="地点图片URL列表")

class ScheduleItem(BaseModel):
    time: str = Field(default="全天")
    place: str = Field(default="未知")
    transport: str = Field(default="步行")
    distance: float = Field(default=0.0)
    duration: float = Field(default=1.0)
    ticket_cost: float = Field(default=0.0)
    food_cost: float = Field(default=0.0)
    desc: str = Field(default="")

class DailyScheduleItem(BaseModel):
    day_num: int = Field(default=1, ge=1)
    schedule_items: List[ScheduleItem] = Field(default_factory=list)

class CostBreakdown(BaseModel):
    flights: float = Field(default=0.0)
    hotels: float = Field(default=0.0)
    food: float = Field(default=0.0)
    transport_tickets: float = Field(default=0.0)
    others: float = Field(default=0.0)

class ExtractedTravelData(BaseModel):
    destination: str = Field(default="未知")
    transportation: str = Field(default="自驾")
    duration_days: int = Field(default=1)
    budget: float = Field(default=0.0)
    start_date: str = Field(default_factory=lambda: datetime.now().strftime("%Y-%m-%d"))
    end_date: str = Field(default_factory=lambda: (datetime.now() + timedelta(days=2)).strftime("%Y-%m-%d"))
    parsed_locations: List[ParsedLocation] = Field(default_factory=list)
    daily_schedule: List[DailyScheduleItem] = Field(default_factory=list)
    cost_breakdown: CostBreakdown = Field(default_factory=CostBreakdown)
    notes: List[str] = Field(default_factory=lambda: ["无"])

# ==========================================
# 核心逻辑：AI调用提取
# ==========================================
from tenacity import retry, stop_after_attempt, wait_exponential

@retry(stop=stop_after_attempt(2), wait=wait_exponential(multiplier=1, min=2, max=5), reraise=True)
async def _call_llm_with_retry(prompt: str, system_prompt: str) -> str:
    from app.tools.openai_client import openai_client
    return await openai_client.generate_text(
        prompt=prompt,
        system_prompt=system_prompt,
        response_format={"type": "json_object"},
        temperature=0.1
    )

async def _extract_travel_from_text(text: str) -> ExtractedTravelData:
    """从文本中提取旅游行程信息"""
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

        # 针对 parsed_locations 的特别提取说明
        - 原文中提到的每一个具体地点（如：屯溪、碧山村、某某餐厅等），都必须单独作为一个对象放入 parsed_locations 数组中！
        - id: 从1开始递增的整数
        - day: 格式必须严格为 "Day 1", "Day 2", "Day 3" 这种格式
        - excerpt: 必须填入原文原话
        - selected: 必须全部固定为 true

        待处理文本：
        {text}
        """

        raw_content = await _call_llm_with_retry(prompt, "你是一个纯JSON输出机器，绝对不输出markdown代码块或废话。")
        
        json_str = raw_content.strip()
        match = re.search(r'\{[\s\S]*\}', json_str)
        if match:
            json_str = match.group(0)

        try:
            json_data = json.loads(json_str)
            validated_data = ExtractedTravelData(**json_data)
            logger.info(f"✅ AI提取成功：找到了 {len(validated_data.parsed_locations)} 个地点。")
            return validated_data
        except Exception as e:
            logger.error(f"❌ 数据解析失败: {e}\n【AI原始输出】: {json_str}")
            return ExtractedTravelData()

    except Exception as e:
        logger.error(f"❌ AI调用异常: {e}")
        return ExtractedTravelData()

# ==========================================
# API端点
# ==========================================
@router.post("/upload")
async def upload_image_and_extract(
    file: UploadFile = File(..., description="上传旅游攻略图片"),
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user),
):
    """
    上传图片 → OCR识别 → AI提取旅游攻略
    独立接口，不影响现有smart_import功能
    """
    try:
        # 1. 检查OCR服务是否配置
        if not ocr_service.is_configured():
            raise HTTPException(status_code=400, detail="百度OCR服务未配置，请设置BAIDU_OCR_API_KEY和BAIDU_OCR_SECRET_KEY")

        # 2. 读取图片文件并转换为base64
        image_data = await file.read()
        image_base64 = base64.b64encode(image_data).decode("utf-8")
        logger.info(f"📤 收到图片文件: {file.filename}, 大小: {len(image_data)} bytes")

        # 3. 使用百度OCR识别图片中的文字
        ocr_result = await ocr_service.recognize_travel_itinerary(image_base64)
        extracted_text = ocr_result.get("text", "")
        
        if not extracted_text.strip():
            raise HTTPException(status_code=400, detail="图片中未识别到文字内容")
        
        logger.info(f"✅ OCR识别成功，识别到 {len(extracted_text)} 字符")

        # 4. 使用AI提取行程信息
        extracted_data = await _extract_travel_from_text(extracted_text)

        # 5. 为地点添加图片
        image_service = PlaceImageService()
        enriched_locations = []
        for location in extracted_data.parsed_locations:
            enriched_location = await image_service.enrich_location_with_image(location.model_dump())
            enriched_locations.append(ParsedLocation(**enriched_location))
        
        extracted_data.parsed_locations = enriched_locations

        # 6. 存入数据库（草稿状态）
        start_date = datetime.strptime(extracted_data.start_date, "%Y-%m-%d")
        end_date = datetime.strptime(extracted_data.end_date, "%Y-%m-%d")

        plan_data = {
            "title": f"{extracted_data.destination} 图片解析行程" if extracted_data.destination != "未知" else "图片解析行程草案",
            "destination": extracted_data.destination,
            "description": "通过图片OCR识别解析的行程",
            "user_id": current_user.id,
            "start_date": start_date,
            "end_date": end_date,
            "duration_days": extracted_data.duration_days,
            "budget": extracted_data.budget,
            "transportation": extracted_data.transportation,
            "status": "draft",
            "preferences": extracted_data.model_dump()
        }

        service = TravelPlanService(db)
        plan = await service.create_travel_plan(TravelPlanCreate(**plan_data))

        return {
            "success": True,
            "data": TravelPlanResponse.model_validate(plan).model_dump(),
            "message": "图片解析完成，已识别行程信息",
            "ocr_text": extracted_text  # 返回识别的原始文本供调试
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ 图片导入失败: {e}")
        raise HTTPException(status_code=500, detail=f"图片导入失败: {str(e)}")

@router.post("/recognize-only")
async def recognize_image_only(
    file: UploadFile = File(..., description="上传图片"),
    current_user: User = Depends(get_current_user),
):
    """
    仅识别图片文字（不提取行程）
    用于预览OCR识别结果
    """
    try:
        if not ocr_service.is_configured():
            raise HTTPException(status_code=400, detail="百度OCR服务未配置")

        image_data = await file.read()
        image_base64 = base64.b64encode(image_data).decode("utf-8")

        ocr_result = await ocr_service.recognize_travel_itinerary(image_base64)
        extracted_text = ocr_result.get("text", "")

        return {
            "success": True,
            "text": extracted_text,
            "length": len(extracted_text),
            "raw_results": ocr_result.get("raw_results", {})
        }

    except Exception as e:
        logger.error(f"❌ OCR识别失败: {e}")
        raise HTTPException(status_code=500, detail=f"OCR识别失败: {str(e)}")
