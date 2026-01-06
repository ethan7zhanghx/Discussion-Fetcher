"""Reddit discussion fetcher - PRAW API only."""

from typing import List, Optional
from datetime import datetime
import praw
from prawcore.exceptions import PrawcoreException, ResponseException

from .base import BaseFetcher
from .models import Platform, ContentType, RedditPost, create_reddit_discussion
from .utils import retry_on_failure
from .config import Config


# 固定的 Reddit 板块列表 - 总是获取所有这些板块
REDDIT_SUBREDDITS = [
    "LocalLLM",
    "LocalLlaMa",
    "ChatGPT",
    "ArtificialIntelligence",
    "OpenSourceeAI",
    "singularity",
    "machinelearningnews",
    "SillyTavernAI",
    "StableDiffusion"
]


class RedditFetcher(BaseFetcher):
    """Fetcher for Reddit discussions using PRAW API."""

    def __init__(
        self,
        client_id: Optional[str] = None,
        client_secret: Optional[str] = None,
        user_agent: Optional[str] = None,
        verbose: bool = False,
        rate_limit: Optional[float] = None,
        config: Optional[Config] = None,
        auto_save: bool = True
    ):
        """
        Initialize Reddit fetcher.

        Args:
            client_id: Reddit API client ID
            client_secret: Reddit API client secret
            user_agent: Reddit API user agent
            verbose: Enable verbose logging
            rate_limit: API rate limit (calls per second)
            config: Configuration instance
            auto_save: Automatically save to database (default: True)
        """
        if config is None:
            config = Config()

        self.client_id = client_id or config.REDDIT_CLIENT_ID
        self.client_secret = client_secret or config.REDDIT_CLIENT_SECRET
        self.user_agent = user_agent or config.REDDIT_USER_AGENT

        if not self.client_id or not self.client_secret:
            raise ValueError(
                "Reddit credentials required. "
                "Set REDDIT_CLIENT_ID and REDDIT_CLIENT_SECRET in .env"
            )

        super().__init__(
            platform=Platform.REDDIT,
            verbose=verbose,
            rate_limit=rate_limit,
            config=config,
            auto_save=auto_save
        )

        self._authenticate()

    def _authenticate(self) -> None:
        """Authenticate with Reddit API."""
        try:
            self.reddit = praw.Reddit(
                client_id=self.client_id,
                client_secret=self.client_secret,
                user_agent=self.user_agent,
                check_for_async=False
            )
            self.reddit.user.me()
            self.logger.info("✓ Reddit API authenticated")
        except Exception as e:
            self.logger.error(f"Reddit authentication failed: {e}")
            raise

    @staticmethod
    def _convert_timestamp(timestamp: float) -> datetime:
        """Convert Unix timestamp to datetime."""
        return datetime.fromtimestamp(timestamp)

    @retry_on_failure(max_attempts=3, exceptions=(PrawcoreException, ResponseException))
    def search_subreddit(
        self,
        subreddit_name: str,
        query: str,
        time_filter: Optional[str] = None,
        sort_by: str = "relevance",
        limit: Optional[int] = None,
        search_keywords: Optional[str] = None
    ) -> List[RedditPost]:
        """
        Search for posts in a subreddit using PRAW API.

        Args:
            subreddit_name: Subreddit name
            query: Search query (e.g., "ERNIE")
            time_filter: Time filter ("day", "week", "month", "year", "all")
            sort_by: Sort method ("relevance", "hot", "top", "new")
            limit: Maximum number of posts (None = all available)

        Returns:
            List of RedditPost objects
        """
        posts = []

        try:
            self.rate_limiter.wait_if_needed()
            subreddit = self.reddit.subreddit(subreddit_name)

            submissions = subreddit.search(
                query=query,
                sort=sort_by,
                time_filter=time_filter or "all",
                limit=limit
            )

            for submission in submissions:
                self.rate_limiter.wait_if_needed()

                post = create_reddit_discussion(
                    post_id=submission.id,
                    title=submission.title,
                    content=submission.selftext,
                    author=submission.author.name if submission.author else "[deleted]",
                    created_at=self._convert_timestamp(submission.created_utc),
                    subreddit=submission.subreddit.display_name,
                    url=submission.url,
                    permalink=f"https://reddit.com{submission.permalink}",
                    score=submission.score,
                    content_type=ContentType.POST,
                    upvote_ratio=submission.upvote_ratio,
                    num_comments=submission.num_comments,
                    is_self=submission.is_self,
                    link_flair_text=submission.link_flair_text,
                    search_keywords=search_keywords
                )
                posts.append(post)

            if posts:
                self.add_discussions(posts, source='api')

            if self.verbose:
                self.logger.info(f"Found {len(posts)} posts matching '{query}' in r/{subreddit_name}")

        except ResponseException as e:
            if hasattr(e, 'response') and hasattr(e.response, 'status_code'):
                status = e.response.status_code
                self.logger.error(f"Failed to search r/{subreddit_name} (HTTP {status}): {e}")
            else:
                self.logger.error(f"Failed to search r/{subreddit_name}: {e}")
        except PrawcoreException as e:
            self.logger.warning(f"Failed to search r/{subreddit_name} (PRAW error): {e}")
        except Exception as e:
            self.logger.error(f"Unexpected error searching r/{subreddit_name}: {e}", exc_info=self.verbose)

        return posts

    @retry_on_failure(max_attempts=3, exceptions=(PrawcoreException, ResponseException))
    def search_all_reddit(
        self,
        query: str,
        time_filter: Optional[str] = None,
        sort_by: str = "relevance",
        limit: Optional[int] = None,
        search_keywords: Optional[str] = None
    ) -> List[RedditPost]:
        """
        Search across ALL of Reddit (not limited to specific subreddits).

        Args:
            query: Search query (e.g., "PaddleOCR-VL")
            time_filter: Time filter ("day", "week", "month", "year", "all")
            sort_by: Sort method ("relevance", "hot", "top", "new")
            limit: Maximum number of posts (None = all available)
            search_keywords: Search keywords for tagging

        Returns:
            List of RedditPost objects
        """
        posts = []

        try:
            self.rate_limiter.wait_if_needed()

            # Search across all of Reddit using r/all
            submissions = self.reddit.subreddit("all").search(
                query=query,
                sort=sort_by,
                time_filter=time_filter or "all",
                limit=limit
            )

            for submission in submissions:
                self.rate_limiter.wait_if_needed()

                post = create_reddit_discussion(
                    post_id=submission.id,
                    title=submission.title,
                    content=submission.selftext,
                    author=submission.author.name if submission.author else "[deleted]",
                    created_at=self._convert_timestamp(submission.created_utc),
                    subreddit=submission.subreddit.display_name,
                    url=submission.url,
                    permalink=f"https://reddit.com{submission.permalink}",
                    score=submission.score,
                    content_type=ContentType.POST,
                    upvote_ratio=submission.upvote_ratio,
                    num_comments=submission.num_comments,
                    is_self=submission.is_self,
                    link_flair_text=submission.link_flair_text,
                    search_keywords=search_keywords
                )
                posts.append(post)

            if posts:
                self.add_discussions(posts, source='api')

            if self.verbose:
                self.logger.info(f"Found {len(posts)} posts matching '{query}' across all Reddit")

        except ResponseException as e:
            if hasattr(e, 'response') and hasattr(e.response, 'status_code'):
                status = e.response.status_code
                self.logger.error(f"Failed to search all Reddit (HTTP {status}): {e}")
            else:
                self.logger.error(f"Failed to search all Reddit: {e}")
        except PrawcoreException as e:
            self.logger.warning(f"Failed to search all Reddit (PRAW error): {e}")
        except Exception as e:
            self.logger.error(f"Unexpected error searching all Reddit: {e}", exc_info=self.verbose)

        return posts

    @retry_on_failure(max_attempts=3, exceptions=(PrawcoreException, ResponseException))
    def fetch_post_comments(
        self,
        post_id: str,
        post_title: str,
        subreddit_name: str,
        max_comments: Optional[int] = None,
        search_keywords: Optional[str] = None,
        replace_more_limit: int = 0
    ) -> List[RedditPost]:
        """
        获取单个 post 下的所有评论（使用 PRAW API）

        Args:
            post_id: Post ID
            post_title: Post 标题
            subreddit_name: Subreddit 名称
            max_comments: 最大评论数（None = 全部）
            search_keywords: 搜索关键词
            replace_more_limit: "展开更多评论"的次数限制
                - 0 = 展开所有（推荐用于全局搜索）
                - None = 不展开（只获取已加载的评论）
                - N = 最多展开 N 次 "MoreComments" 对象
                注意：每个 MoreComments 对象通常包含 20-100 条评论

        Returns:
            List of RedditPost objects (comments)
        """
        comments = []

        try:
            self.rate_limiter.wait_if_needed()
            submission = self.reddit.submission(id=post_id)

            # 展开"更多评论"链接
            # limit=0 表示全部展开（适合重要帖子或全局搜索）
            # limit=None 表示不展开，只获取已加载的评论
            # limit=N 表示最多展开 N 次（适合快速获取）
            if replace_more_limit is None:
                submission.comments.replace_more(limit=None)
            else:
                # 设置更高的阈值以获取更多评论
                submission.comments.replace_more(limit=replace_more_limit)

            # 获取所有评论（扁平化列表）
            all_comments = submission.comments.list()

            comment_count = 0
            for comment in all_comments:
                self.rate_limiter.wait_if_needed()

                # 跳过被删除的评论
                if not hasattr(comment, 'body') or not comment.body:
                    continue

                # 跳过 [deleted] 和 [removed]
                if comment.body in ['[deleted]', '[removed]']:
                    continue

                try:
                    comment_obj = create_reddit_discussion(
                        post_id=comment.id,
                        title=post_title,  # 评论的 title 使用 post 的 title
                        content=comment.body,
                        author=comment.author.name if comment.author else "[deleted]",
                        created_at=self._convert_timestamp(comment.created_utc),
                        subreddit=subreddit_name,
                        url=f"https://reddit.com{comment.permalink}",
                        permalink=comment.permalink,
                        score=comment.score,
                        content_type=ContentType.COMMENT,
                        parent_id=post_id,  # parent_id 指向所属的 post
                        search_keywords=search_keywords
                    )
                    comments.append(comment_obj)
                    comment_count += 1

                    # 达到最大数量限制
                    if max_comments and comment_count >= max_comments:
                        break

                except Exception as e:
                    self.logger.debug(f"Failed to parse comment {comment.id}: {e}")
                    continue

            if self.verbose and comments:
                self.logger.info(f"  ✓ Fetched {len(comments)} comments from post {post_id[:8]}...")

        except ResponseException as e:
            if hasattr(e, 'response') and hasattr(e.response, 'status_code'):
                status = e.response.status_code
                self.logger.warning(f"Failed to fetch comments for post {post_id} (HTTP {status}): {e}")
            else:
                self.logger.warning(f"Failed to fetch comments for post {post_id}: {e}")
        except PrawcoreException as e:
            self.logger.warning(f"Failed to fetch comments for post {post_id} (PRAW error): {e}")
        except Exception as e:
            self.logger.error(f"Unexpected error fetching comments for post {post_id}: {e}", exc_info=self.verbose)

        return comments

    def fetch(
        self,
        query: str = "ERNIE",
        time_filter: Optional[str] = None,
        sort_by: str = "relevance",
        limit: Optional[int] = None,
        fetch_comments: bool = True,
        max_comments_per_post: Optional[int] = None,
        days_limit: Optional[int] = None,
        replace_more_limit: int = 0
    ) -> List[RedditPost]:
        """
        Fetch from ALL predefined subreddits.

        总是从以下所有板块获取数据（9个）：
        - LocalLLM
        - LocalLlaMa
        - ChatGPT
        - ArtificialIntelligence
        - OpenSourceeAI
        - singularity
        - machinelearningnews
        - SillyTavernAI
        - StableDiffusion

        Args:
            query: Search query (default: "ERNIE")
            time_filter: Time filter (None = all time)
            sort_by: Sort method (default: "relevance")
            limit: Max posts per subreddit (None = all available)
            fetch_comments: 是否获取每个 post 下的评论（默认: True）
            max_comments_per_post: 每个 post 最多获取的评论数（None = 全部）
            days_limit: 只获取最近 N 天的数据（None = 全部历史数据）
            replace_more_limit: "展开更多评论"的次数限制（0=全部展开，推荐）

        Returns:
            List of all posts and comments from all subreddits
        """
        all_discussions = []

        self.logger.info(f"Fetching from {len(REDDIT_SUBREDDITS)} subreddits with query '{query}'")
        if fetch_comments:
            self.logger.info(f"Will also fetch comments from each post")
        if days_limit:
            self.logger.info(f"Time filter: last {days_limit} days")

        # 计算时间阈值
        from datetime import datetime, timedelta
        cutoff_date = None
        if days_limit:
            # PRAW 返回的是 naive datetime，所以这里也用 naive
            cutoff_date = datetime.now() - timedelta(days=days_limit)

        for idx, subreddit_name in enumerate(REDDIT_SUBREDDITS, 1):
            self.logger.info(f"[{idx}/{len(REDDIT_SUBREDDITS)}] Searching r/{subreddit_name}...")

            posts = self.search_subreddit(
                subreddit_name=subreddit_name,
                query=query,
                time_filter=time_filter,
                sort_by=sort_by,
                limit=limit,
                search_keywords=query  # 使用查询关键词作为标签
            )

            # 时间过滤 - Posts
            if cutoff_date:
                filtered_posts = [p for p in posts if p.created_at >= cutoff_date]
                if len(filtered_posts) < len(posts):
                    self.logger.debug(f"  Filtered {len(posts) - len(filtered_posts)} posts older than {days_limit} days")
                posts = filtered_posts

            all_discussions.extend(posts)

            # 获取每个 post 下的评论
            if fetch_comments and posts:
                self.logger.info(f"  Fetching comments from {len(posts)} posts in r/{subreddit_name}...")

                post_comments = []
                for post in posts:
                    comments = self.fetch_post_comments(
                        post_id=post.id,  # 使用 .id 而不是 .post_id
                        post_title=post.title,
                        subreddit_name=subreddit_name,
                        max_comments=max_comments_per_post,
                        search_keywords=query,  # 使用查询关键词作为标签
                        replace_more_limit=replace_more_limit
                    )

                    # 时间过滤 - Comments
                    if cutoff_date:
                        comments = [c for c in comments if c.created_at >= cutoff_date]

                    post_comments.extend(comments)

                if post_comments:
                    # 保存评论到数据库
                    self.add_discussions(post_comments, source='api')
                    all_discussions.extend(post_comments)
                    self.logger.info(f"  ✓ Fetched {len(post_comments)} comments from r/{subreddit_name}")

        posts_count = sum(1 for d in all_discussions if d.content_type == ContentType.POST)
        comments_count = sum(1 for d in all_discussions if d.content_type == ContentType.COMMENT)

        self.logger.info(f"✓ Fetched {posts_count} posts + {comments_count} comments from {len(REDDIT_SUBREDDITS)} subreddits")
        self.logger.info(f"  Total: {len(all_discussions)} discussions")

        return all_discussions
