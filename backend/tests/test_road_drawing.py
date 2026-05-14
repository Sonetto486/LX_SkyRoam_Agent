"""
测试道路描绘功能 - 步行和驾车路线的polyline提取
"""

import asyncio
import sys
import os
import io

# 设置标准输出编码为UTF-8
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# 添加backend目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.tools.amap_rest_client import amap_rest_client


async def test_walking_directions():
    """测试步行路线规划"""
    print("\n=== 测试步行路线规划 ===")

    # 三亚两个景点之间的步行路线
    origin = "109.506186,18.253277"  # 三亚湾
    destination = "109.510944,18.247832"  # 附近景点

    routes = await amap_rest_client.get_directions(origin, destination, "walking")

    if routes:
        print(f"[OK] 获取到 {len(routes)} 条步行路线")
        for i, route in enumerate(routes):
            print(f"\n路线 {i+1}:")
            print(f"  类型: {route.get('type')}")
            print(f"  距离: {route.get('distance')} 公里")
            print(f"  时间: {route.get('duration')} 分钟")
            path_points = route.get('path', [])
            print(f"  路径点数量: {len(path_points)}")
            if path_points:
                print(f"  前3个路径点: {path_points[:3]}")
    else:
        print("[FAIL] 未获取到步行路线")


async def test_driving_directions():
    """测试驾车路线规划"""
    print("\n=== 测试驾车路线规划 ===")

    # 三亚两个景点之间的驾车路线
    origin = "109.506186,18.253277"  # 三亚湾
    destination = "109.528333,18.303056"  # 大东海

    routes = await amap_rest_client.get_directions(origin, destination, "driving")

    if routes:
        print(f"[OK] 获取到 {len(routes)} 条驾车路线")
        for i, route in enumerate(routes):
            print(f"\n路线 {i+1}:")
            print(f"  类型: {route.get('type')}")
            print(f"  距离: {route.get('distance')} 公里")
            print(f"  时间: {route.get('duration')} 分钟")
            path_points = route.get('path', [])
            print(f"  路径点数量: {len(path_points)}")
            if path_points:
                print(f"  前3个路径点: {path_points[:3]}")
    else:
        print("[FAIL] 未获取到驾车路线")


async def test_transit_directions():
    """测试公交路线规划"""
    print("\n=== 测试公交路线规划 ===")

    # 三亚两个景点之间的公交路线
    origin = "109.506186,18.253277"  # 三亚湾
    destination = "109.528333,18.303056"  # 大东海

    routes = await amap_rest_client.get_directions(origin, destination, "transit", "三亚")

    if routes:
        print(f"[OK] 获取到 {len(routes)} 条公交路线")
        for i, route in enumerate(routes):
            print(f"\n路线 {i+1}:")
            print(f"  类型: {route.get('type')}")
            print(f"  距离: {route.get('distance')} 公里")
            print(f"  时间: {route.get('duration')} 分钟")
    else:
        print("[FAIL] 未获取到公交路线")


async def test_polyline_parsing():
    """测试polyline解析"""
    print("\n=== 测试polyline解析 ===")

    # 测试polyline字符串
    test_polyline = "109.506186,18.253277;109.507000,18.254000;109.508000,18.255000"

    points = amap_rest_client._parse_polyline(test_polyline)

    print(f"输入: {test_polyline}")
    print(f"解析结果: {points}")
    print(f"点数: {len(points)}")

    if len(points) == 3:
        print("[OK] polyline解析正确")
    else:
        print("[FAIL] polyline解析错误")


async def main():
    """主测试函数"""
    print("=" * 60)
    print("道路描绘功能测试")
    print("=" * 60)

    # 测试polyline解析
    await test_polyline_parsing()

    # 测试步行路线
    await test_walking_directions()

    # 测试驾车路线
    await test_driving_directions()

    # 测试公交路线
    await test_transit_directions()

    print("\n" + "=" * 60)
    print("测试完成")
    print("=" * 60)

    # 关闭客户端
    await amap_rest_client.close()


if __name__ == "__main__":
    asyncio.run(main())
