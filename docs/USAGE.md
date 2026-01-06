# DiscussionFetcher 使用文档

**自动化全量抓取 HuggingFace 和 Reddit 讨论数据**

---

## 🎯 核心特性

- ✅ **完全自动化**：配置一次，之后全自动运行
- ✅ **全量数据**：自动抓取多个来源的完整数据
- ✅ **零手动操作**：除了首次导出 cookies，无需任何手动操作
- ✅ **智能去重**：自动合并数据，避免重复
- ✅ **Web 界面**：可视化操作和数据查看

---

## 📦 数据覆盖范围

### Reddit
- **板块数量**：9个主流 AI/LLM 板块
  - LocalLLM, LocalLlaMa, ChatGPT
  - ArtificialIntelligence, OpenSourceeAI
  - singularity, machinelearningnews
  - SillyTavernAI, StableDiffusion

- **数据类型**：
  - **Posts（帖子）**：使用官方 API 获取
  - **Comments（评论）**：使用 Selenium 自动浏览器获取

- **时间范围**：
  - Posts：全部历史数据
  - Comments：最近 30 天（避免数据量过大）

### HuggingFace
- **数据来源**：ERNIE 相关模型的讨论
- **时间范围**：全部历史数据

---

## 🚀 快速开始

### 第一步：安装依赖

```bash
# 克隆或下载项目后
cd DiscussionFetcher_v2.0

# 安装依赖
pip install -r requirements.txt
```

**依赖说明**：
- `praw`：Reddit 官方 API（获取 Posts）
- `selenium`：浏览器自动化（获取 Comments）
- `beautifulsoup4`：HTML 解析
- `pandas`：数据处理
- `flask`：Web 界面

### 第二步：配置 API 凭证（可选）

Reddit Posts 使用官方 API，需要配置凭证：

```bash
# 复制配置文件
cp .env.example .env

# 编辑 .env，填入你的凭证
# REDDIT_CLIENT_ID=your_client_id
# REDDIT_CLIENT_SECRET=your_client_secret
# REDDIT_USER_AGENT=DiscussionFetcher/1.0
```

**如何获取 Reddit API 凭证**：
1. 访问 https://www.reddit.com/prefs/apps
2. 点击 "Create App" 或 "Create Another App"
3. 填写信息：
   - name: `DiscussionFetcher`
   - type: 选择 `script`
   - redirect uri: `http://localhost:8080`
4. 创建后，复制 `client_id` 和 `client_secret`

> 💡 **提示**：如果不配置，仍可获取 HuggingFace 数据和 Reddit Comments，只是无法获取 Reddit Posts。

### 第三步：导出 Cookies（唯一手动步骤）

**为什么需要 Cookies？**
- ✅ 避免 CAPTCHA 验证
- ✅ 避免登录弹窗
- ✅ 避免限流（已登录用户限制更少）
- ✅ 获取完整内容（几百条评论/板块）

**导出步骤（仅需一次）：**

#### 方法 1: 使用 EditThisCookie 插件（推荐）

1. **安装插件**
   - Chrome/Edge: https://chrome.google.com/webstore → 搜索 "EditThisCookie"
   - Firefox: https://addons.mozilla.org → 搜索 "EditThisCookie"

2. **登录 Reddit**
   - 访问 https://www.reddit.com
   - 登录你的账号（如果没有账号，注册一个）

3. **导出 Cookies**
   - 点击浏览器工具栏的 EditThisCookie 图标（饼干图标）
   - 点击 "Export" 按钮（📤 图标）
   - Cookies 会自动复制到剪贴板
   - 创建文件 `cookies.json`，粘贴内容并保存

```bash
# 在项目根目录创建 cookies.json
# 粘贴从 EditThisCookie 导出的内容
nano cookies.json  # 或使用任何文本编辑器
```

#### 方法 2: 使用浏览器开发者工具

1. 登录 Reddit
2. 按 F12 打开开发者工具
3. 切换到 "Application" / "存储" 标签
4. 左侧选择 "Cookies" → "https://www.reddit.com"
5. 找到重要的 cookies（如 `reddit_session`）
6. 按照以下格式创建 `cookies.json`：

```json
[
  {
    "name": "reddit_session",
    "value": "你的_session_值",
    "domain": ".reddit.com"
  }
]
```

**验证 Cookies 是否有效**：
```bash
python3 -c "from pathlib import Path; print('✓ cookies.json 存在' if Path('./cookies.json').exists() else '✗ 未找到 cookies.json')"
```

---

## 🎮 使用方法

### 方式 1: Web 界面（推荐新手）

最简单的方式，可视化操作：

```bash
# 启动 Web 服务器
./start.sh

# 或手动启动
python3 web_server.py
```

然后访问：http://127.0.0.1:5000

**Web 界面功能**：
- 📊 实时统计（总数、各平台数据量）
- 🚀 一键抓取（选择平台、输入关键词）
- 🔍 搜索和筛选（全文搜索、按平台筛选）
- 💾 数据导出（CSV/Excel 格式）
- 📝 数据浏览（分页查看所有讨论）

### 方式 2: 命令行（推荐自动化）

#### 完整抓取（推荐）

```bash
# 一键抓取所有数据（Posts + Comments）
python3 fetch_all.py --reddit-comments

# 输出示例：
# ✓ Reddit Posts: 45 条
# ✓ Reddit Comments: 18 条（滚动 5 次/板块，最近30天）
# ✓ HuggingFace: 193 条
# ✓ 总计: 256 条数据已保存到数据库
```

**参数说明**：
- `--reddit-comments`：同时抓取评论（需要 cookies.json）
- `--max-pages N`：每个板块最多滚动 N 次（默认5次，约100-150条评论/板块）
- `--platforms`：指定平台（reddit, huggingface, all）
- `--cookies`：指定 cookies 文件路径（默认 ./cookies.json）

#### 高级用法

```bash
# 仅抓取 Reddit（不含评论）
python3 fetch_all.py --platforms reddit

# 仅抓取 HuggingFace
python3 fetch_all.py --platforms huggingface

# 增加评论抓取深度（更多评论，但更慢）
python3 fetch_all.py --reddit-comments --max-pages=20

# 使用自定义 cookies 文件
python3 fetch_all.py --reddit-comments --cookies=/path/to/cookies.json
```

### 方式 3: Python API（高级用户）

```python
# 1. 抓取 Reddit Posts
from src.reddit import RedditFetcher

reddit = RedditFetcher(verbose=True)
posts = reddit.fetch(query='ERNIE')
print(f"获取 {len(posts)} 个帖子")

# 2. 抓取 Reddit Comments（需要 cookies）
from src.reddit_comments_selenium import RedditCommentsSeleniumFetcher

comments_fetcher = RedditCommentsSeleniumFetcher(
    cookies_file='./cookies.json',
    headless=True,  # 无头模式（不显示浏览器）
    verbose=True
)
comments = comments_fetcher.fetch(
    query='ERNIE',
    max_scrolls=10,  # 每个板块滚动10次
    days_limit=30    # 只获取最近30天
)
print(f"获取 {len(comments)} 条评论")

# 3. 抓取 HuggingFace
from src.huggingface import HuggingFaceFetcher

hf = HuggingFaceFetcher(verbose=True)
discussions = hf.fetch('ERNIE-4.5')
print(f"获取 {len(discussions)} 条讨论")
```

---

## 📊 查看数据

### 方式 1: Web 界面

访问 http://127.0.0.1:5000，在界面中：
- 查看实时统计
- 搜索和筛选讨论
- 导出数据

### 方式 2: 命令行工具

```bash
# 查看统计
python3 db_manager.py stats

# 导出为 Excel
python3 db_manager.py export --format excel --output data.xlsx

# 导出为 CSV
python3 db_manager.py export --format csv --output data.csv

# 按平台导出
python3 db_manager.py export --format excel --output reddit_data.xlsx --platform reddit
```

### 方式 3: 直接查询数据库

```python
from src.database import DatabaseManager

db = DatabaseManager()

# 查询最近的讨论
recent = db.get_recent_discussions(limit=10)

# 搜索
results = db.search_discussions(keyword='ERNIE', limit=100)

# 按平台查询
reddit_posts = db.query_discussions(platform='reddit', content_type='post')
reddit_comments = db.query_discussions(platform='reddit', content_type='comment')
hf_discussions = db.query_discussions(platform='huggingface')
```

数据库位置：`./data/discussions.db`（SQLite）

---

## ⚙️ 自动化定时抓取

### 方法 1: cron（Linux/Mac）

```bash
# 编辑 crontab
crontab -e

# 添加定时任务（每天凌晨2点运行）
0 2 * * * cd /path/to/DiscussionFetcher_v2.0 && python3 fetch_all.py --reddit-comments >> logs/fetch.log 2>&1
```

### 方法 2: Windows 任务计划程序

1. 打开"任务计划程序"
2. 创建基本任务
3. 触发器：每天
4. 操作：启动程序
   - 程序：`python3`
   - 参数：`fetch_all.py --reddit-comments`
   - 起始于：`C:\path\to\DiscussionFetcher_v2.0`

### 方法 3: 后台服务（推荐）

创建一个简单的 Python 脚本 `auto_fetch.py`：

```python
#!/usr/bin/env python3
"""自动定时抓取脚本"""

import time
import schedule
from pathlib import Path
import sys

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent))

from src.reddit import RedditFetcher
from src.reddit_comments_selenium import RedditCommentsSeleniumFetcher
from src.huggingface import HuggingFaceFetcher

def fetch_all():
    """执行完整抓取"""
    print(f"\n{'='*60}")
    print(f"开始抓取 - {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*60}\n")

    # Reddit Posts
    reddit = RedditFetcher(verbose=True)
    reddit.fetch(query='ERNIE')

    # Reddit Comments
    if Path('./cookies.json').exists():
        comments = RedditCommentsSeleniumFetcher(headless=True, verbose=True)
        comments.fetch(query='ERNIE', max_scrolls=10, days_limit=30)

    # HuggingFace
    hf = HuggingFaceFetcher(verbose=True)
    hf.fetch('ERNIE-4.5')

    print(f"\n{'='*60}")
    print(f"抓取完成 - {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*60}\n")

# 每天凌晨2点运行
schedule.every().day.at("02:00").do(fetch_all)

print("自动抓取服务已启动")
print("每天凌晨 02:00 自动运行")
print("按 Ctrl+C 停止\n")

# 首次启动立即运行一次
fetch_all()

# 持续运行
while True:
    schedule.run_pending()
    time.sleep(60)
```

运行后台服务：
```bash
# 前台运行（测试）
python3 auto_fetch.py

# 后台运行（生产环境）
nohup python3 auto_fetch.py > logs/auto_fetch.log 2>&1 &
```

---

## 🔧 性能调优

### 调整抓取深度

```bash
# 快速抓取（每个板块约50条评论）
python3 fetch_all.py --reddit-comments --max-pages=3

# 标准抓取（每个板块约100-150条评论，推荐）
python3 fetch_all.py --reddit-comments --max-pages=5

# 深度抓取（每个板块约200-300条评论）
python3 fetch_all.py --reddit-comments --max-pages=10

# 完整抓取（每个板块约400-500条评论，耗时长）
python3 fetch_all.py --reddit-comments --max-pages=20
```

**性能对比**：

| 滚动次数 | 评论数/板块 | 总评论数（9个板块） | 耗时 |
|---------|-----------|------------------|-----|
| 3 次 | ~50 条 | ~450 条 | ~2 分钟 |
| 5 次 | ~100 条 | ~900 条 | ~3 分钟 |
| 10 次 | ~200 条 | ~1800 条 | ~5 分钟 |
| 20 次 | ~400 条 | ~3600 条 | ~10 分钟 |

### 减少板块数量

如果只关注特定板块，可以修改 `src/reddit.py`：

```python
# 编辑 src/reddit.py，找到 REDDIT_SUBREDDITS
REDDIT_SUBREDDITS = [
    "LocalLLM",
    "ChatGPT",
    "ArtificialIntelligence",
    # 注释掉不需要的板块
    # "LocalLlaMa",
    # "OpenSourceeAI",
]
```

---

## 🛠️ 常见问题

### Q1: Cookies 过期怎么办？

**症状**：
- 抓取评论时出现 CAPTCHA
- 日志显示 "需要登录" 或 "被限流"

**解决**：
重新导出 cookies（按照"第三步"重新操作一次）

```bash
# 删除旧的 cookies
rm cookies.json

# 重新导出（按照前面的步骤）
# 然后重新运行抓取
python3 fetch_all.py --reddit-comments
```

### Q2: ChromeDriver 下载失败

**症状**：
```
Could not reach host. Are you offline?
WebDriver 初始化失败
```

**解决方法 1**：检查网络连接
```bash
# 测试网络
curl https://www.google.com
```

**解决方法 2**：手动安装 ChromeDriver
```bash
# Mac
brew install chromedriver

# Ubuntu/Debian
sudo apt-get install chromium-chromedriver

# 手动下载
# 访问 https://chromedriver.chromium.org/downloads
# 下载对应版本的 ChromeDriver
```

### Q3: 抓取速度太慢

**原因**：
- Selenium 需要加载完整页面
- 每个板块需要滚动多次

**优化方案**：
1. 减少滚动次数：`--max-pages=3`
2. 减少板块数量（修改 `src/reddit.py`）
3. 只抓取 Posts，不抓取 Comments
4. 使用多进程（高级用户）

### Q4: 没有找到评论

**可能原因**：
1. 搜索关键词在该板块确实没有评论
2. 所有评论都超过30天（被时间过滤了）
3. Cookies 失效，无法加载完整内容

**检查方法**：
```bash
# 测试单个板块（显示浏览器窗口）
python3 -c "
from src.reddit_comments_selenium import RedditCommentsSeleniumFetcher
f = RedditCommentsSeleniumFetcher(headless=False, verbose=True)
f.fetch(subreddits=['LocalLLM'], max_scrolls=3, days_limit=30)
"
```

### Q5: 数据库文件过大

**清理旧数据**：
```python
from src.database import DatabaseManager
from datetime import datetime, timedelta

db = DatabaseManager()

# 删除超过90天的数据
cutoff = datetime.now() - timedelta(days=90)
# 需要自己实现删除逻辑，或直接删除数据库重新抓取
```

**重建数据库**：
```bash
# 备份
cp data/discussions.db data/discussions.db.backup

# 删除
rm data/discussions.db

# 重新抓取
python3 fetch_all.py --reddit-comments
```

---

## 📖 进阶使用

### 自定义搜索关键词

```bash
# 搜索其他关键词
python3 fetch_all.py --reddit-comments  # 默认搜索 "ERNIE"

# 修改代码搜索其他关键词
# 编辑 fetch_all.py，修改第61行和第97行的 query='ERNIE'
```

### 添加更多板块

编辑 `src/reddit.py`：

```python
REDDIT_SUBREDDITS = [
    # 现有板块
    "LocalLLM", "LocalLlaMa", "ChatGPT",
    "ArtificialIntelligence", "OpenSourceeAI",
    "singularity", "machinelearningnews",
    "SillyTavernAI", "StableDiffusion",

    # 添加新板块
    "MachineLearning",
    "artificial",
    "learnmachinelearning",
]
```

### 修改时间范围

编辑 `src/reddit_comments_selenium.py`，修改 `fetch` 方法的 `days_limit` 默认值：

```python
def fetch(
    self,
    query: str = "ERNIE",
    ...
    days_limit: int = 60  # 改为60天
):
```

或在调用时指定：
```python
comments_fetcher.fetch(query='ERNIE', days_limit=60)
```

---

## 📂 项目结构

```
DiscussionFetcher_v2.0/
├── fetch_all.py              # 主入口：一键抓取所有数据
├── web_server.py            # Web 界面服务器
├── start.sh                 # 快速启动脚本
├── db_manager.py            # 数据库管理工具
├── requirements.txt         # 依赖列表
├── .env                     # API 凭证配置
├── cookies.json            # Reddit cookies（需自己导出）
│
├── src/
│   ├── reddit.py           # Reddit Posts 抓取（PRAW API）
│   ├── reddit_comments_selenium.py  # Reddit Comments 抓取（Selenium）
│   ├── huggingface.py      # HuggingFace 抓取
│   ├── database.py         # 数据库管理
│   ├── models.py           # 数据模型
│   └── config.py           # 配置管理
│
├── web/
│   ├── templates/
│   │   └── index.html      # Web 界面
│   └── static/
│       ├── css/style.css
│       └── js/app.js
│
├── data/
│   └── discussions.db      # SQLite 数据库（自动创建）
│
└── docs/
    ├── USAGE.md            # 本文档
    ├── README.md           # 项目说明
    ├── SELENIUM_GUIDE.md   # Selenium 详细说明
    └── WEB_USAGE.md        # Web 界面说明
```

---

## 🎯 推荐工作流

### 日常使用（推荐）

```bash
# 1. 首次使用：导出 cookies（仅需一次）
#    按照"第三步"操作

# 2. 安装依赖（仅需一次）
pip install -r requirements.txt

# 3. 每次抓取数据
python3 fetch_all.py --reddit-comments

# 4. 查看数据（可选）
python3 db_manager.py stats
python3 db_manager.py export --format excel --output data.xlsx
```

### 自动化部署（推荐生产环境）

```bash
# 1. 部署到服务器
git clone <repo_url>
cd DiscussionFetcher_v2.0

# 2. 配置环境
pip install -r requirements.txt
cp .env.example .env
# 编辑 .env

# 3. 上传 cookies.json
# 在本地导出，然后上传到服务器
scp cookies.json user@server:/path/to/DiscussionFetcher_v2.0/

# 4. 设置定时任务
crontab -e
# 添加：0 2 * * * cd /path/to/DiscussionFetcher_v2.0 && python3 fetch_all.py --reddit-comments

# 5. 启动 Web 界面（可选）
```

---

## 📞 支持

- **文档**：查看项目中的其他 Markdown 文档
  - `README.md` - 项目概述
  - `SELENIUM_GUIDE.md` - Selenium 技术详解
  - `WEB_USAGE.md` - Web 界面使用说明

- **问题反馈**：如有问题，请检查"常见问题"部分

---

## 📝 总结

### 🎯 一次性设置

1. ✅ 安装依赖：`pip install -r requirements.txt`
2. ✅ 配置 API（可选）：编辑 `.env`
3. ✅ 导出 Cookies（必需）：保存为 `cookies.json`

### 🚀 之后使用

```bash
# 一行命令，全自动抓取
python3 fetch_all.py --reddit-comments
```

就这么简单！🎉
