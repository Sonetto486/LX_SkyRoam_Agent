"""
智能对话接口 - 无需认证，集成RAG检索（放置于 endpoints/ 目录）
注意：此文件用于本地开发和无认证测试。生产环境请谨慎开放。
"""
from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional, AsyncGenerator
import logging
import json
from sse_starlette.sse import EventSourceResponse
from pathlib import Path
import importlib.util
import asyncio

router = APIRouter()
logger = logging.getLogger(__name__)

# 修正 RAG 路径：从 endpoints/ 回到项目根，再到 backend/rag_pipeline.py
RAG_PIPELINE_PATH = Path(__file__).resolve().parents[5] / "backend" / "rag_pipeline.py"


class SmartChatRequest(BaseModel):
    """智能对话请求模型"""
    message: str
    user_id: Optional[str] = "test_user"
    use_rag: Optional[bool] = True


class SmartChatResponse(BaseModel):
    """智能对话响应模型"""
    answer: str
    sources: Optional[list] = []
    rag_used: bool = False
    error: Optional[str] = None


@router.post("")
async def smart_chat(request: SmartChatRequest):
    """智能对话接口 - 无需认证，集成RAG检索（同步返回）"""
    logger.info(f"📝 收到智能对话请求: {request.message[:50]}...")
    logger.debug(f"[smart-chat] request={request.model_dump()!r}")

    try:
        # 动态导入 rag_pipeline
        if RAG_PIPELINE_PATH.exists():
            logger.info(f"[smart-chat] 检测到 rag_pipeline: {RAG_PIPELINE_PATH}")
            spec = importlib.util.spec_from_file_location("rag_pipeline", str(RAG_PIPELINE_PATH))
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)  # type: ignore
            if hasattr(mod, "answer_question"):
                func = getattr(mod, "answer_question")
                logger.info("[smart-chat] 开始等待 rag_pipeline.answer_question 返回")
                if asyncio.iscoroutinefunction(func):
                    result = await func(request.message, use_backend_embedding=False)
                else:
                    loop = asyncio.get_running_loop()
                    result = await loop.run_in_executor(None, lambda: func(request.message, use_backend_embedding=False))

                logger.debug(f"[smart-chat] rag result={result!r}")
                answer = result.get("answer", "抱歉，无法获取回答")
                sources = result.get("sources", [])
                logger.info(f"✅ RAG回答生成成功，长度: {len(answer)} 字符，来源: {len(sources)} 个")
                return SmartChatResponse(answer=answer, sources=sources[:5], rag_used=True)

        return SmartChatResponse(answer="RAG服务暂时不可用，请检查后端配置。", rag_used=False, error="rag_not_available")

    except Exception as e:
        logger.error(f"❌ RAG处理失败: {e}", exc_info=True)
        return SmartChatResponse(answer=f"处理请求时出错: {str(e)}", rag_used=False, error=str(e))


@router.post("/stream")
async def smart_chat_stream(request: SmartChatRequest):
    """流式智能对话接口 - SSE格式（降级实现）"""
    logger.info(f"[smart-chat-stream] 收到请求 message_len={len(request.message or '')}")
    logger.debug(f"[smart-chat-stream] request={request.model_dump()!r}")

    async def event_generator() -> AsyncGenerator:
        try:
            if RAG_PIPELINE_PATH.exists():
                logger.info(f"[smart-chat-stream] 检测到 rag_pipeline: {RAG_PIPELINE_PATH}")
                spec = importlib.util.spec_from_file_location("rag_pipeline", str(RAG_PIPELINE_PATH))
                mod = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(mod)  # type: ignore

                if hasattr(mod, "answer_question_stream"):
                    logger.info("[smart-chat-stream] 开始等待 rag_pipeline.answer_question_stream 输出分块")
                    async for chunk in getattr(mod, "answer_question_stream")(request.message, use_backend_embedding=False):
                        logger.debug(f"[smart-chat-stream] chunk={chunk!r}")
                        yield {"event": "message", "data": json.dumps({"type": "content", "content": chunk}, ensure_ascii=False)}
                    logger.info("[smart-chat-stream] 分块输出完成")
                    yield {"event": "done", "data": json.dumps({"type": "complete"})}
                    return

                if hasattr(mod, "answer_question"):
                    func = getattr(mod, "answer_question")
                    logger.info("[smart-chat-stream] 没有流式接口，改为等待同步 answer_question 返回")
                    if asyncio.iscoroutinefunction(func):
                        result = await func(request.message, use_backend_embedding=False)
                    else:
                        loop = asyncio.get_running_loop()
                        result = await loop.run_in_executor(None, lambda: func(request.message, use_backend_embedding=False))

                    logger.debug(f"[smart-chat-stream] rag result={result!r}")
                    yield {"event": "message", "data": json.dumps({"type": "content", "content": result.get("answer", "")}, ensure_ascii=False)}
                    yield {"event": "done", "data": json.dumps({"type": "complete"})}
                    return

            yield {"event": "error", "data": json.dumps({"error": "rag_not_available"})}

        except Exception as e:
            logger.error(f"❌ 流式处理失败: {e}", exc_info=True)
            yield {"event": "error", "data": json.dumps({"error": str(e)})}

    async def sse_iter():
        async for ev in event_generator():
            yield f"data: {ev['data']}\n\n"

    return EventSourceResponse(sse_iter())


@router.get("/health")
async def health_check():
    return {"status": "ok", "service": "smart-chat"}
