"""
数据库迁移脚本：为 topic 表添加 continent 字段
运行方式：cd backend && python scripts/add_topic_continent.py
"""
import asyncio
import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text


async def add_continent_column():
    """为 topic 表添加 continent 字段"""

    # 动态导入，避免循环依赖
    from app.core.config import settings
    from sqlalchemy.ext.asyncio import create_async_engine

    # 创建异步引擎
    engine = create_async_engine(
        settings.DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://"),
        echo=False,
        pool_pre_ping=True
    )

    print("开始执行数据库迁移...")
    print("=" * 50)

    async with engine.begin() as conn:
        # 检查 topic 表是否存在
        table_exists = await conn.execute(
            text("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables
                    WHERE table_schema = 'public'
                    AND table_name = 'topic'
                )
            """)
        )
        if not table_exists.scalar():
            print("⚠️ topic 表不存在，请先创建表")
            await engine.dispose()
            return

        # 检查字段是否已存在
        check_sql = """
        SELECT EXISTS (
            SELECT FROM information_schema.columns
            WHERE table_schema = 'public'
            AND table_name = 'topic'
            AND column_name = 'continent'
        )
        """
        result = await conn.execute(text(check_sql))
        exists = result.scalar()

        if exists:
            print("✓ continent 字段已存在，无需添加")
            await engine.dispose()
            return

        # 添加 continent 字段
        alter_sql = "ALTER TABLE topic ADD COLUMN continent VARCHAR(50)"
        await conn.execute(text(alter_sql))
        print("✓ 已添加 continent 字段")

        # 创建索引
        index_sql = "CREATE INDEX IF NOT EXISTS idx_topic_continent ON topic(continent)"
        await conn.execute(text(index_sql))
        print("✓ 已创建索引 idx_topic_continent")

        # 更新现有数据的 continent 值（根据 region 推断）
        update_sql = """
        UPDATE topic SET continent = CASE
            WHEN region IN ('华北', '华东', '华南', '华中', '西南', '西北', '东北') THEN 'asia'
            WHEN region ILIKE '%日本%' OR region ILIKE '%韩国%' THEN 'asia'
            WHEN region ILIKE '%欧洲%' OR region ILIKE '%法国%' OR region ILIKE '%意大利%' OR region ILIKE '%英国%' THEN 'europe'
            WHEN region ILIKE '%美国%' OR region ILIKE '%加拿大%' THEN 'north_america'
            WHEN region ILIKE '%澳大利亚%' OR region ILIKE '%新西兰%' THEN 'oceania'
            ELSE 'asia'
        END
        WHERE continent IS NULL
        """
        result = await conn.execute(text(update_sql))
        print(f"✓ 已更新 {result.rowcount} 条数据的 continent 值")

    await engine.dispose()
    print("=" * 50)
    print("迁移完成！")


async def main():
    try:
        await add_continent_column()
    except Exception as e:
        print(f"迁移失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())