import argparse
import asyncio
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Dict, Any
from uuid import uuid4

import chromadb
import dashscope
import openai
from dotenv import load_dotenv
from loguru import logger

SCRIPT_DIR = Path(__file__).resolve().parent
BACKEND_DIR = SCRIPT_DIR.parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

dotenv_path = BACKEND_DIR / ".env"
load_dotenv(dotenv_path=dotenv_path)

from app.core.config import settings
from app.platforms.xhs.real_crawler import XiaoHongShuRealCrawler


@dataclass
class ChromaConfig:
    persist_dir: Path
    collection_name: str


@dataclass
class EmbeddingConfig:
    provider: str
    openai_api_key: str
    openai_api_base: str
    openai_embed_model: str
    dashscope_api_key: str
    dashscope_embed_model: str
    timeout: float


def load_chroma_config() -> ChromaConfig:
    persist_dir = Path(os.getenv("CHROMA_PERSIST_DIR", str(BACKEND_DIR / "data" / "chroma")))
    collection_name = os.getenv("CHROMA_COLLECTION", "rag_xhs_notes")
    return ChromaConfig(persist_dir=persist_dir, collection_name=collection_name)


def load_embedding_config() -> EmbeddingConfig:
    provider = settings.EMBEDDING_PROVIDER.lower()
    openai_api_key = settings.OPENAI_API_KEY
    openai_api_base = settings.OPENAI_API_BASE
    openai_embed_model = settings.OPENAI_EMBEDDING_MODEL
    dashscope_api_key = settings.DASHSCOPE_API_KEY
    dashscope_embed_model = settings.DASHSCOPE_EMBEDDING_MODEL
    timeout = float(os.getenv("OPENAI_TIMEOUT", str(settings.OPENAI_TIMEOUT)))
    if provider == "dashscope" and not dashscope_api_key:
        raise ValueError("DASHSCOPE_API_KEY is required for dashscope embeddings")
    if provider == "openai" and not openai_api_key:
        raise ValueError("OPENAI_API_KEY is required for openai embeddings")
    return EmbeddingConfig(
        provider=provider,
        openai_api_key=openai_api_key,
        openai_api_base=openai_api_base,
        openai_embed_model=openai_embed_model,
        dashscope_api_key=dashscope_api_key,
        dashscope_embed_model=dashscope_embed_model,
        timeout=timeout,
    )


def log_embedding_config(config: EmbeddingConfig) -> None:
    if config.provider == "dashscope":
        logger.info(
            "Embedding provider=dashscope, model={model}, api_key_set={has_key}",
            model=config.dashscope_embed_model,
            has_key=bool(config.dashscope_api_key),
        )
    else:
        logger.info(
            "Embedding provider=openai, model={model}, api_base={base}, api_key_set={has_key}",
            model=config.openai_embed_model,
            base=config.openai_api_base,
            has_key=bool(config.openai_api_key),
        )


def normalize_text(text: str) -> str:
    return " ".join(text.replace("\u3000", " ").split())


def chunk_text(text: str, chunk_size: int, overlap: int) -> Iterable[str]:
    if chunk_size <= 0:
        return []
    if overlap >= chunk_size:
        overlap = max(chunk_size - 1, 0)
    index = 0
    length = len(text)
    while index < length:
        yield text[index:index + chunk_size]
        if chunk_size == 0:
            break
        index += max(chunk_size - overlap, 1)


def build_content(note: Dict[str, Any]) -> str:
    title = normalize_text(note.get("title", ""))
    desc = normalize_text(note.get("desc", ""))
    tags = note.get("tag_list") or []
    tag_text = " ".join([normalize_text(str(tag)) for tag in tags if tag])
    parts = [p for p in [title, desc, tag_text] if p]
    return "\n".join(parts)


def extract_author(note: Dict[str, Any]) -> str:
    user_info = note.get("user_info") or {}
    return normalize_text(user_info.get("nickname", ""))


def get_collection(chroma_config: ChromaConfig):
    chroma_config.persist_dir.mkdir(parents=True, exist_ok=True)
    client = chromadb.PersistentClient(path=str(chroma_config.persist_dir))
    return client.get_or_create_collection(
        name=chroma_config.collection_name,
        metadata={"hnsw:space": "cosine"},
    )


def embed_texts(texts: List[str], config: EmbeddingConfig) -> List[List[float]]:
    if config.provider == "dashscope":
        dashscope.api_key = config.dashscope_api_key
        response = dashscope.TextEmbedding.call(model=config.dashscope_embed_model, input=texts)
        if response.status_code != 200:
            raise RuntimeError(f"DashScope embedding failed: {response}")
        return [item["embedding"] for item in response.output["embeddings"]]

    client = openai.OpenAI(
        api_key=config.openai_api_key,
        base_url=config.openai_api_base if config.openai_api_base != "https://api.openai.com/v1" else None,
        timeout=config.timeout,
    )
    response = client.embeddings.create(model=config.openai_embed_model, input=texts)
    return [item.embedding for item in response.data]


def store_chunks(
    collection,
    chunks: List[str],
    embeddings: List[List[float]],
    metadata: Dict[str, Any],
) -> int:
    ids = []
    metadatas = []
    for index, _ in enumerate(chunks):
        chunk_id = f"{metadata.get('note_id', 'note')}_{index}_{uuid4().hex}"
        ids.append(chunk_id)
        metadatas.append({**metadata, "chunk_index": index})

    collection.add(
        ids=ids,
        documents=chunks,
        embeddings=embeddings,
        metadatas=metadatas,
    )
    return len(chunks)


async def crawl_notes(keyword: str, max_notes: int) -> List[Dict[str, Any]]:
    crawler = XiaoHongShuRealCrawler()
    await crawler.start()
    await crawler.ensure_logged_in()
    notes = await crawler.search(keyword, max_notes)
    await crawler.close()
    return notes


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--keyword", required=True)
    parser.add_argument("--max-notes", type=int, default=20)
    parser.add_argument("--chunk-size", type=int, default=500)
    parser.add_argument("--chunk-overlap", type=int, default=50)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    chroma_config = load_chroma_config()
    embedding_config = load_embedding_config()
    log_embedding_config(embedding_config)
    collection = get_collection(chroma_config)

    notes = asyncio.run(crawl_notes(args.keyword, args.max_notes))
    if not notes:
        logger.warning("未获取到笔记内容")
        return

    total_inserted = 0
    for note in notes:
        content = build_content(note)
        if not content:
            continue
        chunks = list(chunk_text(content, args.chunk_size, args.chunk_overlap))
        if not chunks:
            continue
        embeddings = embed_texts(chunks, embedding_config)
        tags_list = note.get("tag_list") or []
        tags_text = ", ".join([str(tag) for tag in tags_list if tag])
        metadata = {
            "source": note.get("source", "xhs"),
            "note_id": note.get("note_id"),
            "title": note.get("title"),
            "url": note.get("url"),
            "author": extract_author(note),
            "tags": tags_text,
            "liked_count": note.get("liked_count"),
            "comment_count": note.get("comment_count"),
            "collected_count": note.get("collected_count"),
            "share_count": note.get("share_count"),
            "time": note.get("time"),
        }
        inserted = store_chunks(collection, chunks, embeddings, metadata)
        total_inserted += inserted

    logger.info(f"入库完成，新增向量片段 {total_inserted} 条")


if __name__ == "__main__":
    main()
