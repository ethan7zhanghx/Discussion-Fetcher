"""
DiscussionFetcher - A multi-platform discussion fetcher for ERNIE and other topics.
"""

__version__ = "1.0.0"
__author__ = "Your Name"

from .config import Config
from .models import Discussion, Platform, ContentType
from .base import BaseFetcher

__all__ = [
    "Config",
    "Discussion",
    "Platform",
    "ContentType",
    "BaseFetcher",
]
