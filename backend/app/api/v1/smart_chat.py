"""DEPRECATED: smart_chat moved to `app.api.v1.endpoints.smart_chat`.

This file intentionally raises ImportError to avoid duplicate module imports.
Please import the endpoint from `app.api.v1.endpoints.smart_chat` instead.
"""
raise ImportError("smart_chat moved to app.api.v1.endpoints.smart_chat; please import from there")


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

    try:
        # 动态导入 scripts/rag_pipeline 中的 answer_question
        if RAG_PIPELINE_PATH.exists():
            spec = importlib.util.spec_from_file_location("rag_pipeline", str(RAG_PIPELINE_PATH))
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)  # type: ignore
            if hasattr(mod, "answer_question"):
                func = getattr(mod, "answer_question")
                if asyncio.iscoroutinefunction(func):
                    result = await func(request.message, use_backend_embedding=False)
                else:
                    loop = asyncio.get_running_loop()
                    result = await loop.run_in_executor(None, lambda: func(request.message, use_backend_embedding=False))

                answer = result.get("answer", "抱歉，无法获取回答")
                sources = result.get("sources", [])
                logger.info(f"✅ RAG回答生成成功，长度: {len(answer)} 字符，来源: {len(sources)} 个")
                return SmartChatResponse(answer=answer, sources=sources[:5], rag_used=True)

        # 若不存在或失败，返回错误提示
        return SmartChatResponse(answer="RAG服务暂时不可用，请检查后端配置。", rag_used=False, error="rag_not_available")

    except Exception as e:
        logger.error(f"❌ RAG处理失败: {e}", exc_info=True)
        return SmartChatResponse(answer=f"处理请求时出错: {str(e)}", rag_used=False, error=str(e))


@router.post("/stream")
async def smart_chat_stream(request: SmartChatRequest):
    """流式智能对话接口 - SSE格式（降级实现）"""

    async def event_generator() -> AsyncGenerator:
        try:
            # 尝试导入流式函数
            if RAG_PIPELINE_PATH.exists():
                spec = importlib.util.spec_from_file_location("rag_pipeline", str(RAG_PIPELINE_PATH))
                mod = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(mod)  # type: ignore

                if hasattr(mod, "answer_question_stream"):
                    async for chunk in getattr(mod, "answer_question_stream")(request.message, use_backend_embedding=False):
                        yield {"event": "message", "data": json.dumps({"type": "content", "content": chunk}, ensure_ascii=False)}
                    yield {"event": "done", "data": json.dumps({"type": "complete"})}
                    return

                # 降级：同步获取完整回答并一次性返回
                if hasattr(mod, "answer_question"):
                    func = getattr(mod, "answer_question")
                    if asyncio.iscoroutinefunction(func):
                        result = await func(request.message, use_backend_embedding=False)
                    else:
                        loop = asyncio.get_running_loop()
                        result = await loop.run_in_executor(None, lambda: func(request.message, use_backend_embedding=False))

                    yield {"event": "message", "data": json.dumps({"type": "content", "content": result.get("answer", "")}, ensure_ascii=False)}
                    yield {"event": "done", "data": json.dumps({"type": "complete"})}
                    return

            # 如果RAG不可用，返回错误事件
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
    """健康检查接口"""
    return {"status": "ok", "service": "smart-chat"}
