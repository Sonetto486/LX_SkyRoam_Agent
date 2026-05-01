import asyncio
import sys


def run_coro(coro):
    """
    在同步环境中运行异步协程

    对于 Celery Worker (Windows solo pool)，使用新的事件循环
    以避免与现有循环冲突
    """
    try:
        # 检查是否已有事件循环在运行
        loop = asyncio.get_running_loop()
        # 如果有，创建新线程运行
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor() as executor:
            future = executor.submit(asyncio.run, coro)
            return future.result()
    except RuntimeError:
        # 没有运行中的事件循环，直接创建新的
        return asyncio.run(coro)
