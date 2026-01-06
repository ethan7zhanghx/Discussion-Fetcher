"""Reddit Comments Fetcher - 使用 cookies 自动获取评论数据（无需手动保存HTML）"""

import requests
from typing import List, Optional
from pathlib import Path
import json
import re
import html as html_lib
from datetime import datetime
from bs4 import BeautifulSoup

from .base import BaseFetcher
from .models import Platform, RedditPost, create_reddit_discussion, ContentType
from .utils import retry_on_failure
from .config import Config


class RedditCommentsFetcher(BaseFetcher):
    """
    使用 HTTP 请求 + cookies 自动获取 Reddit 评论数据

    与 PRAW API (posts) 互补：
    - PRAW API: 获取帖子 (posts)
    - 本类: 获取评论 (comments)

    使用方法：
    1. 从浏览器导出 cookies（使用 EditThisCookie 等插件）
    2. 保存为 ./cookies.json
    3. 运行此脚本自动获取评论数据
    """

    def __init__(
        self,
        cookies_file: str = "./cookies.json",
        verbose: bool = False,
        rate_limit: Optional[float] = 2.0,  # Reddit 限流较严
        config: Optional[Config] = None,
        auto_save: bool = True
    ):
        """
        初始化 Reddit Comments Fetcher

        Args:
            cookies_file: cookies 文件路径（JSON 格式）
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
        self.session = requests.Session()
        self._setup_session()
        self._authenticate()

    def _authenticate(self) -> None:
        """加载 cookies 并验证"""
        cookies_path = Path(self.cookies_file)

        if not cookies_path.exists():
            self.logger.warning(
                f"未找到 cookies 文件: {self.cookies_file}\n"
                f"请按照以下步骤导出 cookies：\n"
                f"1. 在浏览器中登录 Reddit\n"
                f"2. 安装 EditThisCookie 插件（Chrome/Edge）\n"
                f"3. 点击插件图标 → Export → 复制 JSON\n"
                f"4. 保存为 {self.cookies_file}"
            )
            raise FileNotFoundError(f"Cookies file not found: {self.cookies_file}")

        try:
            with open(cookies_path, 'r') as f:
                cookies_data = json.load(f)

            # 支持两种格式：
            # 1. EditThisCookie 格式（数组）
            # 2. 简单字典格式
            if isinstance(cookies_data, list):
                # EditThisCookie 格式: [{"name": "...", "value": "...", "domain": "..."}]
                for cookie in cookies_data:
                    self.session.cookies.set(
                        cookie['name'],
                        cookie['value'],
                        domain=cookie.get('domain', '.reddit.com')
                    )
            elif isinstance(cookies_data, dict):
                # 简单字典格式: {"cookie_name": "cookie_value"}
                for name, value in cookies_data.items():
                    self.session.cookies.set(name, value, domain='.reddit.com')

            self.logger.info(f"✓ 已加载 {len(self.session.cookies)} 个 cookies")

        except Exception as e:
            self.logger.error(f"加载 cookies 失败: {e}")
            raise

    def _setup_session(self) -> None:
        """配置 requests session（模拟浏览器）"""
        self.session.headers.update({
            'User-Agent': (
                'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) '
                'AppleWebKit/537.36 (KHTML, like Gecko) '
                'Chrome/120.0.0.0 Safari/537.36'
            ),
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1'
        })

    @retry_on_failure(max_attempts=3, exceptions=(requests.RequestException,))
    def fetch_search_page(
        self,
        query: str,
        subreddit: Optional[str] = None,
        sort: str = "relevance",
        time_filter: str = "all",
        after: Optional[str] = None
    ) -> tuple[str, Optional[str]]:
        """
        获取 Reddit 搜索页面的 HTML（支持分页）

        Args:
            query: 搜索关键词
            subreddit: 子版块名称（None = 全站搜索）
            sort: 排序方式（relevance, hot, top, new, comments）
            time_filter: 时间范围（hour, day, week, month, year, all）
            after: 分页参数（用于获取下一页）

        Returns:
            (HTML 内容, 下一页的 after 参数)
        """
        self.rate_limiter.wait_if_needed()

        # 构建 URL
        if subreddit:
            url = f"https://www.reddit.com/r/{subreddit}/search/"
        else:
            url = "https://www.reddit.com/search/"

        params = {
            'q': query,
            'sort': sort,
            't': time_filter,
            'type': 'comment'  # 获取评论
        }

        if subreddit:
            params['restrict_sr'] = 'on'  # 限制在当前 subreddit

        if after:
            params['after'] = after  # 分页参数

        try:
            self.logger.debug(f"请求 URL: {url}?{requests.compat.urlencode(params)}")
            response = self.session.get(url, params=params, timeout=30)
            response.raise_for_status()

            # 检查是否被限流
            if 'whoa there, pardner' in response.text.lower():
                self.logger.error("❌ 被 Reddit 限流，请稍后再试")
                return "", None

            # 检查是否需要验证
            if 'Prove your humanity' in response.text:
                self.logger.error("❌ 需要完成 CAPTCHA 验证，请在浏览器中操作后重新导出 cookies")
                return "", None

            self.logger.debug(f"✓ 获取 HTML 成功（{len(response.text)} 字符）")

            # 尝试从 HTML 中提取下一页的 after 参数
            next_after = self._extract_next_after(response.text)

            return response.text, next_after

        except requests.RequestException as e:
            self.logger.error(f"请求失败: {e}")
            raise

    def _extract_next_after(self, html_content: str) -> Optional[str]:
        """
        从 HTML 中提取下一页的 after 参数

        Args:
            html_content: HTML 内容

        Returns:
            下一页的 after 参数，如果没有则返回 None
        """
        try:
            # 查找 "下一页" 链接
            soup = BeautifulSoup(html_content, 'html.parser')

            # 方法 1: 查找包含 after 参数的链接
            next_link = soup.find('a', href=re.compile(r'after='))
            if next_link:
                href = next_link.get('href', '')
                match = re.search(r'after=([^&]+)', href)
                if match:
                    return match.group(1)

            # 方法 2: 查找特定的下一页按钮
            next_button = soup.find('a', string=re.compile(r'next|下一页', re.I))
            if next_button:
                href = next_button.get('href', '')
                match = re.search(r'after=([^&]+)', href)
                if match:
                    return match.group(1)

            return None

        except Exception as e:
            self.logger.debug(f"提取 after 参数失败: {e}")
            return None

    def parse_timestamp(self, ts_string: str) -> Optional[datetime]:
        """
        解析时间戳（复用 parse_reddit_html.py 的逻辑）
        """
        try:
            # 尝试作为毫秒时间戳解析
            if ts_string.isdigit():
                timestamp_ms = int(ts_string)
                return datetime.fromtimestamp(timestamp_ms / 1000.0)
            # 尝试作为 ISO 格式解析
            else:
                ts_clean = ts_string.replace('Z', '+00:00')
                ts_clean = re.sub(r'\+0000$', '+00:00', ts_clean)
                return datetime.fromisoformat(ts_clean)
        except Exception as e:
            self.logger.warning(f"时间戳解析失败: {ts_string}, 错误: {e}")
            return None

    def parse_comment_element(self, element) -> Optional[RedditPost]:
        """
        解析单个评论元素（复用 parse_reddit_html.py 的逻辑）
        """
        try:
            # 1. 提取 tracking data
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

            # 2. 提取作者
            author = '[deleted]'
            author_link = element.find('a', href=re.compile(r'/user/'))
            if author_link:
                author = author_link.text.strip()

            # 3. 提取评论内容
            content = ''
            content_div = element.find('div', id=re.compile(r'search-comment-t1_'))
            if content_div:
                content = content_div.get_text(separator='\n', strip=True)

            # 4. 提取评分
            score = 0
            votes_span = element.find('span', string=re.compile(r'\d+\s+votes?'))
            if votes_span:
                votes_match = re.search(r'(\d+)\s+votes?', votes_span.text)
                if votes_match:
                    score = int(votes_match.group(1))

            # 5. 提取时间戳
            created_at = None
            time_elem = element.find('faceplate-timeago')
            if time_elem:
                ts = time_elem.get('ts', '')
                if ts:
                    created_at = self.parse_timestamp(ts)

            if created_at is None:
                if comment_id:
                    self.logger.debug(f"评论 {comment_id} 没有时间戳，跳过")
                return None

            # 6. 提取链接
            url = ''
            permalink = ''
            comment_link = element.find('a', href=re.compile(r'/comments/.*/.*/.*/'))
            if comment_link:
                permalink = comment_link.get('href', '')
                if permalink.startswith('/'):
                    url = f"https://www.reddit.com{permalink}"
                else:
                    url = permalink

            # 创建 RedditPost 对象
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
            self.logger.error(f"解析评论时出错: {e}")
            return None

    def parse_html(self, html_content: str) -> List[RedditPost]:
        """
        解析 HTML 内容，提取评论

        Args:
            html_content: HTML 字符串

        Returns:
            RedditPost 对象列表
        """
        soup = BeautifulSoup(html_content, 'html.parser')

        # 检查是否被限流或需要验证
        if 'whoa there, pardner' in html_content.lower():
            self.logger.error("❌ HTML 显示被限流")
            return []

        if 'Prove your humanity' in html_content:
            self.logger.error("❌ HTML 显示需要 CAPTCHA 验证")
            return []

        # 查找所有评论元素
        comment_elements = soup.find_all(
            'search-telemetry-tracker',
            attrs={'view-events': 'search/view/comment'}
        )

        self.logger.debug(f"找到 {len(comment_elements)} 个评论元素")

        comments = []
        for idx, elem in enumerate(comment_elements, 1):
            comment = self.parse_comment_element(elem)
            if comment:
                comments.append(comment)
                if self.verbose and idx % 10 == 0:
                    self.logger.debug(f"已解析 {idx}/{len(comment_elements)}")

        self.logger.info(f"✓ 成功解析 {len(comments)} 条评论")
        return comments

    def fetch(
        self,
        query: str = "ERNIE",
        subreddits: Optional[List[str]] = None,
        sort: str = "relevance",
        time_filter: str = "all",
        max_pages: int = 5
    ) -> List[RedditPost]:
        """
        从 Reddit 获取评论数据（支持多页）

        Args:
            query: 搜索关键词
            subreddits: 子版块列表（None = 使用默认列表）
            sort: 排序方式
            time_filter: 时间范围
            max_pages: 每个板块最多获取的页数（默认5页，约125条评论）

        Returns:
            RedditPost 对象列表（评论）
        """
        if subreddits is None:
            # 使用与 reddit.py 相同的默认列表
            from .reddit import REDDIT_SUBREDDITS
            subreddits = REDDIT_SUBREDDITS

        all_comments = []

        self.logger.info(f"开始从 {len(subreddits)} 个板块获取评论（每个板块最多 {max_pages} 页）...")

        for idx, subreddit in enumerate(subreddits, 1):
            self.logger.info(f"[{idx}/{len(subreddits)}] 获取 r/{subreddit} 的评论...")

            try:
                subreddit_comments = []
                after = None
                page_num = 1

                # 循环获取多页
                while page_num <= max_pages:
                    self.logger.debug(f"  第 {page_num} 页...")

                    # 获取 HTML
                    html_content, next_after = self.fetch_search_page(
                        query=query,
                        subreddit=subreddit,
                        sort=sort,
                        time_filter=time_filter,
                        after=after
                    )

                    if not html_content:
                        self.logger.warning(f"r/{subreddit} 第 {page_num} 页获取失败")
                        break

                    # 解析 HTML
                    comments = self.parse_html(html_content)

                    if not comments:
                        self.logger.debug(f"  第 {page_num} 页没有评论，停止")
                        break

                    subreddit_comments.extend(comments)
                    self.logger.debug(f"  第 {page_num} 页获取 {len(comments)} 条评论")

                    # 检查是否有下一页
                    if not next_after:
                        self.logger.debug(f"  没有更多页面，停止")
                        break

                    after = next_after
                    page_num += 1

                all_comments.extend(subreddit_comments)
                self.logger.info(f"  从 r/{subreddit} 获取 {len(subreddit_comments)} 条评论（{page_num-1} 页）")

            except Exception as e:
                self.logger.error(f"处理 r/{subreddit} 时出错: {e}")
                continue

        # 自动保存到数据库
        if all_comments:
            self.add_discussions(all_comments, source='web')

        self.logger.info(f"✓ 总计获取 {len(all_comments)} 条评论")
        return all_comments

    def save_html_debug(self, html_content: str, filename: str) -> None:
        """
        保存 HTML 到文件（用于调试）

        Args:
            html_content: HTML 内容
            filename: 文件名
        """
        filepath = Path("./data/html_debug") / filename
        filepath.parent.mkdir(parents=True, exist_ok=True)

        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(html_content)

        self.logger.info(f"✓ 已保存调试 HTML 到 {filepath}")


def export_cookies_guide():
    """
    显示如何导出 cookies 的指南
    """
    guide = """
╔════════════════════════════════════════════════════════════════╗
║           如何导出 Reddit Cookies（仅需一次）                    ║
╚════════════════════════════════════════════════════════════════╝

方法 1: 使用 EditThisCookie 插件（推荐）
───────────────────────────────────────
1. 安装插件:
   Chrome/Edge: https://chrome.google.com/webstore → 搜索 "EditThisCookie"
   Firefox: https://addons.mozilla.org → 搜索 "EditThisCookie"

2. 登录 Reddit:
   访问 https://www.reddit.com 并登录

3. 导出 cookies:
   - 点击浏览器工具栏的 EditThisCookie 图标
   - 点击 "Export" 按钮
   - 复制 JSON 内容
   - 保存为 ./cookies.json

方法 2: 浏览器开发者工具
───────────────────────────────────────
1. 登录 Reddit
2. 按 F12 打开开发者工具
3. 切换到 "Application" / "存储" 标签
4. 左侧选择 "Cookies" → "https://www.reddit.com"
5. 复制以下重要 cookies（名称和值）:
   - reddit_session
   - token_v2
   - loid
   - edgebucket

6. 创建 cookies.json 文件:
{
  "reddit_session": "从浏览器复制的值",
  "token_v2": "从浏览器复制的值",
  "loid": "从浏览器复制的值",
  "edgebucket": "从浏览器复制的值"
}

注意事项:
───────────────────────────────────────
• Cookies 会过期，如果失效请重新导出
• 不要分享你的 cookies 文件（包含登录凭证）
• 建议添加到 .gitignore 中

完成后运行:
───────────────────────────────────────
python3 -c "from src.reddit_comments import RedditCommentsFetcher; \
            fetcher = RedditCommentsFetcher(verbose=True); \
            fetcher.fetch(query='ERNIE', subreddits=['LocalLLM'])"

"""
    print(guide)


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "guide":
        export_cookies_guide()
    else:
        # 测试获取数据
        try:
            fetcher = RedditCommentsFetcher(verbose=True)
            comments = fetcher.fetch(query="ERNIE", subreddits=["LocalLLM"])

            print(f"\n✓ 获取 {len(comments)} 条评论")

            # 显示前 3 条
            for i, comment in enumerate(comments[:3], 1):
                print(f"\n[{i}] {comment.author}")
                print(f"    内容: {comment.content[:100]}...")
                print(f"    评分: {comment.score}")
                print(f"    时间: {comment.created_at}")

        except FileNotFoundError:
            print("\n❌ 未找到 cookies.json 文件\n")
            print("请运行以下命令查看导出指南:")
            print("python3 -m src.reddit_comments guide")
