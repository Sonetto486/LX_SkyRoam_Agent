"""API v1 包：汇总并注册 v1 路由"""
from fastapi import APIRouter

router = APIRouter()

# 内置的 openai endpoints（原有文件使用单独 include 的话请保持兼容）
try:
	from . import openai as openai_module  # type: ignore
	router.include_router(openai_module.router, prefix="/openai", tags=["openai"])  # type: ignore
except Exception:
	# 忽略导入错误，路由将在应用启动时由其他模块注册
	pass

# smart-chat 路由（无需认证的测试接口）
try:
	from . import smart_chat as smart_chat_module  # type: ignore
	# 在此处添加前缀 /smart-chat，smart_chat.py 内部路由使用空路径或 /stream
	router.include_router(smart_chat_module.router, prefix="/smart-chat", tags=["smart-chat"])  # type: ignore
except Exception:
	pass
