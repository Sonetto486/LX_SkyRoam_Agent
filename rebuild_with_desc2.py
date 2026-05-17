import pandas as pd
import numpy as np
import json
import pickle
import re
import warnings
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.preprocessing import normalize

warnings.filterwarnings('ignore')

def parse_count(value):
    if pd.isna(value):
        return 0
    value = str(value)
    if '万' in value:
        num = re.findall(r'[\d.]+', value)
        if num:
            return float(num[0]) * 10000
        return 0
    if '+' in value:
        value = value.replace('+', '')
    try:
        return float(value)
    except:
        return 0

df = pd.read_csv('xhs_notes_full.csv', encoding='utf-8-sig')
print(f'读取到 {len(df)} 条笔记')

for col in ['like_count', 'collect_count', 'comment_count']:
    if col in df.columns:
        df[col] = df[col].apply(parse_count)

# 构建文档文本 - 使用 title + desc + tags
texts = []
for idx, row in df.iterrows():
    title = str(row.get('title', ''))
    desc = str(row.get('desc', ''))
    tags = str(row.get('tags', ''))
    # desc 重复两次提高权重
    doc_text = f'{title} {desc} {desc} {tags}'
    texts.append(doc_text)
    if idx < 3:
        print(f'\n样例 {idx+1}:')
        print(f'  title: {title[:50]}')
        print(f'  desc: {desc[:100]}...')

print(f'\n生成 TF-IDF 向量...')
vectorizer = TfidfVectorizer(
    max_features=1024,
    min_df=2,
    max_df=0.95,
    token_pattern=r'(?u)\b\w+\b'
)
vectors = vectorizer.fit_transform(texts).toarray().astype(np.float32)
print(f'向量维度: {vectors.shape}')
print(f'词汇表大小: {len(vectorizer.vocabulary_)}')

# 检查关键词语
keywords = ['北京', '美食', '好吃', '推荐', '攻略', '景点', '东澳岛', '酒店', '打卡']
print('\n词汇表检查:')
for word in keywords:
    if word in vectorizer.vocabulary_:
        print(f'  ✅ "{word}" 在词汇表中')
    else:
        print(f'  ❌ "{word}" 不在词汇表中')

# 归一化
vectors = normalize(vectors, norm='l2')

# 保存
import os
os.makedirs('data/rag_store', exist_ok=True)
np.save('data/rag_store/vectors.npy', vectors)

with open('data/rag_store/vectorizer.pkl', 'wb') as f:
    pickle.dump(vectorizer, f)

metadata = []
for idx, row in df.iterrows():
    metadata.append({
        'id': str(row.get('note_id', idx)),
        'title': str(row.get('title', ''))[:200],
        'desc': str(row.get('desc', ''))[:500],
        'tags': str(row.get('tags', ''))[:200],
        'like_count': float(row.get('like_count', 0)),
        'collect_count': float(row.get('collect_count', 0))
    })

with open('data/rag_store/metadata.json', 'w', encoding='utf-8') as f:
    json.dump(metadata, f, ensure_ascii=False, indent=2)

print(f'\n✅ 索引重建完成，共 {len(metadata)} 条文档')

# 测试搜索
print('\n' + '='*50)
print('测试搜索:')
print('='*50)

test_queries = ['北京', '北京美食', '北京有什么好吃的', '东澳岛', '酒店推荐']
for test_query in test_queries:
    query_vec = vectorizer.transform([test_query]).toarray()
    norm = np.linalg.norm(query_vec)
    if norm > 0:
        query_vec = query_vec / norm
        similarities = np.dot(vectors, query_vec.T).flatten()
        top_idx = np.argsort(similarities)[-5:][::-1]
        print(f'\n查询: "{test_query}"')
        for i, idx in enumerate(top_idx):
            if similarities[idx] > 0.05:
                print(f'  {i+1}. 相似度: {similarities[idx]:.4f}')
                print(f'     标题: {metadata[idx].get("title", "")[:60]}')
