# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

---

## Project Overview

**DiscussionFetcher v2.0** is an automated discussion data collection system that fetches posts and comments from Reddit and HuggingFace about specific topics (default: ERNIE). It includes both CLI tools and a Web interface for data management and visualization.

### Core Capabilities
- **Reddit**: Fetches posts (PRAW API) and comments (Selenium) from 9 AI/ML subreddits
- **HuggingFace**: Fetches model discussions via HuggingFace Hub API
- **Twitter**: CSV import support (no active scraping)
- **Storage**: SQLite database with automatic deduplication
- **Web Interface**: Flask-based dashboard for visualization and management

---

## Essential Commands

### Development Setup
```bash
# Install dependencies
pip install -r requirements.txt

# Set up environment (optional but recommended)
cp .env.example .env
# Edit .env with Reddit/HuggingFace API credentials
```

### Primary Workflows

#### Full Data Fetch (CLI)
```bash
# Posts only (PRAW API - requires Reddit credentials)
python3 fetch_all.py

# Posts + Comments (requires cookies.json from EditThisCookie)
python3 fetch_all.py --reddit-comments

# Custom parameters
python3 fetch_all.py --reddit-comments --max-pages=10 --platforms reddit,huggingface
```

#### Web Interface
```bash
# Start web server
./start.sh
# or
python3 web_server.py

# Access at http://127.0.0.1:5000
```

#### Database Management
```bash
# View statistics
python3 db_manager.py stats

# Export data
python3 db_manager.py export --format excel --output data.xlsx
python3 db_manager.py export --format csv --platform reddit
```

### Testing Individual Components
```bash
# Test Reddit Posts fetcher
python3 -c "from src.reddit import RedditFetcher; r = RedditFetcher(verbose=True); r.fetch(query='ERNIE', limit=10)"

# Test HuggingFace fetcher
python3 -c "from src.huggingface import HuggingFaceFetcher; h = HuggingFaceFetcher(verbose=True); h.fetch('ERNIE')"

# Test Selenium (requires cookies.json)
python3 -c "from src.reddit_comments_selenium import RedditCommentsSeleniumFetcher; s = RedditCommentsSeleniumFetcher(headless=False, verbose=True); s.fetch(query='ERNIE', max_scrolls=3)"
```

---

## Architecture

### Data Flow

```
User → fetch_all.py → Platform Fetchers → BaseFetcher → DatabaseManager → SQLite
                      ↓
                   [Reddit/HF/Twitter]
                      ↓
                   Discussion Models
                      ↓
                   Auto-save to DB
```

### Core Abstraction: BaseFetcher

All platform fetchers inherit from `BaseFetcher` (src/base.py), which provides:
- **Rate limiting**: Configurable per platform
- **Auto-save**: Automatic database persistence after fetching
- **Data export**: CSV/Excel/JSON export methods
- **Logging**: Unified logging with configurable verbosity

**Key Pattern**: Each fetcher must implement:
1. `fetch()` - Main data collection method
2. `_authenticate()` - Platform-specific authentication

### Data Models (src/models.py)

The system uses a **unified Discussion model** with platform-specific extensions:

```python
Discussion (base)
├── RedditPost
├── HuggingFaceDiscussion
└── TwitterPost
```

**Critical Fields**:
- `id`: Platform-specific ID (e.g., Reddit post ID, HF discussion ID)
- `platform_id`: Unique composite ID (platform + id) for deduplication
- `content_type`: Enum (post, comment, discussion, reply)
- `metadata`: Dict for platform-specific fields

### Database Architecture (src/database.py)

**Multi-table design** with foreign key relationships:

```
discussions (main table)
├── db_id (PRIMARY KEY, autoincrement)
├── platform_id (UNIQUE, for deduplication)
├── content, url, created_at
└── search_keywords (comma-separated tags)

reddit_discussions (extends discussions)
├── subreddit, author, title
├── score, upvote_ratio, num_comments
└── permalink, parent_id

huggingface_discussions (extends discussions)
├── model_id, discussion_num
└── status, event_type

twitter_discussions (extends discussions)
├── likes, retweets, views
└── user_display_name, language
```

**Deduplication**: Uses `platform_id` (UNIQUE constraint) for UPSERT operations via `bulk_upsert()`.

### Platform-Specific Implementation Details

#### Reddit (src/reddit.py + src/reddit_comments_selenium.py)

**Two-tier approach**:
1. **PRAW API** (`reddit.py`): Posts only, unlimited history, requires API credentials
2. **Selenium** (`reddit_comments_selenium.py`): Comments only, last 30 days, requires cookies.json

**Key Configuration**:
- `REDDIT_SUBREDDITS` in `src/reddit.py:15-25` defines target subreddits
- Default: 9 AI/ML subreddits (LocalLLM, ChatGPT, ArtificialIntelligence, etc.)
- Selenium uses scrolling (default: 5 scrolls/subreddit ≈ 100-150 comments)

**Retry Logic**: Both fetchers include:
- Exponential backoff (2s → 4s → 8s for Selenium WebDriver init)
- Rate limit detection (30s wait on "whoa there, pardner")
- HTTP status code logging for debugging

#### HuggingFace (src/huggingface.py)

- Uses `huggingface_hub` Python library
- **Search flow**: `search_models()` → `fetch_discussions_for_model()` → `get_discussion_details()`
- **Author handling**: Fixed bug where `discussion.author` can be string or object (line 176-185)
- **Strict filtering**: Option to filter models by exact query match in model ID

#### Web API (web_server.py)

**New endpoints** (added in latest improvements):
- `GET /api/stats/timeline`: Time-series data (day/week/month grouping)
- `GET /api/stats/top_authors`: Most active authors ranking
- `POST /api/cleanup/duplicates`: Remove duplicate entries

**Fetch flow**: `/api/fetch/start` → background thread → `fetch_worker()` → updates `fetch_status` dict

---

## Critical Constraints

### Environment Requirements
- **Python 3.9+** required
- **Chrome/Chromium** required for Selenium (auto-downloads ChromeDriver)
- **cookies.json** required for Reddit comments (export via EditThisCookie browser extension)

### API Credentials (.env)
```bash
# Required for Reddit Posts
REDDIT_CLIENT_ID=your_client_id
REDDIT_CLIENT_SECRET=your_client_secret

# Required for HuggingFace
HUGGINGFACE_TOKEN=your_token
```

### Rate Limits
- Reddit API: 1 req/s (default, configurable in config.py)
- HuggingFace API: 2 req/s (default)
- Selenium: Built-in delays (2-3s between actions)

---

## Common Modification Points

### Adding New Subreddits
Edit `src/reddit.py` line 15-25:
```python
REDDIT_SUBREDDITS = [
    "LocalLLM",
    "YourNewSubreddit",  # Add here
    ...
]
```

### Changing Search Query
Default query is "ERNIE". To change globally:
- Edit `fetch_all.py` lines where `query='ERNIE'` appears (typically line 61 and 97)

### Adjusting Time Filters
- Reddit comments: `days_limit` parameter (default 30 days)
- Modify in `fetch_all.py` or when calling `fetch()` method

### Modifying Selenium Scroll Depth
- `--max-pages N` flag controls scrolls per subreddit
- Default: 5 scrolls ≈ 100-150 comments per subreddit
- Rule of thumb: N scrolls ≈ 20N comments per subreddit

---

## Important Implementation Notes

### Error Handling Pattern
All fetchers use try-except with specific exception types:
```python
except ResponseException as e:  # Reddit HTTP errors
except PrawcoreException as e:  # PRAW library errors
except HfHubHTTPError as e:     # HuggingFace errors
except Exception as e:          # Catch-all
```

Always log with context (HTTP status codes, retry attempts, etc.).

### Auto-save Behavior
By default, fetchers auto-save to database (`auto_save=True`). This means:
- Every `add_discussions()` call triggers database insert
- Database manager uses UPSERT (INSERT OR REPLACE) to prevent duplicates
- **Do not** manually call `save_to_database()` unless `auto_save=False`

### Selenium Headless Mode
- Default: `headless=True` (no browser window)
- For debugging: `headless=False` to see browser actions
- Useful for diagnosing CAPTCHA, login, or cookie issues

### Time Zone Handling
- Reddit PRAW: Returns naive datetimes (local timezone)
- HuggingFace: Returns aware datetimes (UTC)
- Selenium parsing: Attempts to parse both formats
- **Database stores ISO format strings** for consistency

---

## File Organization

```
Root Directory:
├── fetch_all.py         # Main CLI entry point
├── web_server.py        # Flask web server
├── db_manager.py        # Database CLI tool
├── start.sh             # Quick launcher
├── cookies.json         # Reddit cookies (user must create)
├── requirements.txt     # Python dependencies
└── .env                 # Environment configuration

src/                     # Core modules
├── base.py              # BaseFetcher abstract class
├── models.py            # Data models (Discussion, Platform, ContentType)
├── config.py            # Environment config loader
├── database.py          # SQLite database manager
├── logger.py            # Logging setup
├── utils.py             # RateLimiter, retry decorators
├── reddit.py            # Reddit Posts fetcher (PRAW)
├── reddit_comments_selenium.py  # Reddit Comments (Selenium)
├── huggingface.py       # HuggingFace fetcher
└── twitter_importer.py  # Twitter CSV import (no scraping)

docs/                    # Documentation
├── README.md            # Documentation index
├── USAGE.md             # Complete usage guide
├── QUICKSTART.md        # Quick start guide
├── SELENIUM_GUIDE.md    # Selenium + Cookies guide
└── ... (more docs)

scripts/                 # Utility scripts
├── analyze_relevance.py # Analysis tools
├── test_*.py            # Test scripts
└── migrate_*.py         # Migration utilities

examples/                # Example code
└── notebooks/           # Jupyter notebooks

web/                     # Web interface
├── templates/           # HTML templates
└── static/              # CSS/JS assets

data/                    # Data storage
├── discussions.db       # SQLite database (auto-created)
└── exports/             # Export files

logs/                    # Log files
└── fetcher.log          # Main log file
```

---

## Debugging Tips

### Enable Verbose Logging
```python
# All fetchers support verbose=True
reddit = RedditFetcher(verbose=True)
hf = HuggingFaceFetcher(verbose=True)
```

### Check Logs
- Main log: `logs/fetcher.log`
- Web log: `logs/web.log`
- Logs include timestamps, retry attempts, HTTP status codes

### Database Inspection
```bash
# Connect to SQLite
sqlite3 data/discussions.db

# Check stats
SELECT platform, COUNT(*) FROM discussions GROUP BY platform;

# Recent entries
SELECT * FROM discussions ORDER BY fetched_at DESC LIMIT 10;
```

### Common Issues

**HuggingFace returns 0 results**:
- Check `strict_filter=True` in `fetch()` - may filter out valid models
- Use `verbose=True` to see which models were filtered

**Selenium fails with CAPTCHA**:
- Regenerate cookies.json from a logged-in Reddit session
- Check cookies file format (should be JSON array from EditThisCookie)

**Reddit API 503/404 errors**:
- Logged with HTTP status codes (see recent improvements in reddit.py:160-169)
- Automatic retry (3 attempts) with exponential backoff
- May indicate subreddit is private, banned, or Reddit API is down

---

## Recent Improvements (2026-01-06)

See `docs/CHANGELOG_IMPROVEMENTS.md` for details:

1. **Fixed**: HuggingFace `discussion.author` type handling (string vs object)
2. **Enhanced**: Reddit API error logging (HTTP status codes, exception types)
3. **Enhanced**: Selenium retry mechanisms (3x WebDriver init, 2x page load, rate limit handling)
4. **Added**: Web API endpoints for timeline stats, top authors, duplicate cleanup

---

## Key Principles

1. **Idempotency**: All fetch operations are safe to re-run (UPSERT prevents duplicates)
2. **Graceful degradation**: Missing credentials only affect specific platforms
3. **Fail-fast validation**: Use `Config.validate_platform()` before fetching
4. **Separation of concerns**: Fetching (BaseFetcher) vs Storage (DatabaseManager) vs UI (web_server)
