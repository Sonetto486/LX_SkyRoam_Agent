#!/usr/bin/env python3
"""
更新 destinations 表结构，添加缺失的字段
"""

import asyncio
import sys
import os

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.core.database import _get_async_engine_for_current_loop
from loguru import logger

async def update_destinations_table():
    """更新 destinations 表结构，添加缺失的字段"""
    try:
        engine = _get_async_engine_for_current_loop()
        
        async with engine.begin() as conn:
            from sqlalchemy import text
            
            # 检查并添加缺失的字段
            # 添加 timezone 字段
            logger.info("检查并添加 timezone 字段...")
            await conn.execute(text("""
                ALTER TABLE destinations 
                ADD COLUMN IF NOT EXISTS timezone VARCHAR(50)
            """))
            
            # 添加 highlights 字段
            logger.info("检查并添加 highlights 字段...")
            await conn.execute(text("""
                ALTER TABLE destinations 
                ADD COLUMN IF NOT EXISTS highlights JSON
            """))
            
            # 添加 best_time_to_visit 字段
            logger.info("检查并添加 best_time_to_visit 字段...")
            await conn.execute(text("""
                ALTER TABLE destinations 
                ADD COLUMN IF NOT EXISTS best_time_to_visit VARCHAR(200)
            """))
            
            # 添加 safety_score 字段
            logger.info("检查并添加 safety_score 字段...")
            await conn.execute(text("""
                ALTER TABLE destinations 
                ADD COLUMN IF NOT EXISTS safety_score FLOAT
            """))
            
            # 添加 cost_level 字段
            logger.info("检查并添加 cost_level 字段...")
            await conn.execute(text("""
                ALTER TABLE destinations 
                ADD COLUMN IF NOT EXISTS cost_level VARCHAR(20)
            """))
            
            # 添加 images 字段
            logger.info("检查并添加 images 字段...")
            await conn.execute(text("""
                ALTER TABLE destinations 
                ADD COLUMN IF NOT EXISTS images JSON
            """))
            
            # 添加 videos 字段
            logger.info("检查并添加 videos 字段...")
            await conn.execute(text("""
                ALTER TABLE destinations 
                ADD COLUMN IF NOT EXISTS videos JSON
            """))
            
            # 添加 popularity_score 字段（带默认值）
            logger.info("检查并添加 popularity_score 字段...")
            try:
                await conn.execute(text("""
                    ALTER TABLE destinations 
                    ADD COLUMN IF NOT EXISTS popularity_score FLOAT NOT NULL DEFAULT 0.0
                """))
            except Exception as e:
                logger.warning(f"添加 popularity_score 字段失败（可能已存在）: {e}")
            
            # 添加 city 字段
            logger.info("检查并添加 city 字段...")
            await conn.execute(text("""
                ALTER TABLE destinations 
                ADD COLUMN IF NOT EXISTS city VARCHAR(100)
            """))
            
            # 添加 region 字段
            logger.info("检查并添加 region 字段...")
            await conn.execute(text("""
                ALTER TABLE destinations 
                ADD COLUMN IF NOT EXISTS region VARCHAR(100)
            """))
            
            # 添加 latitude 字段
            logger.info("检查并添加 latitude 字段...")
            await conn.execute(text("""
                ALTER TABLE destinations 
                ADD COLUMN IF NOT EXISTS latitude FLOAT
            """))
            
            # 添加 longitude 字段
            logger.info("检查并添加 longitude 字段...")
            await conn.execute(text("""
                ALTER TABLE destinations 
                ADD COLUMN IF NOT EXISTS longitude FLOAT
            """))
            
            # 添加 description 字段
            logger.info("检查并添加 description 字段...")
            await conn.execute(text("""
                ALTER TABLE destinations 
                ADD COLUMN IF NOT EXISTS description TEXT
            """))
            
            # 添加 is_active 字段
            logger.info("检查并添加 is_active 字段...")
            await conn.execute(text("""
                ALTER TABLE destinations 
                ADD COLUMN IF NOT EXISTS is_active BOOLEAN NOT NULL DEFAULT TRUE
            """))
            
        logger.info("✅ destinations 表结构更新完成！")
        
    except Exception as e:
        logger.error(f"❌ 更新 destinations 表失败: {e}")
        import traceback
        logger.error(traceback.format_exc())
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(update_destinations_table())
