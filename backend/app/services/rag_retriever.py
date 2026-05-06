"""
RAG检索服务 - 从PostgreSQL向量数据库检索相关旅行攻略
"""

import asyncio
import time
from typing import List, Dict, Any, Optional
from loguru import logger
import psycopg2
import psycopg2.extras
import requests
import os

from app.core.config import settings


class RAGRetriever:
    """RAG检索器 - 从xhs_note_chunks表中检索相关旅行攻略"""

    def __init__(self):
        # 数据库连接配置
        self.db_config = {
            "dbname": "skyroam",
            "user": "postgres",
            "password": "123456",
            "host": "localhost",
            "port": "5432"
        }

        # 向量化API配置（使用硅基流动）
        self.embedding_api_base = os.getenv(
            "RAG_EMBEDDING_API_BASE",
            "https://api.siliconflow.cn/v1"
        )
        self.embedding_api_key = os.getenv(
            "RAG_EMBEDDING_API_KEY",
            "sk-akxmmyreibwsszkfvxsfnmnifgbaoxswrghligcjnygvgayo"
        )
        self.embedding_model = os.getenv(
            "RAG_EMBEDDING_MODEL",
            "Qwen/Qwen3-Embedding-0.6B"
        )

        # 检索配置
        self.default_top_k = int(os.getenv("RAG_TOP_K", "5"))
        self.similarity_threshold = float(os.getenv("RAG_SIMILARITY_THRESHOLD", "0.5"))

    def get_embedding(self, text: str) -> List[float]:
        """调用API获取文本的向量表示"""
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

        raise Exception("获取向量失败，请检查API配置或网络连接")

    def retrieve(
        self,
        query: str,
        top_k: Optional[int] = None,
        chunk_type: Optional[str] = None,
        destination: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        检索相关旅行攻略

        Args:
            query: 查询文本（如目的地名称或旅行需求）
            top_k: 返回结果数量，默认5
            chunk_type: 切片类型过滤（如'spots', 'food', 'transport'等）
            destination: 目的地过滤

        Returns:
            检索结果列表，每个结果包含:
            - chunk_text: 文本内容
            - chunk_type: 切片类型
            - similarity: 相似度分数
            - note_id: 关联的笔记ID
            - destination: 目的地
        """
        top_k = top_k or self.default_top_k

        try:
            # 获取查询向量
            query_embedding = self.get_embedding(query)

            # 连接数据库
            conn = psycopg2.connect(**self.db_config)
            cursor = conn.cursor(psycopg2.extras.RealDictCursor)

            # 构建SQL查询
            # 使用pgvector的余弦相似度运算符 <=>
            # 注意：余弦距离 = 1 - 余弦相似度，所以距离越小越相似
            sql = """
                SELECT
                    c.id,
                    c.note_id,
                    c.chunk_type,
                    c.chunk_text,
                    c.embedding <=> %s::vector AS distance,
                    n.destination,
                    n.transport_info,
                    n.accommodation_info,
                    n.must_visit_spots,
                    n.food_recommendations,
                    n.practical_tips,
                    n.travel_feelings
                FROM xhs_note_chunks c
                JOIN xhs_notes n ON c.note_id = n.id
                WHERE 1=1
            """
            params = [query_embedding]

            # 添加过滤条件
            if chunk_type:
                sql += " AND c.chunk_type = %s"
                params.append(chunk_type)

            if destination:
                sql += " AND n.destination ILIKE %s"
                params.append(f"%{destination}%")

            # 按相似度排序并限制结果数量
            sql += " ORDER BY c.embedding <=> %s::vector ASC LIMIT %s"
            params.extend([query_embedding, top_k])

            cursor.execute(sql, params)
            results = cursor.fetchall()

            # 转换结果格式
            formatted_results = []
            for row in results:
                similarity = 1 - row['distance']  # 转换距离为相似度
                if similarity >= self.similarity_threshold:
                    formatted_results.append({
                        'id': row['id'],
                        'note_id': row['note_id'],
                        'chunk_type': row['chunk_type'],
                        'chunk_text': row['chunk_text'],
                        'similarity': round(similarity, 4),
                        'destination': row['destination'],
                        'transport_info': row['transport_info'],
                        'accommodation_info': row['accommodation_info'],
                        'must_visit_spots': row['must_visit_spots'],
                        'food_recommendations': row['food_recommendations'],
                        'practical_tips': row['practical_tips'],
                        'travel_feelings': row['travel_feelings']
                    })

            cursor.close()
            conn.close()

            logger.info(f"RAG检索完成: 查询='{query}', 返回{len(formatted_results)}条结果")
            return formatted_results

        except Exception as e:
            logger.error(f"RAG检索失败: {e}")
            return []

    def retrieve_for_destination(
        self,
        destination: str,
        top_k: int = 5
    ) -> Dict[str, Any]:
        """
        为指定目的地检索综合旅行信息

        Args:
            destination: 目的地名称
            top_k: 每种类型返回的结果数量

        Returns:
            包含各类旅行信息的字典
        """
        result = {
            'destination': destination,
            'spots': [],
            'food': [],
            'transport': [],
            'accommodation': [],
            'tips': [],
            'all_chunks': []
        }

        try:
            # 检索所有相关内容
            all_results = self.retrieve(
                query=f"去{destination}旅游",
                top_k=top_k * 2,  # 获取更多结果用于分类
                destination=destination
            )

            # 按类型分类
            for item in all_results:
                chunk_type = item.get('chunk_type', '')
                if chunk_type == 'spots':
                    result['spots'].append(item)
                elif chunk_type == 'food':
                    result['food'].append(item)
                elif chunk_type == 'transport':
                    result['transport'].append(item)
                elif chunk_type == 'accommodation':
                    result['accommodation'].append(item)
                elif chunk_type == 'tips':
                    result['tips'].append(item)

            result['all_chunks'] = all_results

            # 如果没有按类型分类的结果，直接使用所有结果
            if not any([result['spots'], result['food'], result['transport'],
                       result['accommodation'], result['tips']]):
                result['spots'] = all_results

            logger.info(f"目的地'{destination}'检索完成: 景点{len(result['spots'])}条, "
                       f"美食{len(result['food'])}条, 交通{len(result['transport'])}条")

            return result

        except Exception as e:
            logger.error(f"目的地检索失败: {e}")
            return result

    def build_rag_context(
        self,
        destination: str,
        duration_days: Optional[int] = None,
        preferences: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        构建RAG上下文文本，用于提供给AI生成旅行计划

        Args:
            destination: 目的地
            duration_days: 旅行天数
            preferences: 用户偏好

        Returns:
            格式化的上下文文本
        """
        # 检索相关信息
        rag_data = self.retrieve_for_destination(destination, top_k=5)

        if not rag_data['all_chunks']:
            logger.warning(f"未找到目的地'{destination}'的相关攻略数据")
            return ""

        # 构建上下文文本
        context_parts = [f"【{destination}旅行攻略参考】\n"]

        # 景点信息
        if rag_data['spots']:
            context_parts.append("【必打卡景点】")
            for i, item in enumerate(rag_data['spots'][:3], 1):
                context_parts.append(f"{i}. {item['chunk_text']}")
            context_parts.append("")

        # 美食推荐
        if rag_data['food']:
            context_parts.append("【美食推荐】")
            for i, item in enumerate(rag_data['food'][:3], 1):
                context_parts.append(f"{i}. {item['chunk_text']}")
            context_parts.append("")

        # 交通信息
        if rag_data['transport']:
            context_parts.append("【交通安排】")
            for item in rag_data['transport'][:2]:
                context_parts.append(f"- {item['chunk_text']}")
            context_parts.append("")

        # 住宿信息
        if rag_data['accommodation']:
            context_parts.append("【住宿推荐】")
            for item in rag_data['accommodation'][:2]:
                context_parts.append(f"- {item['chunk_text']}")
            context_parts.append("")

        # 实用贴士
        if rag_data['tips']:
            context_parts.append("【实用小贴士】")
            for item in rag_data['tips'][:3]:
                context_parts.append(f"- {item['chunk_text']}")
            context_parts.append("")

        # 如果没有分类信息，使用原始chunk
        if len(context_parts) == 1 and rag_data['all_chunks']:
            context_parts.append("【相关攻略】")
            for item in rag_data['all_chunks'][:5]:
                context_parts.append(f"- {item['chunk_text']}")

        context_text = "\n".join(context_parts)
        logger.info(f"构建RAG上下文完成，长度: {len(context_text)}字符")

        return context_text


# 全局单例
_rag_retriever: Optional[RAGRetriever] = None


def get_rag_retriever() -> RAGRetriever:
    """获取RAG检索器单例"""
    global _rag_retriever
    if _rag_retriever is None:
        _rag_retriever = RAGRetriever()
    return _rag_retriever