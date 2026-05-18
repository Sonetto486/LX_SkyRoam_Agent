"""
Wikimedia Commons API 服务
用于获取景点的真实图片
"""

import asyncio
import httpx
from typing import List, Optional, Dict, Any
from loguru import logger
from app.core.redis import get_cache, set_cache

# Wikimedia Commons API 基础 URL
WIKIMEDIA_API_BASE = "https://commons.wikimedia.org/w/api.php"

# 图片最小尺寸要求
MIN_WIDTH = 400
MIN_HEIGHT = 300

# 缓存 TTL（30天）
WIKIMEDIA_CACHE_TTL = 30 * 24 * 3600


class WikimediaService:
    """Wikimedia Commons 图片服务"""

    # 热门景点中英文名称映射表
    ENGLISH_NAME_MAP = {
        # 北京
        "故宫博物院": "Forbidden City",
        "天安门广场": "Tiananmen Square",
        "八达岭长城": "Badaling Great Wall",
        "颐和园": "Summer Palace",
        "天坛": "Temple of Heaven",
        "圆明园": "Old Summer Palace",
        "北海公园": "Beihai Park",
        "南锣鼓巷": "Nanluoguxiang",
        "什刹海": "Shichahai",
        "国家体育场": "National Stadium Beijing",
        "鸟巢": "National Stadium Beijing",
        "国家游泳中心": "National Aquatics Center",
        "水立方": "National Aquatics Center",
        "北京动物园": "Beijing Zoo",
        "景山公园": "Jingshan Park",
        "恭王府": "Prince Kung's Mansion",
        "雍和宫": "Yonghe Temple",
        "国子监": "Imperial College",
        "香山公园": "Fragrant Hills Park",
        "明十三陵": "Ming Tombs",
        "慕田峪长城": "Mutianyu Great Wall",
        "798艺术区": "798 Art Zone",
        "三里屯": "Sanlitun",
        "王府井": "Wangfujing",
        "前门大街": "Qianmen Street",

        # 上海
        "外滩": "The Bund Shanghai",
        "东方明珠广播电视塔": "Oriental Pearl Tower",
        "东方明珠": "Oriental Pearl Tower",
        "上海环球金融中心": "Shanghai World Financial Center",
        "金茂大厦": "Jin Mao Tower",
        "上海中心大厦": "Shanghai Tower",
        "豫园": "Yu Garden Shanghai",
        "城隍庙": "City God Temple Shanghai",
        "南京路步行街": "Nanjing Road Shanghai",
        "人民广场": "People's Square Shanghai",
        "上海博物馆": "Shanghai Museum",
        "田子坊": "Tianzifang",
        "新天地": "Xintiandi",
        "静安寺": "Jing'an Temple",
        "龙华寺": "Longhua Temple",
        "上海迪士尼乐园": "Shanghai Disney Resort",
        "朱家角古镇": "Zhujiajiao",
        "陆家嘴": "Lujiazui",
        "上海外滩": "The Bund Shanghai",

        # 杭州
        "西湖": "West Lake Hangzhou",
        "西湖风景名胜区": "West Lake Hangzhou",
        "灵隐寺": "Lingyin Temple",
        "雷峰塔": "Leifeng Pagoda",
        "三潭印月": "Three Pools Mirroring the Moon",
        "断桥残雪": "Broken Bridge West Lake",
        "苏堤春晓": "Su Causeway West Lake",
        "白堤": "Bai Causeway West Lake",
        "岳王庙": "Yue Fei Temple",
        "千岛湖": "Qiandao Lake",
        "宋城": "Songcheng",
        "西溪湿地": "Xixi Wetland",
        "龙井茶园": "Longjing Tea Village",
        "杭州宋城": "Songcheng",
        "飞来峰": "Feilai Peak",

        # 成都
        "宽窄巷子": "Kuanzhai Alley",
        "锦里": "Jinli Ancient Street",
        "武侯祠": "Wuhou Shrine",
        "杜甫草堂": "Du Fu Thatched Cottage",
        "大熊猫繁育研究基地": "Giant Panda Breeding Research Base",
        "成都大熊猫基地": "Giant Panda Base Chengdu",
        "春熙路": "Chunxi Road",
        "太古里": "Taikoo Li Chengdu",
        "青城山": "Qingcheng Mountain",
        "都江堰": "Dujiangyan Irrigation System",
        "人民公园": "People's Park Chengdu",
        "文殊院": "Wenshu Monastery",

        # 西安
        "秦始皇兵马俑博物馆": "Terracotta Army",
        "兵马俑": "Terracotta Army",
        "大雁塔": "Big Wild Goose Pagoda",
        "小雁塔": "Small Wild Goose Pagoda",
        "西安城墙": "Xi'an City Wall",
        "钟楼": "Bell Tower Xi'an",
        "鼓楼": "Drum Tower Xi'an",
        "回民街": "Muslim Quarter Xi'an",
        "华清池": "Huaqing Pool",
        "大唐芙蓉园": "Tang Paradise",
        "陕西历史博物馆": "Shaanxi History Museum",
        "大雁塔北广场": "Big Wild Goose Pagoda",

        # 南京
        "中山陵": "Sun Yat-sen Mausoleum",
        "明孝陵": "Ming Xiaoling Tomb",
        "夫子庙": "Confucius Temple Nanjing",
        "秦淮河": "Qinhuai River",
        "总统府": "Presidential Palace Nanjing",
        "玄武湖": "Xuanwu Lake",
        "紫金山": "Purple Mountain Nanjing",
        "南京博物院": "Nanjing Museum",
        "侵华日军南京大屠杀遇难同胞纪念馆": "Nanjing Massacre Memorial Hall",
        "鸡鸣寺": "Jiming Temple",
        "瞻园": "Zhan Garden",
        "老门东": "Laomendong",

        # 苏州
        "拙政园": "Humble Administrator's Garden",
        "留园": "Lingering Garden",
        "狮子林": "Lion Grove Garden",
        "寒山寺": "Hanshan Temple",
        "虎丘": "Tiger Hill Suzhou",
        "苏州博物馆": "Suzhou Museum",
        "平江路": "Pingjiang Road",
        "山塘街": "Shantang Street",
        "周庄古镇": "Zhouzhuang",
        "同里古镇": "Tongli",
        "金鸡湖": "Jinji Lake",

        # 厦门
        "鼓浪屿": "Gulangyu Island",
        "南普陀寺": "Nanputuo Temple",
        "厦门大学": "Xiamen University",
        "曾厝垵": "Zengcuo'an",
        "环岛路": "Island Ring Road Xiamen",
        "胡里山炮台": "Hulishan Fortress",
        "中山路步行街": "Zhongshan Road Xiamen",
        "集美学村": "Jimei School Village",
        "日光岩": "Sunlight Rock",

        # 重庆
        "洪崖洞": "Hongya Cave",
        "解放碑": "Jiefangbei",
        "解放碑步行街": "Jiefangbei Pedestrian Street",
        "磁器口古镇": "Ciqikou Ancient Town",
        "长江索道": "Yangtze River Cableway",
        "武隆天生三桥": "Wulong Karst",
        "大足石刻": "Dazu Rock Carvings",
        "南山一棵树": "Nanshan Tree View Platform",
        "朝天门": "Chaotianmen",
        "李子坝轻轨站": "Liziba Station",

        # 广州
        "广州塔": "Canton Tower",
        "小蛮腰": "Canton Tower",
        "陈家祠": "Chen Clan Ancestral Hall",
        "沙面": "Shamian Island",
        "白云山": "Baiyun Mountain",
        "越秀公园": "Yuexiu Park",
        "中山纪念堂": "Sun Yat-sen Memorial Hall",
        "长隆野生动物世界": "Chimelong Safari Park",
        "长隆欢乐世界": "Chimelong Paradise",
        "北京路步行街": "Beijing Road Guangzhou",
        "珠江夜游": "Pearl River Night Cruise",
        "圣心大教堂": "Sacred Heart Cathedral Guangzhou",
    }

    def __init__(self):
        self._http_client: Optional[httpx.AsyncClient] = None
        self._last_request_time = 0
        self._request_interval = 0.2  # 200ms 间隔

    async def _get_client(self) -> httpx.AsyncClient:
        """获取 HTTP 客户端"""
        if self._http_client is None or self._http_client.is_closed:
            # 添加 User-Agent 头，避免 403 错误
            headers = {
                "User-Agent": "LX-SkyRoam-TravelApp/1.0 (https://github.com/travel-app; contact@travel-app.com) python-httpx/0.24.0"
            }
            self._http_client = httpx.AsyncClient(timeout=30.0, headers=headers)
        return self._http_client

    async def close(self):
        """关闭 HTTP 客户端"""
        if self._http_client and not self._http_client.is_closed:
            await self._http_client.aclose()

    async def _rate_limit(self):
        """请求限流"""
        import time
        now = time.time()
        elapsed = now - self._last_request_time
        if elapsed < self._request_interval:
            await asyncio.sleep(self._request_interval - elapsed)
        self._last_request_time = time.time()

    def get_english_name(self, chinese_name: str) -> Optional[str]:
        """获取景点的英文名称"""
        return self.ENGLISH_NAME_MAP.get(chinese_name)

    async def search_attraction_image(
        self,
        attraction_name: str,
        city: str = "",
        english_name: str = ""
    ) -> Optional[str]:
        """
        搜索景点图片

        Args:
            attraction_name: 景点名称（中文）
            city: 城市名
            english_name: 英文名称（可选，如果不提供会尝试从映射表获取）

        Returns:
            图片 URL 或 None
        """
        # 检查缓存
        cache_key = f"wikimedia:image:{attraction_name}:{city}"
        cached = await get_cache(cache_key)
        if cached:
            logger.debug(f"使用缓存的 Wikimedia 图片: {attraction_name}")
            return cached

        # 获取英文名称
        if not english_name:
            english_name = self.get_english_name(attraction_name) or ""

        # 构建搜索查询
        queries = self._build_search_queries(attraction_name, city, english_name)

        # 遍历查询
        for query in queries:
            try:
                await self._rate_limit()
                image_url = await self._search_and_validate(query)

                if image_url:
                    # 缓存结果
                    await set_cache(cache_key, image_url, ttl=WIKIMEDIA_CACHE_TTL)
                    logger.info(f"Wikimedia 图片获取成功: {attraction_name} -> {image_url[:60]}...")
                    return image_url

            except Exception as e:
                logger.warning(f"Wikimedia 搜索失败 [{query}]: {e}")
                continue

        logger.debug(f"Wikimedia 未找到图片: {attraction_name}")
        return None

    def _build_search_queries(self, name: str, city: str, english: str) -> List[str]:
        """构建搜索查询列表（按优先级排序）"""
        queries = []

        # 清理名称（去除括号内容）
        clean_name = name.split("(")[0].split("（")[0].strip()

        # 1. 中文名称 + 城市
        if city:
            queries.append(f"{clean_name} {city}")

        # 2. 中文名称
        queries.append(clean_name)

        # 3. 英文名称 + China（如果有）
        if english:
            queries.append(f"{english} China")
            queries.append(english)

        # 4. 城市 + China（作为兜底）
        if city:
            queries.append(f"{city} China landmark")

        return queries

    async def _search_and_validate(self, query: str) -> Optional[str]:
        """搜索并验证图片"""
        client = await self._get_client()

        # Step 1: 搜索图片文件
        search_params = {
            "action": "query",
            "list": "search",
            "srnamespace": "6",  # 文件命名空间
            "srsearch": query,
            "srlimit": "10",
            "srfiletype": "bitmap",  # 只搜索图片
            "format": "json",
        }

        try:
            response = await client.get(WIKIMEDIA_API_BASE, params=search_params)
            response.raise_for_status()
            data = response.json()

            search_results = data.get("query", {}).get("search", [])
            if not search_results:
                return None

            # Step 2: 获取图片详情（尺寸、URL）
            # 提取文件标题
            titles = [result["title"] for result in search_results[:5]]

            image_params = {
                "action": "query",
                "titles": "|".join(titles),
                "prop": "imageinfo",
                "iiprop": "url|size|mime",
                "format": "json",
            }

            await self._rate_limit()
            response = await client.get(WIKIMEDIA_API_BASE, params=image_params)
            response.raise_for_status()
            image_data = response.json()

            # Step 3: 筛选符合条件的图片
            pages = image_data.get("query", {}).get("pages", {})
            for page_id, page_info in pages.items():
                if page_id == "-1":
                    continue

                image_info = page_info.get("imageinfo", [])
                if not image_info:
                    continue

                info = image_info[0]
                url = info.get("url", "")
                width = info.get("width", 0)
                height = info.get("height", 0)
                mime = info.get("mime", "")

                # 验证尺寸和格式
                if self._validate_image(url, width, height, mime):
                    return url

            return None

        except httpx.HTTPError as e:
            logger.warning(f"Wikimedia HTTP 错误: {e}")
            return None
        except Exception as e:
            logger.warning(f"Wikimedia 搜索异常: {e}")
            return None

    def _validate_image(self, url: str, width: int, height: int, mime: str) -> bool:
        """验证图片是否符合要求"""
        if not url:
            return False

        # 检查 MIME 类型
        if mime not in ["image/jpeg", "image/png", "image/webp"]:
            return False

        # 检查尺寸
        if width < MIN_WIDTH or height < MIN_HEIGHT:
            return False

        # 排除一些明显不合适的图片（如图标、小图等）
        # 通过 URL 关键词过滤
        exclude_keywords = ["icon", "logo", "button", "flag", "emblem", "coat of arms"]
        url_lower = url.lower()
        for keyword in exclude_keywords:
            if keyword in url_lower:
                return False

        return True


# 全局单例
wikimedia_service = WikimediaService()
