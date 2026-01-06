"""Data models for DiscussionFetcher."""

from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Optional, Dict, Any
from enum import Enum


class Platform(str, Enum):
    """Supported platforms."""
    REDDIT = "reddit"
    HUGGINGFACE = "huggingface"
    ZHIHU = "zhihu"
    DISCORD = "discord"  # Reserved for future
    TWITTER = "twitter"  # Reserved for future
    WECHAT = "wechat"    # Reserved for future


class ContentType(str, Enum):
    """Content types."""
    POST = "post"
    COMMENT = "comment"
    DISCUSSION = "discussion"
    REPLY = "reply"


@dataclass
class Discussion:
    """
    Unified discussion/post/comment data model.

    This model provides a common structure for content from all platforms.
    Platform-specific data is stored in the metadata field.
    """
    # Core fields (common across all platforms)
    id: str
    platform: Platform
    content_type: ContentType
    author: str
    content: str
    created_at: datetime
    url: str

    # Optional common fields
    title: Optional[str] = None
    score: Optional[int] = None
    parent_id: Optional[str] = None

    # Platform-specific metadata
    metadata: Dict[str, Any] = field(default_factory=dict)

    # Fetcher metadata
    fetched_at: datetime = field(default_factory=datetime.now)
    search_keywords: Optional[str] = None  # 搜索关键词（逗号分隔，如 "ERNIE,PaddleOCR-VL"）

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary with serializable types."""
        data = asdict(self)
        # Convert enums to strings
        data['platform'] = self.platform.value
        data['content_type'] = self.content_type.value
        # Convert datetime to ISO format
        data['created_at'] = self.created_at.isoformat()
        data['fetched_at'] = self.fetched_at.isoformat()
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Discussion':
        """Create Discussion from dictionary."""
        data = data.copy()
        # Convert string to enum
        data['platform'] = Platform(data['platform'])
        data['content_type'] = ContentType(data['content_type'])
        # Convert ISO string to datetime
        if isinstance(data.get('created_at'), str):
            data['created_at'] = datetime.fromisoformat(data['created_at'])
        if isinstance(data.get('fetched_at'), str):
            data['fetched_at'] = datetime.fromisoformat(data['fetched_at'])
        return cls(**data)


@dataclass
class RedditPost(Discussion):
    """
    Reddit-specific post model.

    Extends Discussion with Reddit-specific convenience properties.
    """

    def __post_init__(self):
        """Ensure platform is set to Reddit."""
        self.platform = Platform.REDDIT
        if self.content_type not in (ContentType.POST, ContentType.COMMENT):
            self.content_type = ContentType.POST

    @property
    def subreddit(self) -> Optional[str]:
        """Get subreddit name from metadata."""
        return self.metadata.get('subreddit')

    @property
    def upvote_ratio(self) -> Optional[float]:
        """Get upvote ratio from metadata."""
        return self.metadata.get('upvote_ratio')

    @property
    def num_comments(self) -> Optional[int]:
        """Get number of comments from metadata."""
        return self.metadata.get('num_comments')

    @property
    def permalink(self) -> Optional[str]:
        """Get Reddit permalink from metadata."""
        return self.metadata.get('permalink')

    @property
    def is_self(self) -> bool:
        """Check if post is self-post (text only)."""
        return self.metadata.get('is_self', False)

    @property
    def link_flair_text(self) -> Optional[str]:
        """Get link flair text from metadata."""
        return self.metadata.get('link_flair_text')


@dataclass
class HuggingFaceDiscussion(Discussion):
    """
    HuggingFace-specific discussion model.

    Extends Discussion with HuggingFace-specific convenience properties.
    """

    def __post_init__(self):
        """Ensure platform is set to HuggingFace."""
        self.platform = Platform.HUGGINGFACE
        if self.content_type not in (ContentType.DISCUSSION, ContentType.COMMENT):
            self.content_type = ContentType.DISCUSSION

    @property
    def model_id(self) -> Optional[str]:
        """Get model ID from metadata."""
        return self.metadata.get('model_id')

    @property
    def discussion_num(self) -> Optional[int]:
        """Get discussion number from metadata."""
        return self.metadata.get('discussion_num')

    @property
    def status(self) -> Optional[str]:
        """Get discussion status from metadata."""
        return self.metadata.get('status')

    @property
    def event_type(self) -> Optional[str]:
        """Get event type from metadata."""
        return self.metadata.get('event_type')


def create_reddit_discussion(
    post_id: str,
    title: Optional[str],
    content: str,
    author: str,
    created_at: datetime,
    subreddit: str,
    url: str,
    permalink: str,
    score: int = 0,
    content_type: ContentType = ContentType.POST,
    upvote_ratio: Optional[float] = None,
    num_comments: Optional[int] = None,
    is_self: bool = True,
    link_flair_text: Optional[str] = None,
    parent_id: Optional[str] = None,
    search_keywords: Optional[str] = None,
    **kwargs
) -> RedditPost:
    """
    Factory function to create Reddit discussion.

    Args:
        post_id: Reddit post/comment ID
        title: Post title (None for comments)
        content: Post/comment content
        author: Author username
        created_at: Creation timestamp
        subreddit: Subreddit name
        url: Full URL to content
        permalink: Reddit permalink
        score: Upvote score
        content_type: Type of content (post or comment)
        upvote_ratio: Upvote ratio (posts only)
        num_comments: Number of comments (posts only)
        is_self: Whether post is text-only
        link_flair_text: Post flair text
        parent_id: Parent post ID (comments only)
        **kwargs: Additional metadata

    Returns:
        RedditPost instance
    """
    metadata = {
        'subreddit': subreddit,
        'permalink': permalink,
        'upvote_ratio': upvote_ratio,
        'num_comments': num_comments,
        'is_self': is_self,
        'link_flair_text': link_flair_text,
        **kwargs
    }

    return RedditPost(
        id=post_id,
        platform=Platform.REDDIT,
        content_type=content_type,
        title=title,
        author=author,
        content=content,
        created_at=created_at,
        url=url,
        score=score,
        parent_id=parent_id,
        metadata=metadata,
        search_keywords=search_keywords
    )


def create_huggingface_discussion(
    discussion_id: str,
    model_id: str,
    title: str,
    content: str,
    author: str,
    created_at: datetime,
    url: str,
    discussion_num: Optional[int] = None,
    status: Optional[str] = None,
    event_type: Optional[str] = None,
    content_type: ContentType = ContentType.DISCUSSION,
    search_keywords: Optional[str] = None,
    **kwargs
) -> HuggingFaceDiscussion:
    """
    Factory function to create HuggingFace discussion.

    Args:
        discussion_id: Discussion/event ID
        model_id: HuggingFace model ID
        title: Discussion title
        content: Discussion content
        author: Author username
        created_at: Creation timestamp
        url: Full URL to discussion
        discussion_num: Discussion number
        status: Discussion status (open/closed)
        event_type: Event type (comment/status-change/etc)
        content_type: Type of content
        **kwargs: Additional metadata

    Returns:
        HuggingFaceDiscussion instance
    """
    metadata = {
        'model_id': model_id,
        'discussion_num': discussion_num,
        'status': status,
        'event_type': event_type,
        **kwargs
    }

    return HuggingFaceDiscussion(
        id=discussion_id,
        platform=Platform.HUGGINGFACE,
        content_type=content_type,
        title=title,
        author=author,
        content=content,
        created_at=created_at,
        url=url,
        metadata=metadata,
        search_keywords=search_keywords
    )


@dataclass
class TwitterPost(Discussion):
    """
    Twitter-specific post model.

    Extends Discussion with Twitter-specific convenience properties.
    """

    def __post_init__(self):
        """Ensure platform is set to Twitter."""
        self.platform = Platform.TWITTER
        if self.content_type not in (ContentType.POST, ContentType.COMMENT):
            self.content_type = ContentType.POST

    @property
    def likes(self) -> Optional[int]:
        """Get number of likes from metadata."""
        return self.metadata.get('likes')

    @property
    def retweets(self) -> Optional[int]:
        """Get number of retweets from metadata."""
        return self.metadata.get('retweets')

    @property
    def replies(self) -> Optional[int]:
        """Get number of replies from metadata."""
        return self.metadata.get('replies')

    @property
    def views(self) -> Optional[int]:
        """Get number of views from metadata."""
        return self.metadata.get('views')

    @property
    def bookmarks(self) -> Optional[int]:
        """Get number of bookmarks from metadata."""
        return self.metadata.get('bookmarks')

    @property
    def user_display_name(self) -> Optional[str]:
        """Get user display name from metadata."""
        return self.metadata.get('user_display_name')

    @property
    def user_verified(self) -> bool:
        """Check if user is verified."""
        return self.metadata.get('user_verified', False)

    @property
    def user_followers(self) -> Optional[int]:
        """Get user follower count from metadata."""
        return self.metadata.get('user_followers')

    @property
    def language(self) -> Optional[str]:
        """Get tweet language from metadata."""
        return self.metadata.get('language')

    @property
    def tags(self) -> Optional[str]:
        """Get tweet tags/hashtags from metadata."""
        return self.metadata.get('tags')


def create_twitter_post(
    tweet_id: str,
    content: str,
    author: str,
    created_at: datetime,
    url: str,
    content_type: ContentType = ContentType.POST,
    likes: Optional[int] = None,
    retweets: Optional[int] = None,
    replies: Optional[int] = None,
    views: Optional[int] = None,
    bookmarks: Optional[int] = None,
    language: Optional[str] = None,
    tags: Optional[str] = None,
    user_display_name: Optional[str] = None,
    user_verified: bool = False,
    user_followers: Optional[int] = None,
    parent_id: Optional[str] = None,
    search_keywords: Optional[str] = None,
    **kwargs
) -> TwitterPost:
    """
    Factory function to create Twitter post/tweet.

    Args:
        tweet_id: Twitter tweet/post ID
        content: Tweet content
        author: Author username
        created_at: Creation timestamp
        url: Full URL to tweet
        content_type: Type of content (post or comment)
        likes: Number of likes
        retweets: Number of retweets
        replies: Number of replies
        views: Number of views
        bookmarks: Number of bookmarks
        language: Tweet language
        tags: Hashtags/tags
        user_display_name: User's display name
        user_verified: Whether user is verified
        user_followers: User's follower count
        parent_id: Parent tweet ID (for replies/comments)
        **kwargs: Additional metadata

    Returns:
        TwitterPost instance
    """
    metadata = {
        'likes': likes,
        'retweets': retweets,
        'replies': replies,
        'views': views,
        'bookmarks': bookmarks,
        'language': language,
        'tags': tags,
        'user_display_name': user_display_name,
        'user_verified': user_verified,
        'user_followers': user_followers,
        **kwargs
    }

    return TwitterPost(
        id=tweet_id,
        platform=Platform.TWITTER,
        content_type=content_type,
        title=None,  # Twitter doesn't have titles
        author=author,
        content=content,
        created_at=created_at,
        url=url,
        score=likes or 0,  # Use likes as score
        parent_id=parent_id,
        metadata=metadata,
        search_keywords=search_keywords
    )
