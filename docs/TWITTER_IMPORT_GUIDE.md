# Twitter 数据导入指南

## 📋 概述

DiscussionFetcher 现在支持导入 Twitter CSV 数据！你可以手动导出 Twitter 数据（帖子和评论），然后使用导入工具将它们添加到数据库中，与 Reddit 和 HuggingFace 数据一起统一管理和分析。

## 🎯 CSV 格式要求

### 支持的表头（中文）

你的 CSV 文件必须包含以下列（表头顺序可以不同）：

```
序号,ID,链接,发布日期,类型,内容,标签,语言,喜欢数,书签数,转发数,回复数,浏览量,可能敏感,用户ID,用户名,用户昵称,用户头像链接,用户封面图片链接,用户媒体数,用户注册时间,用户个人简介,用户推文数,用户粉丝数,用户所在地,用户是否认证账号,回复推文 ID,回复推文用户名,回复推文用户 ID,回复推文链接
```

### 必填字段

- `ID` - 推文ID（必须唯一）
- `链接` - 推文URL
- `内容` - 推文内容
- `发布日期` - 发布时间（支持各种日期格式）
- `用户名` - 发推用户的用户名

### 可选字段

所有其他字段都是可选的，如果为空会使用默认值（0 或 None）。

### 帖子 vs 评论区分

- **帖子（Post）**：`回复推文 ID` 字段为空
- **评论（Comment）**：`回复推文 ID` 字段有值

## 📥 导入方法

### 方法1：使用命令行工具（推荐）

```bash
# 导入单个文件
python3 -m src.twitter_importer path/to/your/twitter_posts.csv

# 导入多个文件（帖子 + 评论）
python3 -m src.twitter_importer twitter_posts.csv twitter_comments.csv

# 显示详细日志
python3 -m src.twitter_importer twitter_posts.csv -v

# 导入后自动导出为 Excel
python3 -m src.twitter_importer twitter_posts.csv --export

# 指定数据库路径
python3 -m src.twitter_importer twitter_posts.csv --db ./custom/path/discussions.db
```

### 方法2：使用 Python 脚本

```python
from src.twitter_importer import TwitterCSVImporter

# 创建导入器
importer = TwitterCSVImporter(verbose=True)

# 导入单个文件
count = importer.import_csv('twitter_posts.csv')
print(f"导入了 {count} 条记录")

# 导入多个文件
count = importer.import_multiple_files([
    'twitter_posts.csv',
    'twitter_comments.csv'
])
print(f"总共导入了 {count} 条记录")
```

## 📊 查看导入的数据

### 1. 使用 Web 界面（推荐）

启动 Web 服务器：

```bash
python3 web_server.py
```

然后访问 http://127.0.0.1:5000

- 可以按平台筛选（选择 "twitter"）
- 可以搜索推文内容
- 可以导出数据

### 2. 使用命令行查询

```bash
# 查看所有 Twitter 数据
python3 -c "
from src.database import DatabaseManager
db = DatabaseManager()
df = db.get_discussions(platform='twitter')
print(df.head())
"
```

### 3. 直接导出

```bash
# 导出 Twitter 数据为 CSV
python3 -c "
from src.database import DatabaseManager
db = DatabaseManager()
db.export_to_csv('twitter_data.csv', platform='twitter')
"

# 导出所有平台数据为 Excel（每个平台一个 sheet）
python3 -c "
from src.database import DatabaseManager
db = DatabaseManager()
db.export_to_excel('all_platforms.xlsx', platforms=['reddit', 'huggingface', 'twitter'])
"
```

## 🔄 去重机制

### 入库时的行为

- **不去重**：所有数据都会被保存，即使 `ID` 相同
- 这样可以保留历史快照（比如同一条推文在不同时间的点赞数变化）

### 导出时的去重

- **智能去重**：按 `(platform, platform_id)` 分组
- **保留最新**：对于同一个 `ID`，只保留 `fetched_at` 最新的记录
- **结果**：导出的数据中每条推文只出现一次，且是最新的版本

```python
# 导出时自动去重（默认行为）
db.export_to_csv('twitter.csv', platform='twitter', deduplicate=True)

# 导出时不去重（保留所有历史记录）
db.export_to_csv('twitter_all.csv', platform='twitter', deduplicate=False)
```

## 🎨 CSV 样例

这是一个最小的有效 CSV 文件示例：

```csv
序号,ID,链接,发布日期,类型,内容,标签,语言,喜欢数,书签数,转发数,回复数,浏览量,可能敏感,用户ID,用户名,用户昵称,用户头像链接,用户封面图片链接,用户媒体数,用户注册时间,用户个人简介,用户推文数,用户粉丝数,用户所在地,用户是否认证账号,回复推文 ID,回复推文用户名,回复推文用户 ID,回复推文链接
1,1234567890,https://twitter.com/user/status/1234567890,2025-01-15 10:30:00,post,这是一条测试推文,#AI #测试,zh,100,10,5,20,5000,false,9876543210,test_user,测试用户,https://pbs.twimg.com/profile_images/xxx.jpg,,,2020-01-01 00:00:00,这是个人简介,1000,5000,北京,true,,,,
2,1234567891,https://twitter.com/user/status/1234567891,2025-01-15 11:00:00,comment,这是一条回复,,,50,5,2,3,1000,false,1111111111,reply_user,回复用户,,,,,2021-05-01 00:00:00,,500,200,,false,1234567890,test_user,9876543210,https://twitter.com/user/status/1234567890
```

## 💡 使用技巧

### 1. 批量导入多个文件

```bash
# 使用通配符导入所有 CSV
python3 -m src.twitter_importer twitter_*.csv

# 或者明确列出文件
python3 -m src.twitter_importer \
    twitter_posts_part1.csv \
    twitter_posts_part2.csv \
    twitter_comments.csv
```

### 2. 验证导入结果

```bash
# 查看统计信息
python3 -c "
from src.database import DatabaseManager
db = DatabaseManager()
stats = db.get_stats(platform='twitter')
print('Twitter 数据统计:')
print(f'  总数: {stats[\"twitter\"][\"count\"]}')
print(f'  最早: {stats[\"twitter\"][\"earliest\"]}')
print(f'  最新: {stats[\"twitter\"][\"latest\"]}')
"
```

### 3. 查看帖子和评论分布

```bash
python3 -c "
from src.database import DatabaseManager
db = DatabaseManager()
df = db.get_discussions(platform='twitter')
print('内容类型分布:')
print(df['content_type'].value_counts())
"
```

### 4. 导出合并数据

```bash
# 导出所有平台的 Posts
python3 -c "
from src.database import DatabaseManager
db = DatabaseManager()
df = db.get_discussions()
df_posts = df[df['content_type'] == 'post']
df_posts.to_csv('all_posts.csv', index=False, encoding='utf-8-sig')
print(f'导出了 {len(df_posts)} 条 posts')
"
```

## ⚠️ 常见问题

### Q1: 导入时提示 "文件不存在"

**解决**：确保文件路径正确，或使用绝对路径：

```bash
python3 -m src.twitter_importer /Users/xxx/Desktop/twitter_posts.csv
```

### Q2: 日期格式不识别

**支持的日期格式**（会自动识别）：
- `2025-01-15 10:30:00`
- `2025-01-15T10:30:00Z`
- `2025/01/15 10:30:00`
- `15-Jan-2025 10:30`
- 其他标准 ISO 格式

如果日期解析失败，该行会被跳过（使用 `-v` 可查看详细错误）。

### Q3: 数字字段为空怎么办？

**没关系**！所有数字字段（如喜欢数、转发数）为空时会自动使用默认值 0。

### Q4: 如何处理大文件？

**建议**：
1. 分批导入（每次 10000 条左右）
2. 使用 `-v` 查看进度
3. 导入后用 `deduplicate=True` 导出去重

```bash
# 分批导入
python3 -m src.twitter_importer twitter_part1.csv -v
python3 -m src.twitter_importer twitter_part2.csv -v

# 导出去重后的数据
python3 -c "
from src.database import DatabaseManager
db = DatabaseManager()
db.export_to_excel('twitter_dedup.xlsx', platforms=['twitter'], deduplicate=True)
"
```

### Q5: 重复导入同一个文件会怎样？

**会保留所有记录**！
- 入库时不去重，所以每次导入都会添加新记录
- 导出时可以选择去重（`deduplicate=True`）
- 如果误导入多次，可以手动删除数据库重新导入

## 📈 高级用法

### 自定义导入逻辑

```python
from src.twitter_importer import TwitterCSVImporter
from src.database import DatabaseManager

# 创建导入器
importer = TwitterCSVImporter(verbose=True)

# 导入文件
count = importer.import_csv('twitter_posts.csv')

# 查看导入结果
db = DatabaseManager()
df = db.get_discussions(platform='twitter', limit=10)
print(df[['author', 'content', 'likes', 'created_at']])
```

### 过滤导出

```python
from src.database import DatabaseManager

db = DatabaseManager()

# 只导出 2025年的数据
df = db.get_discussions(
    platform='twitter',
    start_date='2025-01-01',
    end_date='2025-12-31'
)

df.to_csv('twitter_2025.csv', index=False, encoding='utf-8-sig')
```

## 🎉 下一步

导入 Twitter 数据后，你可以：

1. **统一分析**：在 Web 界面查看所有平台的讨论
2. **跨平台搜索**：搜索关键词（如 "ERNIE"）会同时搜索 Reddit、HuggingFace、Twitter
3. **导出汇总**：将三个平台的数据导出到一个 Excel 文件（每个平台一个 sheet）

```bash
# 启动 Web 界面
python3 web_server.py

# 访问 http://127.0.0.1:5000
```

## 🆘 需要帮助？

如果遇到问题：

1. 使用 `-v` 参数查看详细日志
2. 检查 CSV 文件编码（应为 UTF-8）
3. 确保必填字段不为空（ID、链接、内容、发布日期、用户名）
4. 查看数据库日志（如果有错误会显示具体原因）

祝使用愉快！🚀
