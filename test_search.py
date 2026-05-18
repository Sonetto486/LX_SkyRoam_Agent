import sys
sys.path.insert(0, 'scripts')
from rag_api import search_with_tfidf

print('测试搜索: 北京美食')
results = search_with_tfidf('北京旅游', k=5)
print(f'结果数: {len(results)}')
for i, r in enumerate(results[:3]):
    sim = r["similarity"]
    title = r["doc"].get("title", "")[:50]
    print(f'{i+1}. 相似度: {sim:.4f}')
    print(f'   标题: {title}')
