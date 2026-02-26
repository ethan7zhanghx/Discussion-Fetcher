"""
数据库管理模块 - 重构版

新架构：
- discussions: 总表（核心字段：内容、链接、时间）
- reddit_discussions: Reddit 特有字段
- huggingface_discussions: HuggingFace 特有字段

使用 db_id (自增) 作为主键，platform_id (唯一) 用于去重
"""

import sqlite3
import pandas as pd
from datetime import datetime
from typing import List, Dict, Optional, Any
from pathlib import Path


class DatabaseManager:
    """数据库管理器"""

    def __init__(self, db_path: str = "./data/discussions.db"):
        """
        初始化数据库管理器

        Args:
            db_path: 数据库文件路径
        """
        self.db_path = db_path

        # 确保目录存在
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)

        # 初始化数据库
        self.init_database()

    def get_connection(self):
        """获取数据库连接"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row  # 返回字典格式
        return conn

    def init_database(self):
        """初始化数据库表结构"""
        conn = self.get_connection()
        cursor = conn.cursor()

        # ==================== 总表 ====================
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS discussions (
                -- 主键（数据库自增ID）
                db_id INTEGER PRIMARY KEY AUTOINCREMENT,

                -- 平台标识
                platform_id TEXT UNIQUE NOT NULL,
                platform TEXT NOT NULL,

                -- 核心内容
                content TEXT NOT NULL,
                url TEXT NOT NULL,
                created_at TIMESTAMP NOT NULL,

                -- 抓取信息
                fetched_at TIMESTAMP NOT NULL,
                source TEXT,  -- 数据来源：api, html, manual
                search_keywords TEXT,  -- 搜索关键词（逗号分隔）
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # 创建索引
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_platform ON discussions(platform)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_platform_id ON discussions(platform_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_created_at ON discussions(created_at)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_fetched_at ON discussions(fetched_at)')

        # 迁移：添加 search_keywords 字段（如果不存在）
        try:
            cursor.execute("ALTER TABLE discussions ADD COLUMN search_keywords TEXT")
        except sqlite3.OperationalError:
            # 字段已存在，跳过
            pass

        cursor.execute('CREATE INDEX IF NOT EXISTS idx_search_keywords ON discussions(search_keywords)')

        # ==================== Reddit 表 ====================
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS reddit_discussions (
                db_id INTEGER PRIMARY KEY,

                -- 基本信息
                subreddit TEXT NOT NULL,
                author TEXT,
                title TEXT,
                content_type TEXT,  -- "post" 或 "comment"

                -- 互动数据
                score INTEGER DEFAULT 0,
                upvote_ratio REAL,
                num_comments INTEGER,

                -- 链接
                permalink TEXT,
                parent_id TEXT,

                -- 帖子特性
                is_self BOOLEAN,
                link_flair_text TEXT,

                FOREIGN KEY (db_id) REFERENCES discussions(db_id) ON DELETE CASCADE
            )
        ''')

        cursor.execute('CREATE INDEX IF NOT EXISTS idx_reddit_subreddit ON reddit_discussions(subreddit)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_reddit_author ON reddit_discussions(author)')

        # ==================== HuggingFace 表 ====================
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS huggingface_discussions (
                db_id INTEGER PRIMARY KEY,

                -- 基本信息
                model_id TEXT NOT NULL,
                author TEXT,
                title TEXT NOT NULL,
                content_type TEXT,  -- "discussion" 或 "comment"

                -- Discussion 信息
                discussion_num INTEGER,
                status TEXT,        -- "open", "closed"
                event_type TEXT,    -- "comment", "status-change" 等

                FOREIGN KEY (db_id) REFERENCES discussions(db_id) ON DELETE CASCADE
            )
        ''')

        cursor.execute('CREATE INDEX IF NOT EXISTS idx_hf_model ON huggingface_discussions(model_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_hf_author ON huggingface_discussions(author)')

        # ==================== Twitter 表 ====================
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS twitter_discussions (
                db_id INTEGER PRIMARY KEY,

                -- 基本信息
                author TEXT,
                content_type TEXT,  -- "post" 或 "comment"

                -- 互动数据
                likes INTEGER DEFAULT 0,
                retweets INTEGER DEFAULT 0,
                replies INTEGER DEFAULT 0,
                views INTEGER,
                bookmarks INTEGER,

                -- 推文属性
                language TEXT,
                tags TEXT,
                possibly_sensitive BOOLEAN,

                -- 用户信息
                user_id TEXT,
                user_display_name TEXT,
                user_avatar TEXT,
                user_banner TEXT,
                user_bio TEXT,
                user_location TEXT,
                user_verified BOOLEAN DEFAULT 0,
                user_followers INTEGER,
                user_tweet_count INTEGER,
                user_media_count INTEGER,
                user_created_at TIMESTAMP,

                -- 回复信息
                parent_id TEXT,
                reply_to_username TEXT,
                reply_to_user_id TEXT,
                reply_to_url TEXT,

                FOREIGN KEY (db_id) REFERENCES discussions(db_id) ON DELETE CASCADE
            )
        ''')

        cursor.execute('CREATE INDEX IF NOT EXISTS idx_twitter_author ON twitter_discussions(author)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_twitter_user_id ON twitter_discussions(user_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_twitter_parent ON twitter_discussions(parent_id)')

        conn.commit()
        conn.close()

    def upsert_discussion(self, data: Dict[str, Any], source: str = 'api') -> bool:
        """
        插入或更新讨论数据（自动去重）

        Args:
            data: 讨论数据字典，必须包含：
                - id: 平台原始ID
                - platform: 平台名称
                - content: 内容
                - url: 链接
                - created_at: 创建时间
            source: 数据来源（api, html, manual）

        Returns:
            是否插入/更新成功
        """
        conn = self.get_connection()
        cursor = conn.cursor()

        try:
            platform_id = data['id']
            platform = data['platform']

            # 检查是否已存在
            cursor.execute('SELECT db_id, fetched_at FROM discussions WHERE platform_id = ?', (platform_id,))
            existing = cursor.fetchone()

            # 处理时间
            created_at = data.get('created_at')
            if isinstance(created_at, str):
                created_at = datetime.fromisoformat(created_at.replace('Z', '+00:00'))

            # 使用传入的 fetched_at，如果没有则使用当前时间
            fetched_at = data.get('fetched_at')
            if fetched_at is None:
                fetched_at = datetime.now()
            elif isinstance(fetched_at, str):
                fetched_at = datetime.fromisoformat(fetched_at.replace('Z', '+00:00'))

            if existing:
                # 已存在，检查是否需要更新
                db_id = existing['db_id']
                old_fetched_at = datetime.fromisoformat(existing['fetched_at'])

                # 只有新数据更新时才更新
                if fetched_at > old_fetched_at:
                    # 更新总表
                    cursor.execute('''
                        UPDATE discussions SET
                            content = ?,
                            url = ?,
                            created_at = ?,
                            fetched_at = ?,
                            source = ?,
                            search_keywords = ?,
                            updated_at = CURRENT_TIMESTAMP
                        WHERE db_id = ?
                    ''', (
                        data.get('content', ''),
                        data.get('url', ''),
                        created_at,
                        fetched_at,
                        source,
                        data.get('search_keywords'),
                        db_id
                    ))

                    # 更新平台表
                    if platform == 'reddit':
                        self._upsert_reddit(cursor, db_id, data)
                    elif platform == 'huggingface':
                        self._upsert_huggingface(cursor, db_id, data)
                    elif platform == 'twitter':
                        self._upsert_twitter(cursor, db_id, data)

                    conn.commit()
                    conn.close()
                    return True
                else:
                    # 旧数据，不更新
                    conn.close()
                    return False
            else:
                # 插入新数据到总表
                cursor.execute('''
                    INSERT INTO discussions (
                        platform_id, platform, content, url, created_at,
                        fetched_at, source, search_keywords
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    platform_id,
                    platform,
                    data.get('content', ''),
                    data.get('url', ''),
                    created_at,
                    fetched_at,
                    source,
                    data.get('search_keywords')
                ))

                db_id = cursor.lastrowid

                # 插入平台特定数据
                if platform == 'reddit':
                    self._insert_reddit(cursor, db_id, data)
                elif platform == 'huggingface':
                    self._insert_huggingface(cursor, db_id, data)
                elif platform == 'twitter':
                    self._insert_twitter(cursor, db_id, data)

                conn.commit()
                conn.close()
                return True

        except Exception as e:
            conn.rollback()
            conn.close()
            raise e

    def _insert_reddit(self, cursor, db_id: int, data: Dict):
        """插入 Reddit 数据"""
        metadata = data.get('metadata', {})

        cursor.execute('''
            INSERT INTO reddit_discussions (
                db_id, subreddit, author, title, content_type,
                score, upvote_ratio, num_comments,
                permalink, parent_id, is_self, link_flair_text
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            db_id,
            metadata.get('subreddit', ''),
            data.get('author', ''),
            data.get('title', ''),
            data.get('content_type', 'post'),
            data.get('score', 0),
            metadata.get('upvote_ratio'),
            metadata.get('num_comments'),
            metadata.get('permalink', ''),
            data.get('parent_id'),
            metadata.get('is_self', False),
            metadata.get('link_flair_text')
        ))

    def _upsert_reddit(self, cursor, db_id: int, data: Dict):
        """更新 Reddit 数据"""
        metadata = data.get('metadata', {})

        cursor.execute('''
            INSERT OR REPLACE INTO reddit_discussions (
                db_id, subreddit, author, title, content_type,
                score, upvote_ratio, num_comments,
                permalink, parent_id, is_self, link_flair_text
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            db_id,
            metadata.get('subreddit', ''),
            data.get('author', ''),
            data.get('title', ''),
            data.get('content_type', 'post'),
            data.get('score', 0),
            metadata.get('upvote_ratio'),
            metadata.get('num_comments'),
            metadata.get('permalink', ''),
            data.get('parent_id'),
            metadata.get('is_self', False),
            metadata.get('link_flair_text')
        ))

    def _insert_huggingface(self, cursor, db_id: int, data: Dict):
        """插入 HuggingFace 数据"""
        metadata = data.get('metadata', {})

        cursor.execute('''
            INSERT INTO huggingface_discussions (
                db_id, model_id, author, title, content_type,
                discussion_num, status, event_type
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            db_id,
            metadata.get('model_id', ''),
            data.get('author', ''),
            data.get('title', ''),
            data.get('content_type', 'discussion'),
            metadata.get('discussion_num'),
            metadata.get('status'),
            metadata.get('event_type')
        ))

    def _upsert_huggingface(self, cursor, db_id: int, data: Dict):
        """更新 HuggingFace 数据"""
        metadata = data.get('metadata', {})

        cursor.execute('''
            INSERT OR REPLACE INTO huggingface_discussions (
                db_id, model_id, author, title, content_type,
                discussion_num, status, event_type
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            db_id,
            metadata.get('model_id', ''),
            data.get('author', ''),
            data.get('title', ''),
            data.get('content_type', 'discussion'),
            metadata.get('discussion_num'),
            metadata.get('status'),
            metadata.get('event_type')
        ))

    def _insert_twitter(self, cursor, db_id: int, data: Dict):
        """插入 Twitter 数据"""
        metadata = data.get('metadata', {})

        # 处理用户创建时间
        user_created_at = metadata.get('user_created_at')
        if isinstance(user_created_at, str):
            try:
                from dateutil import parser
                user_created_at = parser.parse(user_created_at)
            except:
                user_created_at = None

        cursor.execute('''
            INSERT INTO twitter_discussions (
                db_id, author, content_type,
                likes, retweets, replies, views, bookmarks,
                language, tags, possibly_sensitive,
                user_id, user_display_name, user_avatar, user_banner,
                user_bio, user_location, user_verified,
                user_followers, user_tweet_count, user_media_count, user_created_at,
                parent_id, reply_to_username, reply_to_user_id, reply_to_url
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            db_id,
            data.get('author', ''),
            data.get('content_type', 'post'),
            metadata.get('likes', 0),
            metadata.get('retweets', 0),
            metadata.get('replies', 0),
            metadata.get('views'),
            metadata.get('bookmarks'),
            metadata.get('language'),
            metadata.get('tags'),
            metadata.get('possibly_sensitive', False),
            metadata.get('user_id'),
            metadata.get('user_display_name'),
            metadata.get('user_avatar'),
            metadata.get('user_banner'),
            metadata.get('user_bio'),
            metadata.get('user_location'),
            metadata.get('user_verified', False),
            metadata.get('user_followers'),
            metadata.get('user_tweet_count'),
            metadata.get('user_media_count'),
            user_created_at,
            data.get('parent_id'),
            metadata.get('reply_to_username'),
            metadata.get('reply_to_user_id'),
            metadata.get('reply_to_url')
        ))

    def _upsert_twitter(self, cursor, db_id: int, data: Dict):
        """更新 Twitter 数据"""
        metadata = data.get('metadata', {})

        # 处理用户创建时间
        user_created_at = metadata.get('user_created_at')
        if isinstance(user_created_at, str):
            try:
                from dateutil import parser
                user_created_at = parser.parse(user_created_at)
            except:
                user_created_at = None

        cursor.execute('''
            INSERT OR REPLACE INTO twitter_discussions (
                db_id, author, content_type,
                likes, retweets, replies, views, bookmarks,
                language, tags, possibly_sensitive,
                user_id, user_display_name, user_avatar, user_banner,
                user_bio, user_location, user_verified,
                user_followers, user_tweet_count, user_media_count, user_created_at,
                parent_id, reply_to_username, reply_to_user_id, reply_to_url
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            db_id,
            data.get('author', ''),
            data.get('content_type', 'post'),
            metadata.get('likes', 0),
            metadata.get('retweets', 0),
            metadata.get('replies', 0),
            metadata.get('views'),
            metadata.get('bookmarks'),
            metadata.get('language'),
            metadata.get('tags'),
            metadata.get('possibly_sensitive', False),
            metadata.get('user_id'),
            metadata.get('user_display_name'),
            metadata.get('user_avatar'),
            metadata.get('user_banner'),
            metadata.get('user_bio'),
            metadata.get('user_location'),
            metadata.get('user_verified', False),
            metadata.get('user_followers'),
            metadata.get('user_tweet_count'),
            metadata.get('user_media_count'),
            user_created_at,
            data.get('parent_id'),
            metadata.get('reply_to_username'),
            metadata.get('reply_to_user_id'),
            metadata.get('reply_to_url')
        ))

    def bulk_upsert(self, data_list: List[Dict], source: str = 'api') -> int:
        """
        批量插入/更新数据

        Args:
            data_list: 数据列表
            source: 数据来源

        Returns:
            成功插入/更新的记录数
        """
        success_count = 0
        for data in data_list:
            if self.upsert_discussion(data, source):
                success_count += 1
        return success_count

    def get_discussions(
        self,
        platform: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        limit: Optional[int] = None,
        offset: int = 0
    ) -> pd.DataFrame:
        """
        查询所有讨论（联合查询，包含平台字段）

        Args:
            platform: 平台名称（reddit, huggingface）
            start_date: 开始日期（YYYY-MM-DD）
            end_date: 结束日期（YYYY-MM-DD）
            limit: 返回记录数限制
            offset: 偏移量

        Returns:
            DataFrame
        """
        conn = self.get_connection()

        # 联合查询
        query = '''
            SELECT
                d.db_id,
                d.platform_id,
                d.platform,
                d.content,
                d.url,
                d.created_at,
                d.fetched_at,
                d.source,
                d.search_keywords,
                COALESCE(r.author, h.author, t.author) as author,
                COALESCE(r.title, h.title) as title,
                COALESCE(r.content_type, h.content_type, t.content_type) as content_type,
                r.subreddit,
                r.score,
                r.upvote_ratio,
                r.num_comments,
                r.permalink,
                r.parent_id,
                r.is_self,
                r.link_flair_text,
                h.model_id,
                h.discussion_num,
                h.status,
                h.event_type,
                t.likes,
                t.retweets,
                t.replies,
                t.views,
                t.user_display_name,
                t.user_verified,
                t.language
            FROM discussions d
            LEFT JOIN reddit_discussions r ON d.db_id = r.db_id
            LEFT JOIN huggingface_discussions h ON d.db_id = h.db_id
            LEFT JOIN twitter_discussions t ON d.db_id = t.db_id
            WHERE 1=1
        '''
        params = []

        if platform:
            query += ' AND d.platform = ?'
            params.append(platform)

        if start_date:
            query += ' AND DATE(d.created_at) >= ?'
            params.append(start_date)

        if end_date:
            query += ' AND DATE(d.created_at) <= ?'
            params.append(end_date)

        query += ' ORDER BY d.created_at DESC'

        if limit:
            query += ' LIMIT ? OFFSET ?'
            params.extend([limit, offset])

        df = pd.read_sql_query(query, conn, params=params)
        conn.close()

        return df

    def get_reddit_discussions(
        self,
        subreddit: Optional[str] = None,
        **kwargs
    ) -> pd.DataFrame:
        """
        查询 Reddit 讨论

        Args:
            subreddit: 板块名称
            **kwargs: 其他查询参数（传递给 get_discussions）

        Returns:
            DataFrame（只包含 Reddit 数据）
        """
        df = self.get_discussions(platform='reddit', **kwargs)

        if not df.empty and subreddit:
            df = df[df['subreddit'] == subreddit]

        return df

    def get_huggingface_discussions(
        self,
        model_id: Optional[str] = None,
        **kwargs
    ) -> pd.DataFrame:
        """
        查询 HuggingFace 讨论

        Args:
            model_id: 模型ID
            **kwargs: 其他查询参数

        Returns:
            DataFrame（只包含 HuggingFace 数据）
        """
        df = self.get_discussions(platform='huggingface', **kwargs)

        if not df.empty and model_id:
            df = df[df['model_id'] == model_id]

        return df

    def get_stats(self, platform: Optional[str] = None) -> Dict:
        """
        获取数据统计

        Args:
            platform: 平台名称

        Returns:
            统计信息字典
        """
        conn = self.get_connection()
        cursor = conn.cursor()

        stats = {}

        if platform:
            # 单个平台统计
            if platform == 'reddit':
                cursor.execute('''
                    SELECT COUNT(*) as count,
                           MIN(d.created_at) as earliest,
                           MAX(d.created_at) as latest,
                           AVG(r.score) as avg_score
                    FROM discussions d
                    JOIN reddit_discussions r ON d.db_id = r.db_id
                    WHERE d.platform = ?
                ''', (platform,))
            elif platform == 'huggingface':
                cursor.execute('''
                    SELECT COUNT(*) as count,
                           MIN(d.created_at) as earliest,
                           MAX(d.created_at) as latest,
                           NULL as avg_score
                    FROM discussions d
                    JOIN huggingface_discussions h ON d.db_id = h.db_id
                    WHERE d.platform = ?
                ''', (platform,))
            else:
                cursor.execute('''
                    SELECT COUNT(*) as count,
                           MIN(created_at) as earliest,
                           MAX(created_at) as latest,
                           NULL as avg_score
                    FROM discussions
                    WHERE platform = ?
                ''', (platform,))

            row = cursor.fetchone()
            stats[platform] = {
                'count': row['count'],
                'earliest': row['earliest'],
                'latest': row['latest'],
                'avg_score': row['avg_score']
            }
        else:
            # 所有平台统计
            cursor.execute('''
                SELECT platform,
                       COUNT(*) as count,
                       MIN(created_at) as earliest,
                       MAX(created_at) as latest
                FROM discussions
                GROUP BY platform
            ''')

            for row in cursor.fetchall():
                platform_name = row['platform']
                stats[platform_name] = {
                    'count': row['count'],
                    'earliest': row['earliest'],
                    'latest': row['latest'],
                    'avg_score': None
                }

                # 获取平均分（只有 Reddit 有）
                if platform_name == 'reddit':
                    cursor.execute('''
                        SELECT AVG(score) as avg_score
                        FROM reddit_discussions
                    ''')
                    avg_row = cursor.fetchone()
                    stats[platform_name]['avg_score'] = avg_row['avg_score']

        # 总计
        cursor.execute('SELECT COUNT(*) as total FROM discussions')
        stats['total'] = cursor.fetchone()['total']

        conn.close()
        return stats

    def export_to_csv(
        self,
        output_file: str,
        platform: Optional[str] = None,
        search_keywords: Optional[str] = None,
        deduplicate: bool = True,
        **kwargs
    ):
        """
        导出数据到 CSV

        Args:
            output_file: 输出文件路径
            platform: 平台名称
            search_keywords: 按关键词筛选（例如 "ERNIE", "PaddleOCR-VL"）
            deduplicate: 是否去重（默认: True）
            **kwargs: 查询参数
        """
        conn = self.get_connection()

        # 构建查询（需要支持 search_keywords 筛选）
        query = '''
            SELECT
                d.db_id, d.platform_id, d.platform, d.content, d.url, d.created_at,
                d.fetched_at, d.source, d.search_keywords,
                COALESCE(r.author, h.author, t.author) as author,
                COALESCE(r.title, h.title) as title,
                COALESCE(r.content_type, h.content_type, t.content_type) as content_type,
                r.subreddit, r.score, r.upvote_ratio, r.num_comments, r.permalink, r.parent_id,
                r.is_self, r.link_flair_text,
                h.model_id, h.discussion_num, h.status, h.event_type,
                t.likes, t.retweets, t.replies, t.views, t.user_display_name, t.user_verified, t.language
            FROM discussions d
            LEFT JOIN reddit_discussions r ON d.db_id = r.db_id
            LEFT JOIN huggingface_discussions h ON d.db_id = h.db_id
            LEFT JOIN twitter_discussions t ON d.db_id = t.db_id
            WHERE 1=1
        '''
        params = []

        if platform:
            query += ' AND d.platform = ?'
            params.append(platform)

        if search_keywords:
            query += ' AND d.search_keywords = ?'
            params.append(search_keywords)

        query += ' ORDER BY d.created_at DESC'

        df = pd.read_sql_query(query, conn, params=params)
        conn.close()

        if df.empty:
            print(f"⚠️  没有数据可导出")
            return

        # 去重
        if deduplicate:
            original_len = len(df)
            df = self._deduplicate_dataframe(df)
            if len(df) < original_len:
                print(f"  去重: {original_len} → {len(df)} 条")

        # 确保目录存在
        Path(output_file).parent.mkdir(parents=True, exist_ok=True)

        df.to_csv(output_file, index=False, encoding='utf-8-sig')
        print(f"✓ 已导出 {len(df)} 条记录到: {output_file}")

    def _sanitize_for_excel(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        清理 DataFrame 中不兼容 Excel 的字符

        Args:
            df: 原始 DataFrame

        Returns:
            清理后的 DataFrame
        """
        import re

        # Excel 不支持的非法字符（控制字符，除了 tab、newline、carriage return）
        # 允许: \t (tab, 0x09), \n (newline, 0x0A), \r (carriage return, 0x0D)
        # 移除: 其他所有 0x00-0x1F 和 0x7F-0x9F 范围的控制字符
        illegal_chars = re.compile(r'[\x00-\x08\x0B-\x0C\x0E-\x1F\x7F-\x9F]')

        df_copy = df.copy()

        # 对所有字符串列进行清理
        for col in df_copy.columns:
            if df_copy[col].dtype == 'object':  # 字符串列
                df_copy[col] = df_copy[col].apply(
                    lambda x: illegal_chars.sub('', str(x)) if pd.notna(x) else x
                )

        return df_copy

    def _deduplicate_dataframe(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        智能去重：保留每个唯一内容的最新记录

        去重策略：
        - 按 (platform, platform_id) 分组
        - 保留 fetched_at 最新的记录
        - 这样可以去掉重复抓取的数据，保留最新版本

        Args:
            df: 原始 DataFrame

        Returns:
            去重后的 DataFrame
        """
        if df.empty:
            return df

        # 按 (platform, platform_id) 分组，保留 fetched_at 最新的
        df_sorted = df.sort_values('fetched_at', ascending=False)
        df_dedup = df_sorted.drop_duplicates(subset=['platform', 'platform_id'], keep='first')

        # 按 created_at 重新排序（保持时间顺序）
        df_dedup = df_dedup.sort_values('created_at', ascending=False)

        return df_dedup

    def export_to_excel(
        self,
        output_file: str,
        platforms: Optional[List[str]] = None,
        search_keywords: Optional[str] = None,
        deduplicate: bool = True
    ):
        """
        导出数据到 Excel（每个平台一个 sheet）

        Args:
            output_file: 输出文件路径
            platforms: 平台列表
            search_keywords: 按关键词筛选（例如 "ERNIE", "PaddleOCR-VL"）
            deduplicate: 是否去重（默认: True）
        """
        if not platforms:
            platforms = ['reddit', 'huggingface', 'twitter']

        # 确保目录存在
        Path(output_file).parent.mkdir(parents=True, exist_ok=True)

        with pd.ExcelWriter(output_file, engine='openpyxl') as writer:
            for platform in platforms:
                # 使用自定义查询支持 search_keywords 筛选
                conn = self.get_connection()
                query = '''
                    SELECT
                        d.db_id, d.platform_id, d.platform, d.content, d.url, d.created_at,
                        d.fetched_at, d.source, d.search_keywords,
                        COALESCE(r.author, h.author, t.author) as author,
                        COALESCE(r.title, h.title) as title,
                        COALESCE(r.content_type, h.content_type, t.content_type) as content_type,
                        r.subreddit, r.score, r.upvote_ratio, r.num_comments, r.permalink, r.parent_id,
                        r.is_self, r.link_flair_text,
                        h.model_id, h.discussion_num, h.status, h.event_type,
                        t.likes, t.retweets, t.replies, t.views, t.user_display_name, t.user_verified, t.language
                    FROM discussions d
                    LEFT JOIN reddit_discussions r ON d.db_id = r.db_id
                    LEFT JOIN huggingface_discussions h ON d.db_id = h.db_id
                    LEFT JOIN twitter_discussions t ON d.db_id = t.db_id
                    WHERE d.platform = ?
                '''
                params = [platform]

                if search_keywords:
                    query += ' AND d.search_keywords = ?'
                    params.append(search_keywords)

                query += ' ORDER BY d.created_at DESC'

                df = pd.read_sql_query(query, conn, params=params)
                conn.close()
                if not df.empty:
                    # 去重
                    if deduplicate:
                        original_len = len(df)
                        df = self._deduplicate_dataframe(df)
                        if len(df) < original_len:
                            print(f"  {platform}: 去重 {original_len} → {len(df)} 条")

                    # 根据平台选择相关列
                    if platform == 'reddit':
                        cols = ['db_id', 'platform_id', 'search_keywords', 'content', 'url', 'created_at',
                                'author', 'title', 'content_type', 'subreddit', 'score',
                                'upvote_ratio', 'num_comments', 'permalink', 'parent_id', 'fetched_at']
                    elif platform == 'huggingface':
                        cols = ['db_id', 'platform_id', 'search_keywords', 'content', 'url', 'created_at',
                                'author', 'title', 'content_type', 'model_id',
                                'discussion_num', 'status', 'event_type', 'fetched_at']
                    elif platform == 'twitter':
                        cols = ['db_id', 'platform_id', 'search_keywords', 'content', 'url', 'created_at',
                                'author', 'user_display_name', 'content_type',
                                'likes', 'retweets', 'replies', 'views',
                                'user_verified', 'language', 'parent_id', 'fetched_at']
                    else:
                        cols = df.columns.tolist()

                    # 只选择存在的列
                    cols = [c for c in cols if c in df.columns]

                    # 清理不兼容字符
                    df_clean = self._sanitize_for_excel(df[cols])
                    df_clean.to_excel(writer, sheet_name=platform, index=False)
                    print(f"✓ {platform}: {len(df)} 条记录")

            # 添加汇总 sheet
            conn = self.get_connection()
            query_all = '''
                SELECT
                    d.db_id, d.platform_id, d.platform, d.content, d.url, d.created_at,
                    d.fetched_at, d.source, d.search_keywords,
                    COALESCE(r.author, h.author, t.author) as author,
                    COALESCE(r.title, h.title) as title,
                    COALESCE(r.content_type, h.content_type, t.content_type) as content_type
                FROM discussions d
                LEFT JOIN reddit_discussions r ON d.db_id = r.db_id
                LEFT JOIN huggingface_discussions h ON d.db_id = h.db_id
                LEFT JOIN twitter_discussions t ON d.db_id = t.db_id
                WHERE 1=1
            '''
            params_all = []

            if search_keywords:
                query_all += ' AND d.search_keywords = ?'
                params_all.append(search_keywords)

            query_all += ' ORDER BY d.created_at DESC'

            df_all = pd.read_sql_query(query_all, conn, params=params_all)
            conn.close()

            if not df_all.empty:
                # 去重
                if deduplicate:
                    original_len = len(df_all)
                    df_all = self._deduplicate_dataframe(df_all)
                    if len(df_all) < original_len:
                        print(f"  all: 去重 {original_len} → {len(df_all)} 条")

                # 汇总表只显示通用字段
                summary_cols = ['db_id', 'platform_id', 'platform', 'search_keywords', 'content', 'url',
                                'created_at', 'author', 'title', 'content_type', 'fetched_at']
                summary_cols = [c for c in summary_cols if c in df_all.columns]

                # 清理不兼容字符
                df_clean = self._sanitize_for_excel(df_all[summary_cols])
                df_clean.to_excel(writer, sheet_name='all', index=False)
                print(f"✓ all: {len(df_all)} 条记录")

        print(f"✓ 已导出到: {output_file}")

    def migrate_from_old_database(self, old_db_path: str):
        """
        从旧数据库迁移数据

        Args:
            old_db_path: 旧数据库路径
        """
        print(f"开始从旧数据库迁移: {old_db_path}")

        old_conn = sqlite3.connect(old_db_path)
        old_conn.row_factory = sqlite3.Row
        old_cursor = old_conn.cursor()

        # 查询旧数据
        old_cursor.execute('SELECT * FROM discussions')
        old_rows = old_cursor.fetchall()

        print(f"找到 {len(old_rows)} 条旧数据")

        success = 0
        for row in old_rows:
            try:
                # 转换为字典
                row_dict = dict(row)

                # 转换为新格式
                data = {
                    'id': row_dict['id'],
                    'platform': row_dict['platform'],
                    'content': row_dict.get('content', ''),
                    'url': row_dict.get('url', ''),
                    'created_at': row_dict.get('created_at'),
                    'author': row_dict.get('author', ''),
                    'title': row_dict.get('title'),
                    'content_type': row_dict.get('content_type', 'post'),
                    'score': row_dict.get('score', 0),
                    'parent_id': row_dict.get('parent_id'),
                    'metadata': {},
                    'fetched_at': row_dict.get('fetched_at')  # 保留原始 fetched_at
                }

                # 解析 metadata
                if row_dict.get('metadata'):
                    import json
                    data['metadata'] = json.loads(row_dict['metadata'])

                # 插入新数据库
                source = row_dict.get('source', 'api')
                if self.upsert_discussion(data, source=source):
                    success += 1

                if success % 100 == 0:
                    print(f"  已迁移 {success} 条...")

            except Exception as e:
                print(f"  ⚠️  迁移失败 {dict(row).get('id', 'unknown')}: {e}")
                continue

        old_conn.close()
        print(f"✓ 迁移完成！成功: {success}/{len(old_rows)}")

    def query_discussions(
        self,
        platform: Optional[str] = None,
        content_type: Optional[str] = None,
        search_keywords: Optional[str] = None,
        limit: Optional[int] = 100,
        offset: int = 0
    ) -> List[Dict]:
        """
        查询讨论（返回字典列表，用于 Web API）

        Args:
            platform: 平台筛选
            content_type: 内容类型筛选
            limit: 返回记录数
            offset: 偏移量

        Returns:
            字典列表
        """
        conn = self.get_connection()
        cursor = conn.cursor()

        query = '''
            SELECT
                d.db_id,
                d.platform_id as id,
                d.platform,
                d.content,
                d.url,
                d.created_at,
                d.fetched_at,
                d.source,
                d.search_keywords,
                COALESCE(r.author, h.author, t.author) as author,
                COALESCE(r.title, h.title) as title,
                COALESCE(r.content_type, h.content_type, t.content_type) as content_type,
                r.score,
                r.subreddit,
                r.permalink,
                t.likes,
                t.retweets
            FROM discussions d
            LEFT JOIN reddit_discussions r ON d.db_id = r.db_id
            LEFT JOIN huggingface_discussions h ON d.db_id = h.db_id
            LEFT JOIN twitter_discussions t ON d.db_id = t.db_id
            WHERE 1=1
        '''
        params = []

        if platform:
            query += ' AND d.platform = ?'
            params.append(platform)

        if content_type:
            query += ' AND (r.content_type = ? OR h.content_type = ? OR t.content_type = ?)'
            params.extend([content_type, content_type, content_type])

        if search_keywords:
            query += ' AND d.search_keywords = ?'
            params.append(search_keywords)

        query += ' ORDER BY d.created_at DESC LIMIT ? OFFSET ?'
        params.extend([limit, offset])

        cursor.execute(query, params)
        rows = cursor.fetchall()

        result = [dict(row) for row in rows]
        conn.close()

        return result

    def query_posts_with_comments_stats(
        self,
        platform: Optional[str] = None,
        search_keywords: Optional[str] = None,
        limit: Optional[int] = 100,
        offset: int = 0
    ) -> List[Dict]:
        """
        查询帖子及其评论统计信息（用于前端展示，只显示帖子）

        Args:
            platform: 平台筛选
            search_keywords: 搜索关键词筛选
            limit: 返回记录数
            offset: 偏移量

        Returns:
            字典列表，每条记录包含：
            - 帖子信息（所有字段）
            - comment_count: 该帖子的评论总数
            - latest_comment_at: 最新评论时间
            - has_new_comments: 是否有新评论（基于 latest_comment_at 和 created_at 判断）
        """
        conn = self.get_connection()
        cursor = conn.cursor()

        # 主查询：获取帖子信息
        main_query = '''
            SELECT
                d.db_id,
                d.platform_id as id,
                d.platform,
                d.content,
                d.url,
                d.created_at,
                d.fetched_at,
                d.source,
                d.search_keywords,
                COALESCE(r.author, h.author, t.author) as author,
                COALESCE(r.title, h.title) as title,
                COALESCE(r.content_type, h.content_type, t.content_type) as content_type,
                r.score,
                r.subreddit,
                r.permalink,
                t.likes,
                t.retweets
            FROM discussions d
            LEFT JOIN reddit_discussions r ON d.db_id = r.db_id
            LEFT JOIN huggingface_discussions h ON d.db_id = h.db_id
            LEFT JOIN twitter_discussions t ON d.db_id = t.db_id
            WHERE (r.content_type = 'post' OR h.content_type = 'discussion' OR t.content_type = 'post')
        '''
        params = []

        if platform:
            main_query += ' AND d.platform = ?'
            params.append(platform)

        if search_keywords:
            main_query += ' AND d.search_keywords = ?'
            params.append(search_keywords)

        # 按最新评论时间排序（活跃度排序）
        # 使用子查询获取每个帖子的最新评论时间
        main_query += '''
            ORDER BY COALESCE(
                (SELECT MAX(d2.created_at)
                 FROM discussions d2
                 LEFT JOIN reddit_discussions r2 ON d2.db_id = r2.db_id
                 LEFT JOIN huggingface_discussions h2 ON d2.db_id = h2.db_id
                 WHERE (r2.parent_id = d.platform_id OR h2.parent_id = d.platform_id)
                ),
                d.created_at
            ) DESC
            LIMIT ? OFFSET ?
        '''
        params.extend([limit, offset])

        cursor.execute(main_query, params)
        rows = cursor.fetchall()

        result = []

        # 为每个帖子查询评论统计
        for row in rows:
            post_dict = dict(row)
            post_id = post_dict['id']
            post_platform = post_dict['platform']

            # 查询该帖子的评论
            if post_platform == 'reddit':
                comment_query = '''
                    SELECT
                        COUNT(*) as comment_count,
                        MAX(d2.created_at) as latest_comment_at
                    FROM discussions d2
                    LEFT JOIN reddit_discussions r2 ON d2.db_id = r2.db_id
                    WHERE r2.parent_id = ?
                '''
            elif post_platform == 'huggingface':
                comment_query = '''
                    SELECT
                        COUNT(*) as comment_count,
                        MAX(d2.created_at) as latest_comment_at
                    FROM discussions d2
                    LEFT JOIN huggingface_discussions h2 ON d2.db_id = h2.db_id
                    WHERE h2.parent_id = ?
                '''
            else:  # twitter
                comment_query = '''
                    SELECT
                        COUNT(*) as comment_count,
                        MAX(d2.created_at) as latest_comment_at
                    FROM discussions d2
                    LEFT JOIN twitter_discussions t2 ON d2.db_id = t2.db_id
                    WHERE t2.parent_id = ?
                '''

            cursor.execute(comment_query, (post_id,))
            comment_stats = cursor.fetchone()

            if comment_stats:
                comment_count = comment_stats['comment_count']
                latest_comment_at = comment_stats['latest_comment_at']

                post_dict['comment_count'] = comment_count
                post_dict['latest_comment_at'] = latest_comment_at

                # 判断是否有新评论（最新评论时间晚于帖子创建时间）
                if latest_comment_at:
                    post_created_at = datetime.fromisoformat(post_dict['created_at'].replace('Z', '+00:00'))
                    latest_comment_dt = datetime.fromisoformat(latest_comment_at.replace('Z', '+00:00'))
                    post_dict['has_new_comments'] = latest_comment_dt > post_created_at
                else:
                    post_dict['has_new_comments'] = False
            else:
                post_dict['comment_count'] = 0
                post_dict['latest_comment_at'] = None
                post_dict['has_new_comments'] = False

            result.append(post_dict)

        conn.close()
        return result

    def search_discussions(
        self,
        keyword: str,
        platform: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict]:
        """
        搜索讨论

        搜索范围:
        - 讨论内容 (content)
        - 标题 (title)
        - 搜索关键词标签 (search_keywords)
        - HuggingFace 模型 ID (model_id)
        - Reddit 子版块 (subreddit)

        Args:
            keyword: 搜索关键词
            platform: 平台筛选
            limit: 返回记录数

        Returns:
            字典列表
        """
        conn = self.get_connection()
        cursor = conn.cursor()

        query = '''
            SELECT
                d.db_id,
                d.platform_id as id,
                d.platform,
                d.content,
                d.url,
                d.created_at,
                d.fetched_at,
                d.source,
                d.search_keywords,
                COALESCE(r.author, h.author) as author,
                COALESCE(r.title, h.title) as title,
                COALESCE(r.content_type, h.content_type) as content_type,
                r.score,
                r.subreddit,
                h.model_id
            FROM discussions d
            LEFT JOIN reddit_discussions r ON d.db_id = r.db_id
            LEFT JOIN huggingface_discussions h ON d.db_id = h.db_id
            WHERE (
                d.content LIKE ? OR
                r.title LIKE ? OR
                h.title LIKE ? OR
                d.search_keywords LIKE ? OR
                h.model_id LIKE ? OR
                r.subreddit LIKE ?
            )
        '''
        params = [f'%{keyword}%', f'%{keyword}%', f'%{keyword}%',
                  f'%{keyword}%', f'%{keyword}%', f'%{keyword}%']

        if platform:
            query += ' AND d.platform = ?'
            params.append(platform)

        query += ' ORDER BY d.created_at DESC LIMIT ?'
        params.append(limit)

        cursor.execute(query, params)
        rows = cursor.fetchall()

        result = [dict(row) for row in rows]
        conn.close()

        return result

    def get_recent_discussions(self, limit: int = 10) -> List[Dict]:
        """
        获取最近的讨论

        Args:
            limit: 返回记录数

        Returns:
            字典列表
        """
        return self.query_discussions(limit=limit, offset=0)

    def get_stats_detailed(self) -> Dict:
        """
        获取详细统计（用于 Web API）

        Returns:
            详细统计信息
        """
        conn = self.get_connection()
        cursor = conn.cursor()

        stats = {}

        # 总数
        cursor.execute('SELECT COUNT(*) as total FROM discussions')
        stats['total'] = cursor.fetchone()['total']

        # 按平台统计
        cursor.execute('''
            SELECT platform, COUNT(*) as count
            FROM discussions
            GROUP BY platform
        ''')
        platforms = {}
        for row in cursor.fetchall():
            platforms[row['platform']] = row['count']
        stats['platforms'] = platforms

        # 按内容类型统计
        cursor.execute('''
            SELECT content_type, COUNT(*) as count
            FROM reddit_discussions
            WHERE content_type IS NOT NULL
            GROUP BY content_type
        ''')
        content_types = {}
        for row in cursor.fetchall():
            content_types[row['content_type']] = row['count']

        cursor.execute('''
            SELECT content_type, COUNT(*) as count
            FROM huggingface_discussions
            WHERE content_type IS NOT NULL
            GROUP BY content_type
        ''')
        for row in cursor.fetchall():
            ct = row['content_type']
            content_types[ct] = content_types.get(ct, 0) + row['count']
        stats['content_types'] = content_types

        conn.close()
        return stats

    def get_search_keywords(self) -> List[str]:
        """
        获取所有不同的搜索关键词列表

        Returns:
            关键词列表（去重且排除 NULL）
        """
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute('''
            SELECT DISTINCT search_keywords
            FROM discussions
            WHERE search_keywords IS NOT NULL
            ORDER BY search_keywords
        ''')

        keywords = [row['search_keywords'] for row in cursor.fetchall()]
        conn.close()

        return keywords
