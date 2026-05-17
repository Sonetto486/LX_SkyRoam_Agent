"""
RAG MVP pipeline (preprocess -> vectorize -> retrieve -> generate)

Usage examples:
  # install deps for this script
  pip install -r scripts/requirements-rag.txt

  # build index from notes.csv and comments.csv
  python scripts/rag_pipeline.py build-index --notes notes.csv --comments comments.csv --output-dir data/rag_store

  # query
  python scripts/rag_pipeline.py query --query "珠海东澳岛值得去吗" --city 珠海 --k 5 --index-dir data/rag_store

Environment:
  - If you want LLM generation, set `OPENAI_API_KEY` and optionally `OPENAI_API_BASE` and `OPENAI_MODEL`.
  - This script uses `sentence-transformers` + `faiss` by default to build a local vector index.

"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from dataclasses import dataclass, asdict
from typing import List, Dict, Optional, Tuple

import numpy as np
import pandas as pd

try:
    from sentence_transformers import SentenceTransformer
except Exception:
    SentenceTransformer = None

try:
    import faiss
except Exception:
    faiss = None

try:
    import openai
except Exception:
    openai = None


@dataclass
class NoteDoc:
    id: str
    city: Optional[str]
    category: Optional[str]
    quality_score: float
    content_text: str
    publish_time: Optional[str]
    key_comments: List[Dict]
    metadata: Dict


def extract_city(text: str, known_cities: Optional[List[str]] = None) -> Optional[str]:
    if not text:
        return None
    if known_cities is None:
        # a short default list; you can replace with a full city list
        known_cities = [
            "北京",
            "上海",
            "广州",
            "深圳",
            "珠海",
            "杭州",
            "成都",
            "重庆",
            "西安",
        ]
    for city in known_cities:
        if city in text:
            return city
    return None


def classify_category(tags_text: str) -> str:
    if not tags_text:
        return "other"
    t = tags_text.lower()
    if any(x in t for x in ["美食", "吃", "餐厅", "小吃"]):
        return "food"
    if any(x in t for x in ["酒店", "住宿", "民宿"]):
        return "hotel"
    if any(x in t for x in ["景点", "玩法", "景区"]):
        return "attraction"
    if any(x in t for x in ["避坑", "踩雷", "注意"]):
        return "warning"
    return "other"


def compute_quality_score(row: Dict) -> float:
    like = float(row.get("like_count") or 0)
    collect = float(row.get("collect_count") or 0)
    comment = float(row.get("comment_count") or 0)
    return like * 0.5 + collect * 0.3 + comment * 0.2


def process_note(row: Dict) -> NoteDoc:
    content = "".join([str(row.get(k) or "") for k in ["title", "content"]])
    tags = row.get("tags") or ""
    city = extract_city(content + tags)
    category = classify_category(tags)
    quality_score = compute_quality_score(row)
    key_comments = []
    return NoteDoc(
        id=str(row.get("note_id") or row.get("id") or ""),
        city=city,
        category=category,
        quality_score=quality_score,
        content_text=(str(row.get("title") or "") + "\n" + str(row.get("content") or "")).strip(),
        publish_time=row.get("publish_time"),
        key_comments=key_comments,
        metadata={"source_row": row},
    )


def enrich_with_comments(note: NoteDoc, comments_for_note: List[Dict]) -> NoteDoc:
    high_value = [
        c
        for c in comments_for_note
        if (int(c.get("like_count") or 0) > 10)
        or ("避雷" in (c.get("comment_content") or ""))
        or ("推荐" in (c.get("comment_content") or ""))
    ]
    note.key_comments = high_value
    return note


def build_embeddings(model_name: str, texts: List[str]) -> np.ndarray:
    # 优先尝试使用后端已有的 embedding 方法（backend/scripts/rag_pgvector/ingest_xhs_to_pgvector.py）
    try:
        import importlib.util
        backend_module_path = os.path.join(os.path.dirname(__file__), "..", "backend", "scripts", "rag_pgvector", "ingest_xhs_to_pgvector.py")
        backend_module_path = os.path.abspath(backend_module_path)
        if os.path.exists(backend_module_path):
            spec = importlib.util.spec_from_file_location("ingest_xhs_to_pgvector", backend_module_path)
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)  # type: ignore
            # build a minimal config object similar to EmbeddingConfig if available
            try:
                cfg = mod.load_embedding_config()
                embeddings = mod.embed_texts(texts, cfg)
                return np.asarray(embeddings, dtype=np.float32)
            except Exception:
                # fall through to local embeddings
                pass
    except Exception:
        pass

    # 回退到本地 sentence-transformers
    if SentenceTransformer is None:
        raise RuntimeError("sentence-transformers is not installed; see scripts/requirements-rag.txt")
    model = SentenceTransformer(model_name)
    emb = model.encode(texts, show_progress_bar=True, convert_to_numpy=True)
    return emb


def build_faiss_index(vectors: np.ndarray, index_path: str) -> None:
    if faiss is None:
        raise RuntimeError("faiss is not installed; see scripts/requirements-rag.txt")
    dim = vectors.shape[1]
    index = faiss.IndexFlatIP(dim)
    # normalize for cosine-like inner product
    faiss.normalize_L2(vectors)
    index.add(vectors)
    faiss.write_index(index, index_path)


def load_faiss_index(index_path: str, dim: int):
    if faiss is None:
        raise RuntimeError("faiss is not installed; see scripts/requirements-rag.txt")
    index = faiss.read_index(index_path)
    return index


def save_metadata(metadata: List[Dict], path: str):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(metadata, f, ensure_ascii=False, indent=2)


def load_metadata(path: str) -> List[Dict]:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def hybrid_search(
    query: str,
    index_dir: str,
    k: int = 5,
    city: Optional[str] = None,
    embed_model: str = "paraphrase-multilingual-MiniLM-L12-v2",
):
    meta_path = os.path.join(index_dir, "metadata.json")
    index_path = os.path.join(index_dir, "faiss.index")
    if not os.path.exists(meta_path) or not os.path.exists(index_path):
        raise FileNotFoundError("index not found; run build-index first")
    metadata = load_metadata(meta_path)
    vectors = np.load(os.path.join(index_dir, "vectors.npy"))
    # embed query
    # 尝试使用后端的 embed_query 实现（backend/scripts/rag_pgvector/ask_rag.py），否则回退到本地 sentence-transformers
    q_emb = None
    try:
        import importlib.util
        ask_path = os.path.join(os.path.dirname(__file__), "..", "backend", "scripts", "rag_pgvector", "ask_rag.py")
        ask_path = os.path.abspath(ask_path)
        if os.path.exists(ask_path):
            spec = importlib.util.spec_from_file_location("ask_rag", ask_path)
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)  # type: ignore
            # construct a RemoteModelConfig if load_remote_model_config exists
            try:
                cfg = mod.load_remote_model_config()
                q_emb = mod.embed_query(query, cfg)
                q_emb = np.asarray(q_emb, dtype=np.float32)[None, :]
            except Exception:
                q_emb = None
    except Exception:
        q_emb = None

    if q_emb is None:
        if SentenceTransformer is None:
            raise RuntimeError("sentence-transformers not installed")
        model = SentenceTransformer(embed_model)
        q_emb = model.encode([query], convert_to_numpy=True)
    faiss.normalize_L2(q_emb)
    idx = load_faiss_index(index_path, q_emb.shape[1])
    D, I = idx.search(q_emb, min(k * 3, vectors.shape[0]))
    candidates = []
    for score, idxid in zip(D[0], I[0]):
        if idxid < 0:
            continue
        doc = metadata[idxid]
        # simple city filter
        if city and doc.get("city") and city != doc.get("city"):
            continue
        candidates.append({"doc": doc, "similarity": float(score)})

    # keyword boosting: if query contains tokens matching title/restaurant name, boost
    q_low = query.lower()
    for c in candidates:
        text = (c["doc"].get("content_text") or "").lower()
        boost = 1.0
        if any(tok in text for tok in re.findall(r"[\u4e00-\u9fff]+", q_low)):
            boost += 0.1
        c["final_score"] = c["similarity"] * 0.6 + c["doc"].get("quality_score", 0) * 0.4 * 1e-3

    # dedupe by title/content snippet
    seen = set()
    out = []
    for c in sorted(candidates, key=lambda x: -x.get("final_score", 0)):
        key = (c["doc"].get("id"),)
        if key in seen:
            continue
        seen.add(key)
        out.append(c)
        if len(out) >= k:
            break
    return out


def build_prompt_from_docs(query: str, docs: List[Dict]) -> str:
    """构建带实体标记的提示词"""
    header = "你是一个专业旅行助手，基于下列小红书用户内容回答用户问题。\n请优先引用点赞/收藏高的笔记，并提示避坑信息。\n---\n"
    pieces = []
    for i, d in enumerate(docs, 1):
        doc = d["doc"]
        src = doc.get("metadata", {}).get("source_row", {})
        title = src.get("title") or src.get("note_id")
        pieces.append(f"[{i}] 标题: {title}\n城市: {doc.get('city')}\n得分: {doc.get('quality_score')}\n内容片段: {doc.get('content_text')[:400]}\n评论摘录: {doc.get('key_comments')[:2]}\n---\n")
    
    # 添加实体标记要求
    marking_instruction = """
【重要】回答格式要求：
1. 用口语化的语气，像朋友聊天，可以适当用表情符号
2. 如果提到景点、餐馆、酒店，请在名称前后添加标识符：
   * 景点用 [景点]名称[/景点] 
   * 餐馆用 [餐馆]名称[/餐馆]
   * 酒店用 [酒店]名称[/酒店]
3. 示例："建议去 [景点]故宫[/景点] 逛逛，然后去 [餐馆]四季民福[/餐馆] 吃烤鸭"
4. 要点清晰，包含店名/位置/价格/避坑提示
"""
    
    prompt = (
        header
        + marking_instruction
        + "\n检索到的参考内容：\n"
        + "\n".join(pieces)
        + "\n用户问题：\n"
        + query
        + "\n\n请基于参考内容直接给出实用的回答。"
    )
    return prompt


def generate_with_openai(prompt: str, max_tokens: int = 512, temperature: float = 0.2) -> str:
    if openai is None:
        raise RuntimeError("openai package not installed; please install it to enable LLM generation")
    api_key = os.getenv("OPENAI_API_KEY")
    api_base = os.getenv("OPENAI_API_BASE")
    model = os.getenv("OPENAI_MODEL") or os.getenv("OPENAI_CHAT_MODEL") or "gpt-3.5-turbo"
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY not set in env")
    openai.api_key = api_key
    if api_base:
        openai.api_base = api_base
    # We use ChatCompletions
    messages = [
        {"role": "system", "content": "你是一个专业旅行助手，回答要简洁、有用、引用用户内容时说明来源。"},
        {"role": "user", "content": prompt},
    ]
    resp = openai.ChatCompletion.create(model=model, messages=messages, max_tokens=max_tokens, temperature=temperature)
    return resp.choices[0].message.content


def action_build_index(args):
    notes_path = args.notes
    comments_path = args.comments
    output_dir = args.output_dir
    os.makedirs(output_dir, exist_ok=True)

    df = pd.read_csv(notes_path, dtype=str).fillna("")
    comments = None
    if comments_path and os.path.exists(comments_path):
        comments = pd.read_csv(comments_path, dtype=str).fillna("")
    id_to_comments = {}
    if comments is not None:
        for _, r in comments.iterrows():
            nid = str(r.get("note_id") or r.get("noteId") or "")
            id_to_comments.setdefault(nid, []).append(r.to_dict())

    docs: List[Dict] = []
    texts = []
    for _, r in df.iterrows():
        note = process_note(r.to_dict())
        if note.id and id_to_comments:
            note = enrich_with_comments(note, id_to_comments.get(note.id, []))
        meta = asdict(note)
        docs.append(meta)
        texts.append(note.content_text)

    model_name = args.embed_model
    print(f"Embedding {len(texts)} documents with model {model_name}...")
    emb = build_embeddings(model_name, texts)
    vectors_path = os.path.join(output_dir, "vectors.npy")
    np.save(vectors_path, emb)
    meta_path = os.path.join(output_dir, "metadata.json")
    save_metadata(docs, meta_path)
    index_path = os.path.join(output_dir, "faiss.index")
    build_faiss_index(emb, index_path)
    print("Index built and saved to", output_dir)


def action_query(args):
    results = hybrid_search(args.query, args.index_dir, k=args.k, city=args.city, embed_model=args.embed_model)
    print("Top results:")
    for i, r in enumerate(results, 1):
        print(f"[{i}] id={r['doc'].get('id')}, city={r['doc'].get('city')}, score={r['similarity']}")
    prompt = build_prompt_from_docs(args.query, results)
    print("\n--- PROMPT SENT TO LLM (preview) ---\n")
    print(prompt[:4000])
    if args.generate:
        print("\nCalling LLM...\n")
        out = generate_with_openai(prompt, max_tokens=args.max_tokens, temperature=args.temperature)
        print("\n--- LLM ANSWER ---\n")
        print(out)


def main(argv: Optional[List[str]] = None):
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="cmd")

    p_build = sub.add_parser("build-index")
    p_build.add_argument("--notes", required=True)
    p_build.add_argument("--comments", required=False)
    p_build.add_argument("--output-dir", default="data/rag_store")
    p_build.add_argument("--embed-model", default="paraphrase-multilingual-MiniLM-L12-v2")

    p_q = sub.add_parser("query")
    p_q.add_argument("--query", required=True)
    p_q.add_argument("--index-dir", default="data/rag_store")
    p_q.add_argument("--k", type=int, default=5)
    p_q.add_argument("--city", required=False)
    p_q.add_argument("--embed-model", default="paraphrase-multilingual-MiniLM-L12-v2")
    p_q.add_argument("--generate", action="store_true", help="Call LLM to generate answer; requires OPENAI_API_KEY")
    p_q.add_argument("--max-tokens", dest="max_tokens", type=int, default=512)
    p_q.add_argument("--temperature", type=float, default=0.2)

    args = parser.parse_args(argv)
    if args.cmd == "build-index":
        action_build_index(args)
    elif args.cmd == "query":
        action_query(args)
    else:
        parser.print_help()

# ========== 实体提取相关函数 ==========

def build_entity_extraction_prompt(answer_text: str) -> str:
    """构建第二阶段提示词：从回答中提取实体为JSON格式"""
    
    return f"""请从下面这段旅行推荐文本中，提取所有被推荐的景点、餐馆和酒店。

注意：只需要提取回答中明确推荐的实体，不要提取仅作为参考或背景提到的。

推荐文本：
{answer_text}

请严格按照以下JSON格式输出，不要添加任何其他文字：
{{
    "entities": [
        {{"type": "attraction", "name": "景点名称", "icon": "🏛️"}},
        {{"type": "restaurant", "name": "餐馆名称", "icon": "🍜"}},
        {{"type": "hotel", "name": "酒店名称", "icon": "🏨"}}
    ]
}}

如果没有实体，输出：{{"entities": []}}

现在输出："""


def extract_marked_entities(text: str) -> list:
    """从带标识的文本中提取实体（作为备用方案）"""
    entities = []
    
    # 提取景点
    attraction_pattern = r'\[景点\](.*?)\[/?景点\]'
    for match in re.findall(attraction_pattern, text):
        name = match.strip()
        if name and not any(e['name'] == name and e['type'] == 'attraction' for e in entities):
            entities.append({
                'type': 'attraction',
                'name': name,
                'icon': '🏛️'
            })
    
    # 提取餐馆
    restaurant_pattern = r'\[餐馆\](.*?)\[/?餐馆\]'
    for match in re.findall(restaurant_pattern, text):
        name = match.strip()
        if name and not any(e['name'] == name and e['type'] == 'restaurant' for e in entities):
            entities.append({
                'type': 'restaurant',
                'name': name,
                'icon': '🍜'
            })
    
    # 提取酒店
    hotel_pattern = r'\[酒店\](.*?)\[/?酒店\]'
    for match in re.findall(hotel_pattern, text):
        name = match.strip()
        if name and not any(e['name'] == name and e['type'] == 'hotel' for e in entities):
            entities.append({
                'type': 'hotel',
                'name': name,
                'icon': '🏨'
            })
    
    return entities


def clean_marked_text(text: str) -> str:
    """移除标识符，只保留纯文本用于显示"""
    text = re.sub(r'\[景点\]', '', text)
    text = re.sub(r'\[/景点\]', '', text)
    text = re.sub(r'\[餐馆\]', '', text)
    text = re.sub(r'\[/餐馆\]', '', text)
    text = re.sub(r'\[酒店\]', '', text)
    text = re.sub(r'\[/酒店\]', '', text)
    return text


def parse_entity_extraction_result(text: str) -> list:
    """解析第二阶段的JSON结果"""
    if not text:
        return []
    
    # 清理可能的代码块标记
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"\s*```$", "", cleaned)
    
    try:
        data = json.loads(cleaned)
        if isinstance(data, dict):
            entities_data = data.get("entities", [])
            if isinstance(entities_data, list):
                valid_entities = []
                for item in entities_data:
                    if isinstance(item, dict):
                        entity_type = str(item.get("type", "")).strip().lower()
                        name = str(item.get("name", "")).strip()
                        if entity_type in {"attraction", "restaurant", "hotel"} and name:
                            valid_entities.append({
                                "type": entity_type,
                                "name": name,
                                "icon": item.get("icon") or (
                                    "🏛️" if entity_type == "attraction" else 
                                    "🍜" if entity_type == "restaurant" else "🏨"
                                )
                            })
                return valid_entities
    except (json.JSONDecodeError, KeyError, TypeError):
        pass
    
    return []
# ========== 为 FastAPI 添加的异步接口（两阶段版本）==========
async def answer_question(question: str, use_backend_embedding: bool = False, conversation_history: list = None) -> dict:
    """
    异步问答接口，支持两阶段实体提取
    
    Args:
        question: 用户问题
        use_backend_embedding: 是否使用后端embedding（暂未实现）
        conversation_history: 对话历史
    
    Returns:
        dict: {
            "answer": str,      # 清洗后的纯文本回答
            "raw_answer": str,  # 原始带标记的回答
            "entities": list,   # 提取的实体列表
            "sources": list     # 参考来源
        }
    """
    import asyncio
    
    loop = asyncio.get_event_loop()
    index_dir = os.path.join(os.path.dirname(__file__), "..", "data", "rag_store")
    
    if not os.path.exists(index_dir):
        return {
            "answer": f"RAG索引不存在，请先运行: python scripts/rag_pipeline.py build-index --notes <notes.csv> --comments <comments.csv> --output-dir data/rag_store",
            "entities": [],
            "raw_answer": "",
            "sources": []
        }
    
    try:
        # 第一阶段：检索相关内容
        enhanced_question = question
        if conversation_history and len(conversation_history) > 0:
            context = []
            for msg in conversation_history[-4:]:
                role = "用户" if msg.get("role") == "user" else "助手"
                context.append(f"{role}: {msg.get('content', '')}")
            if context:
                enhanced_question = f"对话历史:\n" + "\n".join(context) + f"\n\n当前问题: {question}"
        
        # 调用同步的 hybrid_search
        results = await loop.run_in_executor(
            None,
            lambda: hybrid_search(
                query=enhanced_question,
                index_dir=index_dir,
                k=5,
                city=None,
                embed_model="paraphrase-multilingual-MiniLM-L12-v2"
            )
        )
        
        if not results:
            return {
                "answer": f"抱歉，没有找到关于「{question}」的相关内容。试试换个问法？",
                "entities": [],
                "raw_answer": "",
                "sources": []
            }
        
        # 第二阶段：生成带标记的回答
        first_prompt = build_prompt_from_docs(enhanced_question, results)
        
        try:
            # 第一次调用：生成带标识的回答（提高温度让回答更自然）
            raw_answer = await loop.run_in_executor(
                None,
                lambda: generate_with_openai(first_prompt, max_tokens=800, temperature=0.8)
            )
            
            # 第三阶段：从回答中提取实体
            second_prompt = build_entity_extraction_prompt(raw_answer)
            extraction_text = await loop.run_in_executor(
                None,
                lambda: generate_with_openai(second_prompt, max_tokens=300, temperature=0.3)
            )
            
            # 解析提取结果
            entities = parse_entity_extraction_result(extraction_text)
            
            # 如果JSON解析失败，使用正则备用方案
            if not entities:
                print("⚠️ JSON解析失败，使用正则备用方案")
                entities = extract_marked_entities(raw_answer)
            
            # 清理标识符，得到最终显示文本
            clean_answer = clean_marked_text(raw_answer)
            
            print(f"📋 提取到 {len(entities)} 个实体: {[e['name'] for e in entities]}")
            
        except Exception as e:
            print(f"❌ LLM 调用失败: {e}")
            # 如果LLM不可用，返回检索到的内容
            clean_answer = f"基于检索到的 {len(results)} 条小红书攻略：\n\n"
            for i, r in enumerate(results, 1):
                doc = r["doc"]
                clean_answer += f"\n{i}. {doc.get('content_text', '')[:300]}...\n"
            entities = []
            raw_answer = clean_answer
        
        # 格式化来源
        sources = []
        for r in results[:5]:
            doc = r["doc"]
            sources.append({
                "title": doc.get("metadata", {}).get("source_row", {}).get("title", "未命名"),
                "content": doc.get("content_text", "")[:200],
                "score": r.get("similarity", 0),
                "like_count": doc.get("quality_score", 0)
            })
        
        return {
            "answer": clean_answer,
            "raw_answer": raw_answer,
            "entities": entities,
            "sources": sources
        }
        
    except Exception as e:
        print(f"❌ 处理失败: {e}")
        import traceback
        traceback.print_exc()
        return {
            "answer": f"处理失败: {str(e)}",
            "entities": [],
            "raw_answer": "",
            "sources": []
        }


if __name__ == "__main__":
    main()
