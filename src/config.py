"""Configuration management for DiscussionFetcher."""

import os
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv

# Load .env file at module import time
_project_root = Path(__file__).parent.parent
_env_path = _project_root / '.env'
if _env_path.exists():
    load_dotenv(_env_path)


class Config:
    """Central configuration management."""

    def __init__(self, env_file: Optional[str] = None):
        """
        Initialize configuration.

        Args:
            env_file: Path to .env file. If None, uses already loaded config.
        """
        if env_file:
            load_dotenv(env_file, override=True)

    # HuggingFace Configuration
    HUGGINGFACE_TOKEN = os.getenv('HUGGINGFACE_TOKEN')
    HF_API_TIMEOUT = int(os.getenv('HF_API_TIMEOUT', '30'))

    # Reddit Configuration
    REDDIT_CLIENT_ID = os.getenv('REDDIT_CLIENT_ID')
    REDDIT_CLIENT_SECRET = os.getenv('REDDIT_CLIENT_SECRET')
    REDDIT_USER_AGENT = os.getenv('REDDIT_USER_AGENT', 'DiscussionFetcher/1.0')
    REDDIT_API_TIMEOUT = int(os.getenv('REDDIT_API_TIMEOUT', '30'))

    # General Configuration
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
    LOG_FILE = os.getenv('LOG_FILE', 'logs/fetcher.log')
    DATA_DIR = os.getenv('DATA_DIR', './data')

    # Rate Limiting (requests per second)
    REDDIT_RATE_LIMIT = float(os.getenv('REDDIT_RATE_LIMIT', '1.0'))
    HF_RATE_LIMIT = float(os.getenv('HF_RATE_LIMIT', '2.0'))

    @classmethod
    def validate(cls) -> None:
        """
        Validate that all required configuration is present.

        Raises:
            ValueError: If required configuration is missing.
        """
        required = {
            'HUGGINGFACE_TOKEN': cls.HUGGINGFACE_TOKEN,
            'REDDIT_CLIENT_ID': cls.REDDIT_CLIENT_ID,
            'REDDIT_CLIENT_SECRET': cls.REDDIT_CLIENT_SECRET,
        }

        missing = [key for key, value in required.items() if not value]

        if missing:
            raise ValueError(
                f"Missing required configuration: {', '.join(missing)}. "
                f"Please check your .env file or environment variables."
            )

    @classmethod
    def validate_platform(cls, platform: str) -> None:
        """
        Validate configuration for a specific platform.

        Args:
            platform: Platform name ('huggingface' or 'reddit')

        Raises:
            ValueError: If platform configuration is missing.
        """
        if platform.lower() == 'huggingface':
            if not cls.HUGGINGFACE_TOKEN:
                raise ValueError(
                    "HUGGINGFACE_TOKEN is required. "
                    "Please set it in your .env file."
                )
        elif platform.lower() == 'reddit':
            if not cls.REDDIT_CLIENT_ID or not cls.REDDIT_CLIENT_SECRET:
                raise ValueError(
                    "REDDIT_CLIENT_ID and REDDIT_CLIENT_SECRET are required. "
                    "Please set them in your .env file."
                )
        else:
            raise ValueError(f"Unknown platform: {platform}")
