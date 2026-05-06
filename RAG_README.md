# RAG向量化数据库使用指南

## 概述

本项目使用PostgreSQL + pgvector实现RAG（检索增强生成）功能，用于在生成旅行计划时检索相关的旅行攻略数据。

## 系统架构

```
Excel数据 → import_rag_dataset.py → PostgreSQL (xhs_notes + xhs_note_chunks)
                                          ↓
用户请求 → RAG检索服务 → 向量相似度搜索 → 返回相关攻略
                                          ↓
                                    AI生成旅行计划
```

## 使用步骤

### 第一步：初始化数据库

在PostgreSQL中执行建表语句：

```bash
psql -U postgres -d skyroam -f database/rag_pgvector_init.sql
```

或在数据库管理工具（如Navicat、DBeaver）中执行 `database/rag_pgvector_init.sql` 文件。

### 第二步：导入数据

修改 `scripts/import_rag_dataset.py` 中的配置（已修改）：

```python
EXCEL_FILE_PATH = r"E:\prog\gongChengShiXun\LX_SkyRoam_Agent\travel_guide.xlsx"
EMBEDDING_API_BASE = "https://api.siliconflow.cn/v1"
EMBEDDING_API_KEY = "sk-akxmmyreibwsszkfvxsfnmnifgbaoxswrghligcjnygvgayo"
EMBEDDING_MODEL = "Qwen/Qwen3-Embedding-0.6B"
```

运行导入脚本：

```bash
cd scripts
python import_rag_dataset.py
```

### 第三步：测试RAG检索

运行测试脚本验证检索功能：

```bash
python test_rag.py
```

### 第四步：在旅行计划生成中使用

RAG检索已集成到 `backend/app/services/plan_generator.py` 的景点方案生成流程中。

当用户生成旅行计划时，系统会自动：
1. 根据目的地检索相关攻略
2. 将检索结果作为上下文提供给AI
3. AI综合分析后生成旅行方案

## 数据库表结构

### xhs_notes（游记主表）

| 字段 | 类型 | 说明 |
|------|------|------|
| id | SERIAL | 主键 |
| destination | VARCHAR(100) | 目的地 |
| transport_info | TEXT | 交通安排 |
| accommodation_info | TEXT | 住宿推荐 |
| must_visit_spots | TEXT | 必打卡景点 |
| food_recommendations | TEXT | 美食推荐 |
| practical_tips | TEXT | 实用小贴士 |
| travel_feelings | TEXT | 旅行感悟 |
| source_type | VARCHAR(50) | 数据来源 |
| created_at | TIMESTAMP | 创建时间 |

### xhs_note_chunks（向量分表）

| 字段 | 类型 | 说明 |
|------|------|------|
| id | SERIAL | 主键 |
| note_id | INTEGER | 关联游记ID |
| chunk_type | VARCHAR(50) | 切片类型 |
| chunk_text | TEXT | 文本内容 |
| embedding | vector(1024) | 向量表示 |
| created_at | TIMESTAMP | 创建时间 |

## API配置

RAG检索服务使用以下环境变量（可选，有默认值）：

```bash
RAG_EMBEDDING_API_BASE=https://api.siliconflow.cn/v1
RAG_EMBEDDING_API_KEY=your-api-key
RAG_EMBEDDING_MODEL=Qwen/Qwen3-Embedding-0.6B
RAG_TOP_K=5
RAG_SIMILARITY_THRESHOLD=0.5
```

## 注意事项

1. **向量维度**：建表时设置的向量维度为1024，需确保使用的Embedding模型输出维度一致
2. **API配额**：向量化API有调用限制，大量数据导入时注意控制速率
3. **数据库连接**：确保PostgreSQL已安装pgvector扩展
4. **数据质量**：导入前检查Excel数据格式，确保字段名称正确

## 故障排查

### 问题1：找不到相关结果

- 检查数据库是否有数据：`SELECT COUNT(*) FROM xhs_note_chunks;`
- 检查向量是否正确生成：`SELECT id, chunk_text FROM xhs_note_chunks LIMIT 5;`

### 问题2：API调用失败

- 检查API Key是否正确
- 检查网络连接
- 查看API配额是否用尽

### 问题3：向量维度不匹配

- 确认Embedding模型的输出维度
- 修改建表语句中的向量维度：`embedding vector(维度数)`

## 相关文件

- `scripts/import_rag_dataset.py` - 数据导入脚本
- `database/rag_pgvector_init.sql` - 建表语句
- `backend/app/services/rag_retriever.py` - RAG检索服务
- `backend/app/services/plan_generator.py` - 旅行计划生成（已集成RAG）
- `test_rag.py` - 测试脚本