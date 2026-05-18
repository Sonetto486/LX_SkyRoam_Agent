"""
Xiaohongshu notes pre-import script
Pre-imports xiaohongshu notes for popular destinations to improve performance
"""
import asyncio
import sys
import os

# Add backend to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from loguru import logger
from sqlalchemy import text
from app.core.database import async_session
from app.services.xhs_api_client import XHSAPIClient


# Popular destinations to pre-import
POPULAR_DESTINATIONS = [
    "上海", "北京", "杭州", "成都", "西安", "南京", "苏州", "厦门", "重庆", "广州",
    "深圳", "武汉", "长沙", "青岛", "大连", "三亚", "丽江", "大理", "桂林", "张家界",
    "黄山", "九寨沟", "西藏", "新疆", "云南", "四川", "江苏", "浙江"
]

NOTES_PER_DESTINATION = 20  # Number of notes to import per destination


async def import_xiaohongshu_notes():
    """Import xiaohongshu notes for all popular destinations"""
    xhs_client = XHSAPIClient()

    total_imported = 0
    failed_destinations = []

    for destination in POPULAR_DESTINATIONS:
        try:
            logger.info(f"Importing notes for {destination}...")

            # Search notes
            response = await xhs_client.search_notes(f"{destination}旅游攻略", limit=NOTES_PER_DESTINATION)

            logger.info(f"API response for {destination}: status={response.get('status') if response else 'None'}, results_count={len(response.get('results', [])) if response else 0}")

            if not response or response.get("status") != "success":
                logger.warning(f"Failed to fetch notes for {destination}: {response}")
                failed_destinations.append(destination)
                continue

            results = response.get("results", [])

            if not results:
                logger.warning(f"No notes found for {destination}")
                continue

            # Save to database
            async with async_session() as db:
                for note_data in results:
                    try:
                        # Check if note already exists
                        existing = await db.execute(
                            text("SELECT id FROM xiaohongshu_notes WHERE note_id = :note_id"),
                            {"note_id": note_data.get("note_id", "")}
                        )
                        if existing.fetchone():
                            continue

                        # Insert new note
                        await db.execute(
                            text("""
                                INSERT INTO xiaohongshu_notes
                                (note_id, title, description, img_urls, tag_list, liked_count, location, destination, relevance_score, url)
                                VALUES (:note_id, :title, :description, :img_urls, :tag_list, :liked_count, :location, :destination, :relevance_score, :url)
                            """),
                            {
                                "note_id": note_data.get("note_id", ""),
                                "title": note_data.get("title", ""),
                                "description": note_data.get("desc", ""),
                                "img_urls": str(note_data.get("img_urls", [])),
                                "tag_list": str(note_data.get("tag_list", [])),
                                "liked_count": note_data.get("liked_count", 0),
                                "location": note_data.get("location", ""),
                                "destination": destination,
                                "relevance_score": note_data.get("relevance_score", 0.0),
                                "url": note_data.get("url", "")
                            }
                        )
                    except Exception as e:
                        logger.warning(f"Failed to insert note: {e}")
                        continue

                await db.commit()

            logger.info(f"Imported {len(results)} notes for {destination}")
            total_imported += len(results)

            # Rate limiting
            await asyncio.sleep(2)

        except Exception as e:
            logger.error(f"Error importing notes for {destination}: {e}")
            failed_destinations.append(destination)

    logger.info(f"Total imported: {total_imported} notes")
    if failed_destinations:
        logger.warning(f"Failed destinations: {failed_destinations}")


if __name__ == "__main__":
    logger.info("Starting xiaohongshu notes pre-import...")
    asyncio.run(import_xiaohongshu_notes())
    logger.info("Pre-import completed!")
