#!/usr/bin/env python3
"""Web Server for DiscussionFetcher - 提供 Web 界面和 API"""

from flask import Flask, render_template, jsonify, request, send_file
from flask_cors import CORS
from pathlib import Path
import os
import sys
from datetime import datetime
import threading
import time

# 添加 src 到 path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.database import DatabaseManager
from src.reddit import RedditFetcher
from src.huggingface import HuggingFaceFetcher

app = Flask(__name__, template_folder='web/templates', static_folder='web/static')
CORS(app)

# 全局变量
db = DatabaseManager()
fetch_status = {
    'running': False,
    'platform': None,
    'progress': '',
    'error': None
}


@app.route('/')
def index():
    """主页"""
    return render_template('index.html')


@app.route('/api/stats')
def get_stats():
    """获取数据库统计"""
    try:
        stats = db.get_stats_detailed()

        # 获取最近更新时间
        recent = db.get_recent_discussions(limit=1)
        last_update = recent[0]['fetched_at'] if recent else None

        return jsonify({
            'success': True,
            'data': {
                'total': stats.get('total', 0),
                'platforms': stats.get('platforms', {}),
                'content_types': stats.get('content_types', {}),
                'last_update': last_update
            }
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/discussions')
def get_discussions():
    """获取讨论列表"""
    try:
        platform = request.args.get('platform')
        content_type = request.args.get('content_type')
        search_keywords = request.args.get('search_keywords')
        limit = int(request.args.get('limit', 100))
        offset = int(request.args.get('offset', 0))

        discussions = db.query_discussions(
            platform=platform,
            content_type=content_type,
            search_keywords=search_keywords,
            limit=limit,
            offset=offset
        )

        return jsonify({
            'success': True,
            'data': discussions,
            'count': len(discussions)
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/search')
def search_discussions():
    """搜索讨论"""
    try:
        keyword = request.args.get('keyword', '')
        platform = request.args.get('platform')
        limit = int(request.args.get('limit', 100))

        if not keyword:
            return jsonify({'success': False, 'error': 'Keyword required'}), 400

        discussions = db.search_discussions(
            keyword=keyword,
            platform=platform,
            limit=limit
        )

        return jsonify({
            'success': True,
            'data': discussions,
            'count': len(discussions)
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/export')
def export_data():
    """导出数据"""
    try:
        format_type = request.args.get('format', 'csv')
        platform = request.args.get('platform')
        search_keywords = request.args.get('search_keywords')

        # 构建文件名
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        parts = ['discussions']
        if platform:
            parts.append(platform)
        if search_keywords:
            parts.append(search_keywords.replace(' ', '_'))
        parts.append(timestamp)
        filename = f'{"_".join(parts)}.{format_type}'
        filepath = Path('./data/exports') / filename
        filepath.parent.mkdir(parents=True, exist_ok=True)

        # 导出
        if format_type == 'csv':
            db.export_to_csv(str(filepath), platform=platform, search_keywords=search_keywords, limit=None)
        elif format_type == 'excel':
            # Excel 导出需要特殊处理
            if platform:
                db.export_to_excel(str(filepath), platforms=[platform], search_keywords=search_keywords)
            else:
                db.export_to_excel(str(filepath), search_keywords=search_keywords)
        else:
            return jsonify({'success': False, 'error': 'Invalid format'}), 400

        return send_file(filepath, as_attachment=True)

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/fetch/start', methods=['POST'])
def start_fetch():
    """开始抓取数据（后台任务）"""
    global fetch_status

    if fetch_status['running']:
        return jsonify({
            'success': False,
            'error': 'Fetch already running'
        }), 400

    try:
        data = request.json
        platforms = data.get('platforms', ['reddit', 'huggingface'])
        query = data.get('query', 'ERNIE')
        include_comments = data.get('include_comments', False)
        reddit_search_mode = data.get('reddit_search_mode', 'subreddits')

        # 启动后台线程
        thread = threading.Thread(
            target=fetch_worker,
            args=(platforms, query, include_comments, reddit_search_mode)
        )
        thread.daemon = True
        thread.start()

        return jsonify({
            'success': True,
            'message': 'Fetch started'
        })

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/fetch/status')
def fetch_status_api():
    """获取抓取状态"""
    return jsonify({
        'success': True,
        'data': fetch_status
    })


def fetch_worker(platforms, query, include_comments, reddit_search_mode='subreddits'):
    """后台抓取任务"""
    global fetch_status

    fetch_status['running'] = True
    fetch_status['error'] = None

    try:
        # Reddit
        if 'reddit' in platforms:
            fetch_status['platform'] = 'reddit'

            reddit = RedditFetcher(verbose=False)

            # 根据搜索方式选择不同的抓取方法
            if reddit_search_mode == 'global':
                fetch_status['progress'] = f'🔍 Reddit 全局搜索关键词: {query}'
                time.sleep(0.5)  # 让前端有时间捕捉这个状态

                # 全局搜索
                posts = reddit.search_all_reddit(
                    query=query,
                    limit=100,
                    search_keywords=query
                )

                fetch_status['progress'] = f'✓ Reddit: 找到 {len(posts)} 条帖子'
                time.sleep(0.5)

                # 获取评论
                if include_comments and posts:
                    total_comments = 0
                    for idx, post in enumerate(posts, 1):
                        fetch_status['progress'] = f'📥 获取评论 ({idx}/{len(posts)}): {post.title[:30]}...'
                        comments = reddit.fetch_post_comments(
                            post_id=post.id,
                            post_title=post.title,
                            subreddit_name=post.subreddit,
                            search_keywords=query,
                            replace_more_limit=0  # 全局搜索时展开所有评论
                        )
                        total_comments += len(comments)

                    fetch_status['progress'] = f'✓ Reddit: 获取了 {total_comments} 条评论'
                    time.sleep(0.5)
            else:
                fetch_status['progress'] = f'🔍 Reddit 子版块搜索关键词: {query}'
                time.sleep(0.5)

                # 特定子版块搜索（原有方式）
                reddit.fetch(query=query, fetch_comments=include_comments)

                fetch_status['progress'] = f'✓ Reddit: 子版块搜索完成'
                time.sleep(0.5)

            # Selenium Comments（仅在特定子版块模式 + 不自动获取评论时可用）
            # 注意：全局搜索模式下，如果勾选了"获取评论"，已经在上面用 PRAW 获取过了
            # 这里的 Selenium 方式是针对特定子版块的额外评论获取方式（需要 cookies）
            # 由于逻辑复杂，这里暂时跳过 Selenium 评论获取，全部使用 PRAW 的方式

        # HuggingFace
        if 'huggingface' in platforms:
            fetch_status['platform'] = 'huggingface'
            fetch_status['progress'] = f'🔍 HuggingFace 搜索模型: {query}'
            time.sleep(0.5)

            hf = HuggingFaceFetcher(verbose=False)
            discussions = hf.fetch(query)

            fetch_status['progress'] = f'✓ HuggingFace: 获取了 {len(discussions)} 条讨论'
            time.sleep(0.5)

        fetch_status['progress'] = '🎉 所有平台抓取完成！'
        time.sleep(0.5)

    except Exception as e:
        fetch_status['error'] = str(e)
        fetch_status['progress'] = f'Error: {e}'

    finally:
        fetch_status['running'] = False


@app.route('/api/cookies/check')
def check_cookies():
    """检查 cookies 文件是否存在"""
    cookies_path = Path('./cookies.json')
    return jsonify({
        'success': True,
        'exists': cookies_path.exists()
    })


@app.route('/api/keywords')
def get_keywords():
    """获取所有搜索关键词列表"""
    try:
        keywords = db.get_search_keywords()
        return jsonify({
            'success': True,
            'data': keywords
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/twitter/import', methods=['POST'])
def import_twitter_csv():
    """导入 Twitter CSV 文件"""
    try:
        if 'files' not in request.files:
            return jsonify({'success': False, 'error': 'No files uploaded'}), 400

        files = request.files.getlist('files')
        if not files:
            return jsonify({'success': False, 'error': 'No files uploaded'}), 400

        # 获取搜索关键词（可选）
        search_keywords = request.form.get('keywords', None)

        # 创建临时目录
        temp_dir = Path('./data/temp_uploads')
        temp_dir.mkdir(parents=True, exist_ok=True)

        # 保存文件
        saved_files = []
        for file in files:
            if file.filename.endswith('.csv'):
                filepath = temp_dir / file.filename
                file.save(str(filepath))
                saved_files.append(str(filepath))

        if not saved_files:
            return jsonify({'success': False, 'error': 'No valid CSV files'}), 400

        # 导入数据
        from src.twitter_importer import TwitterCSVImporter
        importer = TwitterCSVImporter(verbose=False, search_keywords=search_keywords)
        total_count = importer.import_multiple_files(saved_files)

        # 清理临时文件
        for filepath in saved_files:
            try:
                os.remove(filepath)
            except:
                pass

        return jsonify({
            'success': True,
            'data': {
                'success_count': total_count,
                'files_processed': len(saved_files)
            }
        })

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/stats/timeline')
def get_timeline_stats():
    """获取时间线统计数据（按日/周/月分组）"""
    try:
        group_by = request.args.get('group_by', 'day')  # day, week, month
        platform = request.args.get('platform')
        days = int(request.args.get('days', 30))  # 默认最近30天

        # 获取统计数据
        from datetime import datetime, timedelta
        import sqlite3

        cutoff_date = datetime.now() - timedelta(days=days)

        # 构建查询
        conn = sqlite3.connect(db.db_path)
        cursor = conn.cursor()

        # 根据分组方式设置SQL日期格式
        date_formats = {
            'day': '%Y-%m-%d',
            'week': '%Y-W%W',
            'month': '%Y-%m'
        }
        date_format = date_formats.get(group_by, '%Y-%m-%d')

        # 构建WHERE子句
        where_clauses = [f"created_at >= ?"]
        params = [cutoff_date.isoformat()]

        if platform:
            where_clauses.append("platform = ?")
            params.append(platform)

        where_sql = " AND ".join(where_clauses)

        # 执行查询
        query = f"""
            SELECT
                strftime('{date_format}', created_at) as date_group,
                COUNT(*) as count,
                platform,
                content_type
            FROM discussions
            WHERE {where_sql}
            GROUP BY date_group, platform, content_type
            ORDER BY date_group
        """

        cursor.execute(query, params)
        results = cursor.fetchall()
        conn.close()

        # 格式化结果
        timeline_data = {}
        for row in results:
            date_group, count, plat, ctype = row
            if date_group not in timeline_data:
                timeline_data[date_group] = {'total': 0, 'by_platform': {}, 'by_type': {}}

            timeline_data[date_group]['total'] += count
            timeline_data[date_group]['by_platform'][plat] = timeline_data[date_group]['by_platform'].get(plat, 0) + count
            timeline_data[date_group]['by_type'][ctype] = timeline_data[date_group]['by_type'].get(ctype, 0) + count

        return jsonify({
            'success': True,
            'data': timeline_data,
            'group_by': group_by,
            'days': days
        })

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/stats/top_authors')
def get_top_authors():
    """获取最活跃的作者统计"""
    try:
        platform = request.args.get('platform')
        limit = int(request.args.get('limit', 20))
        days = int(request.args.get('days', 30))

        from datetime import datetime, timedelta
        import sqlite3

        cutoff_date = datetime.now() - timedelta(days=days)

        conn = sqlite3.connect(db.db_path)
        cursor = conn.cursor()

        # 构建查询
        where_clauses = [f"created_at >= ?", "author != '[deleted]'"]
        params = [cutoff_date.isoformat()]

        if platform:
            where_clauses.append("platform = ?")
            params.append(platform)

        where_sql = " AND ".join(where_clauses)
        params.append(limit)

        query = f"""
            SELECT
                author,
                COUNT(*) as post_count,
                platform,
                MAX(created_at) as last_post
            FROM discussions
            WHERE {where_sql}
            GROUP BY author, platform
            ORDER BY post_count DESC
            LIMIT ?
        """

        cursor.execute(query, params)
        results = cursor.fetchall()
        conn.close()

        authors = []
        for row in results:
            authors.append({
                'author': row[0],
                'post_count': row[1],
                'platform': row[2],
                'last_post': row[3]
            })

        return jsonify({
            'success': True,
            'data': authors,
            'count': len(authors)
        })

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/cleanup/duplicates', methods=['POST'])
def cleanup_duplicates():
    """清理重复数据"""
    try:
        # 调用数据库去重功能
        removed_count = db.remove_duplicates()

        return jsonify({
            'success': True,
            'data': {
                'removed_count': removed_count
            }
        })

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


if __name__ == '__main__':
    print("=" * 60)
    print("DiscussionFetcher Web Interface")
    print("=" * 60)
    print()
    print("Starting server at http://127.0.0.1:5000")
    print()
    print("Press Ctrl+C to stop")
    print("=" * 60)

    app.run(host='0.0.0.0', port=5000, debug=True)
