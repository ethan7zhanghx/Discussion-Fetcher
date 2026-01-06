#!/usr/bin/env python3
"""给现有的 Twitter 数据添加 search_keywords 标签"""

import argparse
from src.database import DatabaseManager


def update_twitter_keywords(keyword: str, dry_run: bool = False):
    """
    给所有 Twitter 数据添加 search_keywords 标签

    Args:
        keyword: 要添加的关键词（例如 "ERNIE"）
        dry_run: 如果为 True，只显示会更新多少条，不实际更新
    """
    db = DatabaseManager()
    conn = db.get_connection()
    cursor = conn.cursor()

    # 检查有多少条 Twitter 数据没有标记
    cursor.execute("""
        SELECT COUNT(*) as count
        FROM discussions
        WHERE platform = 'twitter' AND search_keywords IS NULL
    """)

    count = cursor.fetchone()['count']

    print("=" * 60)
    print(f"找到 {count} 条未标记的 Twitter 数据")
    print("=" * 60)

    if count == 0:
        print("✓ 所有 Twitter 数据都已标记！")
        return 0

    if dry_run:
        print(f"\n[DRY RUN] 将会把这 {count} 条数据标记为: {keyword}")
        print("提示：去掉 --dry-run 参数来实际执行更新")
        return count

    # 实际更新
    cursor.execute("""
        UPDATE discussions
        SET search_keywords = ?
        WHERE platform = 'twitter' AND search_keywords IS NULL
    """, (keyword,))

    conn.commit()
    updated = cursor.rowcount

    print(f"\n✓ 成功更新 {updated} 条 Twitter 数据")
    print(f"  标记为: {keyword}")
    print("=" * 60)

    return updated


def main():
    parser = argparse.ArgumentParser(
        description='给现有的 Twitter 数据添加 search_keywords 标签',
        epilog='示例: python3 update_twitter_keywords.py --keyword "ERNIE"'
    )
    parser.add_argument(
        '--keyword',
        type=str,
        required=True,
        help='要添加的搜索关键词（例如 "ERNIE"）'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='只显示会更新多少条，不实际更新'
    )

    args = parser.parse_args()

    update_twitter_keywords(args.keyword, dry_run=args.dry_run)


if __name__ == '__main__':
    main()
