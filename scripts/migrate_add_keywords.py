#!/usr/bin/env python3
"""
迁移脚本：给所有现有数据添加 ERNIE 标签
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from database import DatabaseManager


def migrate_add_keywords():
    """给所有现有数据添加 search_keywords = 'ERNIE'"""

    print("=" * 60)
    print("迁移脚本：添加搜索关键词标签")
    print("=" * 60)
    print()

    db = DatabaseManager()
    conn = db.get_connection()
    cursor = conn.cursor()

    # 统计需要更新的记录
    cursor.execute("SELECT COUNT(*) as count FROM discussions WHERE search_keywords IS NULL")
    count = cursor.fetchone()['count']

    if count == 0:
        print("✓ 所有数据已有关键词标签，无需更新")
        conn.close()
        return

    print(f"发现 {count} 条记录没有关键词标签")
    print("正在更新为 'ERNIE'...")
    print()

    # 更新所有没有 search_keywords 的记录
    cursor.execute("""
        UPDATE discussions
        SET search_keywords = 'ERNIE'
        WHERE search_keywords IS NULL
    """)

    conn.commit()

    print(f"✓ 成功更新 {cursor.rowcount} 条记录")
    print()

    # 显示统计
    cursor.execute("""
        SELECT search_keywords, COUNT(*) as count
        FROM discussions
        GROUP BY search_keywords
    """)

    print("当前关键词分布：")
    for row in cursor.fetchall():
        keyword = row['search_keywords'] or '(无标签)'
        count = row['count']
        print(f"  {keyword}: {count} 条")

    conn.close()

    print()
    print("=" * 60)
    print("✓ 迁移完成！")
    print("=" * 60)


if __name__ == '__main__':
    migrate_add_keywords()
