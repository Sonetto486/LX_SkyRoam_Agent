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
    lat: Optional[float] = Field(default=None, description="纬度")
    lng: Optional[float] = Field(default=None, description="经度")

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
    """
    全球普适主线版：只保留主要游玩/消费点，将关联地标合并入描述。
    """
    try:
        today = datetime.now().strftime("%Y-%m-%d")
        prompt = f"""
        # 角色与任务
        你是一位极其严谨的全球旅行数据结构化专家。你的任务是从杂乱的游记、手帐或 OCR 文本中，精准提炼出【高价值主线行程】，并严格按 JSON 格式输出。

        # 核心指令：【绝对的 POI 层级控制】
        为了防止地图 API 搜索崩溃，你必须严格遵循以下“主次分类与降级合并”规则：

        1. 【甄别主线目的地 (Main POI)】：
           - 只有具有独立名称的明确景区、知名地标、大型商圈或明确作为主目的地的酒店/餐厅，才能被提取为独立的 `place`（如：红山森林动物园、故宫博物院、环球影城）。
           - 提取的名称必须是标准全称，方便地图 API 精准检索。

        2. 【强制降级与合并附属地点 (Sub-POI Merging) - 核心红线】：
           - **绝对禁止**将方位词（如：北门、南门、出口）、通用建筑设施（如：检票处、城墙、观景台、索道、某条路）或泛指地点作为独立景点提取！
           - **绝对禁止**将主线行程中的“顺路行为”（如：去景点的路上吃个小吃、在景区里买个文创、出景区后顺着城墙走走）拆分为独立目的地！
           - 所有被判定为“附属地点”或“顺路行为”的信息，必须作为游玩攻略、周边贴士，**全部合并写入与之最相关的主线目的地的 `desc` (描述) 字段中**。
           - 示例判断：原文“北门有很多鸭血粉丝店，吃完从北门进红山动物园”。主目的地是【南京红山森林动物园】，“北门吃鸭血粉丝”作为细节写入动物园的 desc。

        3. 【全球地理校准与纠错】：
           - 结合上下文自动推断准确的目的地城市（Destination）。
           - 自动修正由于用户口语化或 OCR 识别导致的错别字（如“鸡呜寺” -> “鸡鸣寺”）。

        # 输出格式要求 (Strict JSON)
        {{
            "_thinking": "简述思考过程：1. 识别出的主 POI 有哪些。2. 哪些泛地点或顺路地点被触发了降级合并机制。3. 修正了哪些地理名称错别字。",
            "destination": "标准化的目的地城市名称（如：南京、东京、巴黎）",
            "daily_schedule": [
                {{
                    "day_num": 1,
                    "schedule_items": [
                        {{
                            "place": "修正后的主目的地标准全称（必须能用于地图精准搜索）",
                            "desc": "包含怎么进、吃什么、游玩细节，以及所有被降级合并过来的周边地标/路线信息（越丰富、越具体越好）"
                        }}
                    ]
                }}
            ],
            "parsed_locations": [
                {{
                    "name": "主目的地名称（与 schedule_items 中的 place 保持一致）",
                    "type": "景点 / 餐饮 / 酒店 / 交通",
                    "excerpt": "从原文中提取一句最能代表该地点的原汁原味的评价（要求一字不改）",
                    "highlight": "基于原文为你总结的核心亮点（15字以内）"
                }}
            ]
        }}

        待处理文本：
        {text}
        """

     

        raw_content = await _call_llm_with_retry(prompt, "你是一个行程提炼专家，只保留核心主线，合并次要信息。")
        
     
        # 极其严格的 JSON 截取逻辑
        json_str = raw_content.strip()
        match = re.search(r'\{[\s\S]*\}', json_str)
        if match:
            json_str = match.group(0)

        try:
            json_data = json.loads(json_str)
            if "_thinking" in json_data:
                logger.info(f"🧠 AI 解析思维链: {json_data['_thinking']}")
                del json_data["_thinking"]
            
            return ExtractedTravelData(**json_data)
        except Exception as e:
            logger.error(f"❌ 普适性解析失败: {e}\n输出内容: {json_str}")
            return ExtractedTravelData()

    except Exception as e:
        logger.error(f"❌ AI 调用异常: {e}")
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
