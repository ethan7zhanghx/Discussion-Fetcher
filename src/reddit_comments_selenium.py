"""Reddit Comments Fetcher - 使用 Selenium + Cookies 自动获取完整评论数据"""

import json
import time
import re
from typing import List, Optional
from pathlib import Path
from datetime import datetime

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup

from .base import BaseFetcher
from .models import Platform, RedditPost, create_reddit_discussion, ContentType
from .config import Config
import html as html_lib


class RedditCommentsSeleniumFetcher(BaseFetcher):
    """
    使用 Selenium + Cookies 自动获取 Reddit 评论数据

    优势：
    - ✅ 自动化：无需手动保存 HTML
    - ✅ 完整数据：可以滚动加载所有评论（几百条/板块）
    - ✅ 避免限制：使用 cookies 避免 CAPTCHA 和登录弹窗

    使用方法：
    1. 从浏览器导出 cookies（使用 EditThisCookie 等插件）
    2. 保存为 ./cookies.json
    3. 运行此脚本自动获取评论数据
    """

    def __init__(
        self,
        cookies_file: str = "./cookies.json",
        headless: bool = True,
        verbose: bool = False,
        rate_limit: Optional[float] = 3.0,
        config: Optional[Config] = None,
        auto_save: bool = True
    ):
        """
        初始化 Reddit Comments Selenium Fetcher

        Args:
            cookies_file: cookies 文件路径（JSON 格式）
            headless: 是否使用无头模式（不显示浏览器窗口）
            verbose: 详细日志
            rate_limit: 请求频率限制（秒/次）
            config: 配置实例
            auto_save: 自动保存到数据库
        """
        if config is None:
            config = Config()

        super().__init__(
            platform=Platform.REDDIT,
            verbose=verbose,
            rate_limit=rate_limit,
            config=config,
            auto_save=auto_save
        )

        self.cookies_file = cookies_file
        self.headless = headless
        self.driver = None
        self._setup_driver()
        self._authenticate()

    def _authenticate(self) -> None:
        """加载 cookies"""
        cookies_path = Path(self.cookies_file)

        if not cookies_path.exists():
            self.logger.warning(
                f"未找到 cookies 文件: {self.cookies_file}\n"
                f"将尝试不使用 cookies（可能需要手动验证 CAPTCHA）"
            )
            return

        try:
            # 先访问 Reddit 主页（需要在同域名下才能设置 cookies）
            self.driver.get("https://www.reddit.com")
            time.sleep(2)

            with open(cookies_path, 'r') as f:
                cookies_data = json.load(f)

            # 加载 cookies
            if isinstance(cookies_data, list):
                # EditThisCookie 格式
                for cookie in cookies_data:
                    try:
                        # 只添加必要的字段
                        cookie_dict = {
                            'name': cookie['name'],
                            'value': cookie['value'],
                            'domain': cookie.get('domain', '.reddit.com')
                        }
                        # 添加可选字段
                        if 'path' in cookie:
                            cookie_dict['path'] = cookie['path']
                        if 'secure' in cookie:
                            cookie_dict['secure'] = cookie['secure']

                        self.driver.add_cookie(cookie_dict)
                    except Exception as e:
                        self.logger.debug(f"跳过 cookie {cookie.get('name')}: {e}")

            elif isinstance(cookies_data, dict):
                # 简单字典格式
                for name, value in cookies_data.items():
                    try:
                        self.driver.add_cookie({
                            'name': name,
                            'value': value,
                            'domain': '.reddit.com'
                        })
                    except Exception as e:
                        self.logger.debug(f"跳过 cookie {name}: {e}")

            self.logger.info(f"✓ 已加载 cookies")

            # 刷新页面以应用 cookies
            self.driver.refresh()
            time.sleep(2)

        except Exception as e:
            self.logger.error(f"加载 cookies 失败: {e}")

    def _setup_driver(self) -> None:
        """设置 Selenium WebDriver"""
        max_retries = 3
        for attempt in range(max_retries):
            try:
                chrome_options = Options()

                if self.headless:
                    chrome_options.add_argument('--headless')
                    chrome_options.add_argument('--disable-gpu')

                # 其他优化选项
                chrome_options.add_argument('--no-sandbox')
                chrome_options.add_argument('--disable-dev-shm-usage')
                chrome_options.add_argument('--disable-blink-features=AutomationControlled')
                chrome_options.add_argument('--user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')

                # 添加网络超时设置
                chrome_options.add_argument('--dns-prefetch-disable')
                chrome_options.page_load_strategy = 'normal'

                # 自动下载并管理 ChromeDriver
                service = Service(ChromeDriverManager().install())
                self.driver = webdriver.Chrome(service=service, options=chrome_options)

                # 设置页面加载超时（30秒）
                self.driver.set_page_load_timeout(30)
                # 设置隐式等待
                self.driver.implicitly_wait(10)

                self.logger.info("✓ Selenium WebDriver 初始化成功")
                return

            except Exception as e:
                if attempt < max_retries - 1:
                    self.logger.warning(f"WebDriver 初始化失败 (尝试 {attempt + 1}/{max_retries}): {e}，正在重试...")
                    time.sleep(2 ** attempt)  # 指数退避
                else:
                    self.logger.error(f"WebDriver 初始化失败（所有重试均失败）: {e}")
                    raise

    def fetch_global_search_page_with_scroll(
        self,
        query: str,
        sort: str = "new",
        time_filter: str = "all",
        max_scrolls: int = 10
    ) -> str:
        """
        获取 Reddit 全局搜索页面的完整 HTML（通过滚动加载）

        Args:
            query: 搜索关键词
            sort: 排序方式（默认: "new" - 按时间排序，获取最新评论）
            time_filter: 时间范围
            max_scrolls: 最大滚动次数（控制获取量）

        Returns:
            完整的 HTML 内容
        """
        self.rate_limiter.wait_if_needed()

        # 构建全局搜索 URL
        url = "https://www.reddit.com/search/"
        params = f"?q={query}&type=comment&sort={sort}&t={time_filter}"
        full_url = url + params

        self.logger.debug(f"访问全局搜索 URL: {full_url}")

        max_retries = 2
        for attempt in range(max_retries):
            try:
                # 访问页面
                self.driver.get(full_url)
                time.sleep(3)  # 等待初始加载

                # 检查是否有 CAPTCHA 或限流
                page_text = self.driver.page_source.lower()
                if 'whoa there, pardner' in page_text:
                    self.logger.error("❌ 被 Reddit 限流，等待后重试...")
                    if attempt < max_retries - 1:
                        time.sleep(30)  # 限流时等待更长时间
                        continue
                    return ""

                if 'prove your humanity' in page_text:
                    self.logger.error("❌ 需要完成 CAPTCHA 验证")
                    return ""

                # 页面加载成功，退出重试循环
                break

            except Exception as e:
                if attempt < max_retries - 1:
                    self.logger.warning(f"全局搜索页面加载失败 (尝试 {attempt + 1}/{max_retries}): {e}，正在重试...")
                    time.sleep(5)
                    continue
                else:
                    self.logger.error(f"全局搜索页面加载失败（所有重试均失败）: {e}")
                    return ""

        try:
            # 滚动加载更多内容
            last_height = self.driver.execute_script("return document.body.scrollHeight")
            scroll_count = 0
            no_change_count = 0

            self.logger.info(f"开始滚动加载全局搜索结果（最多 {max_scrolls} 次）...")

            while scroll_count < max_scrolls:
                # 滚动到底部
                self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(2)  # 等待内容加载

                # 计算新的滚动高度
                new_height = self.driver.execute_script("return document.body.scrollHeight")

                if new_height == last_height:
                    no_change_count += 1
                    if no_change_count >= 3:
                        self.logger.debug("页面高度不再变化，停止滚动")
                        break
                else:
                    no_change_count = 0
                    scroll_count += 1
                    self.logger.debug(f"滚动 {scroll_count}/{max_scrolls}")

                last_height = new_height

            self.logger.info(f"✓ 滚动完成（{scroll_count} 次）")

            # 获取完整 HTML
            html_content = self.driver.page_source
            self.logger.debug(f"✓ 获取 HTML 成功（{len(html_content)} 字符）")

            return html_content

        except Exception as e:
            self.logger.error(f"获取全局搜索页面失败: {e}")
            return ""

    def fetch_search_page_with_scroll(
        self,
        query: str,
        subreddit: str,
        sort: str = "new",
        time_filter: str = "all",
        max_scrolls: int = 10
    ) -> str:
        """
        获取 Reddit 子版块搜索页面的完整 HTML（通过滚动加载）

        Args:
            query: 搜索关键词
            subreddit: 子版块名称
            sort: 排序方式（默认: "new" - 按时间排序，获取最新评论）
            time_filter: 时间范围
            max_scrolls: 最大滚动次数（控制获取量）

        Returns:
            完整的 HTML 内容
        """
        self.rate_limiter.wait_if_needed()

        # 构建子版块搜索 URL
        url = f"https://www.reddit.com/r/{subreddit}/search/"
        params = f"?q={query}&restrict_sr=1&type=comment&sort={sort}&t={time_filter}"
        full_url = url + params

        self.logger.debug(f"访问 URL: {full_url}")

        max_retries = 2
        for attempt in range(max_retries):
            try:
                # 访问页面
                self.driver.get(full_url)
                time.sleep(3)  # 等待初始加载

                # 检查是否有 CAPTCHA 或限流
                page_text = self.driver.page_source.lower()
                if 'whoa there, pardner' in page_text:
                    self.logger.error("❌ 被 Reddit 限流，等待后重试...")
                    if attempt < max_retries - 1:
                        time.sleep(30)  # 限流时等待更长时间
                        continue
                    return ""

                if 'prove your humanity' in page_text:
                    self.logger.error("❌ 需要完成 CAPTCHA 验证")
                    return ""

                # 页面加载成功，退出重试循环
                break

            except Exception as e:
                if attempt < max_retries - 1:
                    self.logger.warning(f"子版块搜索页面加载失败 (尝试 {attempt + 1}/{max_retries}): {e}，正在重试...")
                    time.sleep(5)
                    continue
                else:
                    self.logger.error(f"子版块搜索页面加载失败（所有重试均失败）: {e}")
                    return ""

        try:
            # 滚动加载更多内容
            last_height = self.driver.execute_script("return document.body.scrollHeight")
            scroll_count = 0
            no_change_count = 0

            self.logger.info(f"开始滚动加载（最多 {max_scrolls} 次）...")

            while scroll_count < max_scrolls:
                # 滚动到底部
                self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(2)  # 等待内容加载

                # 计算新的滚动高度
                new_height = self.driver.execute_script("return document.body.scrollHeight")

                if new_height == last_height:
                    no_change_count += 1
                    if no_change_count >= 3:
                        self.logger.debug("页面高度不再变化，停止滚动")
                        break
                else:
                    no_change_count = 0
                    scroll_count += 1
                    self.logger.debug(f"滚动 {scroll_count}/{max_scrolls}")

                last_height = new_height

            self.logger.info(f"✓ 滚动完成（{scroll_count} 次）")

            # 获取完整 HTML
            html_content = self.driver.page_source
            self.logger.debug(f"✓ 获取 HTML 成功（{len(html_content)} 字符）")

            return html_content

        except Exception as e:
            self.logger.error(f"获取页面失败: {e}")
            return ""

    def parse_timestamp(self, ts_string: str) -> Optional[datetime]:
        """解析时间戳"""
        try:
            if ts_string.isdigit():
                timestamp_ms = int(ts_string)
                return datetime.fromtimestamp(timestamp_ms / 1000.0)
            else:
                ts_clean = ts_string.replace('Z', '+00:00')
                ts_clean = re.sub(r'\+0000$', '+00:00', ts_clean)
                return datetime.fromisoformat(ts_clean)
        except Exception as e:
            self.logger.warning(f"时间戳解析失败: {ts_string}, 错误: {e}")
            return None

    def parse_comment_element(self, element) -> Optional[RedditPost]:
        """解析单个评论元素（复用 parse_reddit_html.py 的逻辑）"""
        try:
            comment_id = ''
            post_id = ''
            post_title = None
            subreddit = ''

            tracking_data = element.get('data-faceplate-tracking-context', '')
            if tracking_data:
                tracking_json = html_lib.unescape(tracking_data)
                tracking_dict = json.loads(tracking_json)

                comment_info = tracking_dict.get('comment', {})
                comment_id = comment_info.get('id', '').replace('t1_', '')
                post_id = comment_info.get('post_id', '').replace('t3_', '')

                post_info = tracking_dict.get('post', {})
                post_title = post_info.get('title', '')

                subreddit_info = tracking_dict.get('subreddit', {})
                subreddit = subreddit_info.get('name', '')

            author = '[deleted]'
            author_link = element.find('a', href=re.compile(r'/user/'))
            if author_link:
                author = author_link.text.strip()

            content = ''
            content_div = element.find('div', id=re.compile(r'search-comment-t1_'))
            if content_div:
                content = content_div.get_text(separator='\n', strip=True)

            score = 0
            votes_span = element.find('span', string=re.compile(r'\d+\s+votes?'))
            if votes_span:
                votes_match = re.search(r'(\d+)\s+votes?', votes_span.text)
                if votes_match:
                    score = int(votes_match.group(1))

            created_at = None
            time_elem = element.find('faceplate-timeago')
            if time_elem:
                ts = time_elem.get('ts', '')
                if ts:
                    created_at = self.parse_timestamp(ts)

            if created_at is None:
                return None

            url = ''
            permalink = ''
            comment_link = element.find('a', href=re.compile(r'/comments/.*/.*/.*/'))
            if comment_link:
                permalink = comment_link.get('href', '')
                if permalink.startswith('/'):
                    url = f"https://www.reddit.com{permalink}"
                else:
                    url = permalink

            if content:
                return create_reddit_discussion(
                    post_id=comment_id,
                    title=post_title,
                    content=content,
                    author=author,
                    created_at=created_at,
                    subreddit=subreddit,
                    url=url,
                    permalink=permalink,
                    score=score,
                    content_type=ContentType.COMMENT,
                    parent_id=post_id
                )

            return None

        except Exception as e:
            self.logger.debug(f"解析评论时出错: {e}")
            return None

    def parse_html(self, html_content: str, days_limit: Optional[int] = None) -> tuple[List[RedditPost], bool]:
        """
        解析 HTML 内容，提取评论

        Args:
            html_content: HTML 字符串
            days_limit: 只获取最近 N 天的评论（None = 不限制）

        Returns:
            (评论列表, 是否遇到超时评论)
        """
        soup = BeautifulSoup(html_content, 'html.parser')

        comment_elements = soup.find_all(
            'search-telemetry-tracker',
            attrs={'view-events': 'search/view/comment'}
        )

        self.logger.debug(f"找到 {len(comment_elements)} 个评论元素")

        comments = []
        has_old_comments = False

        # 计算时间阈值
        cutoff_date = None
        if days_limit:
            from datetime import timedelta, timezone
            # 使用 UTC 时区以匹配解析的时间戳
            cutoff_date = datetime.now(timezone.utc) - timedelta(days=days_limit)
            self.logger.debug(f"时间过滤：只获取 {cutoff_date.strftime('%Y-%m-%d')} 之后的评论")

        for idx, elem in enumerate(comment_elements, 1):
            comment = self.parse_comment_element(elem)
            if comment:
                # 检查时间限制
                if cutoff_date and comment.created_at:
                    if comment.created_at < cutoff_date:
                        self.logger.debug(f"遇到超时评论: {comment.created_at.strftime('%Y-%m-%d')}")
                        has_old_comments = True
                        continue  # 跳过旧评论，但继续检查其他评论

                comments.append(comment)
                if self.verbose and idx % 10 == 0:
                    self.logger.debug(f"已解析 {idx}/{len(comment_elements)}")

        self.logger.info(f"✓ 成功解析 {len(comments)} 条评论（时间限制: {days_limit}天）")
        return comments, has_old_comments

    def fetch(
        self,
        query: str = "ERNIE",
        subreddits: Optional[List[str]] = None,
        sort: str = "new",
        time_filter: str = "all",
        max_scrolls: int = 10,
        days_limit: int = 30,
        search_mode: str = "subreddits",
        search_keywords: Optional[str] = None
    ) -> List[RedditPost]:
        """
        从 Reddit 获取评论数据（自动滚动加载）

        Args:
            query: 搜索关键词
            subreddits: 子版块列表（None = 使用默认列表）
            sort: 排序方式（默认: "new" - 按时间排序，获取最新评论）
            time_filter: 时间范围
            max_scrolls: 每个板块最多滚动次数（默认10次，约200-300条评论）
            days_limit: 只获取最近 N 天的评论（默认30天）
            search_mode: 搜索模式 ("subreddits" 或 "global")
            search_keywords: 搜索关键词标签（用于数据库标记）

        Returns:
            RedditPost 对象列表（评论）
        """
        all_comments = []

        if search_mode == "global":
            # 全局搜索模式
            self.logger.info(f"开始全局搜索评论（最多滚动 {max_scrolls} 次，时间范围: 最近{days_limit}天）...")

            try:
                # 获取完整 HTML（通过滚动）
                html_content = self.fetch_global_search_page_with_scroll(
                    query=query,
                    sort=sort,
                    time_filter=time_filter,
                    max_scrolls=max_scrolls
                )

                if not html_content:
                    self.logger.warning("全局搜索获取失败")
                else:
                    # 解析 HTML（带时间过滤）
                    comments, has_old_comments = self.parse_html(html_content, days_limit=days_limit)

                    # 添加 search_keywords 标签
                    if search_keywords:
                        for comment in comments:
                            comment.search_keywords = search_keywords

                    all_comments.extend(comments)
                    self.logger.info(f"  全局搜索获取 {len(comments)} 条评论（最近{days_limit}天）")

            except Exception as e:
                self.logger.error(f"全局搜索时出错: {e}")

        else:
            # 子版块搜索模式（原有逻辑）
            if subreddits is None:
                from .reddit import REDDIT_SUBREDDITS
                subreddits = REDDIT_SUBREDDITS

            self.logger.info(f"开始从 {len(subreddits)} 个板块获取评论（每个最多滚动 {max_scrolls} 次，时间范围: 最近{days_limit}天）...")

            for idx, subreddit in enumerate(subreddits, 1):
                self.logger.info(f"[{idx}/{len(subreddits)}] 获取 r/{subreddit} 的评论...")

                try:
                    # 获取完整 HTML（通过滚动）
                    html_content = self.fetch_search_page_with_scroll(
                        query=query,
                        subreddit=subreddit,
                        sort=sort,
                        time_filter=time_filter,
                        max_scrolls=max_scrolls
                    )

                    if not html_content:
                        self.logger.warning(f"r/{subreddit} 获取失败，跳过")
                        continue

                    # 解析 HTML（带时间过滤）
                    comments, has_old_comments = self.parse_html(html_content, days_limit=days_limit)

                    # 添加 search_keywords 标签
                    if search_keywords:
                        for comment in comments:
                            comment.search_keywords = search_keywords

                    all_comments.extend(comments)

                    self.logger.info(f"  从 r/{subreddit} 获取 {len(comments)} 条评论（最近{days_limit}天）")

                except Exception as e:
                    self.logger.error(f"处理 r/{subreddit} 时出错: {e}")
                    continue

        # 自动保存到数据库
        if all_comments:
            self.add_discussions(all_comments, source='selenium')

        self.logger.info(f"✓ 总计获取 {len(all_comments)} 条评论（最近{days_limit}天）")
        return all_comments

    def __del__(self):
        """清理资源"""
        if self.driver:
            try:
                self.driver.quit()
            except:
                pass


if __name__ == "__main__":
    import sys

    # 测试获取数据
    try:
        fetcher = RedditCommentsSeleniumFetcher(
            headless=False,  # 显示浏览器窗口（测试时方便观察）
            verbose=True
        )
        comments = fetcher.fetch(query="ERNIE", subreddits=["LocalLLM"], max_scrolls=5)

        print(f"\n✓ 获取 {len(comments)} 条评论")

        # 显示前 3 条
        for i, comment in enumerate(comments[:3], 1):
            print(f"\n[{i}] {comment.author}")
            print(f"    内容: {comment.content[:100]}...")
            print(f"    评分: {comment.score}")
            print(f"    时间: {comment.created_at}")

    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
