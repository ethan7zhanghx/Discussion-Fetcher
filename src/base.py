"""Base fetcher class for all platform implementations."""

from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any
from pathlib import Path
import pandas as pd

from .models import Discussion, Platform
from .logger import setup_logger, get_logger
from .utils import RateLimiter
from .config import Config


class BaseFetcher(ABC):
    """
    Abstract base class for all platform fetchers.

    This class provides common functionality for all fetchers including:
    - Logging setup
    - Rate limiting
    - Data storage (CSV, Excel, JSON)
    - Configuration management
    """

    def __init__(
        self,
        platform: Platform,
        verbose: bool = False,
        rate_limit: Optional[float] = None,
        config: Optional[Config] = None,
        auto_save: bool = True
    ):
        """
        Initialize base fetcher.

        Args:
            platform: Platform identifier
            verbose: Enable verbose logging
            rate_limit: API rate limit (calls per second). If None, uses config default.
            config: Configuration instance. If None, creates new one.
            auto_save: Automatically save to database after fetching (default: True)
        """
        self.platform = platform
        self.verbose = verbose
        self.config = config or Config()
        self.auto_save = auto_save

        # Setup logging
        log_level = "DEBUG" if verbose else self.config.LOG_LEVEL
        self.logger = setup_logger(
            name=f"{self.__class__.__name__}",
            log_file=self.config.LOG_FILE,
            log_level=log_level
        )

        # Setup rate limiter
        if rate_limit is None:
            if platform == Platform.REDDIT:
                rate_limit = self.config.REDDIT_RATE_LIMIT
            elif platform == Platform.HUGGINGFACE:
                rate_limit = self.config.HF_RATE_LIMIT
            else:
                rate_limit = 1.0

        self.rate_limiter = RateLimiter(calls_per_second=rate_limit)

        # Storage for fetched discussions
        self.discussions: List[Discussion] = []

        # Database manager (lazy initialization)
        self._db = None

        self.logger.info(
            f"Initialized {self.__class__.__name__} "
            f"(rate_limit={rate_limit} req/s, verbose={verbose}, auto_save={auto_save})"
        )

    @abstractmethod
    def fetch(self, query: str, **kwargs) -> List[Discussion]:
        """
        Fetch discussions based on query.

        This method must be implemented by subclasses.

        Args:
            query: Search query or identifier
            **kwargs: Platform-specific parameters

        Returns:
            List of Discussion objects
        """
        pass

    @abstractmethod
    def _authenticate(self) -> None:
        """
        Authenticate with the platform API.

        This method must be implemented by subclasses.
        """
        pass

    def clear(self) -> None:
        """Clear stored discussions."""
        self.discussions.clear()
        self.logger.debug("Cleared stored discussions")

    @property
    def db(self):
        """Lazy initialization of database manager"""
        if self._db is None:
            from .database import DatabaseManager
            self._db = DatabaseManager()
        return self._db

    def add_discussions(self, discussions: List[Discussion], source: str = 'api') -> None:
        """
        Add discussions to storage and optionally save to database.

        Args:
            discussions: List of Discussion objects to add
            source: Data source identifier (api, web, html, manual)
        """
        self.discussions.extend(discussions)
        self.logger.debug(f"Added {len(discussions)} discussions to storage")

        # Auto-save to database if enabled
        if self.auto_save and discussions:
            saved_count = self.save_to_database(discussions, source=source)
            if saved_count > 0:
                self.logger.info(f"✓ Auto-saved {saved_count} discussions to database")

    def save_to_database(self, discussions: Optional[List[Discussion]] = None, source: str = 'api') -> int:
        """
        Save discussions to database.

        Args:
            discussions: List of discussions to save. If None, uses self.discussions.
            source: Data source identifier (api, web, html, manual)

        Returns:
            Number of successfully saved discussions
        """
        if discussions is None:
            discussions = self.discussions

        if not discussions:
            self.logger.warning("No discussions to save to database")
            return 0

        # Convert to dict format
        data_list = [d.to_dict() for d in discussions]

        # Bulk upsert
        try:
            saved_count = self.db.bulk_upsert(data_list, source=source)
            self.logger.info(f"Saved {saved_count}/{len(discussions)} discussions to database")
            return saved_count
        except Exception as e:
            self.logger.error(f"Failed to save to database: {e}")
            return 0

    def to_dataframe(self, discussions: Optional[List[Discussion]] = None) -> pd.DataFrame:
        """
        Convert discussions to pandas DataFrame.

        Args:
            discussions: List of discussions to convert. If None, uses self.discussions.

        Returns:
            DataFrame containing discussion data
        """
        if discussions is None:
            discussions = self.discussions

        if not discussions:
            self.logger.warning("No discussions to convert to DataFrame")
            return pd.DataFrame()

        data = [d.to_dict() for d in discussions]
        df = pd.DataFrame(data)

        self.logger.debug(f"Converted {len(discussions)} discussions to DataFrame")
        return df

    def save_csv(
        self,
        filepath: str,
        discussions: Optional[List[Discussion]] = None,
        **kwargs
    ) -> None:
        """
        Save discussions to CSV file.

        Args:
            filepath: Path to output CSV file
            discussions: List of discussions to save. If None, uses self.discussions.
            **kwargs: Additional arguments passed to pandas.DataFrame.to_csv()
        """
        df = self.to_dataframe(discussions)

        if df.empty:
            self.logger.warning(f"No data to save to {filepath}")
            return

        # Ensure directory exists
        Path(filepath).parent.mkdir(parents=True, exist_ok=True)

        # Default encoding for better compatibility
        kwargs.setdefault('encoding', 'utf-8-sig')
        kwargs.setdefault('index', False)

        df.to_csv(filepath, **kwargs)
        self.logger.info(f"Saved {len(df)} discussions to {filepath}")

    def save_excel(
        self,
        filepath: str,
        discussions: Optional[List[Discussion]] = None,
        **kwargs
    ) -> None:
        """
        Save discussions to Excel file.

        Args:
            filepath: Path to output Excel file
            discussions: List of discussions to save. If None, uses self.discussions.
            **kwargs: Additional arguments passed to pandas.DataFrame.to_excel()
        """
        df = self.to_dataframe(discussions)

        if df.empty:
            self.logger.warning(f"No data to save to {filepath}")
            return

        # Ensure directory exists
        Path(filepath).parent.mkdir(parents=True, exist_ok=True)

        # Clean illegal characters for Excel
        # Excel doesn't support certain control characters and invalid Unicode
        import re

        def clean_for_excel(text):
            """Remove illegal characters for Excel"""
            if not isinstance(text, str):
                return text

            # Remove control characters (except tab, newline, carriage return)
            # and invalid Unicode characters (replacement character �)
            text = re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F-\x9F\uFFFD]', '', text)

            return text

        # Apply cleaning to all string columns
        for col in df.columns:
            if df[col].dtype == 'object':  # String columns
                df[col] = df[col].apply(clean_for_excel)

        kwargs.setdefault('index', False)
        kwargs.setdefault('engine', 'openpyxl')

        try:
            df.to_excel(filepath, **kwargs)
            self.logger.info(f"Saved {len(df)} discussions to {filepath}")
        except Exception as e:
            self.logger.error(f"Failed to save Excel file: {e}")
            # Try to save as CSV as fallback
            csv_filepath = filepath.replace('.xlsx', '.csv').replace('.xls', '.csv')
            self.logger.info(f"Attempting to save as CSV instead: {csv_filepath}")
            self.save_csv(csv_filepath, discussions)
            raise

    def save_json(
        self,
        filepath: str,
        discussions: Optional[List[Discussion]] = None,
        **kwargs
    ) -> None:
        """
        Save discussions to JSON file.

        Args:
            filepath: Path to output JSON file
            discussions: List of discussions to save. If None, uses self.discussions.
            **kwargs: Additional arguments passed to pandas.DataFrame.to_json()
        """
        df = self.to_dataframe(discussions)

        if df.empty:
            self.logger.warning(f"No data to save to {filepath}")
            return

        # Ensure directory exists
        Path(filepath).parent.mkdir(parents=True, exist_ok=True)

        kwargs.setdefault('orient', 'records')
        kwargs.setdefault('indent', 2)
        kwargs.setdefault('force_ascii', False)

        df.to_json(filepath, **kwargs)
        self.logger.info(f"Saved {len(df)} discussions to {filepath}")

    def filter_discussions(
        self,
        keyword: Optional[str] = None,
        author: Optional[str] = None,
        min_score: Optional[int] = None,
        **kwargs
    ) -> List[Discussion]:
        """
        Filter stored discussions by criteria.

        Args:
            keyword: Filter by keyword in title or content (case-insensitive)
            author: Filter by author username
            min_score: Minimum score threshold
            **kwargs: Additional platform-specific filters

        Returns:
            Filtered list of discussions
        """
        filtered = self.discussions

        if keyword:
            keyword_lower = keyword.lower()
            filtered = [
                d for d in filtered
                if (d.title and keyword_lower in d.title.lower())
                or (d.content and keyword_lower in d.content.lower())
            ]

        if author:
            filtered = [d for d in filtered if d.author == author]

        if min_score is not None:
            filtered = [
                d for d in filtered
                if d.score is not None and d.score >= min_score
            ]

        self.logger.debug(
            f"Filtered {len(self.discussions)} discussions to {len(filtered)} "
            f"(keyword={keyword}, author={author}, min_score={min_score})"
        )

        return filtered

    def get_stats(self) -> Dict[str, Any]:
        """
        Get statistics about fetched discussions.

        Returns:
            Dictionary containing statistics
        """
        if not self.discussions:
            return {"total": 0}

        stats = {
            "total": len(self.discussions),
            "platform": self.platform.value,
            "content_types": {},
            "authors": len(set(d.author for d in self.discussions)),
            "has_score": sum(1 for d in self.discussions if d.score is not None),
        }

        # Count by content type
        for discussion in self.discussions:
            content_type = discussion.content_type.value
            stats["content_types"][content_type] = \
                stats["content_types"].get(content_type, 0) + 1

        # Score statistics
        scores = [d.score for d in self.discussions if d.score is not None]
        if scores:
            stats["score_stats"] = {
                "min": min(scores),
                "max": max(scores),
                "avg": sum(scores) / len(scores),
            }

        return stats

    def __len__(self) -> int:
        """Return number of stored discussions."""
        return len(self.discussions)

    def __repr__(self) -> str:
        """String representation of fetcher."""
        return (
            f"{self.__class__.__name__}("
            f"platform={self.platform.value}, "
            f"discussions={len(self.discussions)})"
        )
