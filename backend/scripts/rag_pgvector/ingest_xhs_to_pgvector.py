import argparse
import asyncio
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Dict, Any
from uuid import uuid4

import chromadb
import openai
from dotenv import load_dotenv
from loguru import logger

SCRIPT_DIR = Path(__file__).resolve().parent
BACKEND_DIR = SCRIPT_DIR.parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.core.config import settings
from app.platforms.xhs.real_crawler import XiaoHongShuRealCrawler


@dataclass
class ChromaConfig:
    persist_dir: Path
    collection_name: str


@dataclass
class OpenAIConfig:
    api_key: str
    api_base: str
    embed_model: str
    timeout: float


def load_chroma_config() -> ChromaConfig:
    persist_dir = Path(os.getenv("CHROMA_PERSIST_DIR", str(BACKEND_DIR / "data" / "chroma")))
    collection_name = os.getenv("CHROMA_COLLECTION", "rag_xhs_notes")
    return ChromaConfig(persist_dir=persist_dir, collection_name=collection_name)


def load_openai_config() -> OpenAIConfig:
    api_key = settings.OPENAI_API_KEY
    api_base = settings.OPENAI_API_BASE
    embed_model = settings.OPENAI_EMBEDDING_MODEL
    timeout = float(os.getenv("OPENAI_TIMEOUT", str(settings.OPENAI_TIMEOUT)))
    if not api_key:
        raise ValueError("OPENAI_API_KEY is required")
    return OpenAIConfig(api_key=api_key, api_base=api_base, embed_model=embed_model, timeout=timeout)


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


def embed_texts(texts: List[str], config: OpenAIConfig) -> List[List[float]]:
    client = openai.OpenAI(
        api_key=config.api_key,
        base_url=config.api_base if config.api_base != "https://api.openai.com/v1" else None,
        timeout=config.timeout,
    )
    response = client.embeddings.create(model=config.embed_model, input=texts)
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
    load_dotenv()
    args = parse_args()
    chroma_config = load_chroma_config()
    openai_config = load_openai_config()
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
        embeddings = embed_texts(chunks, openai_config)
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
