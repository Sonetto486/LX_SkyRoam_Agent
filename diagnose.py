import pickle
import numpy as np

# 加载 vectorizer
with open('data/rag_store/vectorizer.pkl', 'rb') as f:
    vectorizer = pickle.load(f)

print(f'词汇表大小: {len(vectorizer.vocabulary_)}')
print(f'词汇表示例: {list(vectorizer.vocabulary_.keys())[:20]}')

# 测试查询
query = '北京有什么好吃的'
query_vec = vectorizer.transform([query]).toarray()
print(f'\n查询向量非零值数量: {np.count_nonzero(query_vec)}')
print(f'查询向量总和: {query_vec.sum()}')

# 检查查询中的词是否在词汇表中
for word in ['北京', '好吃', '美食', '推荐', '有什么']:
    if word in vectorizer.vocabulary_:
        print(f'✅ 词 "{word}" 在词汇表中')
    else:
        print(f'❌ 词 "{word}" 不在词汇表中')
