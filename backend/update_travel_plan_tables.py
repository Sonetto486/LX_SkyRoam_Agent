#!/usr/bin/env python3
"""
更新旅行计划相关表结构
"""

import asyncio
import sys
import os

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.core.database import _get_async_engine_for_current_loop
from loguru import logger

async def update_travel_plan_tables():
    """更新旅行计划相关表结构"""
    try:
        engine = _get_async_engine_for_current_loop()
        
        async with engine.begin() as conn:
            from sqlalchemy import text
            
            # 创建或更新 travel_plan_items 表
            logger.info("检查并创建 travel_plan_items 表...")
            await conn.execute(text("""
                CREATE TABLE IF NOT EXISTS travel_plan_items (
                    id BIGSERIAL PRIMARY KEY,
                    title VARCHAR(200) NOT NULL,
                    description TEXT,
                    item_type VARCHAR(50) NOT NULL,
                    start_time TIMESTAMP,
                    end_time TIMESTAMP,
                    duration_hours FLOAT,
                    location VARCHAR(200),
                    address TEXT,
                    coordinates JSON,
                    details JSON,
                    images JSON,
                    travel_plan_id INTEGER NOT NULL REFERENCES travel_plans(id) ON DELETE CASCADE,
                    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
                    updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
                    is_active BOOLEAN NOT NULL DEFAULT TRUE
                )
            """))
            
            # 创建或更新 travel_plan_ratings 表
            logger.info("检查并创建 travel_plan_ratings 表...")
            await conn.execute(text("""
                CREATE TABLE IF NOT EXISTS travel_plan_ratings (
                    id BIGSERIAL PRIMARY KEY,
                    travel_plan_id INTEGER NOT NULL REFERENCES travel_plans(id) ON DELETE CASCADE,
                    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                    score INTEGER NOT NULL,
                    comment TEXT,
                    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
                    updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
                    is_active BOOLEAN NOT NULL DEFAULT TRUE,
                    UNIQUE (travel_plan_id, user_id)
                )
            """))
            
            # 更新 travel_plans 表，添加缺失的字段
            logger.info("检查并更新 travel_plans 表...")
            
            # 添加 departure 字段
            await conn.execute(text("""
                ALTER TABLE travel_plans 
                ADD COLUMN IF NOT EXISTS departure VARCHAR(100)
            """))
            
            # 添加 transportation 字段
            await conn.execute(text("""
                ALTER TABLE travel_plans 
                ADD COLUMN IF NOT EXISTS transportation VARCHAR(50)
            """))
            
            # 添加 preferences 字段
            await conn.execute(text("""
                ALTER TABLE travel_plans 
                ADD COLUMN IF NOT EXISTS preferences JSON
            """))
            
            # 添加 requirements 字段
            await conn.execute(text("""
                ALTER TABLE travel_plans 
                ADD COLUMN IF NOT EXISTS requirements JSON
            """))
            
            # 添加 generated_plans 字段
            await conn.execute(text("""
                ALTER TABLE travel_plans 
                ADD COLUMN IF NOT EXISTS generated_plans JSON
            """))
            
            # 添加 selected_plan 字段
            await conn.execute(text("""
                ALTER TABLE travel_plans 
                ADD COLUMN IF NOT EXISTS selected_plan JSON
            """))
            
            # 添加 status 字段
            await conn.execute(text("""
                ALTER TABLE travel_plans 
                ADD COLUMN IF NOT EXISTS status VARCHAR(20) NOT NULL DEFAULT 'draft'
            """))
            
            # 添加 score 字段
            await conn.execute(text("""
                ALTER TABLE travel_plans 
                ADD COLUMN IF NOT EXISTS score FLOAT
            """))
            
            # 添加 is_public 字段
            await conn.execute(text("""
                ALTER TABLE travel_plans 
                ADD COLUMN IF NOT EXISTS is_public BOOLEAN NOT NULL DEFAULT FALSE
            """))
            
            # 添加 public_at 字段
            await conn.execute(text("""
                ALTER TABLE travel_plans 
                ADD COLUMN IF NOT EXISTS public_at TIMESTAMP
            """))
            
            # 添加 is_active 字段
            await conn.execute(text("""
                ALTER TABLE travel_plans 
                ADD COLUMN IF NOT EXISTS is_active BOOLEAN NOT NULL DEFAULT TRUE
            """))
            
        logger.info("✅ 旅行计划相关表结构更新完成！")
        
    except Exception as e:
        logger.error(f"❌ 更新旅行计划相关表失败: {e}")
        import traceback
        logger.error(traceback.format_exc())
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(update_travel_plan_tables())
