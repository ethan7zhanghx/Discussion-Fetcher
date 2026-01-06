# DiscussionFetcher

**自动化全量抓取 HuggingFace 和 Reddit 关于 ERNIE 的讨论数据**

🎉 **v2.0 新增 Web 界面！** 现在可以通过浏览器可视化操作和查看数据！

---

## ✨ 核心特性

- ✅ **完全自动化** - 配置一次，之后全自动运行
- ✅ **全量数据** - 自动抓取 9 个 Reddit 板块 + HuggingFace
- ✅ **零手动操作** - 除了首次导出 cookies，无需任何手动操作
- ✅ **智能去重** - 自动合并数据，避免重复
- ✅ **Web 界面** - 可视化操作和数据查看

---

## 📦 数据覆盖

### Reddit（9个板块）
- LocalLLM, LocalLlaMa, ChatGPT
- ArtificialIntelligence, OpenSourceeAI
- singularity, machinelearningnews
- SillyTavernAI, StableDiffusion

**数据类型**：
- **Posts（帖子）**：全部历史数据（官方 API）
- **Comments（评论）**：最近 30 天（Selenium 自动化）

### HuggingFace
- ERNIE-4.5 相关模型的讨论
- 全部历史数据

---

## 🚀 快速开始（3步）

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 导出 Cookies（仅需一次）

**为什么需要 Cookies？**
- 避免 CAPTCHA 验证
- 避免限流
- 获取完整评论数据

**如何导出（2分钟）：**

1. 安装 Chrome 插件 **EditThisCookie**
   - https://chrome.google.com/webstore → 搜索 "EditThisCookie"

2. 登录 Reddit
   - 访问 https://www.reddit.com
   - 登录账号（没有就注册一个）

3. 导出 Cookies
   - 点击 EditThisCookie 图标（饼干图标）
   - 点击 "Export" 按钮（📤）
   - 保存为 `cookies.json`

```bash
# 保存到项目根目录
# /path/to/DiscussionFetcher_v2.0/cookies.json
```

> 💡 详细图文教程：查看 [USAGE.md](docs/USAGE.md#第三步导出-cookies唯一手动步骤)

### 3. 运行抓取

```bash
# 方式 1: Web 界面（推荐）
./start.sh
# 然后访问 http://127.0.0.1:5000

# 方式 2: 命令行
python3 fetch_all.py --reddit-comments
```

**就这么简单！** 🎉

---

## 📊 使用示例

### 命令行全量抓取

```bash
# 完整抓取（Posts + Comments）
python3 fetch_all.py --reddit-comments

# 输出示例：
# ✓ Reddit Posts: 45 条
# ✓ Reddit Comments: 18 条（滚动 5 次/板块，最近30天）
# ✓ HuggingFace: 193 条
# ✓ 总计: 256 条数据已保存到数据库
```

### Web 界面操作

```bash
# 启动服务器
./start.sh

# 访问浏览器
# http://127.0.0.1:5000
```

**Web 界面功能**：
- 📊 实时统计
- 🚀 一键抓取
- 🔍 搜索和筛选
- 💾 数据导出（CSV/Excel）
- 📝 数据浏览

### 查看数据

```bash
# 统计
python3 db_manager.py stats

# 导出 Excel
python3 db_manager.py export --format excel --output data.xlsx

# 导出 CSV
python3 db_manager.py export --format csv --output data.csv
```

---

## 📖 文档

| 文档 | 说明 |
|------|------|
| **[USAGE.md](docs/USAGE.md)** | 📘 完整使用文档（推荐阅读） |
| [SELENIUM_GUIDE.md](docs/SELENIUM_GUIDE.md) | 🔧 Selenium + Cookies 技术说明 |
| [WEB_USAGE.md](docs/WEB_USAGE.md) | 🌐 Web 界面详细说明 |

---

## 🔄 自动化定时抓取

### cron（Linux/Mac）

```bash
# 每天凌晨2点自动抓取
crontab -e

# 添加：
0 2 * * * cd /path/to/DiscussionFetcher_v2.0 && python3 fetch_all.py --reddit-comments >> logs/fetch.log 2>&1
```

### Windows 任务计划程序

1. 打开"任务计划程序"
2. 创建基本任务 → 每天
3. 操作：`python3 fetch_all.py --reddit-comments`

---

## ⚙️ 配置（可选）

### Reddit API 凭证

Reddit Posts 使用官方 API，需要配置凭证：

```bash
cp .env.example .env
# 编辑 .env，填入凭证
```

**获取凭证**：
1. 访问 https://www.reddit.com/prefs/apps
2. 创建 App（类型选 "script"）
3. 复制 `client_id` 和 `client_secret`

> 💡 不配置仍可获取 HuggingFace 和 Reddit Comments

### 调整抓取深度

```bash
# 快速抓取（~50条/板块）
python3 fetch_all.py --reddit-comments --max-pages=3

# 标准抓取（~100条/板块，推荐）
python3 fetch_all.py --reddit-comments --max-pages=5

# 深度抓取（~200条/板块）
python3 fetch_all.py --reddit-comments --max-pages=10
```

---

## 📂 项目结构

```
DiscussionFetcher_v2.0/
├── 📄 主要脚本
│   ├── fetch_all.py              # 主入口：一键抓取
│   ├── web_server.py            # Web 界面服务器
│   ├── db_manager.py            # 数据库管理工具
│   └── start.sh                 # 快速启动脚本
│
├── 📁 src/                       # 核心代码模块
│   ├── reddit.py                # Reddit Posts（PRAW API）
│   ├── reddit_comments_selenium.py  # Reddit Comments（Selenium）
│   ├── huggingface.py           # HuggingFace 抓取
│   ├── database.py              # 数据库管理
│   ├── models.py                # 数据模型
│   ├── base.py                  # 基类
│   └── config.py                # 配置管理
│
├── 📁 web/                       # Web 界面资源
│   ├── templates/               # HTML 模板
│   └── static/                  # CSS/JS 资源
│
├── 📁 docs/                      # 📚 完整文档
│   ├── USAGE.md                 # 使用文档
│   ├── QUICKSTART.md            # 快速开始
│   ├── SELENIUM_GUIDE.md        # Selenium 指南
│   └── ... (更多文档)
│
├── 📁 scripts/                   # 🛠️ 工具脚本
│   ├── analyze_relevance.py    # 相关性分析
│   ├── test_*.py                # 测试脚本
│   └── ... (更多工具)
│
├── 📁 examples/                  # 📓 示例代码
│   └── notebooks/               # Jupyter Notebooks
│
├── 📁 data/                      # 💾 数据存储
│   ├── discussions.db           # SQLite 数据库
│   └── exports/                 # 导出文件
│
└── 📁 logs/                      # 📋 日志文件
    └── fetcher.log              # 运行日志
```

---

## 🛠️ 常见问题

### Q: Cookies 过期怎么办？

重新导出即可（按照"快速开始"第2步重新操作）。

### Q: 没有找到评论？

可能原因：
1. 该板块确实没有相关评论
2. 所有评论都超过30天（被过滤了）
3. Cookies 失效

解决：重新导出 cookies，或使用 `headless=False` 查看浏览器。

### Q: ChromeDriver 下载失败？

```bash
# Mac
brew install chromedriver

# Ubuntu/Debian
sudo apt-get install chromium-chromedriver
```

### Q: 速度太慢？

```bash
# 减少滚动次数
python3 fetch_all.py --reddit-comments --max-pages=3

# 或只抓取 Posts（不抓取 Comments）
python3 fetch_all.py
```

更多问题查看 **[USAGE.md](USAGE.md#常见问题)**

---

## 🎯 推荐工作流

### 日常使用

```bash
# 1. 首次：导出 cookies（2分钟，仅需一次）
#    安装 EditThisCookie → 登录 Reddit → 导出

# 2. 安装依赖（仅需一次）
pip install -r requirements.txt

# 3. 之后每次抓取
python3 fetch_all.py --reddit-comments

# 4. 查看数据
python3 db_manager.py stats
```

### 生产部署

```bash
# 1. 部署
git clone <repo_url>
cd DiscussionFetcher_v2.0
pip install -r requirements.txt

# 2. 配置
# 上传 cookies.json 到服务器

# 3. 定时任务
crontab -e
# 添加：0 2 * * * cd /path/to/DiscussionFetcher_v2.0 && python3 fetch_all.py --reddit-comments

# 4. Web 界面（可选）
nohup python3 web_server.py > logs/web.log 2>&1 &
```

---

## 🌟 特性说明

### 数据源

| 数据源 | 方法 | 覆盖范围 | 时间范围 |
|--------|------|---------|---------|
| **Reddit Posts** | PRAW API | 9个板块 | 全部历史 |
| **Reddit Comments** | Selenium | 9个板块 | 最近30天 |
| **HuggingFace** | 官方 API | ERNIE-4.5 | 全部历史 |

### 自动化特性

- ✅ 自动去重（相同 ID 只保留最新）
- ✅ 自动保存（实时写入数据库）
- ✅ 自动滚动（加载完整评论）
- ✅ 自动重试（网络错误）
- ✅ 自动限流（避免被封）

### Web 界面特性

- 📊 实时统计（总数、各平台）
- 🚀 后台抓取（不阻塞界面）
- 🔍 全文搜索（标题、内容）
- 📝 分页浏览（支持筛选）
- 💾 数据导出（CSV/Excel）
- 📱 响应式设计（支持移动端）

---

## 📚 技术栈

- **Python 3.9+**
- **PRAW** - Reddit 官方 API
- **Selenium** - 浏览器自动化
- **BeautifulSoup4** - HTML 解析
- **Flask** - Web 框架
- **SQLite** - 轻量级数据库
- **Pandas** - 数据处理

---

## 📄 许可证

MIT License

---

## 📞 支持

遇到问题？

1. **查看文档**：[USAGE.md](docs/USAGE.md) 有详细说明
2. **常见问题**：[USAGE.md#常见问题](docs/USAGE.md#常见问题)
3. **技术细节**：[SELENIUM_GUIDE.md](docs/SELENIUM_GUIDE.md)

---

## 🎉 总结

### 一次性设置（5分钟）

1. ✅ `pip install -r requirements.txt`
2. ✅ 导出 cookies 为 `cookies.json`
3. ✅ （可选）配置 `.env`

### 之后使用（一行命令）

```bash
python3 fetch_all.py --reddit-comments
```

**就这么简单！** 🚀

详细使用说明请查看 **[USAGE.md](docs/USAGE.md)**
