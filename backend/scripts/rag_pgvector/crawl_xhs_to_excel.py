import argparse
import asyncio
import os
import sys
from pathlib import Path
from typing import Any, Dict, List

import pandas as pd
from dotenv import load_dotenv
from loguru import logger

SCRIPT_DIR = Path(__file__).resolve().parent
BACKEND_DIR = SCRIPT_DIR.parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

load_dotenv(dotenv_path=BACKEND_DIR / ".env")

from app.platforms.xhs.real_crawler import XiaoHongShuRealCrawler


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Crawl XHS notes and export to Excel")
    parser.add_argument("--keyword", required=True, help="Search keyword")
    parser.add_argument("--max-notes", type=int, default=20, help="Max notes to fetch")
    parser.add_argument(
        "--output",
        default=str(SCRIPT_DIR / "xhs_notes.xlsx"),
        help="Output Excel path",
    )
    return parser.parse_args()


def normalize_text(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def extract_author(note: Dict[str, Any]) -> str:
    user_info = note.get("user_info") or {}
    return normalize_text(user_info.get("nickname", ""))


def build_row(note: Dict[str, Any]) -> Dict[str, Any]:
    tags = note.get("tag_list") or []
    tags_text = ", ".join([normalize_text(tag) for tag in tags if tag])
    return {
        "note_id": note.get("note_id"),
        "title": normalize_text(note.get("title")),
        "desc": normalize_text(note.get("desc")),
        "author": extract_author(note),
        "url": note.get("url"),
        "tags": tags_text,
        "liked_count": note.get("liked_count"),
        "comment_count": note.get("comment_count"),
        "collected_count": note.get("collected_count"),
        "share_count": note.get("share_count"),
        "time": note.get("time"),
        "source": note.get("source", "xhs"),
    }


async def crawl_notes(keyword: str, max_notes: int) -> List[Dict[str, Any]]:
    crawler = XiaoHongShuRealCrawler()
    await crawler.start()
    await crawler.ensure_logged_in()
    notes = await crawler.search(keyword, max_notes)
    await crawler.close()
    return notes


def save_to_excel(rows: List[Dict[str, Any]], output_path: str) -> None:
    output = Path(output_path).resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    df = pd.DataFrame(rows)
    df.to_excel(output, index=False)
    logger.info("已保存 Excel: {}", output)


def main() -> None:
    args = parse_args()
    notes = asyncio.run(crawl_notes(args.keyword, args.max_notes))
    if not notes:
        logger.warning("未获取到笔记内容，未生成 Excel")
        return

    rows = [build_row(note) for note in notes]
    save_to_excel(rows, args.output)


if __name__ == "__main__":
    main()
