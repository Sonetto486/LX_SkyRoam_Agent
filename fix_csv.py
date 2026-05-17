import pandas as pd
import json
import re

# 读取 CSV（使用 utf-8-sig）
df = pd.read_csv('xhs_notes.csv', encoding='utf-8-sig')
print(f'读取到 {len(df)} 条笔记')

# 修复可能存在的 Unicode 转义序列
def fix_unicode(text):
    if not isinstance(text, str):
        return text
    # 将 \\uXXXX 格式转换为真正的 Unicode
    try:
        return text.encode('utf-8').decode('unicode_escape')
    except:
        return text

# 修复所有文本列
text_columns = ['title', 'content', 'tags']
for col in text_columns:
    if col in df.columns:
        df[col] = df[col].apply(fix_unicode)
        # 显示样例
        sample = df[col].iloc[0] if len(df) > 0 else ''
        print(f'{col} 样例: {str(sample)[:50]}')

# 保存修复后的 CSV
df.to_csv('xhs_notes_fixed.csv', index=False, encoding='utf-8-sig')
print('\n✅ 已保存修复后的文件: xhs_notes_fixed.csv')
