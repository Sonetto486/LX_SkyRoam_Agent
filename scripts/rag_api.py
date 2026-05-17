import os
import sys
import json
import asyncio
import pickle
import numpy as np
import re
from pathlib import Path

# 加载 .env 文件
try:
    from dotenv import load_dotenv
    env_path = Path(__file__).parent.parent / "backend" / ".env"
    if env_path.exists():
        load_dotenv(env_path)
except:
    pass

INDEX_DIR = Path(__file__).parent.parent / "data" / "rag_store"


def load_vectorizer():
    vectorizer_path = INDEX_DIR / "vectorizer.pkl"
    if vectorizer_path.exists():
        with open(vectorizer_path, 'rb') as f:
            return pickle.load(f)
    return None


def search_with_tfidf(query: str, k: int = 5):
    import numpy as np
    import json
    
    vectors_path = INDEX_DIR / "vectors.npy"
    metadata_path = INDEX_DIR / "metadata.json"
    
    if not vectors_path.exists() or not metadata_path.exists():
        return []
    
    vectors = np.load(vectors_path)
    with open(metadata_path, 'r', encoding='utf-8') as f:
        metadata = json.load(f)
    
    vectorizer = load_vectorizer()
    if vectorizer is None:
        return []
    
    query_vec = vectorizer.transform([query]).toarray().astype(np.float32)
    norm = np.linalg.norm(query_vec)
    
    if norm == 0:
        words = re.findall(r'[\u4e00-\u9fff]+', query)
        if words:
            new_query = ' '.join(words[:5])
            query_vec = vectorizer.transform([new_query]).toarray().astype(np.float32)
            norm = np.linalg.norm(query_vec)
    
    if norm == 0:
        return []
    
    query_vec = query_vec / norm
    similarities = np.dot(vectors, query_vec.T).flatten()
    top_indices = np.argsort(similarities)[-k:][::-1]
    
    results = []
    for idx in top_indices:
        if similarities[idx] > 0.1:
            results.append({
                "doc": metadata[idx],
                "similarity": float(similarities[idx])
            })
    
    return results


def build_marked_prompt(question: str, results: list) -> str:
    """构建带标识的提示词，要求 AI 标注景点/餐馆"""
    
    refs = []
    for i, r in enumerate(results, 1):
        doc = r["doc"]
        title = doc.get("title", "")
        content = doc.get("desc", doc.get("content", ""))[:600]
        tags = doc.get("tags", "")
        
        refs.append(f"""
【参考{i}】{title}
{content}
标签：{tags}
""")
    
    prompt = f"""你是一个经常旅游、喜欢分享的旅行达人。请根据以下小红书攻略内容，用自然、口语化的方式回答用户的问题。

用户问：{question}

参考的小红书笔记：
{''.join(refs)}

【重要】回答格式要求：
1. **景点/景区**：用 `[景点]景点名称[景点]` 的格式包裹，例如：`[景点]故宫[景点]`
2. **餐馆/美食店**：用 `[餐馆]餐馆名称[餐馆]` 的格式包裹，例如：`[餐馆]四季民福烤鸭店[餐馆]`
3. **酒店/民宿**：用 `[酒店]酒店名称[酒店]` 的格式包裹
4. 普通描述内容不需要加标识

示例回答格式：
"我觉得 [景点]故宫[景点] 真的很值得去！从午门进，逛三大殿和西六宫，大概3-4小时。中午可以去 [餐馆]四季民福[餐馆] 吃烤鸭，他们家的酥皮烤鸭超赞！如果预算有限，可以住 [酒店]青年旅舍[酒店] 省钱。"

回答要求：
- 用口语化的语气，像朋友聊天
- 可以适当用表情符号
- 不要用"1. 2. 3."列表格式
- 确保每个提到的实体（景点、餐馆、酒店）都有对应的标识

请回答："""
    
    return prompt


def generate_with_dashscope(prompt: str, max_tokens: int = 800, temperature: float = 0.8) -> str:
    from openai import OpenAI
    
    api_key = os.getenv("DASHSCOPE_API_KEY") or os.getenv("OPENAI_API_KEY")
    api_base = os.getenv("OPENAI_API_BASE", "https://dashscope.aliyuncs.com/compatible-mode/v1")
    model = os.getenv("OPENAI_MODEL", "deepseek-v3")
    
    if not api_key:
        raise RuntimeError("API key not set")
    
    client = OpenAI(api_key=api_key, base_url=api_base)
    
    messages = [
        {"role": "system", "content": "你是旅行分享者，回答要自然亲切。用 [景点]名称[景点] 格式标注景点，[餐馆]名称[餐馆] 标注餐馆。"},
        {"role": "user", "content": prompt},
    ]
    
    response = client.chat.completions.create(
        model=model,
        messages=messages,
        max_tokens=max_tokens,
        temperature=temperature
    )
    
    return response.choices[0].message.content


def extract_marked_entities(text: str):
    """从回答中提取带标识的实体"""
    entities = []
    
    # 提取景点
    attraction_pattern = r'\[景点\](.*?)\[景点\]'
    for match in re.findall(attraction_pattern, text):
        entities.append({
            'type': 'attraction',
            'name': match.strip(),
            'icon': '🏛️'
        })
    
    # 提取餐馆
    restaurant_pattern = r'\[餐馆\](.*?)\[餐馆\]'
    for match in re.findall(restaurant_pattern, text):
        entities.append({
            'type': 'restaurant',
            'name': match.strip(),
            'icon': '🍜'
        })
    
    # 提取酒店
    hotel_pattern = r'\[酒店\](.*?)\[酒店\]'
    for match in re.findall(hotel_pattern, text):
        entities.append({
            'type': 'hotel',
            'name': match.strip(),
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


async def answer_question(question: str, conversation_history: list = None, use_backend_embedding: bool = False) -> dict:
    """异步问答接口，支持对话历史"""
    print(f"📝 处理问题: {question[:50]}...")
    
    try:
        loop = asyncio.get_event_loop()
        
        # 检索
        results = await loop.run_in_executor(None, lambda: search_with_tfidf(question, k=5))
        print(f"📊 检索到 {len(results)} 条结果")
        
        # 构建增强问题（包含对话历史）
        enhanced_question = question
        if conversation_history and len(conversation_history) > 0:
            context = []
            for msg in conversation_history[-4:]:
                role = "用户" if msg.get("role") == "user" else "助手"
                context.append(f"{role}: {msg.get('content', '')}")
            if context:
                enhanced_question = f"对话历史:\n" + "\n".join(context) + f"\n\n当前问题: {question}"
                print(f"📚 添加了 {len(context)} 条对话历史")
        
        # 构建 prompt（这部分需要放在正确的位置）
        if results:
            prompt = build_marked_prompt(enhanced_question, results)  # 注意这里用 enhanced_question
        else:
            print("⚠️ 未检索到相关内容，降级到纯 LLM 回答")
            prompt = f"你是一个旅行分享者。请用自然、口语化的方式回答：{enhanced_question}\n\n注意：用 [景点]名称[景点] 标注景点，[餐馆]名称[餐馆] 标注餐馆。"
        
        # 调用 LLM
        answer = None
        entities = []
        
        try:
            answer = await loop.run_in_executor(
                None,
                lambda: generate_with_dashscope(prompt, max_tokens=800, temperature=0.8)
            )
            print(f"✅ LLM 生成回答成功")
            
            entities = extract_marked_entities(answer)
            clean_answer = clean_marked_text(answer)
            
        except Exception as e:
            print(f"❌ LLM 调用失败: {e}")
            clean_answer = f"抱歉，我暂时没找到关于「{question}」的信息。你可以换个问法试试～"
            entities = []
        
        sources = []
        for r in results[:5]:
            doc = r["doc"]
            sources.append({
                "title": doc.get("title", "小红书笔记"),
                "content": doc.get("desc", doc.get("content", ""))[:200],
                "score": r.get("similarity", 0),
                "like_count": doc.get("like_count", 0)
            })
        
        return {
            "answer": clean_answer,
            "raw_answer": answer,
            "entities": entities,
            "sources": sources
        }
        
    except Exception as e:
        print(f"❌ 处理失败: {e}")
        import traceback
        traceback.print_exc()
        return {
            "answer": f"哎呀，处理出错了：{str(e)}。稍后再试试吧～",
            "entities": [],
            "sources": []
        }

try:
    from rag_pipeline import build_prompt_from_docs
except:
    pass
