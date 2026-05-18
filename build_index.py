
import pandas as pd
import numpy as np
import json
import pickle
import os
import re
from sklearn.feature_extraction.text import TfidfVectorizer

def parse_count(value):
    """将 10万+ 或 1000 转换为数字"""
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

# 读取 CSV
df = pd.read_csv('xhs_notes.csv', encoding='utf-8-sig')
print(f'读取到 {len(df)} 条笔记')

# 清理数字列
for col in ['like_count', 'collect_count', 'comment_count']:
    if col in df.columns:
        df[col] = df[col].apply(parse_count)
        print(f'{col} 转换完成，最大值: {df[col].max():.0f}')

# 构建文档文本
texts = []
for idx, row in df.iterrows():
    title = str(row.get('title', ''))
    content = str(row.get('content', ''))
    tags = str(row.get('tags', ''))
    doc_text = f'{title}\n{content}\n{tags}'
    texts.append(doc_text)

# TF-IDF 向量化
print('生成 TF-IDF 向量...')
vectorizer = TfidfVectorizer(max_features=384, min_df=1, max_df=0.9)
vectors = vectorizer.fit_transform(texts).toarray().astype(np.float32)
print(f'向量维度: {vectors.shape}')

# 保存
os.makedirs('data/rag_store', exist_ok=True)
np.save('data/rag_store/vectors.npy', vectors)

with open('data/rag_store/vectorizer.pkl', 'wb') as f:
    pickle.dump(vectorizer, f)

# 保存 metadata
metadata = []
for idx, row in df.iterrows():
    metadata.append({
        'id': str(row.get('note_id', idx)),
        'title': str(row.get('title', ''))[:200],
        'content': str(row.get('content', ''))[:500],
        'tags': str(row.get('tags', ''))[:200],
        'like_count': float(row.get('like_count', 0)),
        'collect_count': float(row.get('collect_count', 0))
    })

with open('data/rag_store/metadata.json', 'w', encoding='utf-8') as f:
    json.dump(metadata, f, ensure_ascii=False, indent=2)

print(f'✅ 索引重建完成，共 {len(metadata)} 条文档')
