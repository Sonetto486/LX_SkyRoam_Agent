import pandas as pd
import requests
import json
import psycopg2
import psycopg2.extras
from psycopg2.extensions import register_adapter, AsIs
import os
import time
from dotenv import load_dotenv

# 加载环境变量 - 从 backend 目录的 .env 文件
_env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "backend", ".env")
if os.path.exists(_env_path):
    load_dotenv(_env_path)
else:
    load_dotenv()  # 尝试当前目录

# ==============================================================================
# 配置区域 - 从环境变量读取，如果没有则使用默认值
# ==============================================================================
# Excel 数据集路径 - 支持绝对路径和相对路径
_excel_path = os.getenv("RAG_EXCEL_FILE_PATH", "travel_guide.xlsx")
if not os.path.isabs(_excel_path) and not os.path.exists(_excel_path):
    # 如果是相对路径且当前目录找不到，尝试脚本所在目录的上级目录
    _script_dir = os.path.dirname(os.path.abspath(__file__))
    _project_root = os.path.dirname(_script_dir)
    _excel_path = os.path.join(_project_root, "travel_guide.xlsx")
EXCEL_FILE_PATH = _excel_path

# 数据库连接配置 (你的本地 PostgreSQL / SkyRoam 库)
DB_CONFIG = {
    "dbname": os.getenv("RAG_DB_NAME", "skyroam"),
    "user": os.getenv("RAG_DB_USER", "postgres"),
    "password": os.getenv("RAG_DB_PASSWORD", ""),
    "host": os.getenv("RAG_DB_HOST", "localhost"),
    "port": os.getenv("RAG_DB_PORT", "5432")
}

# 向量大模型 API 配置 (智谱 AI)
EMBEDDING_API_BASE = os.getenv("RAG_EMBEDDING_API_BASE", "https://open.bigmodel.cn/api/paas/v4")
EMBEDDING_API_KEY = os.getenv("RAG_EMBEDDING_API_KEY", "")
EMBEDDING_MODEL = os.getenv("RAG_EMBEDDING_MODEL", "embedding-2")  

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
            
            transport_info = str(row.get("交通安排", "")).strip()
            accommodation_info = str(row.get("住宿推荐", "")).strip()
            must_visit_spots = str(row.get("必打卡景点", "")).strip()
            food_recommendations = str(row.get("美食推荐", "")).strip()
            practical_tips = str(row.get("实用小贴士", "")).strip()
            travel_feelings = str(row.get("旅行感悟", "")).strip()
            
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
                INSERT INTO xhs_note_chunks (note_id, chunk_type, chunk_text, embedding)
                VALUES (%s, %s, %s, %s)
                """,
                (note_id, 'mixed', full_text, vector)
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
