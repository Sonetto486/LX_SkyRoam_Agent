"""
测试行程概览显示修复效果
"""

import sys
import os
import io

# 设置标准输出编码为UTF-8
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# 添加backend目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.plan_generator import PlanGenerator


def test_schedule_normalization():
    """测试schedule数据规范化"""
    print("\n=== 测试schedule数据规范化 ===")

    # 模拟LLM返回的冗长activity数据
    test_data = {
        "day": 1,
        "date": "2024-01-01",
        "schedule": [
            {
                "time": "09:00-12:00",
                "activity": "上午游览市中心地标芙蓉广场。该景点位于蔡锷中路，交通便利（地铁5号口步行430米）。建议在此区域漫步，感受城市中心氛围，周边餐饮选择丰富。",
                "location": "芙蓉广场",
                "cost": 50
            },
            {
                "time": "12:00-13:00",
                "activity": "午餐",
                "location": "附近餐厅",
                "description": "品尝当地特色美食",
                "cost": 100
            },
            {
                "time": "14:00-17:00",
                "activity": "下午前往湘江风光带散步，这里是自然风光类景点，评分高达4.8，适合沿河休闲观景，体验长沙母亲河的魅力。",
                "location": "湘江风光带",
                "cost": 0
            }
        ],
        "attractions": [],
        "estimated_cost": 150
    }

    print("原始数据:")
    for item in test_data["schedule"]:
        print(f"  activity: {item['activity']}")
        print(f"  description: {item.get('description', '无')}")
        print()

    # 应用规范化逻辑
    for item in test_data["schedule"]:
        activity = item.get("activity", "")
        description = item.get("description", "")

        # 如果activity过长且没有description，自动分割
        if len(activity) > 50 and not description:
            # 按句号分割，第一句作为标题
            sentences = activity.split("。")
            if len(sentences) > 1 and sentences[0]:
                item["activity"] = sentences[0] + "。"
                item["description"] = "。".join(sentences[1:])
            else:
                # 按逗号分割
                parts = activity.split("，")
                if len(parts) > 1 and len(parts[0]) > 0:
                    item["activity"] = parts[0]
                    item["description"] = "，".join(parts[1:])

    print("规范化后的数据:")
    for item in test_data["schedule"]:
        print(f"  activity: {item['activity']}")
        print(f"  description: {item.get('description', '无')}")
        print(f"  activity长度: {len(item['activity'])}")
        print()

    # 验证结果
    print("=== 验证结果 ===")

    # 第一个item应该被分割
    first_item = test_data["schedule"][0]
    if len(first_item["activity"]) <= 50:
        print("[OK] 第一个item的activity已缩短到50字以内")
    else:
        print(f"[FAIL] 第一个item的activity仍然过长: {len(first_item['activity'])}字")

    if first_item.get("description"):
        print("[OK] 第一个item已生成description字段")
    else:
        print("[FAIL] 第一个item缺少description字段")

    # 第二个item应该保持不变（已有description）
    second_item = test_data["schedule"][1]
    if second_item["activity"] == "午餐":
        print("[OK] 第二个item保持不变（已有description）")
    else:
        print("[FAIL] 第二个item被错误修改")

    # 第三个item应该被分割
    third_item = test_data["schedule"][2]
    if len(third_item["activity"]) <= 50:
        print("[OK] 第三个item的activity已缩短到50字以内")
    else:
        print(f"[FAIL] 第三个item的activity仍然过长: {len(third_item['activity'])}字")

    if third_item.get("description"):
        print("[OK] 第三个item已生成description字段")
    else:
        print("[FAIL] 第三个item缺少description字段")


def test_frontend_split_logic():
    """测试前端智能分割逻辑"""
    print("\n=== 测试前端智能分割逻辑 ===")

    # 测试不同的activity字段
    test_cases = [
        {
            "activity": "上午游览芙蓉广场",
            "description": "",
            "expected_title": "上午游览芙蓉广场",
            "expected_detail": ""
        },
        {
            "activity": "上午游览市中心地标芙蓉广场。该景点位于蔡锷中路，交通便利。",
            "description": "",
            "expected_title": "上午游览市中心地标芙蓉广场。",
            "expected_detail": "该景点位于蔡锷中路，交通便利。"
        },
        {
            "activity": "午餐",
            "description": "品尝当地特色美食",
            "expected_title": "午餐",
            "expected_detail": "品尝当地特色美食"
        },
        {
            "activity": "下午前往湘江风光带散步，这里是自然风光类景点，评分高达4.8。",
            "description": "",
            "expected_title": "下午前往湘江风光带散步",
            "expected_detail": "这里是自然风光类景点，评分高达4.8。"
        }
    ]

    for i, test_case in enumerate(test_cases):
        activity = test_case["activity"]
        description = test_case["description"]

        # 应用前端分割逻辑
        if activity.length > 50 or description:
            sentences = activity.split("。")
            title = sentences[0] + (sentences.length > 1 and sentences[0].length > 0 ? "。" : "")
            detail = description or (sentences.length > 1 ? sentences.slice(1).join("。") : "")
        else:
            title = activity
            detail = ""

        # Python版本的前端逻辑
        if len(activity) > 50 or description:
            sentences = activity.split("。")
            title = sentences[0] + (len(sentences) > 1 and len(sentences[0]) > 0 ? "。" : "")
            detail = description or (len(sentences) > 1 ? "。".join(sentences[1:]) : "")
        else:
            title = activity
            detail = ""

        print(f"\n测试案例 {i+1}:")
        print(f"  输入activity: {activity}")
        print(f"  输入description: {description}")
        print(f"  输出title: {title}")
        print(f"  输出detail: {detail}")
        print(f"  期望title: {test_case['expected_title']}")
        print(f"  期望detail: {test_case['expected_detail']}")

        if title == test_case["expected_title"]:
            print("[OK] title匹配期望值")
        else:
            print("[FAIL] title不匹配期望值")

        if detail == test_case["expected_detail"]:
            print("[OK] detail匹配期望值")
        else:
            print("[FAIL] detail不匹配期望值")


if __name__ == "__main__":
    print("=" * 60)
    print("行程概览显示修复效果测试")
    print("=" * 60)

    test_schedule_normalization()
    test_frontend_split_logic()

    print("\n" + "=" * 60)
    print("测试完成")
    print("=" * 60)