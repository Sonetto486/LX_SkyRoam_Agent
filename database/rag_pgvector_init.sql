-- ==============================================================================
-- SkyRoam RAG 向量数据库初始化脚本 (PostgreSQL + pgvector)
-- 适用数据集：游记/攻略 Excel (包含 目的地, 交通, 住宿, 景点, 美食, 贴士, 感悟)
-- ==============================================================================

-- 1. 确保安装并启用 pgvector 插件
CREATE EXTENSION IF NOT EXISTS vector;

-- 2. 创建主表：存储游记结构化原文
-- 字段设计完全对齐我们收集到的 800+ 条 Excel 数据集
CREATE TABLE IF NOT EXISTS xhs_notes (
    id SERIAL PRIMARY KEY,
    destination VARCHAR(100) NOT NULL,      -- 目的地
    transport_info TEXT,                    -- 交通安排
    accommodation_info TEXT,                -- 住宿推荐
    must_visit_spots TEXT,                  -- 必打卡景点
    food_recommendations TEXT,              -- 美食推荐
    practical_tips TEXT,                    -- 实用小贴士
    travel_feelings TEXT,                   -- 旅行感悟
    source_type VARCHAR(50) DEFAULT 'excel',-- 数据来源标记
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 3. 创建向量分表：存储切片后的文本及其向量
CREATE TABLE IF NOT EXISTS xhs_note_chunks (
    id SERIAL PRIMARY KEY,
    note_id INTEGER NOT NULL REFERENCES xhs_notes(id) ON DELETE CASCADE,
    
    -- 记录这个切片属于哪个信息维度（比如：'transport', 'food', 'spots'，或混合 'mixed'）
    -- 这样在检索时，如果用户问“去北京吃什么”，可以针对性加上 chunk_type = 'food' 的过滤
    chunk_type VARCHAR(50),     
    
    -- 切块后的纯文本段落（大模型检索出来的就是这段文字）
    chunk_text TEXT NOT NULL,   
    
    -- 向量化数组。
    -- 注意：此处的 1024 是向量维度，取决于你随后用的 Embedding 模型。
    -- 比如：BGE-m3 是 1024 维，OpenAI text-embedding-3-small 是 1536 维，m3e-base 是 768 维。
    -- 请组员根据最终调用的向量模型，修改这个数值。
    embedding vector(1024),     
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 4. 为向量字段创建 HNSW 索引（极其重要，用于加速海量数据的余弦相似度检索）
CREATE INDEX IF NOT EXISTS xhs_note_chunks_embedding_idx 
ON xhs_note_chunks USING hnsw (embedding vector_cosine_ops);

-- ==============================================================================
-- 使用说明:
-- 1. 在你的 PostgreSQL 客户端 (Navicat / DBeaver / DataGrip) 中执行此文件即可。
-- 2. 注意确认你的 PostgreSQL 镜像/容器 已经预装了 pgvector。
--    如果没有，推荐使用 Docker 镜像: ankane/pgvector:latest
-- ==============================================================================