"""
OpenAI配置相关API端点
"""

from fastapi import APIRouter, Depends, HTTPException, Body
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from typing import Dict, Any, List, Optional, AsyncGenerator
from pydantic import BaseModel
import asyncio
import json

from app.models.user import User
from app.models.travel_plan import TravelPlan
from app.core.database import get_async_db
from app.tools.openai_client import openai_client
from app.core.config import settings
from app.core.security import get_current_user, is_admin
from loguru import logger


class ChatRequest(BaseModel):
    """聊天请求模型"""
    message: str
    conversation_history: Optional[List[Dict[str, str]]] = None
    system_prompt: Optional[str] = None

router = APIRouter()


DEFAULT_SYSTEM_PROMPT = """你是一个专业的AI助手，专门帮助用户解答关于旅行规划、目的地信息、旅行方案等相关问题。

请遵循以下原则：
1. 提供准确、有用的信息和建议
2. 遵守法律法规，不提供任何违法、违规内容
3. 不涉及政治敏感话题
4. 不传播虚假信息
5. 尊重用户隐私，不泄露用户信息
6. 对于不确定的信息，明确告知用户
7. 保持友好、专业的沟通态度
8. 优先直接回答用户当前问题，不要主动展开无关背景
9. 不要无关地提及用户历史行程、草案或足迹，除非用户明确在询问它们
10. 如果用户的问题很简短或很明确，请给出简洁、直达的答案

如果用户的问题超出你的能力范围或涉及不当内容，请礼貌地告知用户。"""

MAX_TRAVEL_CONTEXT_PLANS = 5
MAX_TRAVEL_CONTEXT_ITEMS_PER_PLAN = 8
MAX_TRAVEL_CONTEXT_CHAR_LIMIT = 4000
TRAVEL_CONTEXT_KEYWORDS = (
    "行程", "旅行", "路线", "规划", "优化", "足迹", "收藏", "我的行程", "我的旅行",
    "建议", "安排", "景点", "酒店", "交通", "吃什么", "美食", "餐厅", "攻略"
)


def _format_datetime(value: Any) -> str:
    if value is None:
        return ""
    if hasattr(value, "strftime"):
        try:
            return value.strftime("%Y-%m-%d %H:%M")
        except Exception:
            return str(value)
    return str(value)


def _normalize_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, (int, float, bool)):
        return str(value)
    if isinstance(value, list):
        items = [_normalize_text(item) for item in value]
        return "、".join(item for item in items if item)
    if isinstance(value, dict):
        parts = []
        for key, item in value.items():
            item_text = _normalize_text(item)
            if item_text:
                parts.append(f"{key}:{item_text}")
        return "；".join(parts)
    return str(value).strip()


def _dedupe_preserve_order(values: List[str]) -> List[str]:
    seen = set()
    deduped: List[str] = []
    for value in values:
        cleaned = value.strip()
        if not cleaned or cleaned in seen:
            continue
        seen.add(cleaned)
        deduped.append(cleaned)
    return deduped


def _build_plan_item_label(item: Any) -> str:
    title = _normalize_text(getattr(item, "title", None))
    location = _normalize_text(getattr(item, "location", None))
    address = _normalize_text(getattr(item, "address", None))
    item_type = _normalize_text(getattr(item, "item_type", None))
    priority = _normalize_text(getattr(item, "priority", None))
    start_time = _format_datetime(getattr(item, "start_time", None))

    label = location or title or address
    if not label:
        return ""

    details = []
    if item_type:
        details.append(f"类型:{item_type}")
    if priority:
        details.append(f"优先级:{priority}")
    if start_time:
        details.append(f"时间:{start_time}")

    if details:
        return f"{label}（{'，'.join(details)}）"
    return label


def _should_include_travel_context(message: str) -> bool:
    """判断当前问题是否值得注入用户行程上下文。"""
    normalized_message = _normalize_text(message)
    if not normalized_message:
        return False

    # 明确的个人行程/规划类问题才注入；普通问答直接回答。
    return any(keyword in normalized_message for keyword in TRAVEL_CONTEXT_KEYWORDS)


async def build_user_travel_context(db: AsyncSession, current_user: User) -> str:
    """自动提取当前用户的行程地点，作为大模型上下文。"""
    result = await db.execute(
        select(TravelPlan)
        .options(selectinload(TravelPlan.items))
        .where(TravelPlan.user_id == current_user.id)
        .order_by(TravelPlan.updated_at.desc())
        .limit(MAX_TRAVEL_CONTEXT_PLANS)
    )
    plans = result.scalars().unique().all()
    if not plans:
        return ""

    lines = [
        "【系统自动补充的用户行程上下文】",
        "仅用于辅助生成旅行相关回复，请优先结合以下地点、路线和时间信息回答。",
        f"用户：{_normalize_text(current_user.full_name) or _normalize_text(current_user.username) or current_user.id}",
    ]

    for index, plan in enumerate(plans, start=1):
        location_parts: List[str] = []

        for value in [plan.departure, plan.destination]:
            text = _normalize_text(value)
            if text:
                location_parts.append(text)

        cities = plan.cities if isinstance(plan.cities, list) else []
        for city in cities:
            text = _normalize_text(city)
            if text:
                location_parts.append(text)

        item_labels: List[str] = []
        for item in (plan.items or [])[:MAX_TRAVEL_CONTEXT_ITEMS_PER_PLAN]:
            item_label = _build_plan_item_label(item)
            if item_label:
                item_labels.append(item_label)
                location_parts.append(item_label.split("（", 1)[0])

        location_parts = _dedupe_preserve_order(location_parts)
        meta_parts: List[str] = []

        if plan.start_date and plan.end_date:
            meta_parts.append(
                f"时间:{_format_datetime(plan.start_date)} 至 {_format_datetime(plan.end_date)}"
            )
        if plan.duration_days:
            meta_parts.append(f"天数:{plan.duration_days}天")
        if plan.travel_mode:
            meta_parts.append(f"交通方式:{_normalize_text(plan.travel_mode)}")
        if plan.tags:
            meta_parts.append(f"标签:{_normalize_text(plan.tags)}")
        if plan.status:
            meta_parts.append(f"状态:{_normalize_text(plan.status)}")

        lines.append(f"{index}. 行程《{_normalize_text(plan.title) or '未命名行程'}》")
        if meta_parts:
            lines.append(f"   - { '；'.join(meta_parts) }")
        if location_parts:
            lines.append(f"   - 相关地点: { '、'.join(location_parts[:15]) }")
        if item_labels:
            lines.append(f"   - 行程点位: { '；'.join(item_labels) }")

    context = "\n".join(lines)
    if len(context) > MAX_TRAVEL_CONTEXT_CHAR_LIMIT:
        context = context[:MAX_TRAVEL_CONTEXT_CHAR_LIMIT - 60] + "\n[... 行程上下文已自动截断 ...]"
    return context


async def build_chat_messages(
    request: ChatRequest,
    current_user: User,
    db: AsyncSession,
) -> List[Dict[str, str]]:
    """构建大模型消息列表，并自动注入用户行程上下文。"""
    system_prompt = request.system_prompt or DEFAULT_SYSTEM_PROMPT
    travel_context = ""
    if _should_include_travel_context(request.message):
        travel_context = await build_user_travel_context(db, current_user)

    if travel_context:
        system_prompt = f"{system_prompt}\n\n{travel_context}"

    messages: List[Dict[str, str]] = [
        {
            "role": "system",
            "content": system_prompt,
        }
    ]

    if request.conversation_history:
        truncated_history = truncate_conversation_history(request.conversation_history)

        if len(truncated_history) < len(request.conversation_history):
            logger.info(
                f"对话历史已截断: {len(request.conversation_history)} -> {len(truncated_history)} 条消息"
            )

        for item in truncated_history:
            if isinstance(item, dict) and "role" in item and "content" in item:
                messages.append({
                    "role": item["role"],
                    "content": item["content"],
                })

    messages.append({
        "role": "user",
        "content": request.message,
    })

    total_chars = sum(len(msg.get("content", "")) for msg in messages)
    max_context_chars = get_max_context_chars()
    if total_chars > max_context_chars:
        logger.warning(f"消息总长度仍然过长 ({total_chars} 字符)，进行二次截断")
        system_msg = messages[0] if messages and messages[0].get("role") == "system" else None
        other_messages = messages[1:] if system_msg else messages

        kept_messages = []
        current_chars = len(system_msg.get("content", "")) if system_msg else 0

        for msg in reversed(other_messages):
            msg_chars = len(msg.get("content", ""))
            if current_chars + msg_chars <= max_context_chars:
                kept_messages.insert(0, msg)
                current_chars += msg_chars
            else:
                break

        messages = ([system_msg] if system_msg else []) + kept_messages
        logger.info(f"二次截断后保留 {len(messages)} 条消息")

    return messages


def get_max_input_tokens() -> int:
    """获取最大输入 token 数（从配置读取）"""
    return settings.OPENAI_MAX_INPUT_TOKENS or 12000


def get_estimated_chars_per_token() -> float:
    """获取 token 估算比例（从配置读取）"""
    return settings.OPENAI_ESTIMATED_CHARS_PER_TOKEN


def get_max_context_chars() -> int:
    """获取最大上下文字符数"""
    max_tokens = get_max_input_tokens()
    chars_per_token = get_estimated_chars_per_token()
    return int(max_tokens * chars_per_token)


def get_max_recent_messages() -> int:
    """获取最多保留的对话轮数（从配置读取）"""
    return settings.OPENAI_MAX_RECENT_MESSAGES


def estimate_tokens(text: str) -> int:
    """估算文本的 token 数量（粗略估算）"""
    chars_per_token = get_estimated_chars_per_token()
    return int((len(text) + chars_per_token - 1) / chars_per_token)


def truncate_conversation_history(
    conversation_history: Optional[List[Dict[str, str]]]
) -> List[Dict[str, str]]:
    """
    智能截断对话历史，确保不超过 token 限制
    
    策略：
    1. 优先保留最近的对话（最多 MAX_RECENT_MESSAGES 轮）
    2. 如果还有空间，保留初始上下文的核心部分
    3. 如果初始上下文太长，截断但保留开头和关键信息
    """
    if not conversation_history:
        return []
    
    if len(conversation_history) == 0:
        return []
    
    # 分离初始上下文（第一个 assistant 消息，通常是长文本）和后续对话
    initial_context = conversation_history[0] if (
        conversation_history[0].get("role") == "assistant"
    ) else None
    conversation_messages = conversation_history[1:] if initial_context else conversation_history
    
    # 保留最近的对话（最多 MAX_RECENT_MESSAGES 轮，即 MAX_RECENT_MESSAGES * 2 条消息）
    max_recent = get_max_recent_messages()
    recent_messages = conversation_messages[-max_recent * 2:] if len(conversation_messages) > max_recent * 2 else conversation_messages
    
    # 计算已使用的 token 数
    used_tokens = sum(estimate_tokens(msg.get("content", "")) for msg in recent_messages)
    
    # 如果有初始上下文，尝试添加它（可能需要截断）
    if initial_context:
        initial_content = initial_context.get("content", "")
        initial_tokens = estimate_tokens(initial_content)
        max_input_tokens = get_max_input_tokens()
        remaining_tokens = max_input_tokens - used_tokens - 1000  # 留出 1000 tokens 缓冲
        
        if initial_tokens <= remaining_tokens:
            # 初始上下文可以完整保留
            return [initial_context] + recent_messages
        elif remaining_tokens > 1000:
            # 初始上下文太长，需要截断
            # 保留开头部分（通常包含重要信息）和结尾部分
            chars_per_token = get_estimated_chars_per_token()
            max_initial_chars = int((remaining_tokens - 500) * chars_per_token)  # 留出 500 tokens
            keep_start_chars = int(max_initial_chars * 0.6)  # 保留 60% 的开头
            keep_end_chars = int(max_initial_chars * 0.4)  # 保留 40% 的结尾
            
            truncated_content = (
                initial_content[:keep_start_chars] +
                "\n\n[... 内容已截断以节省上下文空间 ...]\n\n" +
                initial_content[-keep_end_chars:]
            )
            
            truncated_context = {**initial_context, "content": truncated_content}
            return [truncated_context] + recent_messages
        else:
            # 剩余空间太小，不添加初始上下文，只保留最近对话
            logger.warning(f"初始上下文过长，已丢弃。剩余 tokens: {remaining_tokens}")
            return recent_messages
    
    return recent_messages


@router.get("/config")
async def get_openai_config():
    """获取OpenAI配置信息（包括 token 限制配置）"""
    try:
        config = openai_client.get_client_info()
        # 添加 token 限制配置信息
        config.update({
            "max_input_tokens": get_max_input_tokens(),
            "max_output_tokens": settings.OPENAI_MAX_TOKENS or 4000,
            "context_window": settings.OPENAI_CONTEXT_WINDOW or 16384,
            "estimated_chars_per_token": get_estimated_chars_per_token(),
            "max_recent_messages": get_max_recent_messages(),
        })
        return {
            "status": "success",
            "config": config
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取配置失败: {str(e)}")


@router.post("/test")
async def test_openai_connection():
    """测试OpenAI连接"""
    try:
        # 测试简单的文本生成
        response = await openai_client.generate_text(
            prompt="请简单介绍一下你自己",
            max_tokens=100
        )
        
        return {
            "status": "success",
            "message": "OpenAI连接测试成功",
            "response": response,
            "config": openai_client.get_client_info()
        }
        
    except Exception as e:
        return {
            "status": "error",
            "message": f"OpenAI连接测试失败: {str(e)}",
            "config": openai_client.get_client_info()
        }


@router.post("/generate-plan")
async def generate_ai_plan(
    destination: str,
    duration_days: int,
    budget: float,
    preferences: list,
    requirements: str = ""
):
    """使用AI生成旅行计划"""
    try:
        plan = await openai_client.generate_travel_plan(
            destination=destination,
            duration_days=duration_days,
            budget=budget,
            preferences=preferences,
            requirements=requirements
        )
        
        return {
            "status": "success",
            "plan": plan
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"生成计划失败: {str(e)}")


@router.post("/analyze-data")
async def analyze_travel_data(
    data: Dict[str, Any],
    analysis_type: str = "comprehensive"
):
    """分析旅行数据"""
    try:
        analysis = await openai_client.analyze_travel_data(
            data=data,
            analysis_type=analysis_type
        )
        
        return {
            "status": "success",
            "analysis": analysis
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"数据分析失败: {str(e)}")


@router.post("/optimize-plan")
async def optimize_travel_plan(
    current_plan: Dict[str, Any],
    optimization_goals: list
):
    """优化旅行计划"""
    try:
        optimized_plan = await openai_client.optimize_travel_plan(
            current_plan=current_plan,
            optimization_goals=optimization_goals
        )
        
        return {
            "status": "success",
            "optimized_plan": optimized_plan
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"计划优化失败: {str(e)}")


@router.post("/chat")
async def chat_with_ai(
    request: ChatRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db),
):
    """
    通用AI对话接口，支持上下文记忆
    
    Args:
        request: 聊天请求，包含message、conversation_history和system_prompt
    """
    try:
        messages = await build_chat_messages(request, current_user, db)
        
        # 调用OpenAI API
        max_output_tokens = settings.OPENAI_MAX_TOKENS or 4000
        response = await openai_client._call_api(
            messages=messages,
            max_tokens=max_output_tokens,
            temperature=settings.OPENAI_TEMPERATURE
        )
        
        assistant_message = response.choices[0].message.content
        
        return {
            "status": "success",
            "message": assistant_message,
            "usage": {
                "prompt_tokens": response.usage.prompt_tokens if hasattr(response.usage, 'prompt_tokens') else 0,
                "completion_tokens": response.usage.completion_tokens if hasattr(response.usage, 'completion_tokens') else 0,
                "total_tokens": response.usage.total_tokens if hasattr(response.usage, 'total_tokens') else 0
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"AI对话失败: {str(e)}")


@router.post("/chat/stream")
async def chat_with_ai_stream(
    request: ChatRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db),
):
    """
    流式AI对话接口，支持实时流式响应
    
    Args:
        request: 聊天请求，包含message、conversation_history和system_prompt
    """
    try:
        logger.info(
            f"[AI-Stream] 收到请求 user_id={getattr(current_user, 'id', None)} "
            f"message_len={len(request.message or '')} history_len={len(request.conversation_history or [])}"
        )
        logger.debug(f"[AI-Stream] message={request.message!r}")
        if request.conversation_history:
            logger.debug(f"[AI-Stream] conversation_history={request.conversation_history!r}")

        messages = await build_chat_messages(request, current_user, db)
        logger.info(f"[AI-Stream] 消息构建完成，共 {len(messages)} 条")
        logger.debug(f"[AI-Stream] messages={messages!r}")
        
        async def generate_stream() -> AsyncGenerator[str, None]:
            """生成流式响应"""
            try:
                # 调用OpenAI流式API
                max_output_tokens = settings.OPENAI_MAX_TOKENS or 4000
                logger.info(
                    f"[AI-Stream] 开始等待上游模型响应 model={settings.OPENAI_MODEL} "
                    f"max_tokens={max_output_tokens} temperature={settings.OPENAI_TEMPERATURE}"
                )
                async for chunk in openai_client._call_api_stream(
                    messages=messages,
                    max_tokens=max_output_tokens,
                    temperature=settings.OPENAI_TEMPERATURE
                ):
                    if chunk.choices and len(chunk.choices) > 0:
                        delta = chunk.choices[0].delta
                        if hasattr(delta, 'content') and delta.content:
                            logger.debug(f"[AI-Stream] 收到分块 content_len={len(delta.content)} content={delta.content!r}")
                            # 发送内容块
                            data = {
                                "type": "content",
                                "content": delta.content
                            }
                            yield f"data: {json.dumps(data, ensure_ascii=False)}\n\n"
                        
                        # 检查是否完成
                        if chunk.choices[0].finish_reason:
                            logger.info(f"[AI-Stream] 上游返回结束 finish_reason={chunk.choices[0].finish_reason}")
                            # 发送完成信号
                            usage_data = {}
                            if hasattr(chunk, 'usage') and chunk.usage:
                                usage_data = {
                                    "prompt_tokens": chunk.usage.prompt_tokens if hasattr(chunk.usage, 'prompt_tokens') else 0,
                                    "completion_tokens": chunk.usage.completion_tokens if hasattr(chunk.usage, 'completion_tokens') else 0,
                                    "total_tokens": chunk.usage.total_tokens if hasattr(chunk.usage, 'total_tokens') else 0
                                }
                            
                            data = {
                                "type": "done",
                                "usage": usage_data
                            }
                            logger.debug(f"[AI-Stream] usage={usage_data!r}")
                            yield f"data: {json.dumps(data, ensure_ascii=False)}\n\n"
                            break
            except Exception as e:
                logger.exception(f"[AI-Stream] 流式响应失败: {e}")
                # 发送错误信息
                error_data = {
                    "type": "error",
                    "message": str(e)
                }
                yield f"data: {json.dumps(error_data, ensure_ascii=False)}\n\n"
        
        return StreamingResponse(
            generate_stream(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no"
            }
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"AI流式对话失败: {str(e)}")