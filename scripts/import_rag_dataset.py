import pandas as pd
import requests
import json
import psycopg2
import psycopg2.extras
from psycopg2.extensions import register_adapter, AsIs
import os
import time

# ==============================================================================
# 配置区域
# ==============================================================================
# Excel 数据集路径
EXCEL_FILE_PATH = r"C:\Users\30564\Desktop\Vibe Coding\travel_guide.xlsx"  # 修改为你的实际文件名称

# 数据库连接配置 (你的本地 PostgreSQL / SkyRoam 库)
DB_CONFIG = {
    "dbname": "skyroam",
    "user": "postgres",
    "password": "123456",
    "host": "localhost",
    "port": "5432"
}

# 向量大模型 API 配置 (Ofox API 等提供 OpenAI 兼容格式接口的平台)
EMBEDDING_API_BASE = "https://api.ofox.ai/v1"
EMBEDDING_API_KEY = "your-api-key"
# 根据你的实际供应商修改模型名称，比如："bge-m3", "text-embedding-3-small" 等
EMBEDDING_MODEL = "bge-m3"  

# 适配 numpy 类型到 PostgreSQL
def add_adapters():
    import numpy as np
    register_adapter(np.int64, AsIs)

# ==============================================================================
# 连接并转换向量
# ==============================================================================
def get_embedding(text: str) -> list:
    """调用 API 获取指定文本的向量数组"""
    url = f"{EMBEDDING_API_BASE}/embeddings"
    headers = {
        "Authorization": f"Bearer {EMBEDDING_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": EMBEDDING_MODEL,
        "input": text
    }
    
    max_retries = 3
    for attempt in range(max_retries):
        try:
            response = requests.post(url, headers=headers, json=payload, timeout=10)
            response.raise_for_status()
            data = response.json()
            return data["data"][0]["embedding"]
        except Exception as e:
            print(f" 获取向量异常 {e}，正在重试...({attempt+1}/{max_retries})")
            time.sleep(2)
            
    raise Exception("获取向量失败，请检查 API Key 或网络连通性。")

# ==============================================================================
# 主逻辑处理
# ==============================================================================
def import_and_vectorize():
    add_adapters()
    print("🚀 开始加载 Excel 数据集...")
    if not os.path.exists(EXCEL_FILE_PATH):
        print(f"❌ 找不到文件: {EXCEL_FILE_PATH}")
        return
        
    df = pd.read_excel(EXCEL_FILE_PATH)
    
    # 填充空值以避免报错
    df = df.fillna("")
    
    total_rows = len(df)
    print(f"✅ 成功加载数据集，共 {total_rows} 条数据。准备连接数据库...")
    
    conn = psycopg2.connect(**DB_CONFIG)
    cursor = conn.cursor()
    
    success_count = 0
    try:
        for index, row in df.iterrows():
            destination = str(row.get("目的地", "")).strip()
            if not destination:
                continue
                
            # 1️⃣ 写入原文主表 (xhs_notes)
            transport_info = str(row.get("交通安排", ""))
            accommodation_info = str(row.get("住宿推荐", ""))
            must_visit_spots = str(row.get("必打卡景点", ""))
            food_recommendations = str(row.get("美食推荐", ""))
            practical_tips = str(row.get("实用小贴士", ""))
            travel_feelings = str(row.get("旅行感悟", ""))
            
            insert_note_query = """
                INSERT INTO xhs_notes 
                (destination, transport_info, accommodation_info, must_visit_spots, 
                 food_recommendations, practical_tips, travel_feelings, source_type)
                VALUES (%s, %s, %s, %s, %s, %s, %s, 'excel')
                RETURNING id;
            """
            cursor.execute(insert_note_query, (
                destination, transport_info, accommodation_info, must_visit_spots,
                food_recommendations, practical_tips, travel_feelings
            ))
            note_id = cursor.fetchone()[0]
            
            # 2️⃣ 切片器生成文本块 (Chunking)
            if must_visit_spots:
                # 拼接切片文本
                chunk_text = f"在{destination}，必打卡景点有：{must_visit_spots}"
                
                print(f"[{index+1}/{total_rows}] 正在为 {destination} 获取向量...")
                
                # 获取该段文本的向量数组
                vector_array = get_embedding(chunk_text)
                
                # 3️⃣ 写入向量子表 (xhs_note_chunks)
                insert_chunk_query = """
                    INSERT INTO xhs_note_chunks 
                    (note_id, chunk_type, chunk_text, embedding)
                    VALUES (%s, %s, %s, %s);
                """
                
                # pgvector 支持将 Python lists 直接传入向量列
                cursor.execute(insert_chunk_query, (
                    note_id, 
                    "spots",           # 标记类型为景点
                    chunk_text, 
                    vector_array
                ))
            
            success_count += 1
            if success_count % 10 == 0:
                conn.commit()  # 每 10 条提交一次
                print(f"💾 已提交 {success_count} 条数据到数据库")
                
        conn.commit()
        print(f"\n🎉 导入全部完成！共成功处理 {success_count} 条数据向量化。")
        
    except Exception as e:
        print(f"\n❌ 执行过程中发生错误: {e}")
        conn.rollback()
    finally:
        cursor.close()
        conn.close()

if __name__ == "__main__":
    import_and_vectorize()
