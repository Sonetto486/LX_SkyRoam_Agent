#!/usr/bin/env python3
"""
更新 users 表结构，添加缺失的字段
"""

import asyncio
import sys
import os

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.core.database import _get_async_engine_for_current_loop
from loguru import logger

async def update_users_table():
    """更新 users 表结构，添加缺失的字段"""
    try:
        engine = _get_async_engine_for_current_loop()
        
        async with engine.begin() as conn:
            from sqlalchemy import text
            
            # 检查并添加缺失的字段
            # 添加 role 字段
            logger.info("检查并添加 role 字段...")
            await conn.execute(text("""
                ALTER TABLE users 
                ADD COLUMN IF NOT EXISTS role VARCHAR(20) NOT NULL DEFAULT 'user'
            """))
            
            # 添加 preferences 字段
            logger.info("检查并添加 preferences 字段...")
            await conn.execute(text("""
                ALTER TABLE users 
                ADD COLUMN IF NOT EXISTS preferences TEXT
            """))
            
            # 添加 travel_history 字段
            logger.info("检查并添加 travel_history 字段...")
            await conn.execute(text("""
                ALTER TABLE users 
                ADD COLUMN IF NOT EXISTS travel_history TEXT
            """))
            
            # 添加 is_active 字段
            logger.info("检查并添加 is_active 字段...")
            await conn.execute(text("""
                ALTER TABLE users 
                ADD COLUMN IF NOT EXISTS is_active BOOLEAN NOT NULL DEFAULT TRUE
            """))
            
            # 添加 last_login 字段
            logger.info("检查并添加 last_login 字段...")
            await conn.execute(text("""
                ALTER TABLE users 
                ADD COLUMN IF NOT EXISTS last_login TIMESTAMP
            """))
            
            # 修改 email 字段长度
            logger.info("修改 email 字段长度...")
            await conn.execute(text("""
                ALTER TABLE users 
                ALTER COLUMN email TYPE VARCHAR(100)
            """))
            
            # 添加 username 唯一约束
            logger.info("添加 username 唯一约束...")
            try:
                await conn.execute(text("""
                    ALTER TABLE users 
                    ADD CONSTRAINT users_username_key UNIQUE (username)
                """))
            except Exception as e:
                logger.warning(f"添加 username 唯一约束失败（可能已存在）: {e}")
            
        logger.info("✅ users 表结构更新完成！")
        
    except Exception as e:
        logger.error(f"❌ 更新 users 表失败: {e}")
        import traceback
        logger.error(traceback.format_exc())
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(update_users_table())
