#!/usr/bin/env python3
"""测试 Reddit JSON API 的效果"""

import requests
import json
import time

def test_reddit_json_api():
    """测试 Reddit JSON API"""

    print("=" * 60)
    print("测试 Reddit JSON API")
    print("=" * 60)
    print()

    # 检查 cookies 文件
    import os
    cookies_file = './cookies.json'
    has_cookies = os.path.exists(cookies_file)

    if has_cookies:
        print(f"✓ 找到 cookies 文件: {cookies_file}")
        # 加载 cookies
        session = requests.Session()
        with open(cookies_file, 'r') as f:
            cookies_data = json.load(f)

        if isinstance(cookies_data, list):
            # EditThisCookie 格式
            for cookie in cookies_data:
                session.cookies.set(
                    cookie['name'],
                    cookie['value'],
                    domain=cookie.get('domain', '.reddit.com')
                )
        elif isinstance(cookies_data, dict):
            # 简单字典格式
            for name, value in cookies_data.items():
                session.cookies.set(name, value, domain='.reddit.com')

        print(f"✓ 已加载 {len(session.cookies)} 个 cookies")
    else:
        print(f"⚠️  未找到 cookies 文件: {cookies_file}")
        print("⚠️  将尝试不使用 cookies 访问（可能被限制）")
        session = requests.Session()

    print()

    # 测试参数
    subreddit = "LocalLLM"
    query = "ERNIE"

    # 设置请求头（模拟浏览器）
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
    }
    session.headers.update(headers)

    all_comments = []
    after = None
    page = 1
    max_pages = 3  # 测试 3 页

    print(f"测试板块: r/{subreddit}")
    print(f"搜索关键词: {query}")
    print(f"最多获取: {max_pages} 页")
    print()

    while page <= max_pages:
        print(f"第 {page} 页...")

        # 构建 URL - 尝试不同的方式
        # 方法 1: 直接访问 .json （Reddit 的 JSON 接口）
        # 方法 2: 使用 old.reddit.com
        # 方法 3: 尝试 www.reddit.com

        # 先试 old.reddit.com（可能限制少一些）
        url = f"https://old.reddit.com/r/{subreddit}/search.json"

        params = {
            'q': query,
            'restrict_sr': 'on',  # 限制在当前 subreddit
            'type': 'comment',    # 获取评论
            'sort': 'relevance',
            't': 'all',
            'limit': 100,         # 每页最多 100 条
            'raw_json': 1         # 防止 HTML 转义
        }

        if after:
            params['after'] = after

        try:
            response = session.get(url, params=params, timeout=30)
            response.raise_for_status()

            data = response.json()

            # 检查数据结构
            if 'data' not in data:
                print("❌ 响应中没有 data 字段")
                print(json.dumps(data, indent=2)[:500])
                break

            # 获取评论列表
            children = data['data'].get('children', [])

            if not children:
                print(f"  第 {page} 页没有数据")
                break

            print(f"  获取 {len(children)} 条数据")

            # 检查前几条数据
            for i, child in enumerate(children[:3], 1):
                comment_data = child.get('data', {})
                print(f"    [{i}] ID: {comment_data.get('id', 'N/A')[:10]}")
                print(f"        作者: {comment_data.get('author', 'N/A')}")
                print(f"        内容: {comment_data.get('body', 'N/A')[:50]}...")
                print(f"        评分: {comment_data.get('score', 0)}")

            all_comments.extend(children)

            # 获取下一页的 after 参数
            after = data['data'].get('after')

            if not after:
                print(f"  没有更多页面")
                break

            print(f"  下一页参数: {after}")

            page += 1
            time.sleep(2)  # 避免限流

        except requests.RequestException as e:
            print(f"❌ 请求失败: {e}")
            break
        except json.JSONDecodeError as e:
            print(f"❌ JSON 解析失败: {e}")
            break
        except Exception as e:
            print(f"❌ 未知错误: {e}")
            break

    print()
    print("=" * 60)
    print(f"✓ 测试完成！")
    print(f"  总页数: {page - 1}")
    print(f"  总评论数: {len(all_comments)}")
    print("=" * 60)

    # 保存测试数据
    if all_comments:
        with open('test_reddit_json_output.json', 'w', encoding='utf-8') as f:
            json.dump(all_comments[:5], f, indent=2, ensure_ascii=False)
        print(f"\n✓ 前 5 条数据已保存到 test_reddit_json_output.json")

    return len(all_comments)


if __name__ == "__main__":
    test_reddit_json_api()
