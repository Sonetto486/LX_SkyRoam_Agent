import pandas as pd
import requests
import json
import psycopg2
import psycopg2.extras
from psycopg2.extensions import register_adapter, AsIs
import os
import time
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# ==============================================================================
# 配置区域 - 从环境变量读取，如果没有则使用默认值
# ==============================================================================
# Excel 数据集路径
EXCEL_FILE_PATH = os.getenv("RAG_EXCEL_FILE_PATH", r"travel_guide.xlsx")

# 数据库连接配置 (你的本地 PostgreSQL / SkyRoam 库)
DB_CONFIG = {
    "dbname": os.getenv("RAG_DB_NAME", "skyroam"),
    "user": os.getenv("RAG_DB_USER", "postgres"),
    "password": os.getenv("RAG_DB_PASSWORD", "123456"),
    "host": os.getenv("RAG_DB_HOST", "localhost"),
    "port": os.getenv("RAG_DB_PORT", "5432")
}

# 向量大模型 API 配置 (硅基流动)
EMBEDDING_API_BASE = os.getenv("RAG_EMBEDDING_API_BASE", "https://api.siliconflow.cn/v1")
EMBEDDING_API_KEY = os.getenv("RAG_EMBEDDING_API_KEY", "sk-akxmmyreibwsszkfvxsfnmnifgbaoxswrghligcjnygvgayo")
EMBEDDING_MODEL = os.getenv("RAG_EMBEDDING_MODEL", "Qwen/Qwen3-Embedding-0.6B")  

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
            
            transport_info = str(row.get("交通指南", "")).strip()
            accommodation_info = str(row.get("住宿方案", "")).strip()
            must_visit_spots = str(row.get("必打卡景点", "")).strip()
            food_recommendations = str(row.get("美食推荐", "")).strip()
            practical_tips = str(row.get("实用避雷建议", "")).strip()
            travel_feelings = str(row.get("旅行心路历程", "")).strip()
            
            # 组合全文用于向量检索
            full_text = f"{destination} {must_visit_spots} {food_recommendations} {travel_feelings}"
            
            print(f"[{index+1}/{total_rows}] 正在处理: {destination}...")
            
            # 1. 获取向量
            vector = get_embedding(full_text)
            
            # 2. 存入数据库
            # 先存入主表获取 ID
            cursor.execute(
                """
                INSERT INTO xhs_notes (destination, transport_info, accommodation_info, must_visit_spots, food_recommendations, practical_tips, travel_feelings)
                VALUES (%s, %s, %s, %s, %s, %s, %s) RETURNING id
                """,
                (destination, transport_info, accommodation_info, must_visit_spots, food_recommendations, practical_tips, travel_feelings)
            )
            note_id = cursor.fetchone()[0]
            
            # 再存入分块/向量表
            cursor.execute(
                """
                INSERT INTO xhs_note_chunks (note_id, content, embedding)
                VALUES (%s, %s, %s)
                """,
                (note_id, full_text, vector)
            )
            
            success_count += 1
            if success_count % 10 == 0:
                conn.commit()
                
        conn.commit()
        print(f"\n🎉 处理完成! 成功导入 {success_count} 条数据。")
        
    except Exception as e:
        conn.rollback()
        print(f"❌ 处理过程中出错: {e}")
    finally:
        cursor.close()
        conn.close()

if __name__ == "__main__":
    import_and_vectorize()
