# 快速开始指南

## 改进说明

之前需要**手动保存 HTML** 再解析，现在已改进为**自动获取**！

### 新架构

```
Reddit 数据获取：
├── Posts（帖子）      → PRAW API          (src/reddit.py)
└── Comments（评论）   → Cookies + 自动获取 (src/reddit_comments.py) ✨ 新增
```

## 使用步骤

### 1️⃣ 基础安装

```bash
# 安装依赖
pip install -r requirements.txt

# 配置环境变量（复制 .env.example 为 .env）
cp .env.example .env
# 编辑 .env，填入 Reddit API 凭证
```

### 2️⃣ 快速测试（仅获取 Posts）

```bash
python3 fetch_all.py
```

这会获取：
- ✅ Reddit Posts（9个板块）
- ✅ HuggingFace 数据

### 3️⃣ 完整使用（Posts + Comments）

**Step 1: 导出 Cookies（仅需一次）**

```bash
# 查看详细导出指南
python3 -m src.reddit_comments guide
```

**Step 2: 同时获取 Posts 和 Comments**

```bash
python3 fetch_all.py --reddit-comments
```

这会获取：
- ✅ Reddit Posts（9个板块）
- ✅ Reddit Comments（9个板块）✨ 新增
- ✅ HuggingFace 数据

## 对比：旧方法 vs 新方法

### 旧方法（已废弃）

```bash
# 1. 手动打开浏览器
# 2. 访问 Reddit 搜索页面
# 3. 右键 → 保存为 HTML
# 4. 运行脚本解析
python3 parse_reddit_html.py reddit_page.html
```

❌ **问题**：繁琐、手动操作、每次都要重复

### 新方法（推荐）

```bash
# 1. 导出 cookies（仅需一次）
python3 -m src.reddit_comments guide

# 2. 自动获取所有数据
python3 fetch_all.py --reddit-comments
```

✅ **优势**：自动化、一键完成、可定时运行

## Cookies 导出（详细步骤）

### 方法 1：EditThisCookie 插件（推荐）

1. 安装插件：
   - Chrome/Edge: https://chrome.google.com/webstore → 搜索 "EditThisCookie"
   - Firefox: https://addons.mozilla.org → 搜索 "EditThisCookie"

2. 登录 Reddit：
   - 访问 https://www.reddit.com
   - 登录你的账号

3. 导出 cookies：
   - 点击浏览器工具栏的 EditThisCookie 图标
   - 点击 "Export" 按钮（📤 图标）
   - 复制 JSON 内容
   - 保存为 `./cookies.json`

### 方法 2：浏览器开发者工具

1. 登录 Reddit
2. 按 F12 打开开发者工具
3. 切换到 "Application" / "存储" 标签
4. 左侧选择 "Cookies" → "https://www.reddit.com"
5. 复制重要 cookies 的名称和值
6. 按照 `cookies.example.json` 格式创建 `cookies.json`

## 常见问题

### Q: Cookies 会过期吗？

A: 会的，如果遇到 "需要 CAPTCHA 验证" 或 "被限流" 错误，重新导出 cookies 即可。

### Q: Cookies 安全吗？

A: Cookies 包含你的登录凭证，不要分享给他人。项目已在 `.gitignore` 中排除 `cookies.json`。

### Q: 可以不用 Cookies 吗？

A: 可以，但只能获取 Posts，无法获取 Comments。建议使用 cookies 获取完整数据。

### Q: 获取速度慢？

A: 为避免被限流，默认每个请求间隔 2 秒。可在代码中调整 `rate_limit` 参数。

## 查看数据

```bash
# 查看统计
python3 db_manager.py stats

# 导出为 Excel
python3 db_manager.py export --format excel --output ernie_discussions.xlsx

# 导出为 CSV
python3 db_manager.py export --format csv --output ernie_discussions.csv
```

## 数据结构

所有数据保存在 `./data/discussions.db`，包含：

- **Posts（帖子）**：标题、内容、作者、评分、时间等
- **Comments（评论）**：评论内容、作者、评分、所属帖子等
- **自动去重**：相同 ID 的数据只保留最新版本
- **来源标记**：`source` 字段标识数据来源（api/web）

## 命令速查

```bash
# 仅获取 Posts
python3 fetch_all.py

# 获取 Posts + Comments
python3 fetch_all.py --reddit-comments

# 查看 cookies 导出指南
python3 -m src.reddit_comments guide

# 测试 Comments 获取（单个板块）
python3 -m src.reddit_comments

# 查看数据统计
python3 db_manager.py stats

# 导出数据
python3 db_manager.py export --format excel --output data.xlsx
```

## 定时任务（可选）

使用 cron 定时抓取（Linux/macOS）：

```bash
# 编辑 crontab
crontab -e

# 每天凌晨 2 点运行
0 2 * * * cd /path/to/DiscussionFetcher_v2.0 && python3 fetch_all.py --reddit-comments >> logs/cron.log 2>&1
```

## 技术栈

- **PRAW**: Reddit 官方 API（获取 Posts）
- **Requests + BeautifulSoup**: HTTP 请求 + HTML 解析（获取 Comments）
- **SQLite**: 数据存储
- **Pandas**: 数据处理和导出

## 项目结构

```
DiscussionFetcher_v2.0/
├── src/
│   ├── reddit.py              # Reddit Posts (PRAW API)
│   ├── reddit_comments.py     # Reddit Comments (新增) ✨
│   ├── huggingface.py         # HuggingFace
│   ├── database.py            # 数据库管理
│   └── ...
├── fetch_all.py               # 统一入口（已更新）
├── parse_reddit_html.py       # 旧方法（已废弃）
├── cookies.json               # 你的 cookies（需自行创建）
├── cookies.example.json       # Cookies 格式示例
└── README.md                  # 详细文档
```
