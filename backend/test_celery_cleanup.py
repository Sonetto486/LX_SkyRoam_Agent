"""
测试 Celery Worker 自动停止功能

测试方法：
1. 启动后端服务：python main.py
2. 在另一个终端运行此测试脚本：python test_celery_cleanup.py
3. 观察是否正确停止 Celery Worker

或者手动测试：
1. 启动后端服务
2. 按 Ctrl+C 停止
3. 检查是否还有 celery 进程在运行
"""

import subprocess
import time
import sys
import signal
import os

def check_celery_processes():
    """检查是否有 Celery Worker 进程在运行"""
    try:
        # Windows 使用 tasklist
        if sys.platform == "win32":
            result = subprocess.run(
                ["tasklist", "/FI", "IMAGENAME", "eq", "python.exe"],
                capture_output=True,
                text=True
            )
            lines = result.stdout.strip().split('\n')
            # 过滤出包含 celery 的进程
            celery_processes = []
            for line in lines:
                if 'python.exe' in line.lower():
                    celery_processes.append(line)
            return celery_processes
        else:
            # Linux/Mac 使用 ps
            result = subprocess.run(
                ["ps", "aux"],
                capture_output=True,
                text=True
            )
            lines = result.stdout.strip().split('\n')
            celery_processes = [line for line in lines if 'celery' in line.lower()]
            return celery_processes
    except Exception as e:
        print(f"检查进程失败: {e}")
        return []


def test_graceful_shutdown():
    """测试优雅关闭"""
    print("=" * 60)
    print("测试 Celery Worker 自动停止功能")
    print("=" * 60)

    print("\n1. 启动后端服务...")
    backend_process = subprocess.Popen(
        [sys.executable, "main.py"],
        cwd=os.path.dirname(os.path.abspath(__file__)),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1
    )

    # 等待服务启动
    print("   等待服务启动 (15秒)...")
    time.sleep(15)

    # 检查 Celery Worker 进程
    print("\n2. 检查 Celery Worker 进程...")
    celery_processes = check_celery_processes()
    if celery_processes:
        print(f"   ✅ 发现 {len(celery_processes)} 个 Python 进程:")
        for proc in celery_processes[:5]:  # 只显示前5个
            print(f"      {proc}")
    else:
        print("   ❌ 未发现 Celery Worker 进程")

    # 发送终止信号
    print("\n3. 发送终止信号 (SIGTERM)...")
    backend_process.send_signal(signal.SIGTERM)

    # 等待进程结束
    print("   等待进程结束 (最多20秒)...")
    try:
        backend_process.wait(timeout=20)
        print("   ✅ 后端服务已停止")
    except subprocess.TimeoutExpired:
        print("   ⚠️ 超时，强制终止...")
        backend_process.kill()
        backend_process.wait()

    # 再次检查进程
    print("\n4. 检查 Celery Worker 是否已停止...")
    time.sleep(2)  # 给一点时间让进程完全退出
    celery_processes = check_celery_processes()
    if celery_processes:
        print(f"   ⚠️ 仍有 {len(celery_processes)} 个 Python 进程在运行:")
        for proc in celery_processes[:5]:
            print(f"      {proc}")
        print("\n   注意: 可能有其他 Python 进程在运行，请手动确认 Celery Worker 已停止")
    else:
        print("   ✅ 所有 Celery Worker 进程已停止")

    print("\n" + "=" * 60)
    print("测试完成")
    print("=" * 60)


def manual_test_instructions():
    """手动测试说明"""
    print("=" * 60)
    print("手动测试 Celery Worker 自动停止功能")
    print("=" * 60)
    print("\n步骤：")
    print("1. 在终端启动后端服务:")
    print("   cd backend")
    print("   python main.py")
    print("\n2. 等待服务完全启动，看到 'Celery Worker 已就绪' 消息")
    print("\n3. 按 Ctrl+C 停止服务")
    print("\n4. 观察日志输出，应该看到:")
    print("   - '收到终止信号，正在清理...'")
    print("   - '正在停止 Celery Worker...'")
    print("   - 'Celery Worker 已优雅停止'")
    print("\n5. 检查是否还有 celery 进程:")
    print("   Windows: tasklist | findstr python")
    print("   Linux/Mac: ps aux | grep celery")
    print("\n预期结果:")
    print("   ✅ Celery Worker 进程应该已停止")
    print("   ✅ 不应该有残留的 celery 进程")
    print("=" * 60)


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--manual", action="store_true", help="显示手动测试说明")
    args = parser.parse_args()

    if args.manual:
        manual_test_instructions()
    else:
        test_graceful_shutdown()
