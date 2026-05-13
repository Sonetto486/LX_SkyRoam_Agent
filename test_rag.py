"""
RAG检索服务测试脚本
用于验证向量化数据库检索功能是否正常工作
"""

import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.app.services.rag_retriever import get_rag_retriever


def test_rag_retriever():
    """测试RAG检索功能"""
    print("=" * 60)
    print("RAG检索服务测试")
    print("=" * 60)

    # 初始化检索器
    retriever = get_rag_retriever()

    # 测试1: 基本检索
    print("\n【测试1】基本检索 - 搜索'北京旅游'")
    results = retriever.retrieve(query="北京旅游", top_k=3)
    if results:
        print(f"找到 {len(results)} 条结果:")
        for i, item in enumerate(results, 1):
            print(f"\n结果 {i}:")
            print(f"  目的地: {item.get('destination', 'N/A')}")
            print(f"  类型: {item.get('chunk_type', 'N/A')}")
            print(f"  相似度: {item.get('similarity', 0):.4f}")
            print(f"  内容: {item.get('chunk_text', 'N/A')[:100]}...")
    else:
        print("未找到相关结果，请检查数据库是否有数据")

    # 测试2: 目的地检索
    print("\n" + "=" * 60)
    print("【测试2】目的地检索 - 搜索'上海'")
    dest_results = retriever.retrieve_for_destination("上海", top_k=5)
    print(f"景点: {len(dest_results.get('spots', []))} 条")
    print(f"美食: {len(dest_results.get('food', []))} 条")
    print(f"交通: {len(dest_results.get('transport', []))} 条")
    print(f"住宿: {len(dest_results.get('accommodation', []))} 条")
    print(f"贴士: {len(dest_results.get('tips', []))} 条")

    # 测试3: 构建RAG上下文
    print("\n" + "=" * 60)
    print("【测试3】构建RAG上下文 - '杭州'")
    context = retriever.build_rag_context("杭州")
    if context:
        print("生成的上下文:")
        print("-" * 40)
        print(context[:500] + "..." if len(context) > 500 else context)
    else:
        print("未能生成上下文")

    print("\n" + "=" * 60)
    print("测试完成!")
    print("=" * 60)


if __name__ == "__main__":
    test_rag_retriever()