"""
POI 景点数据导入脚本
将 POIs_V2.csv 中的景点数据向量化并存入 PostgreSQL
"""

import pandas as pd
import requests
import psycopg2
import psycopg2.extras
from psycopg2.extensions import register_adapter, AsIs
import os
import time
import json
from pathlib import Path
from dotenv import load_dotenv

# ==============================================================================
# 配置区域
# ==============================================================================

# 项目根目录
PROJECT_ROOT = Path(__file__).resolve().parent.parent

# CSV 数据集路径
CSV_FILE_PATH = os.getenv("POI_CSV_FILE_PATH", str(PROJECT_ROOT / "POIs_V2.csv"))

# 数据库连接配置（敏感信息从环境变量读取，无默认值）
DB_CONFIG = {
    "dbname": os.getenv("RAG_DB_NAME", "skyroam"),
    "user": os.getenv("RAG_DB_USER", "postgres"),
    "password": os.getenv("RAG_DB_PASSWORD", ""),
    "host": os.getenv("RAG_DB_HOST", "localhost"),
    "port": os.getenv("RAG_DB_PORT", "5432")
}

# 向量化 API 配置（敏感信息从环境变量读取，无默认值）
EMBEDDING_API_BASE = os.getenv("RAG_EMBEDDING_API_BASE", "https://open.bigmodel.cn/api/paas/v4")
EMBEDDING_API_KEY = os.getenv("RAG_EMBEDDING_API_KEY", "")
EMBEDDING_MODEL = os.getenv("RAG_EMBEDDING_MODEL", "embedding-2")  # 智谱AI Embedding模型，向量维度2048

# 批处理配置
BATCH_SIZE = 50  # 每批处理数量
BATCH_DELAY = 0.5  # 批次间隔(秒)，避免API限流
MAX_RETRIES = 3  # API调用最大重试次数

# 进度文件路径
PROGRESS_FILE = PROJECT_ROOT / "scripts" / "poi_import_progress.json"


# ==============================================================================
# 工具函数
# ==============================================================================

def add_adapters():
    """适配 numpy 类型到 PostgreSQL"""
    import numpy as np
    register_adapter(np.int64, AsIs)
    register_adapter(np.float64, AsIs)


def build_searchable_text(row) -> str:
    """
    构建可检索文本
    将景点信息转换为一段自然语言文本，用于向量化检索
    """
    name = str(row.get("Name_ZH", "")).strip()
    city = str(row.get("City_ZH", "")).strip()
    labels = str(row.get("Label_ZH", "")).strip()
    lat = row.get("Latitude_GCJ02")
    lng = row.get("Longitude_GCJ02")

    if not name:
        return ""

    # 基础描述
    text = f"{name}"

    # 添加城市信息
    if city:
        text += f"位于{city}"

    # 添加标签信息
    if labels and labels != "nan":
        text += f"，是一个{labels}类型的景点"
    else:
        text += "，是一个风景名胜"

    # 添加坐标信息
    if pd.notna(lat) and pd.notna(lng):
        text += f"。地理位置：纬度{lat}，经度{lng}"

    # 添加标签关键词增强检索
    if labels and labels != "nan" and ";" in labels:
        label_list = [l.strip() for l in labels.split(";") if l.strip()]
        if len(label_list) > 1:
            text += f"。特色标签：{', '.join(label_list)}"

    return text


def get_embeddings_batch(texts: list) -> list:
    """
    批量获取文本向量
    支持智谱 AI Embedding API
    """
    url = f"{EMBEDDING_API_BASE}/embeddings"
    headers = {
        "Authorization": f"Bearer {EMBEDDING_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": EMBEDDING_MODEL,
        "input": texts
    }

    for attempt in range(MAX_RETRIES):
        try:
            response = requests.post(url, headers=headers, json=payload, timeout=60)
            response.raise_for_status()
            data = response.json()

            # 解析响应 - 兼容不同 API 格式
            embeddings = [None] * len(texts)

            if "data" in data:
                # OpenAI / 智谱 AI 格式
                for item in data["data"]:
                    idx = item.get("index", 0)
                    embeddings[idx] = item["embedding"]
            elif "embeddings" in data:
                # 部分其他 API 格式
                for idx, item in enumerate(data["embeddings"]):
                    embeddings[idx] = item.get("embedding", item)

            # 检查是否所有向量都获取成功
            if None in embeddings:
                raise Exception(f"部分向量获取失败: {embeddings.count(None)} 个为空")

            return embeddings

        except Exception as e:
            print(f"  获取向量失败 (尝试 {attempt+1}/{MAX_RETRIES}): {e}")
            if attempt < MAX_RETRIES - 1:
                time.sleep(3)

    raise Exception("批量获取向量失败，请检查 API 配置或网络连接")


def load_progress() -> dict:
    """加载导入进度"""
    if PROGRESS_FILE.exists():
        with open(PROGRESS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"last_index": 0, "success_count": 0, "failed_ids": []}


def save_progress(progress: dict):
    """保存导入进度"""
    PROGRESS_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(PROGRESS_FILE, "w", encoding="utf-8") as f:
        json.dump(progress, f, ensure_ascii=False, indent=2)


# ==============================================================================
# 主逻辑
# ==============================================================================

def import_poi_data():
    """导入 POI 数据到向量数据库"""
    add_adapters()

    print("=" * 60)
    print("POI 景点数据导入脚本")
    print("=" * 60)
    print(f"CSV路径: {CSV_FILE_PATH}")
    print(f"数据库: {DB_CONFIG['host']}:{DB_CONFIG['port']}/{DB_CONFIG['dbname']}")
    print(f"API地址: {EMBEDDING_API_BASE}")
    print(f"模型: {EMBEDDING_MODEL}")
    print(f"批处理大小: {BATCH_SIZE}")
    print("=" * 60)

    # 检查文件
    if not os.path.exists(CSV_FILE_PATH):
        print(f"找不到文件: {CSV_FILE_PATH}")
        return

    # 加载数据
    print("\n正在加载 CSV 数据...")
    df = pd.read_csv(CSV_FILE_PATH)
    df = df.fillna("")
    total_rows = len(df)
    print(f"成功加载数据集，共 {total_rows} 条数据")

    # 加载进度
    progress = load_progress()
    start_index = progress["last_index"]
    print(f"从第 {start_index + 1} 条继续导入...")

    # 连接数据库
    conn = psycopg2.connect(**DB_CONFIG)
    cursor = conn.cursor()

    try:
        # 准备批量数据
        batch_data = []
        batch_texts = []

        for index in range(start_index, total_rows):
            row = df.iloc[index]
            poi_id = str(row.get("Encrypted_ID", "")).strip()

            if not poi_id:
                continue

            # 检查是否已导入
            cursor.execute("SELECT id FROM poi_attractions WHERE poi_id = %s", (poi_id,))
            if cursor.fetchone():
                print(f"[{index+1}/{total_rows}] 景点 {poi_id} 已存在，跳过")
                continue

            # 构建检索文本
            chunk_text = build_searchable_text(row)
            if not chunk_text:
                continue

            batch_data.append({
                "poi_id": poi_id,
                "name_zh": str(row.get("Name_ZH", "")).strip(),
                "name_en": str(row.get("Name_EN", "")).strip(),
                "city_zh": str(row.get("City_ZH", "")).strip(),
                "city_en": str(row.get("City_EN", "")).strip(),
                "latitude": row.get("Latitude_GCJ02") if pd.notna(row.get("Latitude_GCJ02")) else None,
                "longitude": row.get("Longitude_GCJ02") if pd.notna(row.get("Longitude_GCJ02")) else None,
                "label_zh": str(row.get("Label_ZH", "")).strip(),
                "label_en": str(row.get("Label_EN", "")).strip(),
                "chunk_text": chunk_text
            })
            batch_texts.append(chunk_text)

            # 批量处理
            if len(batch_data) >= BATCH_SIZE:
                process_batch(cursor, conn, batch_data, batch_texts, index, total_rows, progress)
                batch_data = []
                batch_texts = []
                time.sleep(BATCH_DELAY)

        # 处理剩余数据
        if batch_data:
            process_batch(cursor, conn, batch_data, batch_texts, total_rows - 1, total_rows, progress)

        conn.commit()
        print(f"\n导入完成！共成功处理 {progress['success_count']} 条数据")

        if progress["failed_ids"]:
            print(f"失败 {len(progress['failed_ids'])} 条，ID: {progress['failed_ids'][:10]}...")

    except Exception as e:
        print(f"\n执行过程中发生错误: {e}")
        conn.rollback()
        raise
    finally:
        cursor.close()
        conn.close()
        save_progress(progress)


def process_batch(cursor, conn, batch_data, batch_texts, current_index, total_rows, progress):
    """处理一批数据"""
    try:
        # 批量获取向量
        print(f"[{current_index+1}/{total_rows}] 正在获取 {len(batch_texts)} 条向量...")
        embeddings = get_embeddings_batch(batch_texts)

        # 插入数据库
        for i, data in enumerate(batch_data):
            if embeddings[i] is None:
                print(f"  警告: 景点 {data['poi_id']} 向量为空，跳过")
                progress["failed_ids"].append(data["poi_id"])
                continue

            # 插入景点基础信息
            cursor.execute("""
                INSERT INTO poi_attractions
                (poi_id, name_zh, name_en, city_zh, city_en, latitude, longitude, label_zh, label_en)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id
            """, (
                data["poi_id"], data["name_zh"], data["name_en"],
                data["city_zh"], data["city_en"],
                data["latitude"], data["longitude"],
                data["label_zh"], data["label_en"]
            ))
            attraction_id = cursor.fetchone()[0]

            # 插入向量数据
            cursor.execute("""
                INSERT INTO poi_attraction_chunks
                (attraction_id, chunk_text, embedding)
                VALUES (%s, %s, %s)
            """, (attraction_id, data["chunk_text"], embeddings[i]))

            progress["success_count"] += 1

        # 更新进度
        progress["last_index"] = current_index + 1
        conn.commit()
        save_progress(progress)

        print(f"  已提交 {progress['success_count']} 条数据")

    except Exception as e:
        print(f"  批处理失败: {e}")
        raise


if __name__ == "__main__":
    import_poi_data()
