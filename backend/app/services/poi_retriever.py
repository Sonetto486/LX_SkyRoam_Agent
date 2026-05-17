"""
POI 景点向量检索服务
从 PostgreSQL 向量数据库检索景点，并结合高德 API 补充实时信息
"""

import time
from typing import List, Dict, Any, Optional
from loguru import logger
import psycopg2
import requests
from app.core.config import settings
import asyncio

from app.core.config import settings

# pgvector 延迟导入，避免 Celery Worker 环境问题
_pgvector_registered = False


def _ensure_pgvector_registered(conn):
    """确保 pgvector 已注册到连接"""
    global _pgvector_registered
    if not _pgvector_registered:
        try:
            from pgvector.psycopg2 import register_vector
            register_vector(conn)
            _pgvector_registered = True
            logger.info("pgvector 已成功注册")
        except ImportError as e:
            logger.error(f"pgvector 导入失败: {e}")
            raise ImportError("pgvector 包未安装，请运行: pip install pgvector")


class POIRetriever:
    """景点向量检索服务"""

    def __init__(self):
        # 数据库连接配置（使用统一配置）
        self.db_config = {
            "dbname": settings.RAG_DB_NAME,
            "user": settings.RAG_DB_USER,
            "password": settings.RAG_DB_PASSWORD,
            "host": settings.RAG_DB_HOST,
            "port": str(settings.RAG_DB_PORT)
        }

        # 向量化 API 配置（使用统一配置）
        self.embedding_api_base = settings.RAG_EMBEDDING_API_BASE
        self.embedding_api_key = settings.RAG_EMBEDDING_API_KEY
        self.embedding_model = settings.RAG_EMBEDDING_MODEL

        # 高德 API Key
        self.amap_api_key = settings.AMAP_API_KEY

        # 检索配置（使用统一配置）
        self.default_top_k = settings.POI_TOP_K
        self.similarity_threshold = settings.POI_SIMILARITY_THRESHOLD

    def get_embedding(self, text: str) -> List[float]:
        """调用 API 获取文本的向量表示"""
        url = f"{self.embedding_api_base}/embeddings"
        headers = {
            "Authorization": f"Bearer {self.embedding_api_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": self.embedding_model,
            "input": text
        }

        max_retries = 3
        for attempt in range(max_retries):
            try:
                response = requests.post(url, headers=headers, json=payload, timeout=15)
                response.raise_for_status()
                data = response.json()
                return data["data"][0]["embedding"]
            except Exception as e:
                logger.warning(f"获取向量失败 (尝试 {attempt+1}/{max_retries}): {e}")
                if attempt < max_retries - 1:
                    time.sleep(2)

        raise Exception("获取向量失败，请检查 API 配置或网络连接")

    def retrieve_by_destination(
        self,
        destination: str,
        top_k: int = None,
        label_filter: str = None
    ) -> List[Dict[str, Any]]:
        """
        根据目的地检索景点

        Args:
            destination: 目的地名称（如"北京"、"杭州"）
            top_k: 返回结果数量
            label_filter: 标签过滤（如"博物馆"、"公园"）

        Returns:
            景点列表，包含 id, name, city, coordinates, labels 等
        """
        top_k = top_k or self.default_top_k

        try:
            # 构建查询文本
            query_text = f"{destination}旅游景点推荐"
            query_embedding = self.get_embedding(query_text)

            # 连接数据库
            conn = psycopg2.connect(**self.db_config)
            _ensure_pgvector_registered(conn)
            cursor = conn.cursor()

            # 构建SQL查询 - 使用热度排名优先排序
            # 优先使用 attraction_popularity 表的热度排名，其次使用相似度
            sql = """
                SELECT
                    a.id, a.poi_id, a.name_zh, a.name_en,
                    a.city_zh, a.city_en, a.latitude, a.longitude,
                    a.label_zh, a.label_en, a.rating, a.popularity_score,
                    c.chunk_text,
                    c.embedding <=> %s::vector AS distance,
                    COALESCE(p.popularity_rank, 9999) AS popularity_rank,
                    COALESCE(p.popularity_score, 0) AS external_popularity
                FROM poi_attractions a
                JOIN poi_attraction_chunks c ON a.id = c.attraction_id
                LEFT JOIN attraction_popularity p ON a.id = p.attraction_id
                WHERE 1=1
            """
            params = [query_embedding]

            # 添加城市过滤
            if destination:
                sql += " AND (a.city_zh ILIKE %s OR a.name_zh ILIKE %s)"
                params.extend([f"%{destination}%", f"%{destination}%"])

            # 添加标签过滤
            if label_filter:
                sql += " AND a.label_zh ILIKE %s"
                params.append(f"%{label_filter}%")

            # 按热度排名优先排序（排名越小越热门），然后是相似度
            sql += " ORDER BY popularity_rank ASC, distance ASC LIMIT %s"
            params.append(top_k)

            cursor.execute(sql, params)
            results = cursor.fetchall()

            # 转换结果格式
            # 列顺序: id, poi_id, name_zh, name_en, city_zh, city_en, latitude, longitude,
            #         label_zh, label_en, rating, popularity_score, chunk_text, distance, popularity_rank, external_popularity
            attractions = []
            for row in results:
                distance = float(row[13]) if row[13] else 1.0
                similarity = 1 - distance
                rating = float(row[10]) if row[10] else 0.0
                popularity_score = float(row[11]) if row[11] else 0.0
                popularity_rank = int(row[14]) if row[14] else 9999
                external_popularity = float(row[15]) if row[15] else 0.0

                # 使用外部热度评分（如果有）
                final_popularity = external_popularity if external_popularity > 0 else popularity_score

                if similarity >= self.similarity_threshold:
                    attractions.append({
                        "id": row[0],
                        "poi_id": row[1],
                        "name": row[2],
                        "name_en": row[3],
                        "city": row[4],
                        "city_en": row[5],
                        "latitude": float(row[6]) if row[6] else None,
                        "longitude": float(row[7]) if row[7] else None,
                        "labels": row[8].split(";") if row[8] else [],
                        "labels_en": row[9].split(";") if row[9] else [],
                        "rating": rating,
                        "popularity_score": final_popularity,
                        "popularity_rank": popularity_rank,
                        "description": row[12],
                        "similarity": round(similarity, 4)
                    })

            cursor.close()
            conn.close()

            logger.info(f"POI检索完成: 目的地='{destination}', 返回{len(attractions)}条结果, 热度排名范围: {attractions[0].get('popularity_rank', 9999) if attractions else 'N/A'}-{attractions[-1].get('popularity_rank', 9999) if attractions else 'N/A'}")
            return attractions

        except Exception as e:
            logger.error(f"POI检索失败: {e}")
            return []

    def retrieve_by_coordinates(
        self,
        latitude: float,
        longitude: float,
        radius_km: float = 50,
        top_k: int = 20
    ) -> List[Dict[str, Any]]:
        """
        根据坐标检索附近景点

        Args:
            latitude: 纬度
            longitude: 经度
            radius_km: 搜索半径(公里)
            top_k: 返回结果数量

        Returns:
            景点列表
        """
        try:
            conn = psycopg2.connect(**self.db_config)
            cursor = conn.cursor()

            # 使用 PostGIS 计算距离（如果安装了）或使用简化的距离公式
            # 这里使用简化的欧几里得距离近似
            sql = """
                SELECT
                    id, poi_id, name_zh, name_en,
                    city_zh, city_en, latitude, longitude,
                    label_zh, label_en,
                    SQRT(
                        POW(111.0 * (latitude - %s), 2) +
                        POW(111.0 * (longitude - %s) * COS(RADIANS(%s)), 2)
                    ) AS distance_km
                FROM poi_attractions
                WHERE latitude IS NOT NULL AND longitude IS NOT NULL
                ORDER BY distance_km ASC
                LIMIT %s
            """
            cursor.execute(sql, [latitude, longitude, latitude, top_k])
            results = cursor.fetchall()

            attractions = []
            for row in results:
                distance = float(row[10]) if row[10] else 999
                if distance <= radius_km:
                    attractions.append({
                        "id": row[0],
                        "poi_id": row[1],
                        "name": row[2],
                        "name_en": row[3],
                        "city": row[4],
                        "city_en": row[5],
                        "latitude": float(row[6]) if row[6] else None,
                        "longitude": float(row[7]) if row[7] else None,
                        "labels": row[8].split(";") if row[8] else [],
                        "labels_en": row[9].split(";") if row[9] else [],
                        "distance_km": round(distance, 2)
                    })

            cursor.close()
            conn.close()

            logger.info(f"坐标检索完成: ({latitude}, {longitude}), 返回{len(attractions)}条结果")
            return attractions

        except Exception as e:
            logger.error(f"坐标检索失败: {e}")
            return []

    async def retrieve_with_amap_enrichment(
        self,
        destination: str,
        top_k: int = 10
    ) -> List[Dict[str, Any]]:
        """
        检索景点 + 高德 API 补充实时信息

        Args:
            destination: 目的地名称
            top_k: 返回结果数量

        Returns:
            景点列表，包含高德 API 补充的实时信息（评分、门票、开放时间等）
        """
        # 1. 先从向量数据库检索景点
        attractions = self.retrieve_by_destination(destination, top_k=top_k * 2)

        if not attractions:
            logger.warning(f"未找到目的地'{destination}'的景点数据")
            return []

        # 2. 调用高德 API 补充信息
        enriched_attractions = []
        for attraction in attractions[:top_k]:
            enriched = await self._enrich_with_amap(attraction)
            enriched_attractions.append(enriched)

        logger.info(f"景点信息增强完成: {len(enriched_attractions)}条")
        return enriched_attractions

    async def _enrich_with_amap(self, attraction: Dict[str, Any]) -> Dict[str, Any]:
        """使用高德 API 补充景点信息"""
        try:
            if not self.amap_api_key:
                logger.warning("高德 API Key 未配置，跳过信息增强")
                return attraction

            # 调用高德 POI 搜索 - 改进匹配精度
            url = "https://restapi.amap.com/v3/place/text"
            params = {
                "key": self.amap_api_key,
                "keywords": attraction["name"],
                "city": attraction.get("city", ""),
                "citylimit": "true",  # 强制限定城市范围，提高匹配精度
                "types": "110000",  # 风景名胜
                "output": "json",
                "offset": 5,  # 增加返回数量，便于匹配
                "page": 1,
                "extensions": "all"
            }

            import httpx
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(url, params=params)
                result = response.json()

            if result.get("status") == "1" and result.get("pois"):
                # 改进匹配逻辑：优先匹配名称完全一致或包含的结果
                matched_poi = None
                attraction_name = attraction["name"]

                for poi in result["pois"]:
                    poi_name = poi.get("name", "")
                    # 名称完全匹配
                    if poi_name == attraction_name:
                        matched_poi = poi
                        logger.debug(f"景点 '{attraction_name}' 完全匹配到 '{poi_name}'")
                        break
                    # 景点名称包含在POI名称中（如"外滩"匹配"上海外滩"）
                    if attraction_name in poi_name or poi_name in attraction_name:
                        matched_poi = poi
                        logger.debug(f"景点 '{attraction_name}' 包含匹配到 '{poi_name}'")
                        break

                # 如果没有匹配，使用第一个结果
                if not matched_poi:
                    matched_poi = result["pois"][0]
                    logger.warning(f"景点 '{attraction_name}' 未精确匹配，使用第一个结果 '{matched_poi.get('name')}'")

                # 补充信息
                attraction["amap_id"] = matched_poi.get("id")
                attraction["address"] = matched_poi.get("address", "")
                attraction["phone"] = matched_poi.get("tel", "")
                rating = self._parse_rating(matched_poi.get("biz_ext", {}).get("rating"))
                if rating:
                    attraction["rating"] = rating
                    attraction["popularity_score"] = rating * 20  # 转换为0-100分
                else:
                    # 保留数据库中已有的评分（如果存在）
                    db_rating = attraction.get("rating", 0)
                    attraction["rating"] = db_rating if db_rating > 0 else 0.0
                    attraction["popularity_score"] = db_rating * 20 if db_rating > 0 else 0.0
                attraction["cost"] = matched_poi.get("biz_ext", {}).get("cost", "")
                attraction["opening_hours"] = matched_poi.get("biz_ext", {}).get("opening", "")
                attraction["photos"] = [p.get("url") for p in matched_poi.get("photos", [])[:3] if p.get("url")]
                attraction["source"] = "向量数据库 + 高德地图"

                # 更新数据库中的热度字段
                if rating:
                    await self._update_popularity_in_db(attraction["id"], rating)

                logger.info(f"景点 '{attraction_name}' 高德匹配完成: 评分={attraction['rating']}, 匹配POI='{matched_poi.get('name')}'")

            return attraction

        except Exception as e:
            logger.warning(f"高德 API 补充信息失败: {e}")
            return attraction

    def _parse_rating(self, rating) -> Optional[float]:
        """解析评分"""
        if rating is None:
            return None
        try:
            if isinstance(rating, (int, float)):
                return float(rating)
            if isinstance(rating, str) and rating.replace(".", "").isdigit():
                return float(rating)
        except:
            pass
        return None

    async def _update_popularity_in_db(self, attraction_id: int, rating: Optional[float]):
        """更新数据库中的热度字段"""
        if not rating or not attraction_id:
            return

        try:
            conn = psycopg2.connect(**self.db_config)
            cursor = conn.cursor()

            popularity_score = rating * 20  # 转换为0-100分

            sql = """
                UPDATE poi_attractions
                SET rating = %s, popularity_score = %s
                WHERE id = %s
            """
            cursor.execute(sql, (rating, popularity_score, attraction_id))
            conn.commit()

            cursor.close()
            conn.close()
            logger.debug(f"更新景点热度: id={attraction_id}, rating={rating}, popularity={popularity_score}")

        except Exception as e:
            logger.warning(f"更新景点热度失败: {e}")

    def build_poi_context(
        self,
        destination: str,
        top_k: int = 10
    ) -> str:
        """
        构建 POI 上下文文本，用于提供给大模型生成行程

        Args:
            destination: 目的地
            top_k: 景点数量

        Returns:
            格式化的上下文文本
        """
        attractions = self.retrieve_by_destination(destination, top_k=top_k)

        if not attractions:
            return ""

        context_parts = [f"【{destination}热门景点推荐】\n"]

        for i, attr in enumerate(attractions, 1):
            labels_str = "、".join(attr["labels"][:3]) if attr["labels"] else "风景名胜"
            context_parts.append(f"{i}. {attr['name']} - {labels_str}")
            if attr.get("description"):
                context_parts.append(f"   {attr['description']}")
            context_parts.append("")

        context_text = "\n".join(context_parts)
        logger.info(f"构建 POI 上下文完成，长度: {len(context_text)}字符")

        return context_text

    def build_enriched_poi_context(
        self,
        enriched_attractions: List[Dict[str, Any]]
    ) -> str:
        """
        构建包含高德实时信息的 POI 上下文文本

        Args:
            enriched_attractions: 经过高德API补充的景点列表

        Returns:
            格式化的上下文文本，包含评分、门票、开放时间等实时信息
        """
        if not enriched_attractions:
            return ""

        context_parts = ["【景点库推荐（含实时信息）】\n"]
        context_parts.append("以下景点来自全国景点基础库，并已通过高德地图API补充实时信息：\n\n")

        for i, attr in enumerate(enriched_attractions, 1):
            # 景点名称和类型
            labels_str = "、".join(attr["labels"][:3]) if attr["labels"] else "风景名胜"
            context_parts.append(f"{i}. {attr['name']}（{labels_str}）")

            # 地址信息
            if attr.get("address"):
                context_parts.append(f"   地址：{attr['address']}")

            # 高德补充的实时信息
            if attr.get("rating"):
                context_parts.append(f"   评分：{attr['rating']}分")
            if attr.get("cost"):
                context_parts.append(f"   人均消费：{attr['cost']}")
            if attr.get("opening_hours"):
                context_parts.append(f"   开放时间：{attr['opening_hours']}")
            if attr.get("phone"):
                context_parts.append(f"   电话：{attr['phone']}")

            # 坐标信息（用于距离计算）
            if attr.get("latitude") and attr.get("longitude"):
                context_parts.append(f"   坐标：{attr['latitude']}, {attr['longitude']}")

            context_parts.append("")

        context_text = "\n".join(context_parts)
        logger.info(f"构建增强 POI 上下文完成，长度: {len(context_text)}字符，包含{len(enriched_attractions)}个景点")

        return context_text


# 全局单例
_poi_retriever: Optional[POIRetriever] = None


def get_poi_retriever() -> POIRetriever:
    """获取 POI 检索器单例"""
    global _poi_retriever
    if _poi_retriever is None:
        _poi_retriever = POIRetriever()
    return _poi_retriever
