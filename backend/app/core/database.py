"""
数据库配置和连接管理
"""

from sqlalchemy import create_engine, MetaData
from sqlalchemy.orm import sessionmaker

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.dialects.postgresql import insert as pg_insert
import asyncio
from loguru import logger
from typing import Optional, Any  # 【修复】：引入大写的 Any

from app.core.config import settings

# 【修复】：将小写 any 替换为大写 Any
_engines_by_loop: dict[int, Any] = {}
_sessionmaker_by_loop: dict[int, Any] = {}
_sync_engine: Optional[Any] = None
_SessionLocal: Optional[Any] = None


def _current_loop_id():
    """获取当前事件循环的ID"""
    try:
        return id(asyncio.get_running_loop())
    except RuntimeError:
        # 如果没有运行中的事件循环，创建一个新的
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        return id(loop)


def _get_async_engine_for_current_loop():
    """获取当前事件循环对应的异步引擎"""
    loop_id = _current_loop_id()
    engine = _engines_by_loop.get(loop_id)
    if not engine:
        engine = create_async_engine(
            settings.DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://"),
            echo=settings.DATABASE_ECHO,
            pool_pre_ping=True,
            pool_recycle=300
        )
        _engines_by_loop[loop_id] = engine
    return engine


def _get_sync_engine():
    """获取同步数据库引擎（用于迁移等）"""
    global _sync_engine
    if _sync_engine is None:
        _sync_engine = create_engine(
            settings.DATABASE_URL,
            echo=settings.DATABASE_ECHO,
            pool_pre_ping=True,
            pool_recycle=300
        )
    return _sync_engine


def _get_sessionmaker_for_current_loop():
    """获取当前事件循环对应的异步会话工厂"""
    loop_id = _current_loop_id()
    sm = _sessionmaker_by_loop.get(loop_id)
    if not sm:
        engine = _get_async_engine_for_current_loop()
        # 使用 async_sessionmaker
        sm = async_sessionmaker(engine, expire_on_commit=False)
        _sessionmaker_by_loop[loop_id] = sm
    return sm

def get_async_engine():
    """获取当前事件循环对应的异步引擎"""
    return _get_async_engine_for_current_loop()


def get_sync_engine():
    """获取同步数据库引擎"""
    return _get_sync_engine()


# 延迟初始化的导出（避免在模块加载时创建引擎）
def get_async_session_local():
    """获取当前事件循环对应的异步会话工厂"""
    return _get_sessionmaker_for_current_loop()


def get_sync_session_local():
    """获取同步会话工厂"""
    global _SessionLocal
    if _SessionLocal is None:
        _SessionLocal = sessionmaker(
            autocommit=False, 
            autoflush=False, 
            bind=_get_sync_engine()
        )
    return _SessionLocal


# 导入基础模型类
from app.models.base import Base

# 元数据
metadata = MetaData()

# ==================== 兼容性导出 ====================
# 为了向后兼容，提供延迟初始化的导出
# 注意：这些变量在模块加载时不会立即初始化，而是在首次使用时初始化

def __getattr__(name):
    """动态属性访问，用于兼容性导出（延迟初始化）"""
    if name == "async_engine":
        return _get_async_engine_for_current_loop()
    elif name == "AsyncSessionLocal":
        return _get_sessionmaker_for_current_loop()
    elif name == "SessionLocal":
        return get_sync_session_local()
    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")


async def get_async_db():
    """获取异步数据库会话（用于FastAPI依赖注入）"""
    AsyncSessionFactory = _get_sessionmaker_for_current_loop()
    async with AsyncSessionFactory() as session:
        try:
            yield session
        except Exception as e:
            try:
                await session.rollback()
            except Exception:
                pass  # 忽略回滚错误
            import traceback
            logger.error(f"数据库会话错误: {e}\n{traceback.format_exc()}")
            raise
        finally:
            try:
                await session.close()
            except Exception:
                pass  # 忽略关闭错误


def get_sync_db():
    """获取同步数据库会话（用于同步代码）"""
    SessionFactory = get_sync_session_local()
    db = SessionFactory()
    try:
        yield db
    except Exception as e:
        db.rollback()
        logger.error(f"数据库会话错误: {e}")
        raise
    finally:
        db.close()


async def init_db(use_alembic: bool = False, create_tables_directly: bool = True):
    """
    初始化数据库
    
    Args:
        use_alembic: 是否使用 Alembic 进行迁移（默认 False，不推荐）
        create_tables_directly: 是否直接创建表（默认 True，推荐）
                              - True: 检查表是否存在，不存在则创建
                              - False: 跳过表创建
    """
    try:
        # 步骤1: 确保数据库存在
        await create_database_if_not_exists()
        
        # 步骤2: 运行数据库迁移或创建表
        if use_alembic:
            await run_alembic_upgrade()
        elif create_tables_directly:
            await create_tables_if_not_exists()
        else:
            logger.warning("⚠️ 未指定表创建方式，跳过表创建步骤")
        
        # 步骤3: 插入种子数据
        await seed_initial_data()
        
        logger.info("✅ 数据库初始化完成")
        
    except Exception as e:
        logger.error(f"❌ 数据库初始化失败: {e}")
        raise


async def create_database_if_not_exists():
    """如果数据库不存在则创建"""
    try:
        import asyncpg
        from urllib.parse import urlparse
        
        # 解析数据库URL
        parsed = urlparse(settings.DATABASE_URL)
        db_name = parsed.path[1:]  # 去掉开头的 '/'
        username = parsed.username
        password = parsed.password
        host = parsed.hostname
        port = parsed.port or 5432
        
        # 连接到默认的postgres数据库来创建目标数据库
        conn = await asyncpg.connect(
            host=host,
            port=port,
            user=username,
            password=password,
            database='postgres'
        )
        
        try:
            # 检查数据库是否存在
            result = await conn.fetchval(
                "SELECT 1 FROM pg_database WHERE datname = $1", db_name
            )
            
            if not result:
                # 数据库不存在，创建它
                await conn.execute(f'CREATE DATABASE "{db_name}"')
                logger.info(f"✅ 数据库 '{db_name}' 创建成功")
            else:
                logger.info(f"✅ 数据库 '{db_name}' 已存在")
                
        finally:
            await conn.close()
        
    except Exception as e:
        logger.warning(f"⚠️ 数据库创建检查失败: {e}（可能是权限问题或数据库已存在）")
        # 如果创建失败，可能是权限问题或数据库已存在，继续执行


async def run_alembic_upgrade():
    """
    运行 Alembic 迁移到最新版本（在线程池中执行同步操作）
    
    自动处理多个分支头（heads）的情况：
    - 先尝试使用 'head'（单个分支的情况）
    - 如果失败（多个heads），则使用 'heads' 升级所有分支
    """
    try:
        import subprocess
        import sys
        from pathlib import Path
        
        # 获取项目根目录（backend目录）
        backend_dir = Path(__file__).parent.parent.parent
        
        # 在后台线程中运行同步的 Alembic 命令
        loop = asyncio.get_event_loop()
        
        def run_migration(target="head"):
            """在后台线程中运行迁移"""
            result = subprocess.run(
                [sys.executable, "-m", "alembic", "upgrade", target],
                cwd=str(backend_dir),
                capture_output=True,
                text=True
            )
            return result
        
        # 先尝试使用 'head'
        result = await loop.run_in_executor(None, run_migration, "head")
        
        # 如果失败且错误信息包含 "Multiple head revisions"
        if result.returncode != 0:
            error_output = result.stderr or result.stdout or ""
            if "Multiple head revisions" in error_output or "Multiple heads" in error_output:
                logger.info("检测到多个迁移分支头，将升级所有分支...")
                # 使用 'heads' 升级所有分支
                result = await loop.run_in_executor(None, run_migration, "heads")
        
        # 检查最终结果
        if result.returncode != 0:
            error_msg = result.stderr or result.stdout or "未知错误"
            raise RuntimeError(f"Alembic 迁移失败: {error_msg}")
        
        if result.stdout:
            logger.debug(f"Alembic 输出: {result.stdout}")
        
        logger.info("✅ Alembic 迁移完成")
    except Exception as e:
        logger.error(f"❌ Alembic 迁移失败: {e}")
        logger.warning("💡 提示: 如果迁移失败，可以手动运行:")
        logger.warning("   - alembic heads  # 查看所有分支头")
        logger.warning("   - alembic upgrade heads  # 升级所有分支")
        raise


async def check_table_exists(table_name: str) -> bool:
    """检查表是否存在"""
    try:
        engine = _get_async_engine_for_current_loop()
        async with engine.begin() as conn:
            from sqlalchemy import text
            result = await conn.execute(
                text("""
                    SELECT EXISTS (
                        SELECT FROM information_schema.tables 
                        WHERE table_schema = 'public' 
                        AND table_name = :table_name
                    )
                """),
                {"table_name": table_name}
            )
            # 【修复】：强制转换为 bool，消除 Pyright 返回类型错误
            return bool(result.scalar())
    except Exception as e:
        logger.warning(f"检查表 {table_name} 是否存在时出错: {e}")
        return False


async def create_tables_if_not_exists():
    """
    智能创建表：检查表是否存在，不存在则创建
    同时检查并添加缺失的列（用于模型更新后的自动迁移）
    基于当前模型定义，不依赖 Alembic 迁移历史
    """
    try:
        # 导入所有模型以确保它们被注册到 Base.metadata
        from app.models import user, travel_plan, destination, attraction_detail, topic

        engine = _get_async_engine_for_current_loop()

        async with engine.begin() as conn:
            from sqlalchemy import text

            # 查询数据库中已存在的表
            result = await conn.execute(
                text("""
                    SELECT table_name
                    FROM information_schema.tables
                    WHERE table_schema = 'public'
                    AND table_type = 'BASE TABLE'
                """)
            )
            existing_tables = {row[0] for row in result.fetchall()}

            # 获取模型定义的所有表
            model_tables = set(Base.metadata.tables.keys())

            # 找出需要创建的表
            tables_to_create = model_tables - existing_tables
            tables_existing = model_tables & existing_tables

            if tables_to_create:
                logger.info(f"发现 {len(tables_to_create)} 个表需要创建: {', '.join(sorted(tables_to_create))}")
                # 使用 create_all 创建缺失的表（SQLAlchemy 会自动跳过已存在的表）
                await conn.run_sync(Base.metadata.create_all)
                logger.info(f"✅ 成功创建了 {len(tables_to_create)} 个表")

            # 检查并添加缺失的列
            columns_added = await check_and_add_missing_columns(conn, existing_tables)

            if not tables_to_create and not columns_added:
                logger.info(f"✅ 所有表和列已存在（共 {len(tables_existing)} 个表）")

    except Exception as e:
        logger.error(f"❌ 创建表失败: {e}")
        raise


async def check_and_add_missing_columns(conn, existing_tables: set) -> int:
    """
    检查并添加缺失的列

    Args:
        conn: 数据库连接
        existing_tables: 已存在的表名集合

    Returns:
        添加的列数量
    """
    from sqlalchemy import text
    from sqlalchemy.dialects.postgresql import JSONB

    columns_added = 0

    # 定义需要检查的新列（表名 -> [(列名, 列类型, 是否可空), ...])
    new_columns = {
        'travel_plans': [
            ('cities', 'JSONB', True),
            ('members', 'JSONB', True),
            ('packing_list', 'JSONB', True),
            ('travel_mode', 'VARCHAR(50)', True),
            ('tags', 'JSONB', True),
        ],
        'travel_plan_items': [
            ('opening_hours', 'JSONB', True),
            ('phone', 'VARCHAR(50)', True),
            ('website', 'VARCHAR(200)', True),
            ('facilities', 'JSONB', True),
            ('priority', 'VARCHAR(20)', True),
        ],
    }

    for table_name, columns in new_columns.items():
        if table_name not in existing_tables:
            continue

        # 获取该表已有的列
        result = await conn.execute(
            text("""
                SELECT column_name
                FROM information_schema.columns
                WHERE table_schema = 'public'
                AND table_name = :table_name
            """),
            {"table_name": table_name}
        )
        existing_columns = {row[0] for row in result.fetchall()}

        # 检查并添加缺失的列
        for col_name, col_type, nullable in columns:
            if col_name not in existing_columns:
                try:
                    null_str = "NULL" if nullable else "NOT NULL"
                    await conn.execute(
                        text(f"ALTER TABLE {table_name} ADD COLUMN {col_name} {col_type} {null_str}")
                    )
                    logger.info(f"✅ 表 {table_name} 添加列 {col_name}")
                    columns_added += 1
                except Exception as e:
                    logger.warning(f"⚠️ 添加列 {table_name}.{col_name} 失败: {e}")

    # 检查并创建 favorite_locations 表
    if 'favorite_locations' not in existing_tables:
        try:
            await conn.execute(
                text("""
                    CREATE TABLE favorite_locations (
                        id SERIAL PRIMARY KEY,
                        user_id INTEGER NOT NULL REFERENCES users(id),
                        name VARCHAR(200) NOT NULL,
                        address TEXT,
                        coordinates JSONB,
                        category VARCHAR(50),
                        phone VARCHAR(50),
                        poi_id VARCHAR(100),
                        source VARCHAR(20),
                        notes TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        is_active BOOLEAN DEFAULT TRUE
                    )
                """)
            )
            logger.info("✅ 创建表 favorite_locations")
            columns_added += 1
        except Exception as e:
            logger.warning(f"⚠️ 创建表 favorite_locations 失败: {e}")

    return columns_added


async def create_tables_directly():
    """
    直接创建所有表（强制创建，不检查是否存在）
    注意：如果表已存在，可能会报错
    """
    try:
        # 导入所有模型以确保它们被注册
        from app.models import user, travel_plan, destination, attraction_detail, topic

        # 创建所有表
        engine = _get_async_engine_for_current_loop()
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        
        logger.info("✅ 数据库表创建成功（直接创建模式）")
    except Exception as e:
        logger.error(f"❌ 直接创建表失败: {e}")
        raise


async def create_default_users():
    """
    创建默认用户数据并同步自增序列
    """
    try:
        from app.models.user import User
        from app.core.db_seed_data import DEFAULT_USERS
        from sqlalchemy import text  # 引入 text 用于执行原生 SQL

        engine = _get_async_engine_for_current_loop()
        async with engine.begin() as conn:
            user_table = User.__table__
            created_count = 0
            
            for user_data in DEFAULT_USERS:
                # 使用 PostgreSQL 的 ON CONFLICT DO NOTHING
                # 即使 ID 1 已经存在，也不会报错，而是直接跳过
                stmt = pg_insert(user_table).values(user_data).on_conflict_do_nothing(
                    index_elements=["id"]
                )
                result = await conn.execute(stmt)
                if result.rowcount > 0:
                    created_count += 1
            
            if created_count > 0:
                logger.info(f"✅ 成功插入 {created_count} 个默认用户")
                
                # 【关键修复】：手动同步 PostgreSQL 的 ID 序列
                # 否则下次正常注册用户时，数据库仍会尝试分配已存在的 ID (如 1, 2...)
                await conn.execute(text(
                    f"SELECT setval(pg_get_serial_sequence('{user_table.name}', 'id'), "
                    f"coalesce(max(id), 0) + 1, false) FROM {user_table.name};"
                ))
                logger.info("🔄 已同步 users 表自增序列")
            else:
                logger.info("ℹ️  所有默认用户已存在，无需重复插入")
                
    except Exception as e:
        logger.warning(f"⚠️ 默认用户创建或序列同步失败: {e}")
async def close_db():
    """关闭所有数据库连接"""
    # 关闭所有异步引擎
    for engine in _engines_by_loop.values():
        await engine.dispose()
    _engines_by_loop.clear()
    _sessionmaker_by_loop.clear()
    
    # 关闭同步引擎
    global _sync_engine, _SessionLocal
    if _sync_engine:
        _sync_engine.dispose()
        _sync_engine = None
    _SessionLocal = None
    
    logger.info("✅ 数据库连接已关闭")


# 便捷异步Session上下文管理器
# 便捷异步Session上下文管理器
class async_session:
    """异步数据库会话上下文管理器"""
    def __init__(self):
        self._session: Optional[AsyncSession] = None
        self._factory = None
    
    async def __aenter__(self) -> AsyncSession:
        self._factory = _get_sessionmaker_for_current_loop()
        self._session = self._factory()
        
        # 【核心修复】：帮助 Pyright 进行类型收窄，消除返回类型报警
        assert self._session is not None
        
        return self._session
    
    async def __aexit__(self, exc_type, exc, tb):
        if self._session is None:
            return
        
        try:
            if exc:
                await self._session.rollback()
            else:
                await self._session.commit()
        finally:
            await self._session.close()
async def seed_initial_data():
    """插入基础演示数据（种子数据）"""
    try:
        # 创建默认用户
        await create_default_users()
        
        logger.info("✅ 种子数据插入完成")
    except Exception as e:
        logger.warning(f"⚠️ 种子数据插入失败: {e}（可能数据已存在）")