# Chroma + Ollama 本地RAG

本目录提供两步最小闭环：
1. 用现有小红书爬虫采集并写入 Chroma
2. 用本地 Ollama 模型检索+生成回答

## 依赖
- 本地 Ollama 正常运行（默认 `http://localhost:11434`）
- 已拉取模型：`nomic-embed-text`、`deepseek-r1:14b`
- Chroma 使用本地持久化目录，不需要额外数据库

## 环境变量
可在 `backend/.env` 中配置：
- `CHROMA_PERSIST_DIR`（默认 `backend/data/chroma`）
- `CHROMA_COLLECTION`（默认 `rag_xhs_notes`）
- `OLLAMA_BASE_URL`（默认 `http://localhost:11434`）
- `OLLAMA_EMBED_MODEL`（默认 `nomic-embed-text`）
- `OLLAMA_CHAT_MODEL`（默认 `deepseek-r1:14b`）
- `OLLAMA_TEMPERATURE`（默认 `0.3`）

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
