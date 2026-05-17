-- 必须放在最前面，强制客户端使用 UTF-8 编码
SET client_encoding = 'UTF8';

-- ==============================================================================
-- POI 景点向量数据库初始化脚本 (PostgreSQL + pgvector)
-- 适用数据集：POIs_V2.csv (国内景点基础表，约 23736 条)
-- ==============================================================================

-- 1. 确保安装并启用 pgvector 插件
CREATE EXTENSION IF NOT EXISTS vector;

-- 2. 创建景点基础信息表
CREATE TABLE IF NOT EXISTS poi_attractions (
    id SERIAL PRIMARY KEY,
    poi_id VARCHAR(50) NOT NULL,           -- 原始景点ID (Encrypted_ID)
    name_zh VARCHAR(200) NOT NULL,         -- 中文名
    name_en VARCHAR(200),                  -- 英文名
    city_zh VARCHAR(100),                  -- 所属城市(中文)
    city_en VARCHAR(100),                  -- 所属城市(英文)
    latitude DECIMAL(10, 8),               -- 纬度 (GCJ02坐标系)
    longitude DECIMAL(11, 8),              -- 经度 (GCJ02坐标系)
    label_zh VARCHAR(500),                 -- 中文标签 (如：博物馆;公园)
    label_en VARCHAR(500),                 -- 英文标签
    source VARCHAR(50) DEFAULT 'POIs_V2',  -- 数据来源
    rating FLOAT DEFAULT 0.0,              -- 景点评分 (0-5分，来自高德API)
    popularity_score FLOAT DEFAULT 0.0,    -- 热度评分 (0-100分)
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 3. 创建景点向量检索表
CREATE TABLE IF NOT EXISTS poi_attraction_chunks (
    id SERIAL PRIMARY KEY,
    attraction_id INTEGER NOT NULL REFERENCES poi_attractions(id) ON DELETE CASCADE,
    chunk_text TEXT NOT NULL,              -- 可检索文本
    embedding vector(1024),                -- 向量 (维度取决于 Embedding 模型)
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 4. 为向量字段创建 HNSW 索引 (加速相似度检索)
CREATE INDEX IF NOT EXISTS poi_chunks_embedding_idx
ON poi_attraction_chunks USING hnsw (embedding vector_cosine_ops);

-- 5. 为城市字段创建索引 (加速按城市过滤)
CREATE INDEX IF NOT EXISTS poi_attractions_city_idx
ON poi_attractions(city_zh);

-- 6. 为景点ID创建唯一索引 (防止重复导入)
CREATE UNIQUE INDEX IF NOT EXISTS poi_attractions_poi_id_idx
ON poi_attractions(poi_id);

-- 7. 为热度字段创建索引 (加速热度排序)
CREATE INDEX IF NOT EXISTS poi_attractions_rating_idx
ON poi_attractions(rating DESC);

CREATE INDEX IF NOT EXISTS poi_attractions_popularity_idx
ON poi_attractions(popularity_score DESC);

-- 8. 如果表已存在，添加热度字段（兼容已有数据）
-- 注意：如果字段已存在会报错，可以忽略
-- ALTER TABLE poi_attractions ADD COLUMN IF NOT EXISTS rating FLOAT DEFAULT 0.0;
-- ALTER TABLE poi_attractions ADD COLUMN IF NOT EXISTS popularity_score FLOAT DEFAULT 0.0;

-- ==============================================================================
-- 使用说明:
-- 1. 在 PostgreSQL 客户端 (Navicat / DBeaver / DataGrip) 中执行此文件
-- 2. 或使用命令行: psql -U postgres -d skyroam -f database/poi_pgvector_init.sql
-- ==============================================================================