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
import ast

# 根据你的实际项目路径导入
from app.core.database import get_async_db
from app.core.security import get_current_user
from app.models.user import User
from app.services.travel_plan_service import TravelPlanService
from app.schemas.travel_plan import TravelPlanCreate, TravelPlanResponse
from app.core.config import settings
from app.tools.place_image_service import PlaceImageService
from app.tools.baidu_ocr_service import ocr_service

router = APIRouter()

# ==========================================
# 1. Pydantic Schema：UI 适配与极强容错的默认值设计
# ==========================================

class ParsedLocation(BaseModel):
    id: int = Field(default=1)
    name: str = Field(default="未知地点")
    type: str = Field(default="景点")
    address: str = Field(default="地址未知")
    day: str = Field(default="Day 1")
    excerpt: str = Field(default="无说明")
    selected: bool = Field(default=True)
    image_url: Optional[str] = Field(default=None)
    images: List[str] = Field(default_factory=list)
    # 新增字段
    highlight: str = Field(default="")
    lat: Optional[float] = Field(default=None)
    lng: Optional[float] = Field(default=None)
    cost: float = Field(default=0.0)
    # 地理编码详细信息
    formatted_address: str = Field(default="")
    province: str = Field(default="")
    city: str = Field(default="")
    district: str = Field(default="")
    adcode: str = Field(default="")
    level: str = Field(default="")
    
    @field_validator('cost', mode='before')
    @classmethod
    def parse_cost(cls, v):
        if isinstance(v, str):
            match = re.search(r'-?\d+\.?\d*', v)
            if match:
                try: return float(match.group())
                except: pass
            return 0.0
        return v if isinstance(v, (int, float)) else 0.0

    # 关键修复：强制将地理编码字段转换为字符串，防止接收到列表、None 等非法类型
    @field_validator('province', 'city', 'district', 'adcode', 'level', 'formatted_address', mode='before')
    @classmethod
    def coerce_to_string(cls, v):
        if isinstance(v, list):
            return v[0] if v else ""
        if v is None:
            return ""
        return str(v)

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
       
        temperature=0.1
    )

async def _extract_text_logic(text: str) -> ExtractedTravelData:
    """文本提取核心算法（增强容版，支持复杂攻略）"""
    try:
        today = datetime.now().strftime("%Y-%m-%d")
        prompt = f"""
        # 角色
        你是顶级的旅行信息提取与标准化工程师。

        # 任务
        从用户提供的旅行攻略文本中精准提取行程信息。文本可能包含多个独立行程、省钱技巧、混杂格式。
        只提取与**行程安排**直接相关的内容（目的地、每日地点、餐饮、住宿、交通、预算）。
        忽略所有“省钱技巧”、“购物建议”、“买票攻略”、“平台推荐”等非行程核心内容。

        # 核心铁律
        - 严格输出纯JSON，不要包含```json等markdown标签，不加任何解释。
        - 所有数字字段必须是纯数字，禁止带单位（km、元等）。
        - 无对应信息时，字符串填"未知"或"无"，数字填0。
        - 严禁输出 lat/lng 字段（坐标由后端自动获取）。
        - 如果文本包含多个独立行程，只提取**第一个或最详细**的行程；若明显是不同时间/地点的多个行程，则选择文本中篇幅最长、地点最多的那个。
        - 提取的 `destination` 为行程的主要城市或区域（如“河南洛阳开封”或“景德镇”）。
        - 提取的 `duration_days` 根据行程描述的天数计算，若无明确天数则根据具体地点分布估算（最多不超过10天）。

        # 输出JSON结构（必须包含所有字段）
        {{
            "destination": "核心目的地（城市或区域）",
            "transportation": "大交通方式（如高铁/飞机/自驾），无法判断则填"未知"",
            "duration_days": 3,
            "budget": 0,
            "start_date": "{today}",
            "end_date": "YYYY-MM-DD",
            "notes": ["注意事项1", "注意事项2"],
            "daily_schedule": [
                {{
                    "day_num": 1,
                    "schedule_items": [
                        {{
                            "time": "全天或具体时段，如'下午'",
                            "place": "地点或活动名称",
                            "transport": "交通方式（步行/打车/公交等）",
                            "distance": 0,
                            "duration": 1,
                            "ticket_cost": 0,
                            "food_cost": 0,
                            "desc": "简短描述，保留关键信息"
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
                    "name": "具体地点（景点/餐厅/酒店）",
                    "type": "景点/餐饮/酒店/交通 之一",
                    "address": "原文中的相对位置或区域描述，无则填城市名",
                    "day": "Day 1",
                    "excerpt": "原文对该地点的原话或感受（如'震撼力拉满'）",
                    "selected": true,
                    "highlight": "亮点或推荐理由",
                    "cost": 0
                }}
            ]
        }}

        # 详细提取规则
        1. **行程天数与每日安排 (daily_schedule)**
           - 识别明确的天数标记：DAY1、Day 1️⃣、第一天、DAY 1、📅行程：DAY1、day1: 等。
           - 每个有编号的天数独立成一个 `DailyScheduleItem`，其 `schedule_items` 包含该天内按顺序出现的所有地点/活动。
           - 若一天内有多个地点，按原文出现顺序列出。每个地点作为一个 `ScheduleItem`，`time` 字段可根据上下文填“上午/下午/全天/晚上”。
           - 如果原文没有明确分隔天数，则按地点自然分组（根据“- 龙门石窟”、“❶白马寺”等序号）尝试合并成1~3天。

        2. **独立地点列表 (parsed_locations)**
           - 每一个**景点、餐厅、酒店、交通站点（高铁站、机场）** 都必须单独提取为 `ParsedLocation`。
           - 即使地点名称在 `daily_schedule` 中出现过，也必须在 `parsed_locations` 中再出现一次。
           - `id` 从1开始递增。
           - `day` 必须与 `daily_schedule` 中的 `day_num` 对应，格式 `"Day 1"`。
           - `excerpt` 尽量引用原文的评价或描述（如“人少出片，原图直出”）。
           - `highlight` 提取正面评价或特色（如“夜晚亮灯震撼”、“特别出片”）。
           - `cost` 如果原文提到了该地点的花费（如门票、人均餐费），提取数字，否则填0。

        3. **费用提取 (budget / cost_breakdown)**
           - 寻找总花费关键词：“人均花费”、“合计”、“总预算”。提取 `budget` 字段。
           - 分项费用分类：
             - `flights`：机票、飞机票。
             - `hotels`：住宿、酒店、民宿。
             - `food`：吃饭、餐饮、美食。
             - `transport_tickets`：当地交通（打车、公交、租车）、火车票、景点内交通票。
             - `others`：门票（若未单独归类）、购物、文创。
           - 如果没有明确数字，全部填0。

        4. **交通方式 (transportation)**
           - 根据大交通信息判断：高铁/动车/火车 -> “高铁”；飞机 -> “飞机”；自驾 -> “自驾”；混合则填“高铁+当地打车”。

        5. **注意事项 (notes)**
           - 提取非地点类的重要提示：如“提前预约门票”、“带身份证”、“避开节假日”等。
           - 忽略“省钱技巧”、“买票平台比较”。

        6. **过滤规则**
           - 忽略“智行”、“飞飞乐”、“盲盒”、“支付宝出行”、“砍价”等营销或省钱方法。
           - 忽略“主包”、“博主”等自称。
           - 忽略“出发：G3054 6:27-11:42...”这种纯车次时间（除非是行程中的交通工具）。

        # 示例说明（仅理解用，不输出）
        输入文本片段：
        "DAY1 杭州-洛阳
        ❶白马寺-龙门石窟
        晚餐【吕记炒鸡】人均50"
        输出应包含：
        - destination: "洛阳"
        - duration_days: 至少3（从DAY1-DAY5看出）
        - daily_schedule: day_num=1 含两个地点(白马寺、龙门石窟)
        - parsed_locations: 白马寺(类型景点), 龙门石窟(景点), 吕记炒鸡(餐饮)
        - cost_breakdown.food: 50

        现在，请严格按上述规则处理以下文本：

        {text}
        """
        
        raw_content = await _call_llm_with_retry(prompt, "你是一个纯JSON输出机器，绝对不输出markdown代码块或废话。")

        # 记录原始 LLM 输出以便排查（如果输出很大，可根据配置降低日志级别）
        logger.debug(f"LLM 原始输出长度={len(raw_content) if raw_content else 0}")

        def _strip_code_fence(s: str) -> str:
            # 移除 ```、```json 等 code fence
            if not s: return s
            s = s.strip()
            fence_match = re.search(r"```(?:json)?\s*([\s\S]*?)```", s, re.IGNORECASE)
            if fence_match:
                return fence_match.group(1).strip()
            return s

        def _extract_json_by_brace_matching(s: str) -> str:
            # 找到第一个 '{' 并向后匹配到对应的 '}'（支持嵌套）
            if not s: return s
            start = s.find('{')
            if start == -1:
                return s
            depth = 0
            for i in range(start, len(s)):
                ch = s[i]
                if ch == '{':
                    depth += 1
                elif ch == '}':
                    depth -= 1
                    if depth == 0:
                        return s[start:i+1]
            # 回退：未能匹配到完整大括号，返回从第一个 '{' 到末尾的子串
            return s[start:]

        def _clean_json_like(s: str) -> str:
            # 常见修复：把单引号转成双引号，去除多余尾逗号，替换非标准 null/true/false
            if not s: return s
            s2 = s
            # 修复中文引号或智能引号
            s2 = s2.replace("“", '"').replace("”", '"').replace("‘", "'").replace("’", "'")
            # 把单引号包裹的键/值尽量替换为双引号（注意风险，仅作为回退）
            s2 = re.sub(r"(?P<pre>[:\[,\{\s])'(?P<inner>[^']*?)'(?P<post>[,\]\}\s])", lambda m: f"{m.group('pre')}\"{m.group('inner')}\"{m.group('post')}", s2)
            s2 = s2.replace("\',\n\}", '\",\n}')
            # 删除尾随逗号
            s2 = re.sub(r",\s*([}\]])", r"\1", s2)
            # 标准化布尔/空值
            s2 = re.sub(r"\bNone\b", "null", s2)
            s2 = re.sub(r"\bTrue\b", "true", s2)
            s2 = re.sub(r"\bFalse\b", "false", s2)
            return s2

        # 先去除 code fence，然后尝试用大括号匹配提取 JSON
        candidate = _strip_code_fence(raw_content)
        candidate = candidate.strip()
        candidate_json = _extract_json_by_brace_matching(candidate)

        # 最后兜底：如果找不到大括号，直接使用原始文本
        if not candidate_json:
            candidate_json = candidate

        try:
            json_data = json.loads(candidate_json)
            validated_data = ExtractedTravelData(**json_data)
            logger.info(f"✅ AI提取成功：找到了 {len(validated_data.parsed_locations)} 个地点。")
            return validated_data
        except ValidationError as ve:
            logger.error(f"❌ Pydantic数据结构验证失败: {ve}\n【AI原始输出】: {raw_content}")
            return ExtractedTravelData()
        except json.JSONDecodeError as je:
            # 回退措施：对 candidate_json 做常规清洗再试一次
            cleaned = _clean_json_like(candidate_json)
            try:
                json_data = json.loads(cleaned)
                validated_data = ExtractedTravelData(**json_data)
                logger.info(f"✅ AI提取成功（回退清洗后）：找到了 {len(validated_data.parsed_locations)} 个地点。")
                return validated_data
            except Exception:
                # 再尝试 ast.literal_eval（把可能的 Python 字面量解析为 dict）
                try:
                    py_like = cleaned
                    # ast.literal_eval 需要 True/False/None，而上面我们已替换为 json 的 true/false/null，恢复回 Python 格式
                    py_like = py_like.replace('null', 'None').replace('true', 'True').replace('false', 'False')
                    parsed = ast.literal_eval(py_like)
                    if isinstance(parsed, dict):
                        validated_data = ExtractedTravelData(**parsed)
                        logger.info(f"✅ AI提取成功（ast 回退）：找到了 {len(validated_data.parsed_locations)} 个地点。")
                        return validated_data
                except Exception as e2:
                    logger.debug(f"ast 回退解析失败: {e2}")

            # 最终失败：记录完整原始输出供人工排查
            logger.error(f"❌ JSON解析失败(AI输出格式有误): {je}\n【AI原始输出】: {raw_content}")
            return ExtractedTravelData()
        except Exception as e:
            logger.error(f"❌ 数据处理异常: {e}\n【AI原始输出】: {raw_content}")
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
                        await page.goto(real_url, timeout=30000)
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
                        
                        # ========== 新增：提取小红书帖子中的图片并进行OCR识别 ==========
                        image_ocr_text = ""
                        try:
                            if ocr_service.is_configured():
                                # 查找帖子中的所有图片元素
                                img_elements = await page.query_selector_all('img')
                                img_urls = []
                                for img in img_elements:
                                    src = await img.get_attribute('src')
                                    # 过滤掉头像和太小的图片
                                    if src and 'avatar' not in src and 'profile' not in src:
                                        # 获取图片的自然宽度和高度
                                        try:
                                            bounding_box = await img.bounding_box()
                                            if bounding_box and bounding_box.get('width', 0) > 100 and bounding_box.get('height', 0) > 100:
                                                img_urls.append(src)
                                        except:
                                            img_urls.append(src)
                                
                                if img_urls:
                                    logger.info(f"发现 {len(img_urls)} 张图片，开始OCR识别...")
                                    # 对前5张图片进行OCR识别
                                    for i, img_url in enumerate(img_urls[:5]):
                                        try:
                                            logger.info(f"正在识别第 {i+1}/{min(5, len(img_urls))} 张图片...")
                                            img_ocr_text = await ocr_service.recognize_from_url(img_url)
                                            if img_ocr_text and len(img_ocr_text.strip()) > 5:
                                                image_ocr_text += f"\n\n【图片{i+1}中的文字】\n{img_ocr_text}"
                                                logger.info(f"第 {i+1} 张图片识别到 {len(img_ocr_text)} 个字符")
                                        except Exception as ocr_err:
                                            logger.warning(f"第 {i+1} 张图片OCR识别失败: {ocr_err}")
                                            continue
                                    
                                    if image_ocr_text:
                                        logger.info(f"✅ 图片OCR识别完成，共获取 {len(image_ocr_text)} 个字符")
                                else:
                                    logger.info("未在页面中发现图片")
                            else:
                                logger.warning("百度OCR服务未配置，跳过图片识别")
                        except Exception as img_err:
                            logger.warning(f"提取或识别图片时出错: {img_err}")
                        # ========== 图片OCR识别功能结束 ==========

                        # 合并页面文字和图片OCR文字
                        combined_text = f"标题: {title_text}\n\n内容: {detailed_desc}"
                        if image_ocr_text:
                            combined_text += f"\n\n{image_ocr_text}"
                        
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
            
        # ==========================================
        # 4. 为地点添加图片与地理编码信息（修复版）
        # ==========================================
        image_service = PlaceImageService()
        enriched_locations = []

        # 【关键修复】从 AI 提取的核心目的地推断默认城市
        default_city = extracted_info.destination if extracted_info.destination != "未知" else ""
        # 去掉可能的"市"后缀，兼容高德API（上海 / 上海市 均可，但统一处理更稳）
        if default_city and default_city.endswith("市"):
            default_city = default_city[:-1]

        logger.info(f"🗺️ 行程核心目的地推断为: {default_city or '未识别'}, 将用于约束所有地点搜索")

        for location in extracted_info.parsed_locations:
            loc_dict = location.model_dump()
            
            # 别名替换：将口语化名称转换为标准POI名称
            original_name = loc_dict["name"]
            if original_name in PlaceImageService.ALIAS_MAP:
                loc_dict["name"] = PlaceImageService.ALIAS_MAP[original_name]
                loc_dict["original_name"] = original_name  # 保留原名用于展示
            
            # 【关键修复】传入 default_city，强制所有地点在该城市范围内搜索
            enriched_location = await image_service.enrich_location_with_image(
                loc_dict, 
                default_city=default_city
            )
            
            # 如果用了别名，把 name 改回原名，但保留修正的坐标和地址
            if "original_name" in enriched_location:
                enriched_location["name"] = enriched_location.pop("original_name")
            
            enriched_locations.append(ParsedLocation(**enriched_location))

        extracted_info.parsed_locations = enriched_locations
        
        start_date = _safe_parse_date(extracted_info.start_date, datetime.now())
        end_date = _safe_parse_date(extracted_info.end_date, start_date + timedelta(days=extracted_info.duration_days))

        # 5. 存入数据库 (状态设为 draft 草稿)
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