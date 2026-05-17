"""
API v1 路由汇总
"""

from fastapi import APIRouter
from app.api.v1.endpoints import (
    travel_plans,
    destinations,
    users,
    agents,
    openai,
    map,
    data_collection,
    auth,
    proxy,
    attraction_details,
    locations,
    smart_import,
    topics,
    notes,
    image_import,
    xiaohongshu,
    weather,
    pre_generation,
)


api_router = APIRouter()

# 注册各个端点路由
api_router.include_router(
    notes.router,
    prefix="/notes",
    tags=["notes"],
)

api_router.include_router(
    topics.router,
    prefix="/topics",
    tags=["topics"],
)

api_router.include_router(
    auth.router,
    prefix="/auth",
    tags=["auth"],
)

api_router.include_router(
    locations.router,
    prefix="/locations",
    tags=["locations"],
)

api_router.include_router(
    travel_plans.router,
    prefix="/travel-plans",
    tags=["travel-plans"],
)

api_router.include_router(
    destinations.router,
    prefix="/destinations",
    tags=["destinations"],
)

api_router.include_router(
    users.router,
    prefix="/users",
    tags=["users"],
)

api_router.include_router(
    agents.router,
    prefix="/agents",
    tags=["agents"],
)

api_router.include_router(
    openai.router,
    prefix="/openai",
    tags=["openai"],
)

from app.api.v1.endpoints import smart_chat as smart_chat_endpoint

api_router.include_router(
    smart_chat_endpoint.router,
    prefix="/smart-chat",
    tags=["smart-chat"],
)

api_router.include_router(
    map.router,
    prefix="/map",
    tags=["map"],
)

api_router.include_router(
    data_collection.router,
    prefix="/data-collection",
    tags=["data-collection"],
)

api_router.include_router(
    proxy.router,
    prefix="/proxy",
    tags=["proxy"],
)

api_router.include_router(
    attraction_details.router,
    prefix="/attraction-details",
    tags=["attraction-details"],
)

api_router.include_router(
    smart_import.router,
    prefix="/smart-import",
    tags=["smart-import"],
)

api_router.include_router(
    image_import.router,
    prefix="/image-import",
    tags=["image-import"],
)

api_router.include_router(
    xiaohongshu.router,
    prefix="/xiaohongshu",
    tags=["xiaohongshu"],
)

api_router.include_router(
    weather.router,
    prefix="/weather",
    tags=["weather"],
)

api_router.include_router(
    pre_generation.router,
    prefix="/pre-generation",
    tags=["pre-generation"],
)
