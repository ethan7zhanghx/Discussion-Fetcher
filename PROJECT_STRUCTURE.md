# 📁 Project Structure

**DiscussionFetcher v2.0** - 整理后的清晰目录结构

---

## 🎯 项目根目录（简洁）

```
DiscussionFetcher_v2.0/
├── 📄 fetch_all.py              ← 主入口脚本
├── 📄 web_server.py             ← Web 服务器
├── 📄 db_manager.py             ← 数据库管理工具
├── 📄 start.sh                  ← 快速启动脚本
├── 📄 README.md                 ← 项目说明
├── 📄 CLAUDE.md                 ← Claude Code 指南
├── 📄 requirements.txt          ← Python 依赖
├── 📄 .env                      ← 环境配置（需自行创建）
├── 📄 cookies.json              ← Reddit Cookies（需导出）
└── 📄 cookies.example.json      ← Cookies 示例
```

---

## 📚 文档目录（docs/）

**所有文档集中管理**

```
docs/
├── README.md                    ← 文档索引
├── USAGE.md                     ← 完整使用文档
├── QUICKSTART.md                ← 5分钟快速开始
├── README_CLI.md                ← 命令行参数详解
├── WEB_USAGE.md                 ← Web界面使用说明
├── SELENIUM_GUIDE.md            ← Selenium + Cookies 指南
├── REDDIT_API_GUIDE.md          ← Reddit API 配置
├── TWITTER_IMPORT_GUIDE.md      ← Twitter 导入指南
├── DATABASE_GUIDE.md            ← 数据库结构说明
├── HTML_PARSE_GUIDE.md          ← HTML 解析技术
├── TEST_WEB.md                  ← Web 测试说明
└── CHANGELOG_IMPROVEMENTS.md    ← 改进记录（2026-01-06）
```

**快速索引**：
- 🚀 新用户 → [QUICKSTART.md](docs/QUICKSTART.md)
- 📖 详细使用 → [USAGE.md](docs/USAGE.md)
- 🌐 Web界面 → [WEB_USAGE.md](docs/WEB_USAGE.md)
- 🔧 技术细节 → [SELENIUM_GUIDE.md](docs/SELENIUM_GUIDE.md)

---

## 🛠️ 工具脚本（scripts/）

**分析、测试和迁移工具**

```
scripts/
├── README.md                    ← 脚本说明
├── analyze_relevance.py         ← 相关性分析
├── analyze_relevance_v2.py      ← 相关性分析 v2
├── add_value_analysis.py        ← 价值分析
├── test_reddit_json_api.py      ← Reddit API 测试
├── test_analyze.py              ← 分析功能测试
├── parse_reddit_html.py         ← HTML 解析（旧版）
├── migrate_add_keywords.py      ← 数据库迁移
└── update_twitter_keywords.py   ← 更新关键词
```

**用途**：
- 📊 数据分析脚本
- 🧪 功能测试脚本
- 🔄 数据迁移工具

---

## 💻 核心代码（src/）

**Python 模块和类**

```
src/
├── __init__.py                  ← 包初始化
├── base.py                      ← BaseFetcher 基类
├── models.py                    ← 数据模型（Discussion 等）
├── config.py                    ← 配置管理
├── database.py                  ← 数据库管理器
├── logger.py                    ← 日志系统
├── utils.py                     ← 工具函数（限流、重试）
├── reddit.py                    ← Reddit Posts 采集（PRAW）
├── reddit_comments_selenium.py  ← Reddit Comments（Selenium）
├── reddit_comments.py           ← Reddit Comments（旧版）
├── huggingface.py               ← HuggingFace 采集
└── twitter_importer.py          ← Twitter CSV 导入
```

**架构**：
- `BaseFetcher` → 所有采集器的基类
- `Discussion` → 统一数据模型
- `DatabaseManager` → 数据库操作

---

## 🌐 Web 资源（web/）

**Flask Web 界面**

```
web/
├── templates/
│   └── index.html               ← 前端 HTML
└── static/
    ├── css/
    │   └── style.css            ← 样式表
    └── js/
        └── app.js               ← JavaScript 逻辑
```

---

## 💾 数据存储（data/）

**数据库和导出文件**

```
data/
├── discussions.db               ← SQLite 数据库（主要）
├── discussions.db.backup        ← 备份文件
├── backup/                      ← 备份目录
├── exports/                     ← 导出文件（CSV/Excel）
├── html_debug/                  ← HTML 调试文件
└── temp_uploads/                ← 临时上传目录
```

---

## 📓 示例代码（examples/）

**Jupyter Notebooks 和示例**

```
examples/
└── notebooks/
    ├── Reddit.ipynb             ← Reddit 使用示例
    └── HuggingFace.ipynb        ← HuggingFace 示例
```

---

## 📋 日志文件（logs/）

**运行日志**

```
logs/
├── fetcher.log                  ← 主日志（采集记录）
└── web.log                      ← Web 服务器日志
```

---

## 🎨 整理前后对比

### ❌ 整理前（根目录混乱）
```
根目录: 30+ 个文件混在一起
├── 11 个 Markdown 文档
├── 8 个分析/测试脚本
├── 3 个主要脚本
├── 临时数据文件
└── 配置文件
```

### ✅ 整理后（清晰分类）
```
根目录: 仅 9 个核心文件
├── docs/       ← 所有文档（12个）
├── scripts/    ← 工具脚本（8个）
├── src/        ← 核心代码
├── web/        ← Web 资源
├── data/       ← 数据存储
├── examples/   ← 示例代码
└── logs/       ← 日志文件
```

---

## 📊 目录统计

| 目录 | 文件数 | 说明 |
|------|--------|------|
| **根目录** | 9 | 核心脚本和配置 |
| **docs/** | 12 | 完整文档集合 |
| **scripts/** | 8 | 工具和测试脚本 |
| **src/** | 12 | Python 核心模块 |
| **web/** | 3 | Web 界面资源 |
| **examples/** | 2 | Jupyter 示例 |

---

## 🔍 快速导航

### 🆕 新用户入门
1. 查看 [README.md](README.md) - 项目概述
2. 阅读 [docs/QUICKSTART.md](docs/QUICKSTART.md) - 快速开始
3. 运行 `./start.sh` - 启动 Web 界面

### 📖 深入使用
1. [docs/USAGE.md](docs/USAGE.md) - 完整使用文档
2. [docs/README_CLI.md](docs/README_CLI.md) - 命令行参数
3. [CLAUDE.md](CLAUDE.md) - 开发者指南

### 🛠️ 开发和维护
1. [src/](src/) - 查看核心代码
2. [scripts/](scripts/) - 使用工具脚本
3. [docs/DATABASE_GUIDE.md](docs/DATABASE_GUIDE.md) - 数据库结构

---

## ✨ 整理成果

### 改进点
1. ✅ **根目录清爽** - 从 30+ 文件减少到 9 个核心文件
2. ✅ **文档集中** - 所有文档在 `docs/` 目录，易于查找
3. ✅ **工具分离** - 测试和分析脚本在 `scripts/` 目录
4. ✅ **清理临时文件** - 删除了导出的 CSV/Excel 临时文件
5. ✅ **更新引用** - 所有文档链接已更新为新路径

### 维护建议
- 📄 新文档 → 放入 `docs/` 目录
- 🛠️ 新工具脚本 → 放入 `scripts/` 目录
- 📓 新示例 → 放入 `examples/` 目录
- 💾 导出数据 → 使用 `data/exports/` 目录

---

**整理完成时间**: 2026-01-06
**整理效果**: 项目结构更清晰，易于维护和导航 ✨
