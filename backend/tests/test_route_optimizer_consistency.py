"""
测试路线优化功能 - 验证多种出行方案的数据一致性
"""

import asyncio
import sys
import os
import io

# 设置标准输出编码为UTF-8
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# 添加backend目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.route_optimizer import RouteOptimizer


async def test_all_modes_routes():
    """测试获取所有出行方式的实际路线数据"""
    print("\n=== 测试获取所有出行方式的实际路线数据 ===")

    # 创建一个模拟的RouteOptimizer实例（不需要数据库）
    optimizer = RouteOptimizer(None)

    # 三亚两个景点之间的路线
    origin = "109.506186,18.253277"  # 三亚湾
    destination = "109.528333,18.303056"  # 大东海
    straight_distance = 5.0  # 直线距离约5公里

    print(f"起点: {origin}")
    print(f"终点: {destination}")
    print(f"直线距离: {straight_distance} 公里")

    # 获取所有出行方式的实际路线数据
    all_modes_data = await optimizer._get_all_modes_routes(origin, destination, straight_distance)

    print(f"\n获取到 {len(all_modes_data)} 种出行方式的实际数据")

    for mode, data in all_modes_data.items():
        print(f"\n出行方式: {mode}")
        print(f"  实际距离: {data.get('distance')} 公里")
        print(f"  实际时间: {data.get('duration')} 分钟")
        print(f"  路径点数量: {len(data.get('path', []))}")

    # 验证数据一致性
    print("\n=== 验证数据一致性 ===")

    # 检查每种出行方式的数据是否不同
    distances = [data.get('distance') for data in all_modes_data.values()]
    durations = [data.get('duration') for data in all_modes_data.values()]

    print(f"距离列表: {distances}")
    print(f"时间列表: {durations}")

    # 验证距离和时间是否合理
    for mode, data in all_modes_data.items():
        distance = data.get('distance')
        duration = data.get('duration')

        if distance and duration:
            # 计算平均速度
            if duration > 0:
                speed = (distance / duration) * 60  # km/h
                print(f"{mode} 平均速度: {speed:.1f} km/h")

                # 验证速度是否在合理范围内
                if mode == "walking":
                    if speed < 3 or speed > 7:
                        print(f"[WARN] {mode} 速度异常: {speed:.1f} km/h (正常范围: 3-7 km/h)")
                    else:
                        print(f"[OK] {mode} 速度正常")
                elif mode == "transit":
                    if speed < 10 or speed > 30:
                        print(f"[WARN] {mode} 速度异常: {speed:.1f} km/h (正常范围: 10-30 km/h)")
                    else:
                        print(f"[OK] {mode} 速度正常")
                elif mode == "driving":
                    if speed < 20 or speed > 60:
                        print(f"[WARN] {mode} 速度异常: {speed:.1f} km/h (正常范围: 20-60 km/h)")
                    else:
                        print(f"[OK] {mode} 速度正常")


async def test_alternatives_consistency():
    """测试alternatives数组的数据一致性"""
    print("\n=== 测试alternatives数组的数据一致性 ===")

    # 创建一个模拟的RouteOptimizer实例
    optimizer = RouteOptimizer(None)

    # 测试距离
    distance = 3.88  # 公里

    print(f"测试距离: {distance} 公里")

    # 使用估算方法生成alternatives
    alternatives = optimizer._calculate_all_travel_modes(distance)

    print(f"\n估算的alternatives数据:")
    for alt in alternatives:
        print(f"  {alt['mode_label']}: {alt['distance']} 公里, {alt['duration']} 分钟")

    # 验证所有alternatives的距离是否相同（估算方法使用相同的直线距离）
    distances = [alt['distance'] for alt in alternatives]
    if all(d == distances[0] for d in distances):
        print("[OK] 估算方法中所有出行方式的距离相同（使用直线距离）")
    else:
        print("[WARN] 估算方法中出行方式的距离不同")

    # 验证时间是否不同（不同出行方式速度不同）
    durations = [alt['duration'] for alt in alternatives]
    if len(set(durations)) > 1:
        print("[OK] 估算方法中不同出行方式的时间不同（速度不同）")
    else:
        print("[WARN] 估算方法中所有出行方式的时间相同")


async def main():
    """主测试函数"""
    print("=" * 60)
    print("路线优化功能测试 - 验证多种出行方案数据一致性")
    print("=" * 60)

    # 测试获取所有出行方式的实际路线数据
    await test_all_modes_routes()

    # 测试alternatives数组的数据一致性
    await test_alternatives_consistency()

    print("\n" + "=" * 60)
    print("测试完成")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())