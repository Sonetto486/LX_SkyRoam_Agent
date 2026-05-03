import argparse
import json
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import List, Dict, Any

import chromadb
import dashscope
import openai
from dotenv import load_dotenv

SCRIPT_DIR = Path(__file__).resolve().parent
BACKEND_DIR = SCRIPT_DIR.parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

dotenv_path = BACKEND_DIR / ".env"
load_dotenv(dotenv_path=dotenv_path)

from app.core.config import settings


@dataclass
class ChromaConfig:
    persist_dir: Path
    collection_name: str


@dataclass
class RemoteModelConfig:
    provider: str
    openai_api_key: str
    openai_api_base: str
    openai_embed_model: str
    dashscope_api_key: str
    dashscope_embed_model: str
    chat_model: str
    temperature: float
    timeout: float


def load_chroma_config() -> ChromaConfig:
    persist_dir = Path(os.getenv("CHROMA_PERSIST_DIR", str(BACKEND_DIR / "data" / "chroma")))
    collection_name = os.getenv("CHROMA_COLLECTION", "rag_xhs_notes")
    return ChromaConfig(persist_dir=persist_dir, collection_name=collection_name)


def load_remote_model_config() -> RemoteModelConfig:
    provider = settings.EMBEDDING_PROVIDER.lower()
    openai_api_key = settings.OPENAI_API_KEY
    openai_api_base = settings.OPENAI_API_BASE
    openai_embed_model = settings.OPENAI_EMBEDDING_MODEL
    dashscope_api_key = settings.DASHSCOPE_API_KEY
    dashscope_embed_model = settings.DASHSCOPE_EMBEDDING_MODEL
    chat_model = os.getenv("OPENAI_CHAT_MODEL", settings.OPENAI_MODEL)
    temperature = float(os.getenv("OPENAI_TEMPERATURE", str(settings.OPENAI_TEMPERATURE)))
    timeout = float(os.getenv("OPENAI_TIMEOUT", str(settings.OPENAI_TIMEOUT)))
    if provider == "dashscope" and not dashscope_api_key:
        raise ValueError("DASHSCOPE_API_KEY is required for dashscope embeddings")
    if provider == "openai" and not openai_api_key:
        raise ValueError("OPENAI_API_KEY is required for openai embeddings")
    return RemoteModelConfig(
        provider=provider,
        openai_api_key=openai_api_key,
        openai_api_base=openai_api_base,
        openai_embed_model=openai_embed_model,
        dashscope_api_key=dashscope_api_key,
        dashscope_embed_model=dashscope_embed_model,
        chat_model=chat_model,
        temperature=temperature,
        timeout=timeout,
    )


def log_remote_config(config: RemoteModelConfig) -> None:
    if config.provider == "dashscope":
        print(
            f"Embedding provider=dashscope, model={config.dashscope_embed_model}, api_key_set={bool(config.dashscope_api_key)}"
        )
    else:
        print(
            "Embedding provider=openai, model={model}, api_base={base}, api_key_set={has_key}".format(
                model=config.openai_embed_model,
                base=config.openai_api_base,
                has_key=bool(config.openai_api_key),
            )
        )
    print(f"Chat model={config.chat_model}")


def embed_query(query: str, config: RemoteModelConfig) -> List[float]:
    if config.provider == "dashscope":
        dashscope.api_key = config.dashscope_api_key
        response = dashscope.TextEmbedding.call(model=config.dashscope_embed_model, input=[query])
        if response.status_code != 200:
            raise RuntimeError(f"DashScope embedding failed: {response}")
        return response.output["embeddings"][0]["embedding"]

    client = openai.OpenAI(
        api_key=config.openai_api_key,
        base_url=config.openai_api_base if config.openai_api_base != "https://api.openai.com/v1" else None,
        timeout=config.timeout,
    )
    response = client.embeddings.create(model=config.openai_embed_model, input=[query])
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


def generate_answer(prompt: str, config: RemoteModelConfig) -> str:
    client = openai.OpenAI(
        api_key=config.openai_api_key,
        base_url=config.openai_api_base if config.openai_api_base != "https://api.openai.com/v1" else None,
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
    remote_config = load_remote_model_config()
    log_remote_config(remote_config)
    collection = get_collection(chroma_config)
    embedding = embed_query(args.question, remote_config)
    contexts = retrieve_context(collection, embedding, args.top_k)
    prompt = build_prompt(args.question, contexts)
    answer = generate_answer(prompt, remote_config)

    if args.show_context:
        print(json.dumps(contexts, ensure_ascii=False, indent=2))

    print(answer)


if __name__ == "__main__":
    main()
