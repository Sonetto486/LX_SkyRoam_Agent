import argparse
import asyncio
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Dict, Any
from uuid import uuid4

import chromadb
import httpx
from dotenv import load_dotenv
from loguru import logger

SCRIPT_DIR = Path(__file__).resolve().parent
BACKEND_DIR = SCRIPT_DIR.parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.platforms.xhs.real_crawler import XiaoHongShuRealCrawler


@dataclass
class ChromaConfig:
    persist_dir: Path
    collection_name: str


@dataclass
class OllamaConfig:
    base_url: str
    embed_model: str


def load_chroma_config() -> ChromaConfig:
    persist_dir = Path(os.getenv("CHROMA_PERSIST_DIR", str(BACKEND_DIR / "data" / "chroma")))
    collection_name = os.getenv("CHROMA_COLLECTION", "rag_xhs_notes")
    return ChromaConfig(persist_dir=persist_dir, collection_name=collection_name)


def load_ollama_config() -> OllamaConfig:
    base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    embed_model = os.getenv("OLLAMA_EMBED_MODEL", "nomic-embed-text")
    return OllamaConfig(base_url=base_url, embed_model=embed_model)


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


def _request_embedding(client: httpx.Client, base_url: str, model: str, text: str) -> List[float]:
    embeddings_url = f"{base_url}/api/embeddings"
    response = client.post(embeddings_url, json={"model": model, "prompt": text})
    if response.status_code == 404:
        embed_url = f"{base_url}/api/embed"
        response = client.post(embed_url, json={"model": model, "input": text})
    response.raise_for_status()
    data = response.json()
    if "embedding" in data:
        return data["embedding"]
    if "embeddings" in data and data["embeddings"]:
        return data["embeddings"][0]
    raise ValueError("Ollama embedding response missing embedding data")


def embed_texts(texts: List[str], config: OllamaConfig) -> List[List[float]]:
    embeddings: List[List[float]] = []
    with httpx.Client(timeout=60) as client:
        for text in texts:
            embeddings.append(_request_embedding(client, config.base_url, config.embed_model, text))
    return embeddings


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
    ollama_config = load_ollama_config()
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
        embeddings = embed_texts(chunks, ollama_config)
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
