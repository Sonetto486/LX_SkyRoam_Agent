"""
LX SkyRoam Agent - 主应用入口
智能旅游攻略生成系统
"""
import sys
import asyncio

# 必须放在 main.py 的最顶端！解决 Windows 下 Uvicorn + Playwright 的异步冲突
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
import os
import sys
import subprocess
import multiprocessing
import threading
from pathlib import Path
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from contextlib import asynccontextmanager
import uvicorn
from fastapi.staticfiles import StaticFiles
from loguru import logger

from app.core.config import settings
from app.core.logging_config import setup_logging
from app.core.database import init_db
from app.api.v1.api import api_router
from app.core.redis import init_redis
from app.services.background_tasks import start_background_tasks
from app.core.rate_limit import RateLimitMiddleware

# 全局变量存储 Celery Worker 进程
_celery_worker_process = None
_celery_log_file = None


def _stream_celery_logs(pipe, log_prefix):
    """将 Celery 进程的输出流转发到主日志"""
    try:
        for line in iter(pipe.readline, b''):
            if line:
                decoded = line.decode('utf-8', errors='replace').strip()
                if decoded:
                    logger.info(f"[Celery] {decoded}")
    except Exception:
        pass
    finally:
        try:
            pipe.close()
        except Exception:
            pass


def clean_celery_redis_data():
    """清理 Redis 中损坏的 Celery 任务数据"""
    import asyncio
    import redis
    try:
        from app.core.config import settings

        logger.info("🧹 开始清理 Redis 中的 Celery 数据...")

        # 连接到 Celery broker (db=1)
        broker_client = redis.Redis(
            host=settings.REDIS_HOST,
            port=settings.REDIS_PORT,
            password=settings.REDIS_PASSWORD,
            db=settings.CELERY_BROKER_DB,
            decode_responses=True,
            socket_timeout=5,
            socket_connect_timeout=5
        )

        # 测试连接
        broker_client.ping()
        logger.info("✅ Redis broker 连接成功")

        # 清理 celery 队列中可能残留的消息
        _queue_len = broker_client.llen("celery")
        # 处理可能的 Awaitable 返回值
        if asyncio.iscoroutine(_queue_len):
            _queue_len = asyncio.get_event_loop().run_until_complete(_queue_len)
        queue_len: int = _queue_len  # type: ignore
        if queue_len and queue_len > 0:
            logger.info(f"发现 celery 队列中有 {queue_len} 条消息，正在清理...")
            broker_client.delete("celery")
            logger.info("✅ 已清理 celery 队列")

        # 清理 unacked 队列
        _unacked_keys = broker_client.keys("unacked*")
        # 处理可能的 Awaitable 返回值
        if asyncio.iscoroutine(_unacked_keys):
            _unacked_keys = asyncio.get_event_loop().run_until_complete(_unacked_keys)
        unacked_keys: list = _unacked_keys  # type: ignore
        if unacked_keys:
            logger.info(f"发现 {len(unacked_keys)} 个 unacked 键，正在清理...")
            broker_client.delete(*unacked_keys)
            logger.info("✅ 已清理 unacked 队列")

        # 连接到 Celery result backend (db=2)
        result_client = redis.Redis(
            host=settings.REDIS_HOST,
            port=settings.REDIS_PORT,
            password=settings.REDIS_PASSWORD,
            db=settings.CELERY_BACKEND_DB,
            decode_responses=True,
            socket_timeout=5,
            socket_connect_timeout=5
        )

        # 查找所有 Celery 任务结果键
        _result_keys = result_client.keys("celery-task-meta-*")
        # 处理可能的 Awaitable 返回值
        if asyncio.iscoroutine(_result_keys):
            _result_keys = asyncio.get_event_loop().run_until_complete(_result_keys)
        result_keys: list = _result_keys  # type: ignore
        if result_keys:
            logger.info(f"发现 {len(result_keys)} 个 Celery 任务结果，正在清理...")
            result_client.delete(*result_keys)
            logger.info(f"✅ 已清理 {len(result_keys)} 个 Celery 任务结果")
        else:
            logger.info("✅ 没有需要清理的 Celery 任务结果")

        # 清理 _kombu.binding.* 键
        _binding_keys = broker_client.keys("_kombu.binding.*")
        # 处理可能的 Awaitable 返回值
        if asyncio.iscoroutine(_binding_keys):
            _binding_keys = asyncio.get_event_loop().run_until_complete(_binding_keys)
        binding_keys: list = _binding_keys  # type: ignore
        if binding_keys:
            logger.info(f"清理 {len(binding_keys)} 个 kombu binding 键...")
            broker_client.delete(*binding_keys)

        logger.info("✅ Redis Celery 数据清理完成")

    except redis.ConnectionError as e:
        logger.warning(f"⚠️ Redis 连接失败，跳过清理: {e}")
    except Exception as e:
        logger.warning(f"⚠️ 清理 Celery Redis 数据失败: {e}")


def wait_for_celery_worker(timeout: int = 15) -> bool:
    """等待 Celery Worker 就绪"""
    import time
    import asyncio
    from app.core.celery import celery_app

    start_time = time.time()
    last_error = None

    # 先等待 Worker 完全启动
    time.sleep(2)

    while time.time() - start_time < timeout:
        try:
            # 方法1：使用 control.ping() - 最直接的检测方式
            ping_result = celery_app.control.ping(timeout=5)
            # 处理可能的 Awaitable 返回值
            if asyncio.iscoroutine(ping_result):
                ping_result = asyncio.get_event_loop().run_until_complete(ping_result)
            if ping_result and len(ping_result) > 0:
                worker_names = []
                for result in ping_result:
                    worker_names.extend(result.keys())
                logger.info(f"✅ Celery Worker ping 成功: {worker_names}")
                return True

        except Exception as e:
            last_error = e
            logger.debug(f"ping 检测失败: {e}")

        try:
            # 方法2：使用 inspect.stats()
            inspect = celery_app.control.inspect(timeout=5)
            stats = inspect.stats()
            # 处理可能的 Awaitable 返回值
            if asyncio.iscoroutine(stats):
                stats = asyncio.get_event_loop().run_until_complete(stats)
            if stats:
                worker_names = list(stats.keys())
                logger.info(f"✅ 检测到 Celery Workers (stats): {worker_names}")
                return True

        except Exception as e:
            logger.debug(f"stats 检测失败: {e}")

        try:
            # 方法3：检查活跃任务
            inspect_obj = celery_app.control.inspect(timeout=5)
            active = inspect_obj.active()
            # 处理可能的 Awaitable 返回值
            if asyncio.iscoroutine(active):
                active = asyncio.get_event_loop().run_until_complete(active)
            if active is not None:
                logger.info(f"✅ 检测到 Celery Workers (active)")
                return True

        except Exception as e:
            logger.debug(f"active 检测失败: {e}")

        # 等待一段时间再重试
        time.sleep(1)

    # 超时后，尝试直接检查 Redis
    try:
        import redis
        from app.core.config import settings

        redis_client = redis.Redis(
            host=settings.REDIS_HOST,
            port=settings.REDIS_PORT,
            password=settings.REDIS_PASSWORD,
            db=settings.CELERY_BROKER_DB,
            decode_responses=True,
            socket_timeout=2
        )

        # 检查 celery 队列和相关键
        all_keys = redis_client.keys("*")
        # 处理可能的 Awaitable 返回值
        if asyncio.iscoroutine(all_keys):
            all_keys = asyncio.get_event_loop().run_until_complete(all_keys)
        celery_related = [k for k in all_keys if 'celery' in k.lower() or 'worker' in k.lower()]  # type: ignore
        if celery_related:
            logger.info(f"✅ 在 Redis 中检测到 Celery 相关键: {celery_related[:5]}...")
            return True

    except Exception as e:
        logger.debug(f"检查 Redis 失败: {e}")

    if last_error:
        logger.warning(f"等待 Celery Worker 时发生错误: {last_error}")

    return False


def start_celery_worker():
    """启动 Celery Worker 子进程"""
    global _celery_worker_process, _celery_log_file

    # 检查是否禁用自动启动 Celery Worker
    if os.environ.get("DISABLE_AUTO_CELERY", "").lower() in ("1", "true", "yes"):
        return None

    try:
        # 获取当前 Python 解释器路径
        python_exe = sys.executable

        # 获取项目根目录
        project_dir = Path(__file__).parent

        # 创建 Celery 日志文件
        logs_dir = project_dir / "logs"
        logs_dir.mkdir(parents=True, exist_ok=True)
        _celery_log_file = logs_dir / "celery_worker.log"

        # 启动 Celery Worker
        # Windows 使用 solo 池，其他系统使用默认池
        import platform
        if platform.system().lower().startswith("win"):
            pool_arg = "--pool=solo"
        else:
            pool_arg = ""

        cmd = [
            python_exe,
            "-m", "celery",
            "-A", "app.core.celery",
            "worker",
            "--loglevel=info",
            pool_arg
        ]

        # 过滤空参数
        cmd = [c for c in cmd if c]

        # 创建新进程启动 Celery Worker
        # 不使用 CREATE_NEW_CONSOLE，而是捕获输出并转发到主日志
        _celery_worker_process = subprocess.Popen(
            cmd,
            cwd=str(project_dir),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            bufsize=1,  # 行缓冲
            # 在 Windows 上不创建新控制台窗口，日志会转发到主进程
            creationflags=subprocess.CREATE_NO_WINDOW if platform.system().lower().startswith("win") else 0
        )

        # 启动线程转发 Celery 日志到主日志
        stdout_thread = threading.Thread(
            target=_stream_celery_logs,
            args=(_celery_worker_process.stdout, "STDOUT"),
            daemon=True
        )
        stderr_thread = threading.Thread(
            target=_stream_celery_logs,
            args=(_celery_worker_process.stderr, "STDERR"),
            daemon=True
        )
        stdout_thread.start()
        stderr_thread.start()

        return _celery_worker_process
    except Exception as e:
        logger.error(f"启动 Celery Worker 失败: {e}")
        return None


def stop_celery_worker():
    """停止 Celery Worker 子进程"""
    global _celery_worker_process
    if _celery_worker_process:
        try:
            _celery_worker_process.terminate()
            _celery_worker_process.wait(timeout=5)
            logger.info("Celery Worker 已停止")
        except Exception:
            try:
                _celery_worker_process.kill()
                logger.warning("Celery Worker 强制终止")
            except Exception:
                pass
        _celery_worker_process = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动时初始化
    logger = setup_logging()
    logger.info("🚀 启动 LX SkyRoam Agent...")

    # 初始化数据库（智能检查表和列是否存在，不存在则创建/添加）
    await init_db(use_alembic=False, create_tables_directly=True)
    logger.info("✅ 数据库初始化完成")

    # 初始化Redis（非必需，失败时不会阻止应用启动）
    try:
        await init_redis()
        logger.info("✅ Redis初始化完成")
    except Exception as e:
        logger.warning(f"⚠️ Redis初始化失败: {e}")
        logger.warning("⚠️ 应用将在没有Redis的情况下运行，某些功能可能受限")

    # 启动后台任务
    await start_background_tasks()
    logger.info("✅ 后台任务启动完成")

    # 启动 Celery Worker
    logger.info("🔄 正在启动 Celery Worker...")

    # 清理 Redis 中可能损坏的 Celery 数据
    clean_celery_redis_data()

    worker_process = start_celery_worker()
    if worker_process:
        # 等待 Celery Worker 就绪
        logger.info("⏳ 等待 Celery Worker 就绪...")
        import asyncio
        # 在后台线程中等待 Celery Worker
        ready = await asyncio.get_event_loop().run_in_executor(None, wait_for_celery_worker, 15)
        if ready:
            logger.info("✅ Celery Worker 已就绪，可以处理异步任务")
        else:
            logger.warning("⚠️ Celery Worker 启动超时，可能需要手动检查")
    else:
        logger.warning("⚠️ Celery Worker 未自动启动，异步任务可能无法执行")

    yield

    # 关闭时清理
    logger.info("🛑 关闭 LX SkyRoam Agent...")

    # 停止 Celery Worker
    stop_celery_worker()
    logger.info("✅ Celery Worker 已停止")

    logger.info("✅ 应用关闭完成")


# 创建FastAPI应用
app = FastAPI(
    title="LX SkyRoam Agent",
    description="智能旅游攻略生成系统",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# 中间件配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_HOSTS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=settings.ALLOWED_HOSTS
)

# 限流中间件（按IP）
app.add_middleware(RateLimitMiddleware)

# 挂载静态文件目录（用于图片等静态资源）
# 优先挂载静态文件路由，确保在文件不存在时能正确返回404，而不是被后续中间件或路由错误处理
STATIC_DIR = Path(__file__).parent / "uploads"
STATIC_DIR.mkdir(parents=True, exist_ok=True)
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

# 注册API路由
app.include_router(api_router, prefix="/api/v1")


@app.get("/")
async def root():
    """根路径"""
    return {
        "message": "LX SkyRoam Agent API",
        "version": "1.0.0",
        "status": "running"
    }


@app.get("/health")
async def health_check():
    """健康检查"""
    return {
        "status": "healthy",
        "service": "LX SkyRoam Agent",
        "version": "1.0.0"
    }


@app.get("/health/celery")
async def celery_health_check():
    """Celery Worker 健康检查"""
    try:
        import asyncio
        from app.core.celery import celery_app

        inspect = celery_app.control.inspect()

        # 方法1：检查 worker 统计信息
        stats = inspect.stats()
        # 处理可能的 Awaitable 返回值
        if asyncio.iscoroutine(stats):
            stats = await stats
        if stats:
            worker_names = list(stats.keys())
            return {
                "status": "healthy",
                "workers": worker_names,
                "worker_count": len(worker_names),
                "message": f"检测到 {len(worker_names)} 个 Celery Worker 正在运行",
                "method": "stats"
            }

        # 方法2：检查活跃任务
        active = inspect.active()
        # 处理可能的 Awaitable 返回值
        if asyncio.iscoroutine(active):
            active = await active
        if active is not None:
            worker_names = list(active.keys()) if active else []
            return {
                "status": "healthy",
                "workers": worker_names,
                "worker_count": len(worker_names) if worker_names else 1,
                "message": "Celery Worker 正在运行（无活跃任务）",
                "method": "active"
            }

        # 方法3：检查注册的任务
        registered = inspect.registered()
        # 处理可能的 Awaitable 返回值
        if asyncio.iscoroutine(registered):
            registered = await registered
        if registered:
            worker_names = list(registered.keys())
            return {
                "status": "healthy",
                "workers": worker_names,
                "worker_count": len(worker_names),
                "message": f"检测到 {len(worker_names)} 个 Celery Worker 正在运行",
                "method": "registered"
            }

        # 方法4：直接检查 Redis 中的 worker 心跳
        try:
            import redis
            from app.core.config import settings

            redis_client = redis.Redis(
                host=settings.REDIS_HOST,
                port=settings.REDIS_PORT,
                password=settings.REDIS_PASSWORD,
                db=settings.CELERY_BROKER_DB,
                decode_responses=True,
                socket_timeout=2
            )

            worker_keys = redis_client.keys("*celery*")
            if worker_keys:
                return {
                    "status": "healthy",
                    "workers": ["detected via redis"],
                    "worker_count": 1,
                    "message": "在 Redis 中检测到 Celery 数据，Worker 可能正在运行",
                    "method": "redis"
                }

        except Exception:
            pass

        return {
            "status": "unhealthy",
            "workers": [],
            "worker_count": 0,
            "message": "没有检测到运行中的 Celery Worker。请运行: celery -A app.core.celery worker --loglevel=info"
        }
    except Exception as e:
        import traceback
        traceback.print_exc()
        return {
            "status": "error",
            "workers": [],
            "worker_count": 0,
            "message": f"检查 Celery Worker 状态失败: {str(e)}"
        }


if __name__ == "__main__":
    # 通过命令行参数传递host和port
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", type=str, default="0.0.0.0")
    parser.add_argument("--port", type=int, default=8001)
    parser.add_argument("--no-celery", action="store_true", help="禁用自动启动 Celery Worker")
    args = parser.parse_args()

    # 设置环境变量
    if args.no_celery:
        os.environ["DISABLE_AUTO_CELERY"] = "1"

    uvicorn.run(
        "main:app",
        host=args.host,
        port=args.port,
        reload=settings.DEBUG,
        log_level="info"
    )
