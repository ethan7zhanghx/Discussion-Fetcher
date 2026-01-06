"""HuggingFace discussion fetcher."""

from typing import List, Optional
from datetime import datetime
from huggingface_hub import HfApi, get_repo_discussions, get_discussion_details
from huggingface_hub.utils import HfHubHTTPError

from .base import BaseFetcher
from .models import Platform, ContentType, HuggingFaceDiscussion, create_huggingface_discussion
from .utils import retry_on_failure
from .config import Config


class HuggingFaceFetcher(BaseFetcher):
    """Fetcher for HuggingFace model discussions."""

    def __init__(
        self,
        token: Optional[str] = None,
        verbose: bool = False,
        rate_limit: Optional[float] = None,
        config: Optional[Config] = None,
        auto_save: bool = True
    ):
        """
        Initialize HuggingFace fetcher.

        Args:
            token: HuggingFace API token. If None, uses config/env.
            verbose: Enable verbose logging
            rate_limit: API rate limit (calls per second)
            config: Configuration instance
            auto_save: Automatically save to database after fetching (default: True)
        """
        # Initialize config first
        if config is None:
            config = Config()

        # Get token from parameter or config
        self.token = token or config.HUGGINGFACE_TOKEN

        if not self.token:
            raise ValueError(
                "HuggingFace token is required. "
                "Set HUGGINGFACE_TOKEN in .env or pass token parameter."
            )

        # Initialize base class
        super().__init__(
            platform=Platform.HUGGINGFACE,
            verbose=verbose,
            rate_limit=rate_limit,
            config=config,
            auto_save=auto_save
        )

        # Authenticate
        self._authenticate()

    def _authenticate(self) -> None:
        """Authenticate with HuggingFace API."""
        try:
            self.api = HfApi(token=self.token)
            # Test authentication by getting user info
            self.api.whoami()
            self.logger.info("Successfully authenticated with HuggingFace API")
        except Exception as e:
            self.logger.error(f"HuggingFace authentication failed: {e}")
            raise

    @retry_on_failure(max_attempts=3, exceptions=(HfHubHTTPError,))
    def search_models(self, query: str, limit: Optional[int] = None) -> List[str]:
        """
        Search for models by query.

        Args:
            query: Search query (e.g., "ERNIE-4.5")
            limit: Maximum number of model IDs to return

        Returns:
            List of model IDs matching the query
        """
        self.logger.info(f"Searching for models with query: {query}")

        try:
            self.rate_limiter.wait_if_needed()

            models = self.api.list_models(
                search=query,
                limit=limit
            )

            model_ids = [model.id for model in models]

            if self.verbose:
                self.logger.debug(f"Found {len(model_ids)} models: {model_ids}")

            return model_ids

        except HfHubHTTPError as e:
            self.logger.error(f"Failed to search models: {e}")
            raise
        except Exception as e:
            self.logger.error(f"Unexpected error searching models: {e}")
            return []

    @retry_on_failure(max_attempts=3, exceptions=(HfHubHTTPError,))
    def fetch_discussions_for_model(
        self,
        model_id: str,
        include_comments: bool = True,
        search_keywords: Optional[str] = None
    ) -> List[HuggingFaceDiscussion]:
        """
        Fetch all discussions for a specific model.

        Args:
            model_id: HuggingFace model ID
            include_comments: Whether to fetch discussion comments/events

        Returns:
            List of HuggingFaceDiscussion objects
        """
        discussions_list = []

        try:
            self.rate_limiter.wait_if_needed()

            # Get all discussions for the model
            discussions = get_repo_discussions(repo_id=model_id)

            if self.verbose:
                self.logger.debug(
                    f"Fetching discussions for model: {model_id}"
                )

            for discussion in discussions:
                try:
                    if include_comments:
                        # Fetch detailed discussion with all events/comments
                        self.rate_limiter.wait_if_needed()
                        detailed = get_discussion_details(
                            repo_id=model_id,
                            discussion_num=discussion.num
                        )

                        # Process each event in the discussion
                        for event in detailed.events:
                            # Only include events with actual content
                            if hasattr(event, 'content') and event.content:
                                # Handle author (can be object or string)
                                if hasattr(event.author, 'name'):
                                    author_name = event.author.name
                                elif isinstance(event.author, str):
                                    author_name = event.author
                                else:
                                    author_name = "Unknown"

                                event_discussion = create_huggingface_discussion(
                                    discussion_id=f"{model_id}_{discussion.num}_{event.id}",
                                    model_id=model_id,
                                    title=discussion.title,
                                    content=event.content,
                                    author=author_name,
                                    created_at=event.created_at,
                                    url=f"https://huggingface.co/{model_id}/discussions/{discussion.num}",
                                    discussion_num=discussion.num,
                                    status=discussion.status,
                                    event_type=event.type,
                                    content_type=ContentType.COMMENT,
                                    search_keywords=search_keywords
                                )
                                discussions_list.append(event_discussion)
                    else:
                        # Just create discussion without fetching details
                        # Handle author (can be object or string)
                        if discussion.author:
                            if hasattr(discussion.author, 'name'):
                                author_name = discussion.author.name
                            elif isinstance(discussion.author, str):
                                author_name = discussion.author
                            else:
                                author_name = "Unknown"
                        else:
                            author_name = "Unknown"

                        disc_obj = create_huggingface_discussion(
                            discussion_id=f"{model_id}_{discussion.num}",
                            model_id=model_id,
                            title=discussion.title,
                            content=discussion.title,  # Use title as content for summary
                            author=author_name,
                            created_at=discussion.created_at,
                            url=f"https://huggingface.co/{model_id}/discussions/{discussion.num}",
                            discussion_num=discussion.num,
                            status=discussion.status,
                            content_type=ContentType.DISCUSSION,
                            search_keywords=search_keywords
                        )
                        discussions_list.append(disc_obj)

                except Exception as e:
                    self.logger.warning(
                        f"Failed to fetch discussion {discussion.num} "
                        f"for model {model_id}: {e}"
                    )
                    continue

            # Add to discussions and auto-save if enabled
            if discussions_list:
                self.add_discussions(discussions_list, source='api')

            if self.verbose:
                self.logger.debug(
                    f"Fetched {len(discussions_list)} discussions/events "
                    f"from model {model_id}"
                )

        except HfHubHTTPError as e:
            self.logger.warning(f"Failed to fetch discussions for {model_id}: {e}")
        except Exception as e:
            self.logger.error(
                f"Unexpected error fetching discussions for {model_id}: {e}"
            )

        return discussions_list

    def fetch(
        self,
        query: str,
        model_limit: Optional[int] = None,
        include_comments: bool = True,
        auto_save: bool = False,
        strict_filter: bool = True,
        days_limit: Optional[int] = None
    ) -> List[HuggingFaceDiscussion]:
        """
        Fetch discussions for all models matching query.

        Args:
            query: Search query for models (e.g., "ERNIE-4.5")
            model_limit: Maximum number of models to fetch discussions from
            include_comments: Whether to fetch discussion comments/events
            auto_save: Automatically save results after fetching
            strict_filter: If True, only include models whose ID contains the exact query string (default: True)
            days_limit: 只获取最近 N 天的数据（None = 全部历史数据）

        Returns:
            List of all discussions from matching models
        """
        self.logger.info(
            f"Starting fetch for query: '{query}' "
            f"(model_limit={model_limit}, include_comments={include_comments}, strict_filter={strict_filter})"
        )
        if days_limit:
            self.logger.info(f"Time filter: last {days_limit} days")

        # 计算时间阈值
        from datetime import timedelta, timezone
        cutoff_date = None
        if days_limit:
            cutoff_date = datetime.now(timezone.utc) - timedelta(days=days_limit)

        all_discussions = []

        # Search for models
        model_ids = self.search_models(query, limit=model_limit)

        if not model_ids:
            self.logger.warning(f"No models found for query: {query}")
            return all_discussions

        # Apply strict filter if enabled
        if strict_filter:
            original_count = len(model_ids)
            # Filter: model_id must contain the query string (case-insensitive)
            model_ids = [
                model_id for model_id in model_ids
                if query.lower() in model_id.lower()
            ]

            if len(model_ids) < original_count:
                filtered_out = original_count - len(model_ids)
                self.logger.info(
                    f"Strict filter: removed {filtered_out} models not matching '{query}' exactly"
                )

        if not model_ids:
            self.logger.warning(f"No models found after strict filtering for query: {query}")
            return all_discussions

        self.logger.info(f"Found {len(model_ids)} models, fetching discussions...")

        # Fetch discussions for each model
        for idx, model_id in enumerate(model_ids, 1):
            if self.verbose:
                self.logger.info(
                    f"Processing model {idx}/{len(model_ids)}: {model_id}"
                )

            discussions = self.fetch_discussions_for_model(
                model_id=model_id,
                include_comments=include_comments,
                search_keywords=query  # 使用查询关键词作为标签
            )

            # 时间过滤
            if cutoff_date:
                original_count = len(discussions)
                discussions = [d for d in discussions if d.created_at >= cutoff_date]
                if len(discussions) < original_count:
                    self.logger.debug(f"  Filtered {original_count - len(discussions)} discussions older than {days_limit} days")

            all_discussions.extend(discussions)

        # Store discussions
        self.add_discussions(all_discussions)

        self.logger.info(
            f"Fetch complete: {len(all_discussions)} discussions "
            f"from {len(model_ids)} models"
        )

        # Auto-save if requested
        if auto_save and all_discussions:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{self.config.DATA_DIR}/huggingface_{query}_{timestamp}.csv"
            self.save_csv(filename)

        return all_discussions

    def fetch_model_discussions(
        self,
        model_id: str,
        include_comments: bool = True
    ) -> List[HuggingFaceDiscussion]:
        """
        Fetch discussions for a specific model (by exact model ID).

        Args:
            model_id: Exact HuggingFace model ID
            include_comments: Whether to fetch discussion comments/events

        Returns:
            List of discussions from the model
        """
        self.logger.info(f"Fetching discussions for model: {model_id}")

        discussions = self.fetch_discussions_for_model(
            model_id=model_id,
            include_comments=include_comments,
            search_keywords=model_id  # 使用 model_id 作为关键词
        )

        self.add_discussions(discussions)

        self.logger.info(
            f"Fetched {len(discussions)} discussions from {model_id}"
        )

        return discussions
