"""
百度 OCR 文字识别服务
支持通用文字识别、表格识别、印章识别等多种 OCR 能力
"""

import os
import base64
import hashlib
import json
import time
from typing import Optional, Dict, Any, List
from loguru import logger
import httpx
from app.core.config import settings


class BaiduOCRService:
    """百度 OCR 服务封装类"""

    def __init__(self):
        # 修复1：直接从 settings 获取，不需要 hasattr 检查
        self.api_key: str = settings.BAIDU_OCR_API_KEY
        self.secret_key: str = settings.BAIDU_OCR_SECRET_KEY
        self.access_token: Optional[str] = None
        self.token_expires_at: float = 0

    def _get_access_token(self) -> str:
        """
        获取百度 OCR API Access Token
        使用 AK/SK 获取 Access Token，参考：https://cloud.baidu.com/doc/OCR/s/1kbcwp14z
        """
        if self.access_token is not None and time.time() < self.token_expires_at:
            return self.access_token

        if not self.api_key or not self.secret_key:
            raise ValueError("百度 OCR API 密钥未配置，请设置 BAIDU_OCR_API_KEY 和 BAIDU_OCR_SECRET_KEY")

        token_url = "https://aip.baidubce.com/oauth/2.0/token"
        params = {
            "grant_type": "client_credentials",
            "client_id": self.api_key,
            "client_secret": self.secret_key
        }

        try:
            response = httpx.post(token_url, params=params, timeout=30)
            result = response.json()

            if "access_token" in result:
                self.access_token = result["access_token"]
                self.token_expires_at = time.time() + result.get("expires_in", 2592000) - 300
                logger.info(f"✅ 百度 OCR Access Token 获取成功")
                return str(self.access_token)
            else:
                error_msg = result.get("error_description", "未知错误")
                logger.error(f"❌ 百度 OCR Access Token 获取失败: {error_msg}")
                raise Exception(f"获取 Access Token 失败: {error_msg}")

        except httpx.HTTPError as e:
            logger.error(f"❌ HTTP 请求获取 Access Token 失败: {e}")
            raise

    async def _call_ocr_api(self, endpoint: str, params: Dict[str, Any], image_data: Optional[str] = None) -> Dict[str, Any]:
        """
        调用百度 OCR API 的通用方法

        Args:
            endpoint: OCR API 端点
            params: 请求参数
            image_data: base64 编码的图片数据（可选）

        Returns:
            API 响应结果
        """
        access_token = self._get_access_token()
        url = f"https://aip.baidubce.com/rest/2.0/ocr/v1/{endpoint}"

        headers = {"Content-Type": "application/x-www-form-urlencoded"}

        if image_data:
            params["image"] = image_data

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    url,
                    headers=headers,
                    data=params,
                    params={"access_token": access_token},
                    timeout=60
                )
                result = response.json()

                if result.get("error_code"):
                    error_msg = result.get("error_msg", "未知错误")
                    logger.error(f"❌ 百度 OCR API 错误: {error_msg}")
                    raise Exception(f"OCR API 错误: {error_msg}")

                return result

        except httpx.HTTPError as e:
            logger.error(f"❌ 调用百度 OCR API 失败: {e}")
            raise

    async def recognize_general_text(self, image_base64: str) -> str:
        """
        通用文字识别 - 识别图片中的文字

        Args:
            image_base64: base64 编码的图片数据（不含前缀 data:image/...;base64,）

        Returns:
            识别出的文字内容
        """
        logger.info("开始通用文字识别...")

        params = {"image": image_base64}
        result = await self._call_ocr_api("accurate_basic", params)

        words_result = result.get("words_result", [])
        if not words_result:
            logger.warning("未识别到文字内容")
            return ""

        full_text = "\n".join([item.get("words", "") for item in words_result])
        logger.info(f"✅ 通用文字识别成功，识别了 {len(words_result)} 行文字")

        return full_text

    async def recognize_general_text_async(self, image_base64: str) -> Dict[str, Any]:
        """
        通用文字识别（返回完整结果）

        Args:
            image_base64: base64 编码的图片数据

        Returns:
            包含详细位置信息的识别结果
        """
        logger.info("开始通用文字识别（异步）...")

        params = {
            "image": image_base64,
            "detect_direction": "true",
            "recognize_granularity": "small"
        }
        result = await self._call_ocr_api("general", params)

        return result

    async def recognize_web_image(self, image_base64: str) -> Dict[str, Any]:
        """
        网络图片文字识别 - 识别网络图片中的文字

        Args:
            image_base64: base64 编码的图片数据

        Returns:
            识别结果
        """
        logger.info("开始网络图片文字识别...")

        params = {"image": image_base64}
        result = await self._call_ocr_api("webimage", params)

        words_result = result.get("words_result", [])
        full_text = "\n".join([item.get("words", "") for item in words_result])

        logger.info(f"✅ 网络图片文字识别成功，识别了 {len(words_result)} 个文字块")

        return {
            "text": full_text,
            "words_result": words_result
        }

    async def recognize_handwriting(self, image_base64: str) -> str:
        """
        手写文字识别 - 识别手写文字

        Args:
            image_base64: base64 编码的图片数据

        Returns:
            识别出的手写文字内容
        """
        logger.info("开始手写文字识别...")

        params = {"image": image_base64}
        result = await self._call_ocr_api("handwriting", params)

        words_result = result.get("words_result", [])
        if not words_result:
            logger.warning("未识别到手写文字内容")
            return ""

        full_text = "\n".join([item.get("words", "") for item in words_result])
        logger.info(f"✅ 手写文字识别成功，识别了 {len(words_result)} 个文字块")

        return full_text

    async def recognize_travel_itinerary(self, image_base64: str) -> Dict[str, Any]:
        """
        识别旅游攻略图片中的文字（综合多种识别模式）

        Args:
            image_base64: base64 编码的图片数据

        Returns:
            识别结果，包含文本和关键信息
        """
        logger.info("开始旅游攻略图片文字识别...")

        all_text_parts: List[str] = []

        try:
            general_result = await self.recognize_general_text(image_base64)
            if general_result:
                all_text_parts.append(general_result)
                logger.info(f"通用文字识别获取 {len(general_result)} 字符")
        except Exception as e:
            logger.warning(f"通用文字识别失败: {e}")

        try:
            web_result = await self.recognize_web_image(image_base64)
            if web_result.get("text"):
                all_text_parts.append(web_result["text"])
                logger.info(f"网络图片识别获取 {len(web_result['text'])} 字符")
        except Exception as e:
            logger.warning(f"网络图片识别失败: {e}")

        combined_text = "\n".join(all_text_parts)

        logger.info(f"✅ 旅游攻略图片识别完成，总共识别 {len(combined_text)} 字符")

        return {
            "text": combined_text,
            "raw_results": {
                "general": all_text_parts[0] if len(all_text_parts) > 0 else "",
                "web_image": all_text_parts[1] if len(all_text_parts) > 1 else ""
            }
        }

    async def recognize_from_url(self, image_url: str) -> str:
        """
        根据图片 URL 识别文字（下载后识别）

        Args:
            image_url: 图片的网络 URL

        Returns:
            识别出的文字内容
        """
        logger.info(f"从 URL 下载图片并识别: {image_url}")

        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(image_url, timeout=30)
                response.raise_for_status()

                image_data = response.content
                image_base64 = base64.b64encode(image_data).decode("utf-8")

                return await self.recognize_general_text(image_base64)

        except httpx.HTTPError as e:
            logger.error(f"❌ 下载图片失败: {e}")
            raise Exception(f"下载图片失败: {e}")

    def is_configured(self) -> bool:
        """检查 OCR 服务是否已配置"""
        return bool(self.api_key and self.secret_key)


ocr_service = BaiduOCRService()