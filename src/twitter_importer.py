#!/usr/bin/env python3
"""Twitter CSV 导入工具"""

import csv
import argparse
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional
from dateutil import parser as date_parser

from .models import create_twitter_post, ContentType
from .database import DatabaseManager


class TwitterCSVImporter:
    """Twitter CSV 导入器"""

    def __init__(self, db_path: str = "./data/discussions.db", verbose: bool = False, search_keywords: Optional[str] = None):
        """
        初始化导入器

        Args:
            db_path: 数据库路径
            verbose: 是否显示详细日志
            search_keywords: 搜索关键词标签（用于标记导入的数据）
        """
        self.db = DatabaseManager(db_path)
        self.verbose = verbose
        self.search_keywords = search_keywords

    def parse_csv_row(self, row: Dict[str, str]) -> Optional[Dict]:
        """
        解析 CSV 行数据为字典

        CSV 表头：
        序号,ID,链接,发布日期,类型,内容,标签,语言,喜欢数,书签数,转发数,回复数,浏览量,可能敏感,
        用户ID,用户名,用户昵称,用户头像链接,用户封面图片链接,用户媒体数,用户注册时间,
        用户个人简介,用户推文数,用户粉丝数,用户所在地,用户是否认证账号,
        回复推文 ID,回复推文用户名,回复推文用户 ID,回复推文链接

        Args:
            row: CSV 行数据（字典）

        Returns:
            解析后的数据字典，如果失败返回 None
        """
        try:
            # 必填字段检查
            tweet_id = row.get('ID', '').strip()
            content = row.get('内容', '').strip()
            url = row.get('链接', '').strip()
            author = row.get('用户名', '').strip()
            created_at_str = row.get('发布日期', '').strip()

            if not tweet_id or not content or not url:
                if self.verbose:
                    print(f"  ⚠️  跳过无效行: ID={tweet_id}, 内容长度={len(content)}")
                return None

            # 解析发布日期
            try:
                created_at = date_parser.parse(created_at_str)
            except Exception as e:
                if self.verbose:
                    print(f"  ⚠️  无法解析日期 '{created_at_str}': {e}")
                return None

            # 判断内容类型（是否为回复/评论）
            parent_id = row.get('回复推文 ID', '').strip()
            content_type = ContentType.COMMENT if parent_id else ContentType.POST

            # 解析数值字段（可选，带默认值）
            def safe_int(value: str, default: int = 0) -> int:
                try:
                    return int(value.strip()) if value.strip() else default
                except:
                    return default

            def safe_bool(value: str) -> bool:
                value = value.strip().lower()
                return value in ['true', '1', 'yes', '是', 'True']

            # 解析用户注册时间
            user_created_at = None
            user_created_str = row.get('用户注册时间', '').strip()
            if user_created_str:
                try:
                    user_created_at = date_parser.parse(user_created_str)
                except:
                    pass

            # 构建 TwitterPost 数据
            twitter_data = {
                'id': tweet_id,
                'platform': 'twitter',
                'content': content,
                'url': url,
                'created_at': created_at,
                'author': author,
                'content_type': content_type.value,
                'score': safe_int(row.get('喜欢数', '0')),  # 使用 likes 作为 score
                'parent_id': parent_id if parent_id else None,
                'search_keywords': self.search_keywords,  # 添加搜索关键词标签
                'metadata': {
                    'likes': safe_int(row.get('喜欢数', '0')),
                    'retweets': safe_int(row.get('转发数', '0')),
                    'replies': safe_int(row.get('回复数', '0')),
                    'views': safe_int(row.get('浏览量', '')) if row.get('浏览量', '').strip() else None,
                    'bookmarks': safe_int(row.get('书签数', '')) if row.get('书签数', '').strip() else None,
                    'language': row.get('语言', '').strip() or None,
                    'tags': row.get('标签', '').strip() or None,
                    'possibly_sensitive': safe_bool(row.get('可能敏感', '')),
                    'user_id': row.get('用户ID', '').strip() or None,
                    'user_display_name': row.get('用户昵称', '').strip() or None,
                    'user_avatar': row.get('用户头像链接', '').strip() or None,
                    'user_banner': row.get('用户封面图片链接', '').strip() or None,
                    'user_bio': row.get('用户个人简介', '').strip() or None,
                    'user_location': row.get('用户所在地', '').strip() or None,
                    'user_verified': safe_bool(row.get('用户是否认证账号', '')),
                    'user_followers': safe_int(row.get('用户粉丝数', '')) if row.get('用户粉丝数', '').strip() else None,
                    'user_tweet_count': safe_int(row.get('用户推文数', '')) if row.get('用户推文数', '').strip() else None,
                    'user_media_count': safe_int(row.get('用户媒体数', '')) if row.get('用户媒体数', '').strip() else None,
                    'user_created_at': user_created_at,
                    'reply_to_username': row.get('回复推文用户名', '').strip() or None,
                    'reply_to_user_id': row.get('回复推文用户 ID', '').strip() or None,
                    'reply_to_url': row.get('回复推文链接', '').strip() or None,
                }
            }

            return twitter_data

        except Exception as e:
            if self.verbose:
                print(f"  ❌ 解析行失败: {e}")
                print(f"  行数据: {row}")
            return None

    def import_csv(self, csv_file: str) -> int:
        """
        导入 CSV 文件

        Args:
            csv_file: CSV 文件路径

        Returns:
            成功导入的记录数
        """
        csv_path = Path(csv_file)
        if not csv_path.exists():
            raise FileNotFoundError(f"文件不存在: {csv_file}")

        print(f"开始导入: {csv_file}")
        print("=" * 60)

        success_count = 0
        total_count = 0
        post_count = 0
        comment_count = 0

        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)

            for row in reader:
                total_count += 1

                # 解析行数据
                data = self.parse_csv_row(row)
                if not data:
                    continue

                # 保存到数据库
                try:
                    if self.db.upsert_discussion(data, source='csv_import'):
                        success_count += 1

                        # 统计类型
                        if data['content_type'] == 'post':
                            post_count += 1
                        else:
                            comment_count += 1

                        if self.verbose and success_count % 100 == 0:
                            print(f"  已导入 {success_count} 条...")

                except Exception as e:
                    if self.verbose:
                        print(f"  ❌ 插入失败 (ID={data['id']}): {e}")
                    continue

        print("=" * 60)
        print(f"✓ 导入完成！")
        print(f"  总行数: {total_count}")
        print(f"  成功: {success_count} 条")
        print(f"    - Posts: {post_count}")
        print(f"    - Comments: {comment_count}")
        print(f"  失败/跳过: {total_count - success_count} 条")

        return success_count

    def import_multiple_files(self, file_paths: List[str]) -> int:
        """
        导入多个 CSV 文件

        Args:
            file_paths: CSV 文件路径列表

        Returns:
            总成功导入的记录数
        """
        total_success = 0

        for file_path in file_paths:
            print(f"\n处理文件: {file_path}")
            try:
                count = self.import_csv(file_path)
                total_success += count
            except Exception as e:
                print(f"❌ 导入失败: {e}")
                continue

        print(f"\n" + "=" * 60)
        print(f"✓ 全部完成！共导入 {total_success} 条记录")
        print("=" * 60)

        return total_success


def main():
    """命令行入口"""
    parser = argparse.ArgumentParser(description='导入 Twitter CSV 数据到数据库')
    parser.add_argument(
        'files',
        nargs='+',
        help='CSV 文件路径（可以指定多个文件）'
    )
    parser.add_argument(
        '--db',
        default='./data/discussions.db',
        help='数据库路径（默认: ./data/discussions.db）'
    )
    parser.add_argument(
        '--keywords',
        type=str,
        default=None,
        help='搜索关键词标签（用于标记导入的数据，例如 "ERNIE"）'
    )
    parser.add_argument(
        '-v', '--verbose',
        action='store_true',
        help='显示详细日志'
    )
    parser.add_argument(
        '--export',
        action='store_true',
        help='导入后自动导出为 Excel'
    )

    args = parser.parse_args()

    # 创建导入器
    importer = TwitterCSVImporter(
        db_path=args.db,
        verbose=args.verbose,
        search_keywords=args.keywords
    )

    # 导入文件
    total = importer.import_multiple_files(args.files)

    # 自动导出
    if args.export and total > 0:
        print(f"\n导出数据...")
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_file = f'./data/exports/discussions_with_twitter_{timestamp}.xlsx'
        importer.db.export_to_excel(output_file, platforms=['reddit', 'huggingface', 'twitter'])


if __name__ == '__main__':
    main()
