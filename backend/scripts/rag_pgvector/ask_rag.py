import argparse
import json
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import List, Dict, Any

import chromadb
import openai
from dotenv import load_dotenv

SCRIPT_DIR = Path(__file__).resolve().parent
BACKEND_DIR = SCRIPT_DIR.parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.core.config import settings


@dataclass
class ChromaConfig:
    persist_dir: Path
    collection_name: str


@dataclass
class OpenAIConfig:
    api_key: str
    api_base: str
    embed_model: str
    chat_model: str
    temperature: float
    timeout: float


def load_chroma_config() -> ChromaConfig:
    persist_dir = Path(os.getenv("CHROMA_PERSIST_DIR", str(BACKEND_DIR / "data" / "chroma")))
    collection_name = os.getenv("CHROMA_COLLECTION", "rag_xhs_notes")
    return ChromaConfig(persist_dir=persist_dir, collection_name=collection_name)


def load_openai_config() -> OpenAIConfig:
    api_key = settings.OPENAI_API_KEY
    api_base = settings.OPENAI_API_BASE
    embed_model = settings.OPENAI_EMBEDDING_MODEL
    chat_model = os.getenv("OPENAI_CHAT_MODEL", settings.OPENAI_MODEL)
    temperature = float(os.getenv("OPENAI_TEMPERATURE", str(settings.OPENAI_TEMPERATURE)))
    timeout = float(os.getenv("OPENAI_TIMEOUT", str(settings.OPENAI_TIMEOUT)))
    if not api_key:
        raise ValueError("OPENAI_API_KEY is required")
    return OpenAIConfig(
        api_key=api_key,
        api_base=api_base,
        embed_model=embed_model,
        chat_model=chat_model,
        temperature=temperature,
        timeout=timeout,
    )


def embed_query(query: str, config: OpenAIConfig) -> List[float]:
    client = openai.OpenAI(
        api_key=config.api_key,
        base_url=config.api_base if config.api_base != "https://api.openai.com/v1" else None,
        timeout=config.timeout,
    )
    response = client.embeddings.create(model=config.embed_model, input=[query])
    return response.data[0].embedding


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


def generate_answer(prompt: str, config: OpenAIConfig) -> str:
    client = openai.OpenAI(
        api_key=config.api_key,
        base_url=config.api_base if config.api_base != "https://api.openai.com/v1" else None,
        timeout=config.timeout,
    )
    response = client.chat.completions.create(
        model=config.chat_model,
        messages=[{"role": "user", "content": prompt}],
        temperature=config.temperature,
    )
    return response.choices[0].message.content.strip()


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
    openai_config = load_openai_config()
    collection = get_collection(chroma_config)
    embedding = embed_query(args.question, openai_config)
    contexts = retrieve_context(collection, embedding, args.top_k)
    prompt = build_prompt(args.question, contexts)
    answer = generate_answer(prompt, openai_config)

    if args.show_context:
        print(json.dumps(contexts, ensure_ascii=False, indent=2))

    print(answer)


if __name__ == "__main__":
    main()
