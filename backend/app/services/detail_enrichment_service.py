"""
详情获取服务
用于获取景点、住宿、餐饮的详细信息（高德API + LLM生成介绍）
"""

from typing import Dict, Any, Optional, List
from loguru import logger
import httpx
from app.core.config import settings
from app.tools.amap_rest_client import amap_rest_client
from app.tools.openai_client import openai_client


class DetailEnrichmentService:
    """详情获取服务"""

    def __init__(self):
        self.amap_client = amap_rest_client
        self.llm_client = openai_client

    async def enrich_attraction_detail(
        self,
        name: str,
        city: str,
        address: Optional[str] = None,
        coordinates: Optional[Dict[str, float]] = None
    ) -> Dict[str, Any]:
        """
        获取景点详细信息

        Args:
            name: 景点名称
            city: 城市
            address: 地址（可选）
            coordinates: 坐标（可选）

        Returns:
            包含详细信息的字典
        """
        try:
            result = {
                "name": name,
                "city": city,
                "address": address,
                "coordinates": coordinates,
                "description": "",
                "images": [],
                "rating": None,
                "opening_hours": "",
                "phone": "",
                "website": "",
                "facilities": [],
                "ticket_price": None,
                "price_note": "",
                "tips": [],
                "reviews": [],
                "highlights": [],
                "best_time": "",
                "duration": "",
                "source": "高德API + LLM生成"
            }

            # 1. 调用高德API获取POI详情
            amap_data = await self._search_amap_poi(name, city, "景点")

            if amap_data:
                # 合并高德数据
                result["address"] = amap_data.get("address", address)
                result["coordinates"] = amap_data.get("coordinates", coordinates)
                result["rating"] = amap_data.get("rating")
                result["phone"] = amap_data.get("phone", "")
                result["opening_hours"] = amap_data.get("biz_ext", {}).get("opening", "")
                result["images"] = amap_data.get("photos", [])
                result["ticket_price"] = amap_data.get("price")
                result["price_note"] = amap_data.get("cost", "")
                result["facilities"] = self._extract_facilities(amap_data)

            # 2. 调用LLM生成详细景点介绍
            description = await self._generate_attraction_description(name, city, amap_data)
            result["description"] = description

            # 3. 生成游览提示
            tips = await self._generate_attraction_tips(name, city, amap_data)
            result["tips"] = tips

            # 4. 生成真实评价信息
            reviews = await self._generate_attraction_reviews(name, city, amap_data)
            result["reviews"] = reviews

            # 5. 生成亮点特色
            highlights = await self._generate_attraction_highlights(name, city, amap_data)
            result["highlights"] = highlights

            # 6. 生成最佳游览时间和推荐时长
            best_time, duration = await self._generate_visit_info(name, city, amap_data)
            result["best_time"] = best_time
            result["duration"] = duration

            logger.info(f"景点详情获取完成: {name} in {city}")
            return result

        except Exception as e:
            logger.error(f"获取景点详情失败: {e}")
            return {
                "name": name,
                "city": city,
                "error": str(e),
                "source": "获取失败"
            }

    async def enrich_hotel_detail(
        self,
        name: str,
        city: str,
        address: Optional[str] = None,
        coordinates: Optional[Dict[str, float]] = None
    ) -> Dict[str, Any]:
        """
        获取住宿详细信息

        Args:
            name: 酒店名称
            city: 城市
            address: 地址（可选）
            coordinates: 坐标（可选）

        Returns:
            包含详细信息的字典
        """
        try:
            result = {
                "name": name,
                "city": city,
                "address": address,
                "coordinates": coordinates,
                "description": "",
                "images": [],
                "rating": None,
                "star_rating": None,
                "opening_hours": "24小时",
                "phone": "",
                "website": "",
                "facilities": [],
                "price_per_night": None,
                "price_note": "",
                "check_in": "14:00",
                "check_out": "12:00",
                "tips": [],
                "reviews": [],
                "highlights": [],
                "source": "高德API + LLM生成"
            }

            # 1. 调用高德API获取POI详情
            amap_data = await self._search_amap_poi(name, city, "酒店")

            if amap_data:
                # 合并高德数据
                result["address"] = amap_data.get("address", address)
                result["coordinates"] = amap_data.get("coordinates", coordinates)
                result["rating"] = amap_data.get("rating")
                result["phone"] = amap_data.get("phone", "")
                result["images"] = amap_data.get("photos", [])
                result["price_per_night"] = amap_data.get("price")
                result["price_note"] = amap_data.get("cost", "")
                result["facilities"] = self._extract_facilities(amap_data)

            # 2. 调用LLM生成详细酒店介绍
            description = await self._generate_hotel_description(name, city, amap_data)
            result["description"] = description

            # 3. 生成住宿提示
            tips = await self._generate_hotel_tips(name, city, amap_data)
            result["tips"] = tips

            # 4. 生成真实评价信息
            reviews = await self._generate_hotel_reviews(name, city, amap_data)
            result["reviews"] = reviews

            # 5. 生成亮点特色
            highlights = await self._generate_hotel_highlights(name, city, amap_data)
            result["highlights"] = highlights

            logger.info(f"酒店详情获取完成: {name} in {city}")
            return result

        except Exception as e:
            logger.error(f"获取酒店详情失败: {e}")
            return {
                "name": name,
                "city": city,
                "error": str(e),
                "source": "获取失败"
            }

    async def enrich_meal_detail(
        self,
        name: str,
        city: str,
        cuisine: Optional[str] = None,
        address: Optional[str] = None,
        coordinates: Optional[Dict[str, float]] = None
    ) -> Dict[str, Any]:
        """
        获取餐饮详细信息

        Args:
            name: 餐厅名称
            city: 城市
            cuisine: 菜系（可选）
            address: 地址（可选）
            coordinates: 坐标（可选）

        Returns:
            包含详细信息的字典
        """
        try:
            result = {
                "name": name,
                "city": city,
                "cuisine": cuisine,
                "address": address,
                "coordinates": coordinates,
                "description": "",
                "images": [],
                "rating": None,
                "opening_hours": "",
                "phone": "",
                "website": "",
                "facilities": [],
                "average_cost": None,
                "price_note": "",
                "recommended_dishes": [],
                "tips": [],
                "reviews": [],
                "highlights": [],
                "source": "高德API + LLM生成"
            }

            # 1. 调用高德API获取POI详情
            amap_data = await self._search_amap_poi(name, city, "餐厅")

            if amap_data:
                # 合并高德数据
                result["address"] = amap_data.get("address", address)
                result["coordinates"] = amap_data.get("coordinates", coordinates)
                result["rating"] = amap_data.get("rating")
                result["phone"] = amap_data.get("phone", "")
                result["opening_hours"] = amap_data.get("biz_ext", {}).get("opening", "")
                result["images"] = amap_data.get("photos", [])
                result["average_cost"] = amap_data.get("price")
                result["price_note"] = amap_data.get("cost", "")
                result["facilities"] = self._extract_facilities(amap_data)

            # 2. 调用LLM生成详细餐厅介绍
            description = await self._generate_meal_description(name, city, cuisine, amap_data)
            result["description"] = description

            # 3. 生成推荐菜品
            dishes = await self._generate_recommended_dishes(name, city, cuisine, amap_data)
            result["recommended_dishes"] = dishes

            # 4. 生成用餐提示
            tips = await self._generate_meal_tips(name, city, cuisine, amap_data)
            result["tips"] = tips

            # 5. 生成真实评价信息
            reviews = await self._generate_meal_reviews(name, city, cuisine, amap_data)
            result["reviews"] = reviews

            # 6. 生成亮点特色
            highlights = await self._generate_meal_highlights(name, city, cuisine, amap_data)
            result["highlights"] = highlights

            logger.info(f"餐厅详情获取完成: {name} in {city}")
            return result

        except Exception as e:
            logger.error(f"获取餐厅详情失败: {e}")
            return {
                "name": name,
                "city": city,
                "error": str(e),
                "source": "获取失败"
            }

    async def _search_amap_poi(
        self,
        name: str,
        city: str,
        category: str
    ) -> Optional[Dict[str, Any]]:
        """搜索高德POI"""
        try:
            places = await self.amap_client.search_places(name, city, category)

            if places and len(places) > 0:
                # 返回最匹配的第一个结果
                return places[0]

            return None

        except Exception as e:
            logger.warning(f"高德POI搜索失败: {e}")
            return None

    def _extract_facilities(self, amap_data: Dict[str, Any]) -> List[str]:
        """从高德数据提取设施信息"""
        facilities = []

        # 从标签中提取
        tags = amap_data.get("tags", [])
        facility_keywords = ["停车场", "WiFi", "餐厅", "洗手间", "无障碍", "充电", "行李寄存", "健身房", "游泳池", "会议室"]

        for tag in tags:
            for keyword in facility_keywords:
                if keyword in tag:
                    facilities.append(tag)
                    break

        # 默认设施
        if not facilities:
            facilities = ["停车场", "洗手间"]

        return facilities

    async def _generate_attraction_description(
        self,
        name: str,
        city: str,
        amap_data: Optional[Dict[str, Any]]
    ) -> str:
        """生成详细的景点介绍"""
        try:
            # 构建上下文信息
            context = f"景点名称：{name}\n城市：{city}"

            if amap_data:
                context += f"\n地址：{amap_data.get('address', '')}"
                context += f"\n评分：{amap_data.get('rating', '未知')}"
                context += f"\n类型：{amap_data.get('category', '')}"

            prompt = f"""请为以下景点生成一段详细的介绍（200-300字），包含以下内容：

{context}

要求：
1. 开头用一句话概括景点的核心特色
2. 介绍景点的历史背景、文化价值或自然特色
3. 描述景点的主要看点或必游之处
4. 语言生动优美，适合游客阅读
5. 不要包含具体门票价格和开放时间（这些信息会单独显示）
6. 内容要真实可信，避免过度夸张"""

            description = await self.llm_client.generate_text(
                prompt=prompt,
                max_tokens=500,
                temperature=0.7
            )

            return description.strip()

        except Exception as e:
            logger.warning(f"生成景点介绍失败: {e}")
            return f"{name}是{city}的著名景点，拥有独特的历史文化价值和自然风光，是游客必去的打卡之地。"

    async def _generate_attraction_reviews(
        self,
        name: str,
        city: str,
        amap_data: Optional[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """生成真实评价信息"""
        try:
            rating = amap_data.get('rating', 4.5) if amap_data else 4.5

            prompt = f"""请为景点"{name}"（位于{city}，评分{rating}分）生成3-4条真实的游客评价。

要求：
1. 每条评价包含：评价内容（30-60字）、评分（4-5星）、评价者类型（如"家庭游客"、"情侣"、"独自旅行"等）
2. 评价内容要真实可信，包含正面评价和建设性建议
3. 评价风格要多样化，有的侧重景色，有的侧重服务，有的侧重性价比
4. 格式为JSON数组，每条评价格式为：{{"content": "评价内容", "rating": 评分, "visitor_type": "评价者类型"}}

只输出JSON数组，不要其他内容。"""

            reviews_text = await self.llm_client.generate_text(
                prompt=prompt,
                max_tokens=400,
                temperature=0.8
            )

            # 尝试解析JSON
            import json
            try:
                # 提取JSON部分
                json_start = reviews_text.find('[')
                json_end = reviews_text.rfind(']') + 1
                if json_start != -1 and json_end > json_start:
                    json_str = reviews_text[json_start:json_end]
                    reviews = json.loads(json_str)
                    return reviews[:4]
            except json.JSONDecodeError:
                pass

            # 如果解析失败，返回默认评价
            return [
                {"content": f"{name}景色优美，值得一游。建议早点去避开人流高峰。", "rating": 5, "visitor_type": "家庭游客"},
                {"content": f"景点很有特色，但周末人比较多。建议工作日前往体验更好。", "rating": 4, "visitor_type": "情侣"},
            ]

        except Exception as e:
            logger.warning(f"生成景点评价失败: {e}")
            return [
                {"content": f"{name}是{city}的必游景点，推荐前往。", "rating": 5, "visitor_type": "游客"},
            ]

    async def _generate_attraction_highlights(
        self,
        name: str,
        city: str,
        amap_data: Optional[Dict[str, Any]]
    ) -> List[str]:
        """生成景点亮点特色"""
        try:
            prompt = f"""请为景点"{name}"（位于{city}）列出3-4个亮点特色，每个亮点一句话。

要求：
1. 突出景点的独特之处
2. 简洁明了，每条不超过20字
3. 用游客视角描述

只输出亮点列表，每行一个，不要序号。"""

            highlights_text = await self.llm_client.generate_text(
                prompt=prompt,
                max_tokens=150,
                temperature=0.7
            )

            highlights = []
            for line in highlights_text.strip().split('\n'):
                line = line.strip()
                if line and not line.startswith('#'):
                    # 移除序号
                    if line and line[0].isdigit():
                        line = line.lstrip('0123456789.-、 ').strip()
                    if line:
                        highlights.append(line)

            return highlights[:4]

        except Exception as e:
            logger.warning(f"生成景点亮点失败: {e}")
            return ["景色优美", "交通便利", "适合拍照"]

    async def _generate_visit_info(
        self,
        name: str,
        city: str,
        amap_data: Optional[Dict[str, Any]]
    ) -> tuple:
        """生成最佳游览时间和推荐时长"""
        try:
            prompt = f"""请为景点"{name}"（位于{city}）提供以下信息：

1. 最佳游览时间（如"春季3-5月"、"全年皆宜"等）
2. 推荐游览时长（如"2-3小时"、"半天"等）

请用JSON格式输出：{{"best_time": "最佳游览时间", "duration": "推荐游览时长"}}"""

            info_text = await self.llm_client.generate_text(
                prompt=prompt,
                max_tokens=100,
                temperature=0.7
            )

            import json
            try:
                json_start = info_text.find('{')
                json_end = info_text.rfind('}') + 1
                if json_start != -1 and json_end > json_start:
                    json_str = info_text[json_start:json_end]
                    info = json.loads(json_str)
                    return info.get("best_time", "全年皆宜"), info.get("duration", "2-3小时")
            except json.JSONDecodeError:
                pass

            return "全年皆宜", "2-3小时"

        except Exception as e:
            logger.warning(f"生成游览信息失败: {e}")
            return "全年皆宜", "2-3小时"

    async def _generate_attraction_tips(
        self,
        name: str,
        city: str,
        amap_data: Optional[Dict[str, Any]]
    ) -> List[str]:
        """生成游览提示"""
        try:
            prompt = f"""请为景点"{name}"（位于{city}）生成3-5条实用的游览提示，每条一句话。

要求：
1. 简洁实用
2. 针对游客需求
3. 包含最佳游览时间、注意事项等"""

            tips_text = await self.llm_client.generate_text(
                prompt=prompt,
                max_tokens=200,
                temperature=0.7
            )

            # 解析为列表
            tips = []
            for line in tips_text.strip().split('\n'):
                line = line.strip()
                if line and not line.startswith('#'):
                    # 移除序号
                    if line[0].isdigit():
                        line = line.lstrip('0123456789.- ').strip()
                    if line:
                        tips.append(line)

            return tips[:5]

        except Exception as e:
            logger.warning(f"生成游览提示失败: {e}")
            return ["建议提前了解开放时间", "注意保管个人物品"]

    async def _generate_hotel_description(
        self,
        name: str,
        city: str,
        amap_data: Optional[Dict[str, Any]]
    ) -> str:
        """生成详细的酒店介绍"""
        try:
            context = f"酒店名称：{name}\n城市：{city}"

            if amap_data:
                context += f"\n地址：{amap_data.get('address', '')}"
                context += f"\n评分：{amap_data.get('rating', '未知')}"

            prompt = f"""请为以下酒店生成一段详细的介绍（150-250字），包含以下内容：

{context}

要求：
1. 开头用一句话概括酒店的核心特色
2. 介绍酒店的地理位置优势（如靠近景点、交通便利等）
3. 描述酒店的服务特色和设施亮点
4. 语言简洁专业，适合游客阅读
5. 内容要真实可信"""

            description = await self.llm_client.generate_text(
                prompt=prompt,
                max_tokens=400,
                temperature=0.7
            )

            return description.strip()

        except Exception as e:
            logger.warning(f"生成酒店介绍失败: {e}")
            return f"{name}位于{city}，地理位置优越，提供舒适的住宿体验和贴心的服务。"

    async def _generate_hotel_reviews(
        self,
        name: str,
        city: str,
        amap_data: Optional[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """生成酒店真实评价信息"""
        try:
            rating = amap_data.get('rating', 4.5) if amap_data else 4.5

            prompt = f"""请为酒店"{name}"（位于{city}，评分{rating}分）生成3-4条真实的住客评价。

要求：
1. 每条评价包含：评价内容（30-60字）、评分（4-5星）、评价者类型（如"商务出行"、"家庭旅游"、"情侣度假"等）
2. 评价内容要真实可信，包含正面评价和建设性建议
3. 评价风格要多样化，有的侧重位置，有的侧重服务，有的侧重设施
4. 格式为JSON数组，每条评价格式为：{{"content": "评价内容", "rating": 评分, "visitor_type": "评价者类型"}}

只输出JSON数组，不要其他内容。"""

            reviews_text = await self.llm_client.generate_text(
                prompt=prompt,
                max_tokens=400,
                temperature=0.8
            )

            import json
            try:
                json_start = reviews_text.find('[')
                json_end = reviews_text.rfind(']') + 1
                if json_start != -1 and json_end > json_start:
                    json_str = reviews_text[json_start:json_end]
                    reviews = json.loads(json_str)
                    return reviews[:4]
            except json.JSONDecodeError:
                pass

            return [
                {"content": f"酒店位置很好，服务态度不错，房间干净整洁。", "rating": 5, "visitor_type": "商务出行"},
                {"content": f"设施齐全，早餐丰富，性价比高。", "rating": 4, "visitor_type": "家庭旅游"},
            ]

        except Exception as e:
            logger.warning(f"生成酒店评价失败: {e}")
            return [
                {"content": f"{name}住宿体验不错，推荐入住。", "rating": 5, "visitor_type": "游客"},
            ]

    async def _generate_hotel_highlights(
        self,
        name: str,
        city: str,
        amap_data: Optional[Dict[str, Any]]
    ) -> List[str]:
        """生成酒店亮点特色"""
        try:
            prompt = f"""请为酒店"{name}"（位于{city}）列出3-4个亮点特色，每个亮点一句话。

要求：
1. 突出酒店的独特之处
2. 简洁明了，每条不超过20字
3. 用住客视角描述

只输出亮点列表，每行一个，不要序号。"""

            highlights_text = await self.llm_client.generate_text(
                prompt=prompt,
                max_tokens=150,
                temperature=0.7
            )

            highlights = []
            for line in highlights_text.strip().split('\n'):
                line = line.strip()
                if line and not line.startswith('#'):
                    if line and line[0].isdigit():
                        line = line.lstrip('0123456789.-、 ').strip()
                    if line:
                        highlights.append(line)

            return highlights[:4]

        except Exception as e:
            logger.warning(f"生成酒店亮点失败: {e}")
            return ["位置优越", "服务周到", "设施齐全"]

    async def _generate_hotel_tips(
        self,
        name: str,
        city: str,
        amap_data: Optional[Dict[str, Any]]
    ) -> List[str]:
        """生成住宿提示"""
        try:
            prompt = f"""请为酒店"{name}"（位于{city}）生成3条实用的住宿提示，每条一句话。

要求：
1. 简洁实用
2. 针对住客需求
3. 包含入住注意事项"""

            tips_text = await self.llm_client.generate_text(
                prompt=prompt,
                max_tokens=150,
                temperature=0.7
            )

            tips = []
            for line in tips_text.strip().split('\n'):
                line = line.strip()
                if line and not line.startswith('#'):
                    if line[0].isdigit():
                        line = line.lstrip('0123456789.- ').strip()
                    if line:
                        tips.append(line)

            return tips[:3]

        except Exception as e:
            logger.warning(f"生成住宿提示失败: {e}")
            return ["建议提前预订", "入住时确认房间设施"]

    async def _generate_meal_description(
        self,
        name: str,
        city: str,
        cuisine: Optional[str],
        amap_data: Optional[Dict[str, Any]]
    ) -> str:
        """生成详细的餐厅介绍"""
        try:
            context = f"餐厅名称：{name}\n城市：{city}"
            if cuisine:
                context += f"\n菜系：{cuisine}"

            if amap_data:
                context += f"\n地址：{amap_data.get('address', '')}"
                context += f"\n评分：{amap_data.get('rating', '未知')}"

            prompt = f"""请为以下餐厅生成一段详细的介绍（150-250字），包含以下内容：

{context}

要求：
1. 开头用一句话概括餐厅的核心特色
2. 介绍餐厅的菜品特色和口味风格
3. 描述餐厅的环境氛围和服务特点
4. 语言生动诱人，适合食客阅读
5. 内容要真实可信"""

            description = await self.llm_client.generate_text(
                prompt=prompt,
                max_tokens=400,
                temperature=0.7
            )

            return description.strip()

        except Exception as e:
            logger.warning(f"生成餐厅介绍失败: {e}")
            return f"{name}是{city}的特色餐厅，提供美味的{cuisine or '当地'}菜肴，深受食客喜爱。"

    async def _generate_recommended_dishes(
        self,
        name: str,
        city: str,
        cuisine: Optional[str],
        amap_data: Optional[Dict[str, Any]]
    ) -> List[str]:
        """生成推荐菜品"""
        try:
            prompt = f"""请为餐厅"{name}"（位于{city}，菜系：{cuisine or '当地特色'}）推荐4-5道招牌菜品。

要求：
1. 每道菜品一行
2. 简洁明了
3. 符合餐厅特色"""

            dishes_text = await self.llm_client.generate_text(
                prompt=prompt,
                max_tokens=150,
                temperature=0.7
            )

            dishes = []
            for line in dishes_text.strip().split('\n'):
                line = line.strip()
                if line and not line.startswith('#'):
                    if line[0].isdigit():
                        line = line.lstrip('0123456789.- ').strip()
                    if line:
                        dishes.append(line)

            return dishes[:5]

        except Exception as e:
            logger.warning(f"生成推荐菜品失败: {e}")
            return ["特色招牌菜", "当地特色美食"]

    async def _generate_meal_reviews(
        self,
        name: str,
        city: str,
        cuisine: Optional[str],
        amap_data: Optional[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """生成餐厅真实评价信息"""
        try:
            rating = amap_data.get('rating', 4.5) if amap_data else 4.5

            prompt = f"""请为餐厅"{name}"（位于{city}，菜系：{cuisine or '当地特色'}，评分{rating}分）生成3-4条真实的食客评价。

要求：
1. 每条评价包含：评价内容（30-60字）、评分（4-5星）、评价者类型（如"美食爱好者"、"家庭聚餐"、"朋友聚会"等）
2. 评价内容要真实可信，包含对菜品、环境、服务的评价
3. 评价风格要多样化
4. 格式为JSON数组，每条评价格式为：{{"content": "评价内容", "rating": 评分, "visitor_type": "评价者类型"}}

只输出JSON数组，不要其他内容。"""

            reviews_text = await self.llm_client.generate_text(
                prompt=prompt,
                max_tokens=400,
                temperature=0.8
            )

            import json
            try:
                json_start = reviews_text.find('[')
                json_end = reviews_text.rfind(']') + 1
                if json_start != -1 and json_end > json_start:
                    json_str = reviews_text[json_start:json_end]
                    reviews = json.loads(json_str)
                    return reviews[:4]
            except json.JSONDecodeError:
                pass

            return [
                {"content": f"菜品味道不错，分量足，性价比高。", "rating": 5, "visitor_type": "美食爱好者"},
                {"content": f"环境干净整洁，服务态度好。", "rating": 4, "visitor_type": "家庭聚餐"},
            ]

        except Exception as e:
            logger.warning(f"生成餐厅评价失败: {e}")
            return [
                {"content": f"{name}的菜品很有特色，推荐尝试。", "rating": 5, "visitor_type": "食客"},
            ]

    async def _generate_meal_highlights(
        self,
        name: str,
        city: str,
        cuisine: Optional[str],
        amap_data: Optional[Dict[str, Any]]
    ) -> List[str]:
        """生成餐厅亮点特色"""
        try:
            prompt = f"""请为餐厅"{name}"（位于{city}，菜系：{cuisine or '当地特色'}）列出3-4个亮点特色，每个亮点一句话。

要求：
1. 突出餐厅的独特之处
2. 简洁明了，每条不超过20字
3. 用食客视角描述

只输出亮点列表，每行一个，不要序号。"""

            highlights_text = await self.llm_client.generate_text(
                prompt=prompt,
                max_tokens=150,
                temperature=0.7
            )

            highlights = []
            for line in highlights_text.strip().split('\n'):
                line = line.strip()
                if line and not line.startswith('#'):
                    if line and line[0].isdigit():
                        line = line.lstrip('0123456789.-、 ').strip()
                    if line:
                        highlights.append(line)

            return highlights[:4]

        except Exception as e:
            logger.warning(f"生成餐厅亮点失败: {e}")
            return ["菜品地道", "价格实惠", "服务热情"]

    async def _generate_meal_tips(
        self,
        name: str,
        city: str,
        cuisine: Optional[str],
        amap_data: Optional[Dict[str, Any]]
    ) -> List[str]:
        """生成用餐提示"""
        try:
            prompt = f"""请为餐厅"{name}"（位于{city}）生成3条实用的用餐提示，每条一句话。

要求：
1. 简洁实用
2. 针对食客需求
3. 包含用餐注意事项"""

            tips_text = await self.llm_client.generate_text(
                prompt=prompt,
                max_tokens=150,
                temperature=0.7
            )

            tips = []
            for line in tips_text.strip().split('\n'):
                line = line.strip()
                if line and not line.startswith('#'):
                    if line[0].isdigit():
                        line = line.lstrip('0123456789.- ').strip()
                    if line:
                        tips.append(line)

            return tips[:3]

        except Exception as e:
            logger.warning(f"生成用餐提示失败: {e}")
            return ["建议提前预订", "注意营业时间"]


# 创建全局服务实例
detail_enrichment_service = DetailEnrichmentService()