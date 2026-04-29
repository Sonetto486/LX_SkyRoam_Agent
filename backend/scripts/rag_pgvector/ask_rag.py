import argparse
import json
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import List, Dict, Any

import chromadb
import httpx
from dotenv import load_dotenv

SCRIPT_DIR = Path(__file__).resolve().parent
BACKEND_DIR = SCRIPT_DIR.parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))


@dataclass
class ChromaConfig:
    persist_dir: Path
    collection_name: str


@dataclass
class OllamaConfig:
    base_url: str
    embed_model: str
    chat_model: str
    temperature: float


def load_chroma_config() -> ChromaConfig:
    persist_dir = Path(os.getenv("CHROMA_PERSIST_DIR", str(BACKEND_DIR / "data" / "chroma")))
    collection_name = os.getenv("CHROMA_COLLECTION", "rag_xhs_notes")
    return ChromaConfig(persist_dir=persist_dir, collection_name=collection_name)


def load_ollama_config() -> OllamaConfig:
    base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    embed_model = os.getenv("OLLAMA_EMBED_MODEL", "nomic-embed-text")
    chat_model = os.getenv("OLLAMA_CHAT_MODEL", "deepseek-r1:14b")
    temperature = float(os.getenv("OLLAMA_TEMPERATURE", "0.3"))
    return OllamaConfig(
        base_url=base_url,
        embed_model=embed_model,
        chat_model=chat_model,
        temperature=temperature,
    )


def embed_query(query: str, config: OllamaConfig) -> List[float]:
    embeddings_url = f"{config.base_url}/api/embeddings"
    embed_url = f"{config.base_url}/api/embed"
    with httpx.Client(timeout=60) as client:
        response = client.post(embeddings_url, json={"model": config.embed_model, "prompt": query})
        if response.status_code == 404:
            response = client.post(embed_url, json={"model": config.embed_model, "input": query})
        response.raise_for_status()
        data = response.json()
        if "embedding" in data:
            return data["embedding"]
        if "embeddings" in data and data["embeddings"]:
            return data["embeddings"][0]
        raise ValueError("Ollama embedding response missing embedding data")


def get_collection(chroma_config: ChromaConfig):
    chroma_config.persist_dir.mkdir(parents=True, exist_ok=True)
    client = chromadb.PersistentClient(path=str(chroma_config.persist_dir))
    return client.get_or_create_collection(
        name=chroma_config.collection_name,
        metadata={"hnsw:space": "cosine"},
    )


def retrieve_context(collection, embedding: List[float], top_k: int) -> List[Dict[str, Any]]:
    result = collection.query(
        query_embeddings=[embedding],
        n_results=top_k,
        include=["documents", "metadatas", "distances"],
    )
    documents = (result.get("documents") or [[]])[0]
    metadatas = (result.get("metadatas") or [[]])[0]
    distances = (result.get("distances") or [[]])[0]
    ids = (result.get("ids") or [[]])[0]

    results = []
    for doc, meta, distance, item_id in zip(documents, metadatas, distances, ids):
        meta = meta or {}
        score = None
        if distance is not None:
            score = 1 - float(distance)
        results.append(
            {
                "id": item_id,
                "title": meta.get("title"),
                "content": doc,
                "url": meta.get("url"),
                "author": meta.get("author"),
                "tags": meta.get("tags") or [],
                "score": score,
            }
        )
    return results


def build_prompt(question: str, contexts: List[Dict[str, Any]]) -> str:
    sources = []
    for idx, item in enumerate(contexts, start=1):
        title = item.get("title") or ""
        content = item.get("content") or ""
        url = item.get("url") or ""
        author = item.get("author") or ""
        source_text = f"[资料{idx}] 标题: {title}\n作者: {author}\n链接: {url}\n内容: {content}"
        sources.append(source_text)
    source_block = "\n\n".join(sources)
    return (
        "你是一个旅行规划助手。请基于资料回答问题，避免编造。\n\n"
        f"资料:\n{source_block}\n\n"
        f"问题: {question}\n"
        "回答:"
    )


def generate_answer(prompt: str, config: OllamaConfig) -> str:
    url = f"{config.base_url}/api/generate"
    payload = {
        "model": config.chat_model,
        "prompt": prompt,
        "stream": False,
        "options": {"temperature": config.temperature},
    }
    with httpx.Client(timeout=120) as client:
        response = client.post(url, json=payload)
        response.raise_for_status()
        data = response.json()
    return data.get("response", "").strip()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--question", required=True)
    parser.add_argument("--top-k", type=int, default=5)
    parser.add_argument("--show-context", action="store_true")
    return parser.parse_args()


def main() -> None:
    load_dotenv()
    args = parse_args()

    chroma_config = load_chroma_config()
    ollama_config = load_ollama_config()
    collection = get_collection(chroma_config)
    embedding = embed_query(args.question, ollama_config)
    contexts = retrieve_context(collection, embedding, args.top_k)
    prompt = build_prompt(args.question, contexts)
    answer = generate_answer(prompt, ollama_config)

    if args.show_context:
        print(json.dumps(contexts, ensure_ascii=False, indent=2))

    print(answer)


if __name__ == "__main__":
    main()
