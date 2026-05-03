# Chroma + 远程模型 API RAG

本目录提供两步最小闭环：
1. 用现有小红书爬虫采集并写入 Chroma
2. 用远程模型 API 做向量化与问答生成

## 依赖
- 可用的远程模型 API（OpenAI 兼容协议）
- Chroma 使用本地持久化目录，不需要额外数据库

## 环境变量
全局配置位置：`backend/.env`（由 `app/core/config.py` 读取）

可在 `backend/.env` 中配置：
- `CHROMA_PERSIST_DIR`（默认 `backend/data/chroma`）
- `CHROMA_COLLECTION`（默认 `rag_xhs_notes`）
- `EMBEDDING_PROVIDER`（`openai` 或 `dashscope`）
- `DASHSCOPE_API_KEY`（阿里云百炼 API Key）
- `DASHSCOPE_EMBEDDING_MODEL`（默认 `text-embedding-v2`）
- `OPENAI_API_KEY`（远程模型 API Key，用于问答）
- `OPENAI_API_BASE`（远程模型 API Base，OpenAI 兼容）
- `OPENAI_MODEL`（问答模型）
- `OPENAI_EMBEDDING_MODEL`（向量化模型，若 `EMBEDDING_PROVIDER=openai`）
- `OPENAI_TEMPERATURE`（默认 `0.7`）
- `OPENAI_TIMEOUT`（默认 `300`）

## 入库
```bash
python backend/scripts/rag_pgvector/ingest_xhs_to_pgvector.py --keyword "北京旅游" --max-notes 20
```

## 检索问答
```bash
python backend/scripts/rag_pgvector/ask_rag.py --question "北京三日游怎么安排" --top-k 5
```

## 可选建议
- 大批量入库后可以定期清理旧集合或分主题建立多个集合
- 想更细粒度可调小 `--chunk-size` 并适当增大 `--chunk-overlap`
