#!/usr/bin/env python3
"""
解析 Reddit 搜索页面的 HTML

完全避开自动化，直接从浏览器保存的 HTML 中提取数据
输出格式与 API 完全一致，便于数据整合
"""

import re
import json
from datetime import datetime
from bs4 import BeautifulSoup
from typing import List
import html as html_lib
import sys
import os

# 添加 src 目录到 Python 路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from models import RedditPost, create_reddit_discussion, ContentType


def parse_timestamp(ts_string: str) -> datetime:
    """
    解析时间戳

    Args:
        ts_string: 时间戳字符串（毫秒或ISO格式）

    Returns:
        datetime 对象
    """
    try:
        # 尝试作为毫秒时间戳解析
        if ts_string.isdigit():
            timestamp_ms = int(ts_string)
            return datetime.fromtimestamp(timestamp_ms / 1000.0)
        # 尝试作为ISO格式解析
        else:
            # 处理多种格式
            # 2025-10-20T03:51:03.714Z → 2025-10-20T03:51:03.714+00:00
            # 2025-10-20T03:51:03.714000+0000 → 2025-10-20T03:51:03.714000+00:00
            ts_clean = ts_string.replace('Z', '+00:00')

            # 如果是 +0000 格式，转换为 +00:00
            import re
            ts_clean = re.sub(r'\+0000$', '+00:00', ts_clean)

            return datetime.fromisoformat(ts_clean)
    except Exception as e:
        # 如果解析失败，返回 None 而不是当前时间
        print(f"    ⚠️  时间戳解析失败: {ts_string}, 错误: {e}")
        return None


def parse_comment_element(element) -> RedditPost:
    """
    解析单个评论元素，返回 RedditPost 对象（与 API 一致）

    Args:
        element: BeautifulSoup 评论元素

    Returns:
        RedditPost 对象，如果解析失败返回 None
    """
    try:
        # 1. 提取 tracking data（包含结构化信息）
        comment_id = ''
        post_id = ''
        post_title = None
        subreddit = ''

        tracking_data = element.get('data-faceplate-tracking-context', '')
        if tracking_data:
            tracking_json = html_lib.unescape(tracking_data)
            tracking_dict = json.loads(tracking_json)

            # Comment 信息
            comment_info = tracking_dict.get('comment', {})
            comment_id = comment_info.get('id', '').replace('t1_', '')
            post_id = comment_info.get('post_id', '').replace('t3_', '')

            # Post 信息
            post_info = tracking_dict.get('post', {})
            post_title = post_info.get('title', '')

            # Subreddit 信息
            subreddit_info = tracking_dict.get('subreddit', {})
            subreddit = subreddit_info.get('name', '')

        # 2. 提取作者
        author = '[deleted]'
        author_link = element.find('a', href=re.compile(r'/user/'))
        if author_link:
            author = author_link.text.strip()

        # 3. 提取评论内容
        content = ''
        content_div = element.find('div', id=re.compile(r'search-comment-t1_'))
        if content_div:
            # 移除 HTML 标签，只保留文本
            content = content_div.get_text(separator='\n', strip=True)

        # 4. 提取评分
        score = 0
        votes_span = element.find('span', string=re.compile(r'\d+\s+votes?'))
        if votes_span:
            votes_match = re.search(r'(\d+)\s+votes?', votes_span.text)
            if votes_match:
                score = int(votes_match.group(1))

        # 5. 提取时间戳
        created_at = None
        time_elem = element.find('faceplate-timeago')
        if time_elem:
            ts = time_elem.get('ts', '')
            if ts:
                created_at = parse_timestamp(ts)

        # 如果没有找到时间戳，跳过这条评论
        if created_at is None:
            if comment_id:
                print(f"    ⚠️  警告：评论 {comment_id} 没有时间戳，跳过")
            return None

        # 6. 提取链接
        url = ''
        permalink = ''
        comment_link = element.find('a', href=re.compile(r'/comments/.*/.*/.*/'))
        if comment_link:
            permalink = comment_link.get('href', '')
            if permalink.startswith('/'):
                url = f"https://www.reddit.com{permalink}"
            else:
                url = permalink

        # 使用 create_reddit_discussion 创建对象（与 API 完全一致）
        if content:  # 只有有内容的评论才创建对象
            return create_reddit_discussion(
                post_id=comment_id,
                title=post_title,  # 评论的帖子标题
                content=content,
                author=author,
                created_at=created_at,
                subreddit=subreddit,
                url=url,
                permalink=permalink,
                score=score,
                content_type=ContentType.COMMENT,
                parent_id=post_id  # 父帖子 ID
            )

        return None

    except Exception as e:
        print(f"解析评论时出错: {e}")
        import traceback
        traceback.print_exc()
        return None


def parse_reddit_html(html_file: str) -> List[RedditPost]:
    """
    解析整个 HTML 文件，返回 RedditPost 对象列表

    Args:
        html_file: HTML 文件路径

    Returns:
        RedditPost 对象列表
    """
    print(f"正在解析: {html_file}")

    try:
        with open(html_file, 'r', encoding='utf-8') as f:
            html_content = f.read()

        soup = BeautifulSoup(html_content, 'html.parser')

        # 检查是否被限流
        if 'whoa there, pardner' in html_content.lower():
            print("❌ HTML 显示被限流，请等待后重新保存页面")
            return []

        # 检查是否有 CAPTCHA
        if 'Prove your humanity' in html_content:
            print("❌ HTML 显示 CAPTCHA，请在浏览器中完成验证后重新保存")
            return []

        # 查找所有评论元素
        comment_elements = soup.find_all('search-telemetry-tracker',
                                        attrs={'view-events': 'search/view/comment'})

        print(f"找到 {len(comment_elements)} 个评论元素")

        comments = []
        for idx, elem in enumerate(comment_elements, 1):
            comment = parse_comment_element(elem)
            if comment:
                comments.append(comment)
                if idx % 10 == 0:
                    print(f"  已解析 {idx}/{len(comment_elements)}")

        print(f"✓ 成功解析 {len(comments)} 条评论")
        return comments

    except FileNotFoundError:
        print(f"❌ 找不到文件: {html_file}")
        return []
    except Exception as e:
        print(f"❌ 解析失败: {e}")
        import traceback
        traceback.print_exc()
        return []


def save_to_csv(comments: List[RedditPost], output_file: str):
    """
    保存为 CSV（使用与 API 一致的字段）

    Args:
        comments: RedditPost 对象列表
        output_file: 输出文件路径
    """
    import csv

    if not comments:
        print("没有数据可保存")
        return

    # 确保 data 目录存在
    output_dir = os.path.dirname(output_file)
    if output_dir and not os.path.exists(output_dir):
        os.makedirs(output_dir)
        print(f"✓ 创建目录: {output_dir}")

    # CSV 字段（与 API 输出一致）
    fields = [
        'id',           # 评论 ID
        'platform',     # 平台（reddit）
        'content_type', # 内容类型（comment）
        'author',       # 作者
        'content',      # 评论内容
        'created_at',   # 创建时间
        'url',          # 完整 URL
        'title',        # 帖子标题
        'score',        # 评分
        'parent_id',    # 父帖子 ID
        'subreddit',    # 板块名称
        'permalink',    # Reddit permalink
        'fetched_at'    # 抓取时间
    ]

    with open(output_file, 'w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()

        for comment in comments:
            # 转换为字典（使用 RedditPost 的 to_dict 方法）
            data = comment.to_dict()

            # 提取 metadata 中的字段
            row = {
                'id': data.get('id', ''),
                'platform': data.get('platform', 'reddit'),
                'content_type': data.get('content_type', 'comment'),
                'author': data.get('author', ''),
                'content': data.get('content', ''),
                'created_at': data.get('created_at', ''),
                'url': data.get('url', ''),
                'title': data.get('title', ''),
                'score': data.get('score', 0),
                'parent_id': data.get('parent_id', ''),
                'subreddit': data.get('metadata', {}).get('subreddit', ''),
                'permalink': data.get('metadata', {}).get('permalink', ''),
                'fetched_at': data.get('fetched_at', '')
            }

            writer.writerow(row)

    print(f"✓ 已保存到: {output_file}")


def parse_folder(folder_path: str, pattern: str = "*.html") -> List[RedditPost]:
    """
    解析文件夹中所有 HTML 文件

    Args:
        folder_path: 文件夹路径
        pattern: 文件匹配模式（默认 *.html）

    Returns:
        所有评论的 RedditPost 对象列表
    """
    import glob

    # 获取所有匹配的 HTML 文件
    html_files = glob.glob(os.path.join(folder_path, pattern))

    if not html_files:
        print(f"❌ 在 {folder_path} 中未找到匹配 {pattern} 的文件")
        return []

    print(f"找到 {len(html_files)} 个 HTML 文件")
    print()

    all_comments = []

    for idx, html_file in enumerate(html_files, 1):
        filename = os.path.basename(html_file)
        print(f"[{idx}/{len(html_files)}] 处理: {filename}")
        print("-" * 60)

        comments = parse_reddit_html(html_file)
        all_comments.extend(comments)

        print(f"  从 {filename} 解析出 {len(comments)} 条评论")
        print()

    return all_comments


def save_to_database(comments: List[RedditPost], keyword: str = 'ERNIE') -> int:
    """
    保存数据到数据库（仅保存包含关键词的内容）

    Args:
        comments: RedditPost 对象列表
        keyword: 必须包含的关键词（默认 'ERNIE'，不区分大小写）

    Returns:
        成功保存的记录数
    """
    if not comments:
        print("没有数据可保存")
        return 0

    try:
        from database import DatabaseManager

        db = DatabaseManager()

        print()
        print("=" * 60)
        print("保存到数据库...")
        print("=" * 60)

        # 过滤：只保留包含关键词的评论
        filtered_comments = []
        for comment in comments:
            # 在标题或内容中查找关键词（不区分大小写）
            keyword_lower = keyword.lower()
            title_match = comment.title and keyword_lower in comment.title.lower()
            content_match = comment.content and keyword_lower in comment.content.lower()

            if title_match or content_match:
                filtered_comments.append(comment)

        if len(filtered_comments) < len(comments):
            print(f"⚠️  过滤掉 {len(comments) - len(filtered_comments)} 条不包含 '{keyword}' 的内容")

        if not filtered_comments:
            print(f"❌ 没有包含关键词 '{keyword}' 的数据")
            return 0

        print(f"✓ 筛选后保留 {len(filtered_comments)} 条包含 '{keyword}' 的评论")

        # 转换为字典列表
        data_list = [comment.to_dict() for comment in filtered_comments]

        # 批量插入/更新
        success_count = db.bulk_upsert(data_list, source='html')

        print(f"✓ 成功保存 {success_count} 条记录到数据库")
        print(f"  原始评论数: {len(comments)} 条")
        print(f"  筛选后: {len(filtered_comments)} 条")
        print(f"  新增/更新: {success_count} 条")
        print(f"  跳过（已存在且更旧）: {len(filtered_comments) - success_count} 条")

        return success_count

    except ImportError:
        print("⚠️  无法导入 database 模块")
        print("请确保 src/database.py 存在")
        return 0
    except Exception as e:
        print(f"❌ 保存到数据库失败: {e}")
        import traceback
        traceback.print_exc()
        return 0


def main():
    import sys
    import os
    import glob

    print("=" * 60)
    print("Reddit HTML 解析器（API 兼容格式）")
    print("=" * 60)
    print()

    # 检查参数
    if len(sys.argv) > 1:
        input_path = sys.argv[1]
    else:
        # 默认使用当前目录
        input_path = "."

    # 判断是文件还是文件夹
    if os.path.isfile(input_path):
        # 单个文件模式
        print("模式: 单个文件")
        print(f"文件: {input_path}")
        print()

        comments = parse_reddit_html(input_path)

        if not comments:
            print("未找到任何评论")
            return

        # 保存到数据库
        save_to_database(comments)

        # 同时保存 CSV 备份（可选）
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = os.path.basename(input_path).replace('.html', '')
        output_file = f"./data/backup/reddit_{filename}_{timestamp}.csv"
        save_to_csv(comments, output_file)

        # 显示统计
        print()
        print("=" * 60)
        print(f"完成！共解析 {len(comments)} 条评论")
        print(f"数据已保存到数据库")
        print("=" * 60)

    elif os.path.isdir(input_path):
        # 文件夹模式
        print("模式: 批量处理文件夹")
        print(f"文件夹: {input_path}")
        print()

        # 解析文件夹中所有 HTML
        all_comments = parse_folder(input_path, pattern="reddit*.html")

        if not all_comments:
            print("未找到任何评论")
            return

        # 显示预览
        print("=" * 60)
        print("前 3 条评论预览:")
        print("=" * 60)
        print()

        for i, comment in enumerate(all_comments[:3], 1):
            print(f"[{i}] {comment.author}")
            print(f"    ID: {comment.id}")
            print(f"    板块: r/{comment.subreddit}")
            print(f"    帖子: {comment.title[:50] if comment.title else 'N/A'}...")
            content_preview = comment.content[:100]
            print(f"    内容: {content_preview}...")
            print(f"    评分: {comment.score}")
            print(f"    时间: {comment.created_at}")
            print()

        # 保存到数据库
        save_to_database(all_comments)

        # 同时保存 CSV 备份
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = f"./data/backup/reddit_html_batch_{timestamp}.csv"
        save_to_csv(all_comments, output_file)

        # 显示统计
        print()
        print("=" * 60)
        print(f"完成！共解析 {len(all_comments)} 条评论")
        print(f"数据已保存到数据库")
        print(f"CSV 备份: {output_file}")
        print("=" * 60)

    else:
        print("❌ 路径不存在")
        print()
        print("使用方法:")
        print()
        print("1. 单个文件:")
        print("   python3 parse_reddit_html.py reddit_page.html")
        print()
        print("2. 批量处理文件夹:")
        print("   python3 parse_reddit_html.py ./reddit_html/")
        print("   (会处理文件夹中所有 reddit*.html 文件)")
        print()
        print("3. 默认处理当前目录:")
        print("   python3 parse_reddit_html.py")
        print()
        return


if __name__ == "__main__":
    main()
