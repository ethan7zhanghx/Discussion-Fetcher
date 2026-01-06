#!/usr/bin/env python3
"""一次性拉取所有平台数据"""

import argparse
import os
from pathlib import Path
from src.reddit import RedditFetcher
from src.huggingface import HuggingFaceFetcher


def main():
    parser = argparse.ArgumentParser(description='抓取 Reddit、HuggingFace 的讨论数据')

    # 新的 --sources 参数（推荐使用）
    parser.add_argument(
        '--sources',
        nargs='+',
        choices=['praw', 'selenium', 'huggingface', 'all'],
        default=None,
        help=(
            '要抓取的数据源（推荐使用此参数）：\n'
            '  praw       - Reddit PRAW API (posts + comments)\n'
            '  selenium   - Reddit Selenium 搜索页面评论（需要 cookies）\n'
            '  huggingface - HuggingFace 模型讨论\n'
            '  all        - 全部数据源\n'
            '示例: --sources selenium (只爬 Selenium)\n'
            '      --sources praw huggingface (爬 PRAW 和 HF)'
        )
    )

    # 旧参数（向后兼容，但不推荐使用）
    parser.add_argument(
        '--platforms',
        nargs='+',
        choices=['reddit', 'huggingface', 'all'],
        default=None,
        help='[已弃用] 使用 --sources 替代'
    )
    parser.add_argument(
        '--reddit-comments',
        action='store_true',
        help='[已弃用] 使用 --sources selenium 替代'
    )

    parser.add_argument(
        '--query',
        type=str,
        default='ERNIE',
        help='搜索关键词（默认: ERNIE）。示例: --query "PaddleOCR-VL"'
    )
    parser.add_argument(
        '--reddit-mode',
        choices=['subreddits', 'global'],
        default='subreddits',
        help=(
            'Reddit 搜索方式（默认: subreddits）：\n'
            '  subreddits - 在特定子版块中搜索（9个AI相关版块）\n'
            '  global     - 全局搜索整个Reddit（适合小众话题如 PaddleOCR-VL）\n'
            '示例: --reddit-mode global'
        )
    )
    parser.add_argument(
        '--cookies',
        type=str,
        default='./cookies.json',
        help='Cookies 文件路径（用于 Selenium 抓取）。默认: ./cookies.json'
    )
    parser.add_argument(
        '--max-pages',
        type=int,
        default=50,
        help='Selenium 每个板块最多滚动次数（默认: 50，约1250条评论/板块）'
    )
    parser.add_argument(
        '--replace-more-limit',
        type=int,
        default=0,
        help='PRAW 评论展开限制（默认: 0 = 全部展开）。设为 None 则不展开'
    )
    parser.add_argument(
        '--export',
        action='store_true',
        help='抓取完成后自动导出为 CSV 文件'
    )
    parser.add_argument(
        '--export-format',
        choices=['csv', 'excel'],
        default='csv',
        help='导出格式（默认: csv）'
    )
    parser.add_argument(
        '--days',
        type=int,
        default=None,
        help='只获取最近 N 天的数据（默认: None = 全部历史数据）'
    )

    args = parser.parse_args()

    # 确定要抓取的数据源
    sources = []

    if args.sources:
        # 使用新的 --sources 参数
        if 'all' in args.sources:
            sources = ['praw', 'selenium', 'huggingface']
        else:
            sources = args.sources
    else:
        # 向后兼容旧参数
        if args.platforms:
            if 'all' in args.platforms:
                platforms = ['reddit', 'huggingface']
            else:
                platforms = args.platforms

            if 'reddit' in platforms:
                sources.append('praw')
                if args.reddit_comments:
                    sources.append('selenium')
            if 'huggingface' in platforms:
                sources.append('huggingface')
        else:
            # 默认：全部
            sources = ['praw', 'selenium', 'huggingface']

    # 去重
    sources = list(dict.fromkeys(sources))

    print("=" * 60)
    print(f"开始抓取数据 - 数据源: {', '.join(sources)}")
    print("=" * 60)

    results = {}

    # Reddit - PRAW API (posts + comments)
    if 'praw' in sources:
        print("\n[PRAW] 抓取 Reddit 帖子和评论 (PRAW API)...")
        print(f"搜索关键词: {args.query}")
        print(f"搜索方式: {'全局搜索 (整个Reddit)' if args.reddit_mode == 'global' else '子版块搜索 (9个AI版块)'}")

        if args.reddit_mode == 'subreddits':
            print("板块 (9个):")
            print("  - LocalLLM, LocalLlaMa, ChatGPT")
            print("  - ArtificialIntelligence, OpenSourceeAI")
            print("  - singularity, machinelearningnews")
            print("  - SillyTavernAI, StableDiffusion")

        if args.days:
            print(f"  时间范围: 最近 {args.days} 天")
        print(f"  评论展开限制: {args.replace_more_limit} (0=全部展开)")

        reddit = RedditFetcher(verbose=True)

        if args.reddit_mode == 'global':
            # 全局搜索模式
            print("\n开始全局搜索...")
            posts = reddit.search_all_reddit(
                query=args.query,
                limit=100,
                search_keywords=args.query
            )

            # 时间过滤 - Posts
            if args.days:
                from datetime import datetime, timedelta
                cutoff_date = datetime.now() - timedelta(days=args.days)
                posts = [p for p in posts if p.created_at >= cutoff_date]

            discussions = posts.copy()

            # 获取评论
            print(f"\n获取 {len(posts)} 个帖子的评论...")
            all_comments = []
            for idx, post in enumerate(posts, 1):
                print(f"  [{idx}/{len(posts)}] {post.title[:50]}...")
                comments = reddit.fetch_post_comments(
                    post_id=post.id,
                    post_title=post.title,
                    subreddit_name=post.subreddit,
                    search_keywords=args.query,
                    replace_more_limit=args.replace_more_limit
                )

                # 时间过滤 - Comments
                if args.days:
                    comments = [c for c in comments if c.created_at >= cutoff_date]

                all_comments.extend(comments)

            if all_comments:
                reddit.add_discussions(all_comments, source='api')
                discussions.extend(all_comments)
        else:
            # 子版块搜索模式（原有方式）
            discussions = reddit.fetch(
                query=args.query,
                fetch_comments=True,
                days_limit=args.days,
                replace_more_limit=args.replace_more_limit
            )

        # 统计 posts 和 comments
        from src.models import ContentType
        posts_count = sum(1 for d in discussions if d.content_type == ContentType.POST)
        comments_count = sum(1 for d in discussions if d.content_type == ContentType.COMMENT)

        results['Reddit Posts (PRAW)'] = posts_count
        results['Reddit Comments (PRAW)'] = comments_count
        print(f"✓ Reddit Posts: {posts_count} 条")
        print(f"✓ Reddit Comments (from posts): {comments_count} 条")

    # Reddit - Selenium 搜索页面评论
    if 'selenium' in sources:
        print(f"\n[Selenium] 抓取 Reddit 搜索页面评论（Selenium + Cookies）...")
        print(f"搜索关键词: {args.query}")
        print(f"搜索方式: {'全局搜索 (整个Reddit)' if args.reddit_mode == 'global' else '子版块搜索 (9个AI版块)'}")
        print("说明：从搜索页面滚动加载评论（按时间排序，获取最新评论）")

        if args.reddit_mode == 'subreddits':
            print("板块 (9个): 同上")

        if args.days:
            print(f"  时间范围: 最近 {args.days} 天")
        else:
            print(f"  时间范围: 最近 30 天（默认）")

        if args.reddit_mode == 'global':
            print(f"  最大滚动次数: {args.max_pages} 次")
        else:
            print(f"  最大滚动次数: {args.max_pages} 次/板块")

        if not Path(args.cookies).exists():
            print(f"❌ 未找到 cookies 文件: {args.cookies}")
            print("\n如何导出 cookies:")
            print("  python3 -m src.reddit_comments_selenium guide")
            print("\n跳过 Selenium 抓取...")
        else:
            try:
                from src.reddit_comments_selenium import RedditCommentsSeleniumFetcher

                comments_fetcher = RedditCommentsSeleniumFetcher(
                    cookies_file=args.cookies,
                    headless=True,  # 无头模式
                    verbose=True
                )
                # 使用 --days 参数，如果未指定则默认 30 天
                days_limit = args.days if args.days else 30
                comments_fetcher.fetch(
                    query=args.query,
                    max_scrolls=args.max_pages,
                    days_limit=days_limit,
                    search_mode=args.reddit_mode,
                    search_keywords=args.query
                )
                results['Reddit Comments (Selenium)'] = len(comments_fetcher.discussions)
                mode_str = "全局搜索" if args.reddit_mode == 'global' else f"滚动 {args.max_pages} 次/板块"
                print(f"✓ Reddit Search Comments: {results['Reddit Comments (Selenium)']} 条（{mode_str}，最近{days_limit}天）")
                print(f"  提示：数据库已自动去重，重复的评论只保留一份")

            except Exception as e:
                print(f"❌ Selenium 抓取失败: {e}")
                print("提示: cookies 可能已过期，或 Chrome 未安装")
                import traceback
                traceback.print_exc()

    # HuggingFace
    if 'huggingface' in sources:
        print("\n[HuggingFace] 抓取 HuggingFace 模型讨论...")
        print(f"搜索关键词: {args.query}")
        if args.days:
            print(f"  时间范围: 最近 {args.days} 天")
        hf = HuggingFaceFetcher(verbose=True)
        hf.fetch(args.query, days_limit=args.days)
        results['HuggingFace'] = len(hf.discussions)
        print(f"✓ HuggingFace: {results['HuggingFace']} 条")

    # 总计
    if results:
        total = sum(results.values())
        print("\n" + "=" * 60)
        print("✓ 完成！")
        for source, count in results.items():
            print(f"  {source}: {count} 条")
        print(f"  总计: {total} 条数据已保存到数据库")
        print("=" * 60)
    else:
        print("\n" + "=" * 60)
        print("⚠️  未选择任何数据源或抓取失败")
        print("=" * 60)

    # 提示
    print("\n💡 使用提示:")
    print("  基础用法:")
    print("    只爬 Selenium:      python3 fetch_all.py --sources selenium")
    print("    只爬 PRAW:          python3 fetch_all.py --sources praw")
    print("    只爬 HuggingFace:   python3 fetch_all.py --sources huggingface")
    print("    爬 PRAW + Selenium: python3 fetch_all.py --sources praw selenium")
    print("    爬全部:             python3 fetch_all.py --sources all")
    print()
    print("  自定义搜索关键词:")
    print("    python3 fetch_all.py --query \"PaddleOCR-VL\" --sources praw")
    print("    python3 fetch_all.py --query \"ERNIE-4.5\" --sources all")
    print()
    print("  Reddit 搜索方式:")
    print("    子版块搜索 (默认):  python3 fetch_all.py --query \"ERNIE\" --reddit-mode subreddits")
    print("    全局搜索:           python3 fetch_all.py --query \"PaddleOCR-VL\" --reddit-mode global")
    print()
    print("  高级选项:")
    print("    结合时间过滤:       python3 fetch_all.py --sources selenium --days 7")
    print("    自定义滚动次数:     python3 fetch_all.py --sources selenium --max-pages 100")
    print("    评论展开限制:       python3 fetch_all.py --sources praw --replace-more-limit 0")

    # 自动导出
    if args.export and results:
        from src.database import DatabaseManager
        from datetime import datetime

        print("\n" + "=" * 60)
        print("导出数据")
        print("=" * 60)

        db = DatabaseManager()
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

        if args.export_format == 'csv':
            output_file = f'./data/exports/discussions_{timestamp}.csv'
            db.export_to_csv(output_file)
        else:
            output_file = f'./data/exports/discussions_{timestamp}.xlsx'
            db.export_to_excel(output_file)

        print(f"✓ 数据已导出到: {output_file}")


if __name__ == '__main__':
    main()
