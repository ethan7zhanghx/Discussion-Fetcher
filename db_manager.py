#!/usr/bin/env python3
"""
数据库管理工具

提供数据库的查询、导出、统计等功能
"""

import argparse
import sys
import os
from datetime import datetime

# 添加 src 到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from database import DatabaseManager


def show_stats(db: DatabaseManager, platform: str = None):
    """显示数据统计"""
    print("=" * 60)
    print("数据库统计")
    print("=" * 60)
    print()

    stats = db.get_stats(platform)

    if platform:
        # 单个平台
        info = stats.get(platform)
        if info:
            print(f"{platform.capitalize()}:")
            print(f"  记录数: {info['count']}")
            print(f"  最早: {info['earliest']}")
            print(f"  最新: {info['latest']}")
            print(f"  平均评分: {info['avg_score']:.2f}")
        else:
            print(f"⚠️  没有 {platform} 的数据")
    else:
        # 所有平台
        for plat, info in stats.items():
            if plat == 'total':
                continue
            print(f"{plat.capitalize()}:")
            print(f"  记录数: {info['count']}")
            print(f"  最早: {info['earliest']}")
            print(f"  最新: {info['latest']}")
            print(f"  平均评分: {info['avg_score']:.2f}")
            print()

        print("-" * 60)
        print(f"总计: {stats['total']} 条记录")

    print()
    print("=" * 60)


def export_data(db: DatabaseManager, args):
    """导出数据"""
    print("=" * 60)
    print("导出数据")
    print("=" * 60)
    print()

    if args.format == 'csv':
        # 导出 CSV
        output_file = args.output or f"./data/export_{args.platform or 'all'}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"

        db.export_to_csv(
            output_file,
            platform=args.platform,
            start_date=args.start_date,
            end_date=args.end_date,
            limit=args.limit
        )

    elif args.format == 'excel':
        # 导出 Excel
        output_file = args.output or f"./data/export_all_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"

        platforms = [args.platform] if args.platform else ['reddit', 'huggingface']
        db.export_to_excel(output_file, platforms)

    print()
    print("=" * 60)


def query_data(db: DatabaseManager, args):
    """查询数据"""
    print("=" * 60)
    print("查询数据")
    print("=" * 60)
    print()

    df = db.get_discussions(
        platform=args.platform,
        start_date=args.start_date,
        end_date=args.end_date,
        limit=args.limit or 10
    )

    if df.empty:
        print("⚠️  没有找到数据")
    else:
        print(f"找到 {len(df)} 条记录")
        print()
        print(df[['id', 'platform', 'author', 'score', 'created_at', 'title']].head(args.limit or 10))

    print()
    print("=" * 60)


def query_reddit(db: DatabaseManager, args):
    """查询 Reddit 数据"""
    print("=" * 60)
    print("查询 Reddit 数据")
    print("=" * 60)
    print()

    df = db.get_reddit_discussions(
        subreddit=args.subreddit,
        start_date=args.start_date,
        end_date=args.end_date,
        limit=args.limit or 10
    )

    if df.empty:
        print("⚠️  没有找到数据")
    else:
        print(f"找到 {len(df)} 条记录")
        print()
        print(df[['id', 'subreddit', 'author', 'score', 'created_at', 'title']].head(args.limit or 10))

    print()
    print("=" * 60)


def main():
    parser = argparse.ArgumentParser(description='数据库管理工具')
    subparsers = parser.add_subparsers(dest='command', help='命令')

    # stats 命令
    stats_parser = subparsers.add_parser('stats', help='显示统计信息')
    stats_parser.add_argument('--platform', choices=['reddit', 'huggingface'],
                              help='指定平台')

    # export 命令
    export_parser = subparsers.add_parser('export', help='导出数据')
    export_parser.add_argument('--format', choices=['csv', 'excel'],
                               default='csv', help='导出格式（默认: csv）')
    export_parser.add_argument('--platform', choices=['reddit', 'huggingface'],
                               help='指定平台')
    export_parser.add_argument('--output', help='输出文件路径')
    export_parser.add_argument('--start-date', help='开始日期 (YYYY-MM-DD)')
    export_parser.add_argument('--end-date', help='结束日期 (YYYY-MM-DD)')
    export_parser.add_argument('--limit', type=int, help='限制记录数')

    # query 命令
    query_parser = subparsers.add_parser('query', help='查询数据')
    query_parser.add_argument('--platform', choices=['reddit', 'huggingface'],
                              help='指定平台')
    query_parser.add_argument('--start-date', help='开始日期 (YYYY-MM-DD)')
    query_parser.add_argument('--end-date', help='结束日期 (YYYY-MM-DD)')
    query_parser.add_argument('--limit', type=int, default=10, help='限制记录数（默认: 10）')

    # reddit 命令
    reddit_parser = subparsers.add_parser('reddit', help='查询 Reddit 数据')
    reddit_parser.add_argument('--subreddit', help='板块名称')
    reddit_parser.add_argument('--start-date', help='开始日期 (YYYY-MM-DD)')
    reddit_parser.add_argument('--end-date', help='结束日期 (YYYY-MM-DD)')
    reddit_parser.add_argument('--limit', type=int, default=10, help='限制记录数（默认: 10）')

    # cleanup 命令
    cleanup_parser = subparsers.add_parser('cleanup', help='清理旧数据')
    cleanup_parser.add_argument('--days', type=int, default=30,
                                help='保留最近多少天的数据（默认: 30）')

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    # 初始化数据库
    db = DatabaseManager()

    # 执行命令
    if args.command == 'stats':
        show_stats(db, args.platform)
    elif args.command == 'export':
        export_data(db, args)
    elif args.command == 'query':
        query_data(db, args)
    elif args.command == 'reddit':
        query_reddit(db, args)
    elif args.command == 'cleanup':
        db.cleanup_old_data(args.days)


if __name__ == "__main__":
    main()
