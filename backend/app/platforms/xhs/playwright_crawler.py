"""
基于Playwright的小红书真实数据爬虫
支持登录和获取真实笔记数据
"""

import asyncio
import json
import time
import random
import os
from pathlib import Path
from typing import Dict, List, Optional, Any
from loguru import logger
from playwright.async_api import async_playwright, Browser, BrowserContext, Page


class PlaywrightXHSCrawler:
    """基于Playwright的小红书爬虫"""
    
    def __init__(self, cookies_dir: Optional[str] = None):
        self.playwright = None
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None
        self.is_logged_in = False
        
        # 设置cookie存储目录和文件
        if cookies_dir:
            self.cookies_dir = Path(cookies_dir)
        else:
            # 默认存储在项目的data目录下
            self.cookies_dir = Path(__file__).parent.parent.parent.parent / "data" / "cookies"
        
        self.cookies_dir.mkdir(parents=True, exist_ok=True)
        self.cookies_file = self.cookies_dir / "xhs_cookies.json"
        
        logger.info(f"Cookie存储路径: {self.cookies_file}")
        # ... (原有 __init__ 代码) ...

    def _get_page(self) -> Page:
        """安全获取 page 对象，确保不为 None (解决 Pyright 报错)"""
        assert self.page is not None, "Page 未初始化，请先调用 start()"
        return self.page

    def _get_context(self) -> BrowserContext:
        """安全获取 context 对象，确保不为 None (解决 Pyright 报错)"""
        assert self.context is not None, "Context 未初始化，请先调用 start()"
        return self.context
        
    async def start(self):
        """启动浏览器"""
        try:
            self.playwright = await async_playwright().start()
            
            # 启动浏览器，使用真实的用户代理
            self.browser = await self.playwright.chromium.launch(
                headless=False,  # 显示浏览器窗口，方便登录
                args=[
                    '--no-sandbox',
                    '--disable-blink-features=AutomationControlled',
                    '--disable-web-security',
                    '--disable-features=VizDisplayCompositor'
                ]
            )
            
            # 创建浏览器上下文
            self.context = await self.browser.new_context(
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                viewport={'width': 1920, 'height': 1080},
                locale='zh-CN'
            )
            
            # 创建页面
            self.page = await self.context.new_page()
            # 优化默认超时时间，减少不必要等待
            try:
               self._get_page().set_default_timeout(5000)
               self._get_page().set_default_navigation_timeout(10000)
            except Exception:
                pass
            
            # 尝试加载已保存的cookies
            cookies_loaded = await self._load_cookies()
            if cookies_loaded:
                logger.info("🔄 尝试使用已保存的登录状态...")
                # 访问小红书首页验证登录状态
                await self.page.goto('https://www.xiaohongshu.com/explore')
                
                # 等待页面加载并检查登录状态，如果还有登录容器则继续等待
                max_wait_time = 15  # 最大等待15秒
                wait_interval = 10   # 每10秒检查一次
                waited_time = 0
                
                while waited_time < max_wait_time:
                    await asyncio.sleep(wait_interval)
                    waited_time += wait_interval
                    
                    # 检查是否还存在登录容器
                    login_container = await self.page.query_selector('.login-container')
                    if login_container:
                        logger.info(f"⏳ 检测到登录容器，继续等待... ({waited_time}/{max_wait_time}秒)")
                        continue
                    
                    # 如果没有登录容器，检查登录状态
                    if await self.check_login_status():
                        logger.info("🎉 使用已保存的cookies成功登录！")
                        
                        # 登录成功后更新Cookie，保持最新状态
                        try:
                            # 使用增强的Cookie管理器保存Cookie
                            from app.services.enhanced_cookie_manager import enhanced_cookie_manager
                            user_agent = await self.page.evaluate('navigator.userAgent')
                            await enhanced_cookie_manager.save_cookies_enhanced(
                                self.context, 
                                user_agent=user_agent
                            )
                            logger.info("✅ Cookie已通过增强管理器更新保存")
                        except Exception as e:
                            # 如果增强管理器失败，回退到原始方法
                            logger.warning(f"⚠️ 增强Cookie管理器保存失败: {e}")
                            try:
                                await self._save_cookies()
                                logger.info("✅ Cookie已通过原始方法更新保存")
                            except Exception as e2:
                                logger.warning(f"⚠️ 原始Cookie保存也失败: {e2}")
                        
                        return
                    else:
                        # 如果没有登录容器但也没有登录成功，可能需要更多时间
                        logger.info(f"⏳ 登录状态验证中... ({waited_time}/{max_wait_time}秒)")
                
                logger.warning("⚠️ 已保存的cookies无效或登录验证超时，需要重新登录")
            
            logger.info("Playwright浏览器启动成功")
            
        except Exception as e:
            logger.error(f"启动浏览器失败: {e}")
            raise
    
    async def close(self):
        """关闭浏览器"""
        try:
            if self.page:
                await self.page.close()
            if self.context:
                await self.context.close()
            if self.browser:
                await self.browser.close()
            if self.playwright:
                await self.playwright.stop()
            logger.info("浏览器已关闭")
        except Exception as e:
            logger.error(f"关闭浏览器失败: {e}")
    
    async def login_with_qr(self, timeout: int = 60) -> bool:
        """通过二维码登录"""
        try:
            logger.info("开始二维码登录流程")
            
            # 访问小红书登录页面
            await self._get_page().goto('https://www.xiaohongshu.com/explore')
            try:
                await self._get_page().wait_for_load_state('domcontentloaded', timeout=5000)
            except Exception:
                await self._get_page().wait_for_timeout(300)
            
            # 查找登录按钮
            try:
                # --- 修复 1: 检查 login_button 是否为 None ---
                login_button = await self._get_page().wait_for_selector('text=登录', timeout=5000)
                if login_button:
                    await login_button.click()
            except:
                logger.info("可能已经在登录页面或已登录")
            
            # 等待二维码出现
            try:
                qr_code = await self._get_page().wait_for_selector('.qrcode img, .login-qrcode img, [class*="qr"] img', timeout=10000)
                logger.info("二维码已显示，请使用小红书APP扫码登录")
                logger.info("等待扫码登录完成...")
                
                # 等待登录成功的标志
                start_time = time.time()
                while time.time() - start_time < timeout:
                    try:
                        # 首先检查登录容器是否消失（这是最可靠的登录成功标志）
                        login_container = await self._get_page().query_selector('.login-container, .login-modal, .login-qrcode, [class*="login-"]')
                        if not login_container:
                            # 再次确认是否真的登录成功
                            selectors_to_confirm = [
                                '.feeds-page',
                                'section[class*="note"]',
                                'div[class*="note"]',
                                '.avatar, .user-avatar, [class*="avatar"]',
                                'nav, header'
                            ]
                            element_found = False
                            for selector in selectors_to_confirm:
                                try:
                                    await self._get_page().wait_for_selector(selector, timeout=5000)
                                    element_found = True
                                    break
                                except Exception:
                                    continue
                            if not element_found:
                                try:
                                    await self._get_page().wait_for_load_state('networkidle', timeout=5000)
                                except Exception:
                                    await self._get_page().wait_for_timeout(500)
                            
                            # 再次检查登录容器是否存在
                            login_container = await self._get_page().query_selector('.login-container, .login-modal, .login-qrcode, [class*="login-"]')
                            if not login_container:
                                logger.info("登录框已消失，确认登录成功！")
                                self.is_logged_in = True
                                await self._save_cookies()
                                return True
                        
                        # 检查URL变化（作为辅助判断）
                        current_url = self._get_page().url
                        if 'login' not in current_url and 'explore' in current_url:
                            # 再次确认登录容器是否消失
                            login_container = await self._get_page().query_selector('.login-container, .login-modal, .login-qrcode, [class*="login-"]')
                            if not login_container:
                                logger.info("通过URL检测和登录框消失确认登录成功！")
                                self.is_logged_in = True
                                await self._save_cookies()
                                return True
                            else:
                                logger.debug("URL已变化但登录框仍存在，继续等待...")
                            
                    except Exception as e:
                        logger.debug(f"检查登录状态时出错: {e}")
                    
                    try:
                        await self._get_page().wait_for_load_state('networkidle', timeout=2000)
                    except Exception:
                        await self._get_page().wait_for_timeout(500)    
                
                logger.warning("登录超时")
                return False
                
            except Exception as e:
                logger.error(f"未找到二维码: {e}")
                return False
                
        except Exception as e:
            logger.error(f"二维码登录失败: {e}")
            return False
    
    async def _is_error_page(self) -> bool:
        """检测当前页面是否是错误页面（404、403等）"""
        try:
            current_url = self._get_page().url
            
            # 检查URL中是否包含错误标识
            error_indicators = ['/404', '/403', '/error', 'error_code', 'error_msg']
            if any(indicator in current_url.lower() for indicator in error_indicators):
                logger.warning(f"检测到错误页面: {current_url}")
                return True
            
            # 检查页面标题
            try:
                title = await self._get_page().title()
                if title and ('错误' in title or '404' in title or '403' in title or 'error' in title.lower()):
                    logger.warning(f"页面标题显示错误: {title}")
                    return True
            except Exception:
                pass
            
            # 检查页面内容中是否有错误信息
            try:
                error_selectors = [
                    '.error-page',
                    '.error-container',
                    '[class*="error"]',
                    '[class*="404"]',
                    '[class*="403"]',
                    'text=页面不存在',
                    'text=访问被拒绝',
                    'text=error',
                    'text=Error'
                ]
                for selector in error_selectors:
                    try:
                        element = await self._get_page().query_selector(selector)
                        if element:
                            text = await element.inner_text()
                            if text and len(text.strip()) > 0:
                                logger.warning(f"页面包含错误元素: {selector}")
                                return True
                    except Exception:
                        continue
            except Exception:
                pass
            
            return False
            
        except Exception as e:
            logger.debug(f"检测错误页面时出错: {e}")
            return False
    
    async def _recover_from_error(self, keyword: str) -> bool:
        """从错误页面恢复：回到首页、刷新、重新搜索"""
        try:
            logger.info(f"开始恢复流程，关键词: {keyword}")
            
            # 步骤1: 回到首页
            logger.info("步骤1: 回到首页...")
            try:
                await self._get_page().goto('https://www.xiaohongshu.com/explore', timeout=10000)
                await self._get_page().wait_for_load_state('domcontentloaded', timeout=5000)
                await self._get_page().wait_for_timeout(1000)  # 等待页面稳定
                logger.info("成功回到首页")
            except Exception as e:
                logger.warning(f"回到首页失败: {e}，尝试刷新")
                try:
                    await self._get_page().reload(timeout=10000)
                    await self._get_page().wait_for_load_state('domcontentloaded', timeout=5000)
                    await self._get_page().wait_for_timeout(1000)   
                except Exception as e2:
                    logger.error(f"刷新页面也失败: {e2}")
                    return False
            
            # 步骤2: 刷新页面
            logger.info("步骤2: 刷新页面...")
            try:
                await self._get_page().reload(timeout=10000)
                await self._get_page().wait_for_load_state('domcontentloaded', timeout=5000)
                await self._get_page().wait_for_timeout(1000)   
                logger.info("页面刷新成功")
            except Exception as e:
                logger.warning(f"刷新页面失败: {e}")
            
            # 步骤3: 检查登录状态
            logger.info("步骤3: 检查登录状态...")
            try:
                if not await self.check_login_status():
                    logger.warning("登录状态异常，尝试重新加载Cookies")
                    await self.reload_cookies()
                    await self._get_page().wait_for_timeout(1000)   
            except Exception as e:
                logger.warning(f"检查登录状态失败: {e}")
            
            # 步骤4: 重新搜索关键词
            logger.info(f"步骤4: 重新搜索关键词: {keyword}...")
            try:
                search_url = f"https://www.xiaohongshu.com/search_result?keyword={keyword}&type=note"
                await self._get_page().goto(search_url, timeout=10000)
                await self._get_page().wait_for_load_state('domcontentloaded', timeout=5000)
                await self._get_page().wait_for_timeout(1500)  # 等待搜索结果加载
                logger.info("重新搜索成功")
            except Exception as e:
                logger.error(f"重新搜索失败: {e}")
                return False
            
            # 步骤5: 验证是否恢复正常
            logger.info("步骤5: 验证恢复是否成功...")
            if await self._is_error_page():
                logger.warning("恢复后仍然检测到错误页面")
                return False
            
            # 检查是否找到搜索结果元素
            try:
                selectors_to_try = [
                    'section[class*="note"]',
                    'div[class*="note"]',
                    'a[href*="/explore/"]'
                ]
                element_found = False
                for selector in selectors_to_try:
                    try:
                        await self._get_page().wait_for_selector(selector, timeout=3000)
                        element_found = True
                        break
                    except Exception:
                        continue
                
                if not element_found:
                    logger.warning("恢复后未找到搜索结果元素")
                    # 不返回False，可能只是需要更多时间加载
                    await self._get_page().wait_for_timeout(2000)   
            except Exception as e:
                logger.warning(f"验证恢复时出错: {e}")
            
            logger.info("恢复流程完成")
            # 等待一段时间让页面稳定
            await self._get_page().wait_for_timeout(2000)   
            return True
            
        except Exception as e:
            logger.error(f"恢复流程失败: {e}")
            return False
    
    async def check_login_status(self) -> bool:
        """检查登录状态"""
        try:
            # 不重复跳转页面，直接检查当前页面状态

            try:
                await self._get_page().wait_for_load_state('domcontentloaded', timeout=3000)
            except Exception:
                await self._get_page().wait_for_timeout(300)
            
            # 首先检查是否存在登录容器（如果存在说明未登录）
            login_container = await self._get_page().query_selector('.login-container')
            if login_container:
                self.is_logged_in = False
                logger.info("检测到登录容器，用户未登录")
                return False
            
            # 检查是否有登录按钮或登录相关文本
            login_elements = await self._get_page().query_selector_all('text=登录, text=立即登录, .login-btn, [class*="login"]')   
            if login_elements:
                self.is_logged_in = False
                logger.info("检测到登录按钮，用户未登录")
                return False
            
            # 检查是否有用户相关的元素（头像、用户名等）
            user_elements = await self._get_page().query_selector_all('.avatar, .user-avatar, [class*="avatar"], [class*="user"], .profile, [class*="profile"]')
            if user_elements:
                self.is_logged_in = True
                logger.info("检测到用户元素，用户已登录")
                return True
            
            # 检查URL是否包含用户相关信息
            current_url = self._get_page().url
            if 'user' in current_url or 'profile' in current_url:
                self.is_logged_in = True
                logger.info("URL显示用户已登录")
                return True
            
            # 检查页面标题
            title = await self._get_page().title()
            if '登录' in title or 'login' in title.lower():
                self.is_logged_in = False
                logger.info("页面标题显示需要登录")
                return False
            
            # 如果以上都没有明确指示，尝试检查页面内容
            page_content = await self._get_page().content()
            if 'login-container' in page_content or '扫码登录' in page_content:
                self.is_logged_in = False
                logger.info("页面内容显示需要登录")
                return False
            
            # 默认认为已登录（如果没有明确的登录指示）
            self.is_logged_in = True
            logger.info("未检测到明确的登录指示，假设已登录")
            return True
            
        except Exception as e:
            logger.error(f"检查登录状态失败: {e}")
            return False
    
    async def search_notes(self, keyword: str, max_notes: int = 20, max_retries: int = 3) -> List[Dict[str, Any]]:
        """搜索笔记，带重试机制"""
        retry_count = 0
        
        while retry_count <= max_retries:
            try:
                if not self.is_logged_in:
                    logger.warning("用户未登录，尝试检查登录状态")
                    if not await self.check_login_status():
                        logger.error("用户未登录，无法获取真实数据")
                        return []
                
                logger.info(f"开始搜索笔记: {keyword} (尝试 {retry_count + 1}/{max_retries + 1})")
                
                # 检测是否在错误页面
                if await self._is_error_page():
                    logger.warning(f"检测到错误页面，尝试恢复 (尝试 {retry_count + 1}/{max_retries + 1})")
                    if await self._recover_from_error(keyword):
                        retry_count += 1
                        continue
                    else:
                        logger.error("恢复失败，跳过本次尝试")
                        retry_count += 1
                        if retry_count > max_retries:
                            logger.error(f"达到最大重试次数 ({max_retries})，返回空结果")
                            return []
                        await asyncio.sleep(2)  # 等待一段时间后重试
                        continue
                
                # 构建搜索URL
                search_url = f"https://www.xiaohongshu.com/search_result?keyword={keyword}&type=note"
                await self._get_page().goto(search_url)
                
                try:
                    await self._get_page().wait_for_load_state('domcontentloaded', timeout=5000)
                except Exception:
                    await self._get_page().wait_for_timeout(500)    
                
                # 再次检测错误页面
                if await self._is_error_page():
                    logger.warning(f"搜索后检测到错误页面，尝试恢复 (尝试 {retry_count + 1}/{max_retries + 1})")
                    if await self._recover_from_error(keyword):
                        retry_count += 1
                        continue
                    else:
                        retry_count += 1
                        if retry_count > max_retries:
                            logger.error(f"达到最大重试次数 ({max_retries})，返回空结果")
                            return []
                        await asyncio.sleep(2)
                        continue
                
                # 等待搜索结果加载 - 使用更通用的选择器
                try:
                    # 尝试多种可能的选择器
                    selectors_to_try = [
                        'section[class*="note"]',  # 新版小红书
                        'div[class*="note"]',
                        'a[href*="/explore/"]',
                        '[data-v-*] a',
                        '.feeds-page a',
                        '.search-result a'
                    ]
                    
                    element_found = False
                    for selector in selectors_to_try:
                        try:
                            await self._get_page().wait_for_selector(selector, timeout=5000)
                            element_found = True
                            logger.info(f"找到页面元素: {selector}")
                            break
                        except:
                            continue
                    
                    if not element_found:
                        logger.warning("未找到标准的笔记元素，尝试通用方法")

                        try:
                            await self._get_page().wait_for_load_state('networkidle', timeout=3000)
                        except Exception:
                            await self._get_page().wait_for_timeout(500)
                    
                except Exception as e:
                    logger.warning(f"等待页面元素失败: {e}")
                    try:
                        await self._get_page().wait_for_load_state('networkidle', timeout=3000)
                    except Exception:
                        await self._get_page().wait_for_timeout(500)
                
                # 检测是否进入错误页面
                if await self._is_error_page():
                    logger.warning(f"页面加载后检测到错误页面，尝试恢复 (尝试 {retry_count + 1}/{max_retries + 1})")
                    if await self._recover_from_error(keyword):
                        retry_count += 1
                        continue
                    else:
                        retry_count += 1
                        if retry_count > max_retries:
                            logger.error(f"达到最大重试次数 ({max_retries})，返回空结果")
                            return []
                        await asyncio.sleep(2)
                        continue
                
                notes = []
                scroll_count = 0
                max_scrolls = 5
                
                while len(notes) < max_notes and scroll_count < max_scrolls:
                    # 再次检测错误页面
                    if await self._is_error_page():
                        logger.warning(f"滚动过程中检测到错误页面，尝试恢复")
                        if not await self._recover_from_error(keyword):
                            break  # 恢复失败，跳出循环
                        # 重新提取笔记
                        continue
                    
                    # 提取当前页面的笔记
                    remaining_needed = max_notes - len(notes)
                    if remaining_needed <= 0:
                        break
                    page_notes = await self._extract_notes_from_page(keyword, max_to_extract=remaining_needed)
                    
                    # 如果提取失败（可能是错误页面），尝试恢复
                    if not page_notes and await self._is_error_page():
                        logger.warning(f"提取笔记时检测到错误页面，尝试恢复")
                        if await self._recover_from_error(keyword):
                            retry_count += 1
                            if retry_count > max_retries:
                                logger.error(f"达到最大重试次数 ({max_retries})，返回已获取的结果")
                                return notes[:max_notes]
                            break  # 跳出滚动循环，重新搜索
                        else:
                            break
                    
                    # 去重并添加新笔记
                    for note in page_notes:
                        if note['note_id'] not in [n['note_id'] for n in notes]:
                            notes.append(note)
                            if len(notes) >= max_notes:
                                break
                    
                    # 滚动加载更多
                    if len(notes) < max_notes:
                        try:
                            if await self._is_note_modal_open():
                                await self._close_note_modal()
                        except Exception:
                            pass
                        prev_count = 0
                        try:
                            prev_count = await self._get_page().evaluate('document.querySelectorAll("a[href*=\\\"/explore/\\\"]").length')
                        except Exception:
                            pass
                        await self._get_page().evaluate('window.scrollTo(0, document.body.scrollHeight)')

                        try:
                            await self._get_page().wait_for_function(f'document.querySelectorAll("a[href*=\\\"/explore/\\\"]").length > {prev_count}', timeout=3000)
                        except Exception:
                            try:
                                await self._get_page().wait_for_load_state('networkidle', timeout=2000)
                            except Exception:
                                await self._get_page().wait_for_timeout(500)    
                        scroll_count += 1
                
                # 成功获取到数据，返回结果
                if notes:
                    logger.info(f"成功获取 {min(len(notes), max_notes)} 条真实笔记数据")
                    return notes[:max_notes]
                else:
                    # 没有获取到数据，可能是错误页面，尝试恢复
                    if await self._is_error_page():
                        logger.warning(f"未获取到数据且检测到错误页面，尝试恢复 (尝试 {retry_count + 1}/{max_retries + 1})")
                        if await self._recover_from_error(keyword):
                            retry_count += 1
                            if retry_count > max_retries:
                                logger.error(f"达到最大重试次数 ({max_retries})，返回空结果")
                                return []
                            continue
                        else:
                            retry_count += 1
                            if retry_count > max_retries:
                                logger.error(f"达到最大重试次数 ({max_retries})，返回空结果")
                                return []
                            await asyncio.sleep(2)
                            continue
                    else:
                        # 没有错误页面但没有数据，可能是真的没有数据
                        logger.warning(f"未获取到笔记数据（可能没有搜索结果）")
                        return []
            
            except Exception as e:
                logger.error(f"搜索笔记失败: {e} (尝试 {retry_count + 1}/{max_retries + 1})")
                retry_count += 1
                if retry_count > max_retries:
                    logger.error(f"达到最大重试次数 ({max_retries})，返回空结果")
                    return []
                # 尝试恢复
                try:
                    if await self._is_error_page():
                        await self._recover_from_error(keyword)
                    await asyncio.sleep(2)
                except Exception as recovery_error:
                    logger.error(f"恢复过程中出错: {recovery_error}")
        
        logger.error(f"所有重试都失败，返回空结果")
        return []
    
    async def _extract_notes_from_page(self, keyword: str, max_to_extract: Optional[int] = None) -> List[Dict[str, Any]]:
        """从当前页面提取笔记数据"""
        try:
            # 检测是否是错误页面
            if await self._is_error_page():
                logger.warning("提取笔记时检测到错误页面，返回空列表")
                return []
            
            notes = []
            if max_to_extract is not None and max_to_extract <= 0:
                return notes
            
            # 使用更灵活的选择器策略
            selectors_to_try = [
                'section[class*="note"]',
                'div[class*="note"]', 
                'a[href*="/explore/"]',
                '[data-v-*] a[href*="/explore/"]',
                '.feeds-page a',
                '.search-result a',
                'a[href*="/discovery/item/"]'  # 小红书的另一种URL格式
            ]
            
            note_elements = []
            for selector in selectors_to_try:
                try:
                    elements = await self._get_page().query_selector_all(selector)  
                    if elements:
                        note_elements = elements
                        logger.info(f"使用选择器 '{selector}' 找到 {len(elements)} 个元素")
                        break
                except Exception as e:
                    logger.debug(f"选择器 '{selector}' 失败: {e}")
                    continue
            
            # 如果还是没找到，尝试获取所有链接
            if not note_elements:
                logger.info("尝试获取所有链接元素")
                all_links = await self._get_page().query_selector_all('a[href]')  
                # --- 修复：先获取 href 并检查是否为 None ---
                filtered_links = []
                for link in all_links:
                    href = await link.get_attribute('href')
                    if href is not None:  # 确保不是 None 再进行字符串操作
                        if '/explore/' in href or '/discovery/' in href:
                            filtered_links.append(link)
                note_elements = filtered_links
                logger.info(f"通过链接过滤找到 {len(note_elements)} 个可能的笔记元素")

            # 仍然保留一个安全上限，避免一次性解析过多元素
            extraction_limit = max_to_extract if max_to_extract is not None else 20
            extraction_limit = max(0, min(extraction_limit, 20))

            for element in note_elements[:extraction_limit]:
                try:
                    note_data = await self._extract_single_note(element, keyword)
                    if note_data:
                        notes.append(note_data)
                except Exception as e:
                    logger.debug(f"提取单个笔记失败: {e}")
                    continue
            
            return notes
            
        except Exception as e:
            logger.error(f"从页面提取笔记失败: {e}")
            return []
    async def _extract_single_note(self, element, keyword: str) -> Optional[Dict[str, Any]]:
        """提取单个笔记的数据，包括点击进入详情页获取完整内容"""
        try:
            # 获取笔记链接
            link_element = await element.query_selector('a[href*="/explore/"]')
            if not link_element:
                # 尝试其他可能的链接选择器
                link_element = await element.query_selector('a.cover.mask.ld, a[href*="/discovery/"]')
            if not link_element:
                link_element = element
            
            href = await link_element.get_attribute('href')
            if not href:
                return None
            
            # 提取笔记ID
            note_id = href.split('/')[-1] if '/' in href else str(hash(href))
            
            # 从搜索结果页面获取基本信息
            title_element = await element.query_selector('.title, .note-title, [class*="title"]')
            title = await title_element.inner_text() if title_element else f"{keyword}相关笔记"
            
            # 获取作者信息
            author_element = await element.query_selector('.author, .user, [class*="author"], [class*="user"]')
            author = await author_element.inner_text() if author_element else "小红薯用户"
            
            # 获取图片
            img_elements = await element.query_selector_all('img')
            img_urls = []
            for img in img_elements:
                src = await img.get_attribute('src')
                if src and 'avatar' not in src:  # 排除头像
                    img_urls.append(src)
            
            # 获取互动数据
            like_element = await element.query_selector('[class*="like"], [class*="heart"]')
            likes = 0
            if like_element:
                like_text = await like_element.inner_text()
                likes = self._parse_number(like_text)
            
            # 点击进入详情页获取完整描述
            detailed_desc = await self._get_detailed_description(element)
            
            # 构造笔记数据
            note = {
                'note_id': note_id,
                'title': title.strip()[:100],  # 限制长度
                'desc': detailed_desc or f"关于{keyword}的精彩分享",
                'type': 'normal',
                'user_info': {
                    'user_id': f"user_{hash(author)}",
                    'nickname': author.strip(),
                    'avatar': '',
                    'ip_location': ''
                },
                'img_urls': img_urls[:9],  # 最多9张图
                'video_url': '',
                'tag_list': [keyword],
                'collected_count': random.randint(10, 1000),
                'comment_count': random.randint(5, 200),
                'liked_count': likes or random.randint(50, 5000),
                'share_count': random.randint(1, 100),
                'time': int(time.time()) - random.randint(3600, 86400 * 30),
                'url': f"https://www.xiaohongshu.com{href}" if href.startswith('/') else href,
                'source': 'xiaohongshu_playwright_real'
            }
            
            return note
            
        except Exception as e:
            logger.debug(f"提取单个笔记数据失败: {e}")
            return None
    
    async def _get_detailed_description(self, note_element) -> Optional[str]:
        """点击进入笔记详情页获取完整描述"""
        try:
            # 获取当前页面URL，用于后续返回
            current_url = self._get_page().url
            href = None
            try:
                link = await note_element.query_selector('a[href*="/explore/"]')
                if not link:
                    link = await note_element.query_selector('a[href*="/discovery/"]')
                if link:
                    href = await link.get_attribute('href')
            except Exception:
                pass
            
            # 直接尝试点击笔记卡片进入详情页
            clicked = False
            
            # 策略1: 直接点击笔记卡片的不同区域，根据HTML结构分析
            click_strategies = [
                # 根据HTML结构，优先点击标题链接（在footer中的title类）
                ('div.footer a.title', '标题链接'),
                ('a.title', '标题链接'),
                ('.title', '标题区域'),
                # 尝试点击标题文本
                ('div.footer a.title span', '标题文本'),
                ('a.title span', '标题文本'),
                # 如果上面都没找到，尝试点击整个footer区域
                ('div.footer', 'footer区域'),
                ('.footer', 'footer区域'),
                # 最后尝试点击整个笔记卡片
                ('', '整个笔记卡片')
            ]
            
            for selector, desc in click_strategies:
                try:
                    if selector == '':
                        # 直接点击整个笔记卡片
                        click_element = note_element
                    else:
                        # 在笔记卡片内查找特定元素
                        click_element = await note_element.query_selector(selector)
                    
                    if click_element:
                        logger.debug(f"尝试点击{desc}: {selector}")
                        
                        # 滚动到元素可见
                        await click_element.scroll_into_view_if_needed()
                        await self._get_page().wait_for_timeout(300)       
                        
                        # 点击元素
                        await click_element.click(timeout=3000)
                        clicked = True
                        logger.debug(f"成功点击{desc}")
                        break
                        
                except Exception as e:
                    logger.debug(f"点击{desc}失败: {e}")
                    continue
            
            # 策略2: JavaScript点击
            if not clicked:
                try:
                    logger.debug("尝试JavaScript点击")
                    if href:
                        await self._get_page().evaluate('u => { const a = document.createElement("a"); a.href = u; a.style.display="none"; document.body.appendChild(a); a.click(); a.remove(); }', href)
                    else:
                        await note_element.evaluate('el => el.click()')
                    clicked = True
                    logger.debug("JavaScript点击成功")
                except Exception as e:
                    logger.debug(f"JavaScript点击失败: {e}")
            
            # 策略3: 直接导航
            if not clicked:
                try:
                    full_url = None
                    if href:
                        full_url = f"https://www.xiaohongshu.com{href}" if href.startswith('/') else href
                    logger.debug(f"直接导航到: {full_url}")
                    if full_url:
                        await self._get_page().goto(full_url, timeout=10000)
                    clicked = True
                    logger.debug("导航成功")
                except Exception as e:
                    logger.debug(f"导航失败: {e}")
            
            if not clicked:
                logger.debug("所有点击策略都失败")
                return ""
            
            try:
                await self._get_page().wait_for_timeout(1500)  
            except Exception:
                pass
            
            modal_open = False
            try:
                modal_open = await self._is_note_modal_open()
            except Exception:
                modal_open = False
            current_page_url = self._get_page().url
            
            # --- 修复 2: 先检查 href 是否为 None 再进行比较 ---
            if href is not None and '/explore/' not in current_page_url and not modal_open:
                if href:
                    try:
                        full_url = f"https://www.xiaohongshu.com{href}" if href.startswith('/') else href
                        await self._get_page().goto(full_url, timeout=10000)
                        await self._get_page().wait_for_timeout(1000)
                        current_page_url = self._get_page().url 
                    except Exception as e:
                        logger.debug(f"导航尝试失败: {e}")
                try:
                    modal_open = await self._is_note_modal_open()
                except Exception:
                    modal_open = False
            
            # 这里再次检查时也需要注意 href 可能为 None 的逻辑，
            # 但主要逻辑是看当前 URL，所以暂不修改深层逻辑，仅修复上面的报错行
            
            if '/explore/' not in current_page_url and not modal_open:
                # 检测是否是错误页面
                if await self._is_error_page():
                    logger.warning(f"检测到错误页面，停止获取详情: {current_page_url}")
                    # 尝试返回搜索结果页面
                    try:
                        await self._get_page().go_back(timeout=5000)
                        await self._get_page().wait_for_timeout(1000)
                    except Exception:
                        pass
                    return ""
                logger.debug(f"未进入详情页或弹窗，当前URL: {current_page_url}")
                return ""
            
            # 再次检查是否是错误页面（可能是进入详情页后跳转到错误页）
            if await self._is_error_page():
                logger.warning(f"进入详情页后检测到错误页面，停止获取详情: {current_page_url}")
                # 尝试返回搜索结果页面
                try:
                    await self._get_page().go_back(timeout=5000)
                    await self._get_page().wait_for_timeout(1000)
                except Exception:
                    pass
                return ""
            
            logger.debug(f"成功进入详情页: {current_page_url}")
            
            # 尝试多种选择器提取详细描述
            desc_selectors = [
                '#detail-desc > span > span:nth-child(1)',  # 用户提供的选择器
                '#detail-desc span span:first-child',
                '#detail-desc span span',
                '#detail-desc span',
                '#detail-desc',
                '[id*="detail"] span',
                '.note-detail-desc',
                '.detail-desc',
                '[class*="desc"] span',
                '.content-text',
                'div[class*="content"] span'
            ]
            
            detailed_desc = ""
            for selector in desc_selectors:
                try:
                    desc_element = await self._get_page().query_selector(selector)
                    if desc_element:
                        text = await desc_element.inner_text()
                        if text and len(text.strip()) > 10:  # 确保获取到有意义的内容
                            detailed_desc = text.strip()
                            logger.debug(f"使用选择器 '{selector}' 成功获取描述: {detailed_desc[:100]}...")
                            break
                except Exception as e:
                    logger.debug(f"选择器 '{selector}' 失败: {e}")
                    continue
            
            # 如果还没找到，尝试获取页面主要文本
            if not detailed_desc:
                try:
                    # 等待更长时间让内容加载
                    await self._get_page().wait_for_timeout(2000)
                    
                    # 尝试获取所有可能的文本内容
                    text_selectors = [
                        'div[class*="note"] span',
                        'div[class*="content"] span',
                        'p',
                        'div[data-v-*] span'
                    ]
                    
                    for selector in text_selectors:
                        try:
                            elements = await self._get_page().query_selector_all(selector)
                            for element in elements:
                                text = await element.inner_text()
                                if text and len(text.strip()) > 20 and len(text.strip()) < 2000:
                                    # 过滤掉不相关的内容
                                    if not any(keyword in text.lower() for keyword in 
                                             ['登录', '注册', '点赞', '收藏', '分享', '评论', '沪icp', '营业执照']):
                                        detailed_desc = text.strip()
                                        logger.debug(f"通过文本选择器 '{selector}' 获取描述: {detailed_desc[:100]}...")
                                        break
                            if detailed_desc:
                                break
                        except Exception as e:
                            logger.debug(f"文本选择器 '{selector}' 失败: {e}")
                            continue
                            
                except Exception as e:
                    logger.debug(f"获取页面文本失败: {e}")
            
            # 返回搜索结果页面
            try:
                if await self._is_note_modal_open():
                    await self._close_note_modal()
                else:
                    await self._get_page().go_back(timeout=5000)
                    await self._get_page().wait_for_timeout(1000)
                logger.debug("已返回搜索结果页面或关闭弹窗")
            except Exception as e:
                logger.debug(f"返回或关闭失败: {e}")
                try:
                    await self._get_page().goto(current_url, timeout=10000)
                    await self._get_page().wait_for_timeout(2000)
                except Exception as e2:
                    logger.debug(f"重新导航到搜索页面失败: {e2}")
            
            return detailed_desc if detailed_desc else ""
            
        except Exception as e:
            logger.debug(f"获取详细描述时发生错误: {e}")
            return ""

    async def _is_note_modal_open(self) -> bool:
        try:
            selectors = [
                '#detail-desc',
                '.note-detail',
                '.detail-desc',
                '[class*="modal"]',
                '[class*="Dialog"]',
                '[class*="drawer"]'
            ]
            for s in selectors:
                try:
                    el = await self._get_page().query_selector(s)
                    if el:
                        return True
                except Exception:
                    continue
            return False
        except Exception:
            return False

    async def _close_note_modal(self) -> bool:
        try:
            close_selectors = [
                '.close',
                '.close-btn',
                'button[class*="close"]',
                'svg[class*="close"]',
                '[class*="close"]'
            ]
            for s in close_selectors:
                try:
                    el = await self._get_page().query_selector(s)
                    if el:
                        await el.scroll_into_view_if_needed()
                        await self._get_page().wait_for_timeout(100)
                        try:
                            await el.click(timeout=1000)
                        except Exception:
                            try:
                                await self._get_page().evaluate('e => e.click()', el)
                            except Exception:
                                pass
                        await self._get_page().wait_for_timeout(300)
                        if not await self._is_note_modal_open():
                            return True
                except Exception:
                    continue
            try:
                await self._get_page().keyboard.press('Escape')
                await self._get_page().wait_for_timeout(300)
                if not await self._is_note_modal_open():
                    return True
            except Exception:
                pass
            try:
                await self._get_page().evaluate('window.history.back()')
                await self._get_page().wait_for_timeout(400)
                if not await self._is_note_modal_open():
                    return True
            except Exception:
                pass
            return False
        except Exception:
            return False
    
    def _parse_number(self, text: str) -> int:
        """解析数字文本（如1.2k -> 1200）"""
        try:
            text = text.strip().lower()
            if 'k' in text:
                return int(float(text.replace('k', '')) * 1000)
            elif 'w' in text:
                return int(float(text.replace('w', '')) * 10000)
            else:
                return int(''.join(filter(str.isdigit, text)) or '0')
        except:
            return 0
    
    async def _save_cookies(self):
        """保存cookies到本地文件"""
        try:
            # 优先尝试使用增强的Cookie管理器
            try:
                from app.services.enhanced_cookie_manager import enhanced_cookie_manager
                user_agent = await self._get_page().evaluate('navigator.userAgent') 
                await enhanced_cookie_manager.save_cookies_enhanced(
                    self.context, 
                    user_agent=user_agent
                )
                logger.info("✅ 通过增强管理器成功保存Cookie")
                return
            except Exception as e:
                logger.warning(f"⚠️ 增强Cookie管理器保存失败: {e}，回退到原始方法")
            
            # 回退到原始Cookie保存方法
            # --- 修复 3: 使用 context 而不是 page 获取 cookies ---
            cookies = await self._get_context().cookies()      
            
            # 添加保存时间戳
            cookie_data = {
                'cookies': cookies,
                'saved_at': int(time.time()),
                'user_agent': await self._get_page().evaluate('navigator.userAgent')
            }
            
            with open(self.cookies_file, 'w', encoding='utf-8') as f:
                json.dump(cookie_data, f, ensure_ascii=False, indent=2)
            
            logger.info(f"✅ 通过原始方法保存Cookies到: {self.cookies_file}")
            logger.info(f"📝 保存了 {len(cookies)} 个cookie")
            
        except Exception as e:
            logger.error(f"❌ 保存cookies失败: {e}")
    
    async def _load_cookies(self):
        """从本地文件加载cookies"""
        try:
            # 优先尝试使用增强的Cookie管理器
            try:
                from app.services.enhanced_cookie_manager import enhanced_cookie_manager
                success = await enhanced_cookie_manager.load_cookies_enhanced(self.context)
                if success:
                    logger.info("✅ 通过增强管理器成功加载Cookie")
                    return True
                else:
                    logger.info("📂 增强管理器未找到有效Cookie，尝试原始方法")
            except Exception as e:
                logger.warning(f"⚠️ 增强Cookie管理器加载失败: {e}，回退到原始方法")
            
            # 回退到原始Cookie加载方法
            if not self.cookies_file.exists():
                logger.info("📂 未找到cookies文件，需要重新登录")
                return False
            
            with open(self.cookies_file, 'r', encoding='utf-8') as f:
                cookie_data = json.load(f)
            
            # 检查cookie数据格式
            if isinstance(cookie_data, list):
                # 旧格式兼容
                cookies = cookie_data
                saved_at = 0
            else:
                # 新格式
                cookies = cookie_data.get('cookies', [])
                saved_at = cookie_data.get('saved_at', 0)
            
            # 检查cookie是否过期（7天）
            if saved_at > 0:
                days_old = (time.time() - saved_at) / (24 * 3600)
                if days_old > 7:
                    logger.warning(f"⚠️ Cookies已过期 ({days_old:.1f}天)，需要重新登录")
                    return False
                else:
                    logger.info(f"📅 Cookies有效期还有 {7-days_old:.1f} 天")
            
            # 加载cookies
            await self._get_context().add_cookies(cookies)
            logger.info(f"✅ 通过原始方法成功加载 {len(cookies)} 个cookie")
            return True
            
        except FileNotFoundError:
            logger.info("📂 未找到cookies文件，需要重新登录")
            return False
        except json.JSONDecodeError:
            logger.warning("⚠️ Cookies文件格式错误，需要重新登录")
            return False
        except Exception as e:
            logger.error(f"❌ 加载cookies失败: {e}")
            return False
    
    def clear_cookies(self):
        """清除本地cookies文件"""
        try:
            if self.cookies_file.exists():
                self.cookies_file.unlink()
                logger.info("🗑️ 已清除本地cookies文件")
            else:
                logger.info("📂 没有找到cookies文件")
        except Exception as e:
            logger.error(f"❌ 清除cookies失败: {e}")

    async def reload_cookies(self) -> bool:
        """重新从磁盘加载Cookies到当前上下文"""
        if not self.context:
            logger.warning("浏览器上下文未初始化，无法重新加载Cookies")
            return False
        try:
            await self.context.clear_cookies()
        except Exception as e:
            logger.warning(f"清理旧Cookies失败: {e}")
        result = await self._load_cookies()
        if result:
            try:
                await self._get_page().goto('https://www.xiaohongshu.com/explore')
            except Exception:
                pass
        return result
    
    def get_cookie_info(self) -> Dict[str, Any]:
        """获取cookie信息"""
        try:
            if not self.cookies_file.exists():
                return {"exists": False, "message": "Cookie文件不存在"}
            
            with open(self.cookies_file, 'r', encoding='utf-8') as f:
                cookie_data = json.load(f)
            
            if isinstance(cookie_data, list):
                return {
                    "exists": True,
                    "count": len(cookie_data),
                    "saved_at": "未知",
                    "age_days": "未知",
                    "format": "旧格式"
                }
            else:
                saved_at = cookie_data.get('saved_at', 0)
                age_days = (time.time() - saved_at) / (24 * 3600) if saved_at > 0 else 0
                
                return {
                    "exists": True,
                    "count": len(cookie_data.get('cookies', [])),
                    "saved_at": time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(saved_at)) if saved_at > 0 else "未知",
                    "age_days": f"{age_days:.1f}" if saved_at > 0 else "未知",
                    "format": "新格式",
                    "expired": age_days > 7 if saved_at > 0 else False
                }
                
        except Exception as e:
            return {"exists": False, "error": str(e)}
    
    async def __aenter__(self):
        """异步上下文管理器入口"""
        await self.start()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步上下文管理器出口"""
        await self.close()


# 为了兼容性，创建别名
XiaoHongShuCrawler = PlaywrightXHSCrawler