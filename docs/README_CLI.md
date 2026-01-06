# DiscussionFetcher - 命令行使用文档

完整的命令行配置和使用指南。

---

## 📋 目录

- [快速开始](#快速开始)
- [环境配置](#环境配置)
- [命令行参数详解](#命令行参数详解)
- [使用场景示例](#使用场景示例)
- [常见问题](#常见问题)

---

## 🚀 快速开始

### 最简单的用法

```bash
# 使用默认配置抓取 ERNIE 相关讨论（所有数据源）
python3 fetch_all.py

# 指定搜索关键词
python3 fetch_all.py --query "PaddleOCR-VL"

# 只抓取 Reddit PRAW 数据
python3 fetch_all.py --sources praw

# 抓取最近 7 天的数据
python3 fetch_all.py --sources praw --days 7
```

---

## ⚙️ 环境配置

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置 API 凭证

创建 `.env` 文件（参考 `.env.example`）：

```bash
# Reddit API 凭证（必需）
REDDIT_CLIENT_ID=your_client_id_here
REDDIT_CLIENT_SECRET=your_client_secret_here
REDDIT_USER_AGENT=DiscussionFetcher/2.0

# HuggingFace Token（可选，提高 API 限制）
HUGGINGFACE_TOKEN=your_token_here
```

#### 如何获取 Reddit API 凭证

1. 访问 https://www.reddit.com/prefs/apps
2. 点击 "Create App" 或 "Create Another App"
3. 填写信息：
   - **name**: DiscussionFetcher
   - **App type**: 选择 "script"
   - **redirect uri**: http://localhost:8080
4. 创建后获得：
   - **client_id**: 应用 ID（在应用名称下方）
   - **client_secret**: secret（点击 "secret" 查看）

#### 如何获取 HuggingFace Token（可选）

1. 访问 https://huggingface.co/settings/tokens
2. 点击 "New token"
3. 设置权限为 "read"
4. 复制 token 到 `.env` 文件

### 3. 配置 Cookies（可选，仅 Selenium 需要）

如果需要使用 Selenium 抓取 Reddit 评论：

```bash
# 查看导出 cookies 指南
python3 -m src.reddit_comments_selenium guide

# 导出 cookies 后保存为 cookies.json
```

---

## 📖 命令行参数详解

### 主要参数

#### `--sources` - 选择数据源（推荐使用）

选择要抓取的数据源，可以选择一个或多个。

```bash
--sources praw              # 只抓取 Reddit PRAW API（帖子 + 评论）
--sources selenium          # 只抓取 Reddit Selenium（搜索页面评论）
--sources huggingface       # 只抓取 HuggingFace 讨论
--sources praw huggingface  # 抓取 PRAW 和 HuggingFace
--sources all               # 抓取所有数据源
```

**数据源说明：**

| 数据源 | 说明 | 优点 | 缺点 |
|--------|------|------|------|
| `praw` | Reddit PRAW API | 稳定可靠，包含帖子和评论 | 受 API 限制 |
| `selenium` | Reddit Selenium 自动化 | 可获取搜索页面评论 | 需要 cookies，速度较慢 |
| `huggingface` | HuggingFace 模型讨论 | 包含模型相关讨论和评论 | 仅适用于 HuggingFace 模型 |

#### `--query` - 搜索关键词

指定要搜索的关键词。

```bash
--query "ERNIE"          # 默认值
--query "PaddleOCR-VL"   # 搜索 PaddleOCR-VL
--query "GPT-4"          # 搜索 GPT-4
```

**注意：**
- 对于 HuggingFace，query 应该是模型名称（例如 "ERNIE-4.5"）
- 对于 Reddit，query 是搜索关键词
- 建议使用引号包裹关键词，特别是包含特殊字符时

#### `--reddit-mode` - Reddit 搜索方式

控制 Reddit 搜索是在特定子版块还是全局搜索。

```bash
--reddit-mode subreddits  # 在9个AI子版块中搜索（默认）
--reddit-mode global      # 全局搜索整个Reddit
```

**默认值：** `subreddits`

**说明：**

| 模式 | 适用场景 | 优点 | 缺点 |
|------|---------|------|------|
| `subreddits` | 热门话题（如 ERNIE、ChatGPT） | 结果更精准，AI相关性高 | 可能遗漏小众讨论 |
| `global` | 小众话题（如 PaddleOCR-VL） | 覆盖整个Reddit，不遗漏 | 结果可能不够精准 |

**预设的9个子版块：**
- LocalLLM, LocalLlaMa
- ChatGPT, ArtificialIntelligence
- OpenSourceeAI, singularity
- machinelearningnews
- SillyTavernAI, StableDiffusion

**使用建议：**
```bash
# 热门话题 - 使用子版块搜索
python3 fetch_all.py --query "ERNIE" --reddit-mode subreddits

# 小众话题 - 使用全局搜索
python3 fetch_all.py --query "PaddleOCR-VL" --reddit-mode global
```

#### `--days` - 时间范围

只获取最近 N 天的数据。

```bash
--days 7    # 最近 7 天
--days 30   # 最近 30 天
--days 365  # 最近一年
```

**默认值：** `None`（全部历史数据）

#### `--max-pages` - Selenium 滚动次数

控制 Selenium 的最大滚动次数。

```bash
--max-pages 10   # 滚动 10 次（约 250 条评论）
--max-pages 50   # 滚动 50 次（约 1250 条评论，默认）
--max-pages 100  # 滚动 100 次（约 2500 条评论）
```

**默认值：** `50`

**说明：**
- **子版块模式**: 每个子版块滚动 N 次（9个子版块 × N）
- **全局模式**: 在全局搜索结果页面滚动 N 次（总共 N 次）
- 每次滚动约加载 25 条评论
- 滚动次数越多，获取的评论越多，但耗时也越长
- 推荐对于小众话题使用较大值（50-100），热门话题使用较小值（10-20）

#### `--replace-more-limit` - PRAW 评论展开限制

控制 PRAW API 展开 "更多评论" 的次数。

```bash
--replace-more-limit 0     # 展开所有评论（默认，推荐）
--replace-more-limit 10    # 最多展开 10 次 "MoreComments"
--replace-more-limit 50    # 最多展开 50 次
```

**默认值：** `0`（展开所有）

**说明：**
- `0` 表示展开所有 "更多评论" 链接，获取最完整的评论
- 每个 "MoreComments" 对象通常包含 20-100 条评论
- 对于评论很多的帖子，设置为 `0` 可能会很慢
- 如果只需要快速获取主要评论，可以设置为 `10` 或 `None`

#### `--cookies` - Cookies 文件路径

指定 Selenium 使用的 cookies 文件。

```bash
--cookies ./cookies.json          # 默认路径
--cookies /path/to/your/cookies.json
```

**默认值：** `./cookies.json`

### 导出参数

#### `--export` - 自动导出

抓取完成后自动导出数据。

```bash
--export                           # 启用自动导出
--export --export-format csv       # 导出为 CSV（默认）
--export --export-format excel     # 导出为 Excel
```

**导出文件位置：** `./data/exports/discussions_<timestamp>.<format>`

### 已弃用参数（向后兼容）

以下参数已弃用，建议使用新的参数：

```bash
--platforms reddit huggingface     # 已弃用，使用 --sources praw huggingface
--reddit-comments                  # 已弃用，使用 --sources selenium
```

---

## 🎯 使用场景示例

### 场景 1: 抓取 ERNIE 相关讨论（默认配置）

```bash
python3 fetch_all.py
```

这将：
- 抓取所有数据源（PRAW + Selenium + HuggingFace）
- 搜索关键词：ERNIE
- 时间范围：全部历史数据
- Selenium 滚动 50 次/子版块
- PRAW 展开所有评论

### 场景 2: 抓取小众话题（如 PaddleOCR-VL）

对于小众话题，建议使用全局搜索和更多滚动次数：

```bash
python3 fetch_all.py \
  --query "PaddleOCR-VL" \
  --reddit-mode global \
  --sources praw selenium \
  --max-pages 100 \
  --days 365
```

说明：
- 搜索 "PaddleOCR-VL"
- **使用全局搜索模式**（整个Reddit）
- 使用 PRAW 和 Selenium
- 每个子版块滚动 100 次（获取更多评论）
- 只获取最近一年的数据

### 场景 3: 快速抓取最近讨论（只要帖子不要评论）

```bash
python3 fetch_all.py --query "ERNIE" --sources praw --days 7 --replace-more-limit None
```

说明：
- 只抓取 Reddit PRAW
- 只获取最近 7 天
- 不展开 "更多评论"（只获取已加载的评论）
- 速度快，适合快速获取最新动态

### 场景 4: 深度抓取（获取所有评论）

```bash
python3 fetch_all.py \
  --query "ChatGPT" \
  --reddit-mode subreddits \
  --sources praw selenium \
  --max-pages 100 \
  --replace-more-limit 0
```

说明：
- 使用子版块搜索模式
- 使用 PRAW 和 Selenium 双重抓取
- Selenium 每个子版块滚动 100 次
- PRAW 展开所有评论
- 获取最完整的数据，但耗时较长

### 场景 5: 只抓取 HuggingFace 模型讨论

```bash
python3 fetch_all.py --query "ERNIE-4.5" --sources huggingface --days 30
```

说明：
- 只抓取 HuggingFace
- 搜索模型 "ERNIE-4.5"
- 只获取最近 30 天

### 场景 6: 抓取并自动导出

```bash
python3 fetch_all.py --query "ERNIE" --sources praw --days 7 --export --export-format excel
```

说明：
- 抓取完成后自动导出为 Excel
- 文件保存在 `./data/exports/` 目录

### 场景 7: 小众话题 + Selenium 全局搜索

```bash
python3 fetch_all.py \
  --query "PaddleOCR-VL" \
  --reddit-mode global \
  --sources selenium \
  --max-pages 100 \
  --days 365
```

说明：
- 使用全局搜索模式
- 只使用 Selenium（需要 cookies.json）
- 全局搜索页面滚动 100 次
- 获取最近一年的数据
- 适合小众话题，确保不遗漏任何讨论

### 场景 8: 定期抓取（Cron Job）

创建脚本 `daily_fetch.sh`：

```bash
#!/bin/bash
cd /path/to/DiscussionFetcher_v2.0
python3 fetch_all.py --query "ERNIE" --sources praw --days 1 --export
```

添加到 crontab：

```bash
# 每天凌晨 2 点抓取昨天的数据
0 2 * * * /path/to/daily_fetch.sh >> /path/to/logs/fetch.log 2>&1
```

---

## 🔍 高级用法

### 组合多个参数

```bash
# 抓取 PaddleOCR-VL 最近 30 天的数据，使用全局搜索 + PRAW + Selenium，展开所有评论，导出为 Excel
python3 fetch_all.py \
  --query "PaddleOCR-VL" \
  --reddit-mode global \
  --sources praw selenium \
  --days 30 \
  --replace-more-limit 0 \
  --max-pages 100 \
  --export \
  --export-format excel
```

### 使用环境变量覆盖配置

```bash
# 临时使用不同的 Reddit 凭证
REDDIT_CLIENT_ID=xxx REDDIT_CLIENT_SECRET=yyy python3 fetch_all.py
```

### 调试模式

查看详细日志输出（所有 fetcher 默认 `verbose=True`）：

```bash
python3 fetch_all.py --sources praw 2>&1 | tee fetch.log
```

---

## ❓ 常见问题

### Q1: 如何指定搜索关键词？

A: 使用 `--query` 参数：

```bash
python3 fetch_all.py --query "你的关键词"
```

### Q2: 为什么评论只抓取了很少？

A: 可能的原因和解决方案：

1. **PRAW 的 replace_more_limit 太小**
   ```bash
   # 确保设置为 0 以展开所有评论
   python3 fetch_all.py --replace-more-limit 0
   ```

2. **Selenium 的 max_pages 太小**
   ```bash
   # 增加滚动次数
   python3 fetch_all.py --sources selenium --max-pages 100
   ```

3. **时间范围太短**
   ```bash
   # 不设置 --days 参数，获取全部历史数据
   python3 fetch_all.py
   ```

### Q3: 如何区分 Reddit 全局搜索和子版块搜索？

A: 使用 `--reddit-mode` 参数：

```bash
# 子版块搜索（默认）- 在9个AI相关版块中搜索
python3 fetch_all.py --query "ERNIE" --reddit-mode subreddits

# 全局搜索 - 搜索整个Reddit
python3 fetch_all.py --query "PaddleOCR-VL" --reddit-mode global
```

**什么时候使用全局搜索？**
- 小众话题（如 PaddleOCR-VL）
- 新兴技术或产品
- 跨领域讨论

**什么时候使用子版块搜索？**
- 热门AI话题（如 ERNIE、ChatGPT）
- 需要更精准、AI相关性高的结果
- 减少无关噪音

**也可以通过 Web 界面选择：**
访问 http://localhost:5000，在 "Reddit 搜索方式" 中选择。

### Q4: cookies.json 在哪里？如何获取？

A: Selenium 需要 cookies 文件来登录 Reddit。获取方法：

```bash
# 查看详细指南
python3 -m src.reddit_comments_selenium guide
```

简要步骤：
1. 安装浏览器扩展（如 EditThisCookie）
2. 登录 Reddit
3. 导出 cookies 为 JSON 格式
4. 保存为 `cookies.json`

### Q5: 如何导出数据？

A: 有两种方式：

1. **命令行自动导出**
   ```bash
   python3 fetch_all.py --export --export-format excel
   ```

2. **使用数据库管理脚本**
   ```bash
   python3 db_manager.py --export-csv
   python3 db_manager.py --export-excel
   ```

### Q6: 数据库在哪里？

A: SQLite 数据库位于：

```
./data/discussions.db
```

可以使用任何 SQLite 客户端查看，或使用：

```bash
python3 db_manager.py --stats
```

### Q7: 如何查看抓取进度？

A: 有两种方式：

1. **命令行**: 默认会显示详细日志
   ```bash
   python3 fetch_all.py  # 自动显示进度
   ```

2. **Web 界面**: 访问 http://localhost:5000
   ```bash
   python3 web_server.py
   ```

### Q8: 抓取速度太慢怎么办？

A: 优化建议：

1. **只抓取必要的数据源**
   ```bash
   python3 fetch_all.py --sources praw  # 只用 PRAW，速度最快
   ```

2. **限制时间范围**
   ```bash
   python3 fetch_all.py --days 7  # 只抓取最近 7 天
   ```

3. **减少评论展开次数**
   ```bash
   python3 fetch_all.py --replace-more-limit 10  # 只展开 10 次
   ```

4. **并行抓取（需要修改代码）**
   - 目前暂不支持，计划在后续版本添加

### Q9: 如何避免重复数据？

A: 系统自动处理重复：

- **入库时**: 使用 `UNIQUE` 约束自动去重（基于 platform + platform_id）
- **导出时**: 可以选择去重导出（保留最新的 fetched_at）

```bash
# 数据库自动去重，无需手动处理
python3 fetch_all.py
```

### Q10: Reddit API 限制怎么办？

A: Reddit API 有速率限制（60 请求/分钟）：

1. **系统自动处理**: 内置了 rate limiter
2. **如果仍然遇到限制**:
   - 减少 `--replace-more-limit`
   - 使用 `--days` 限制时间范围
   - 分批次抓取

---

## 📚 相关文档

- [主 README](README.md) - 项目概览
- [Web 界面使用](README.md#web-界面) - Web 界面文档
- [Twitter 导入指南](TWITTER_IMPORT_GUIDE.md) - 如何导入 Twitter CSV
- [数据库 Schema](src/database.py) - 数据库结构

---

## 📞 获取帮助

如遇到问题：

1. **查看帮助信息**
   ```bash
   python3 fetch_all.py --help
   ```

2. **查看日志**
   ```bash
   python3 fetch_all.py 2>&1 | tee fetch.log
   ```

3. **提交 Issue** (如果是 bug)

---

## 🎓 最佳实践

### 1. 首次使用

```bash
# 先测试小范围
python3 fetch_all.py --sources praw --days 1 --replace-more-limit 10

# 确认正常后，再全量抓取
python3 fetch_all.py --sources all
```

### 2. 定期更新

```bash
# 每天抓取最新数据（增量更新）
python3 fetch_all.py --sources praw --days 1 --export
```

### 3. 数据备份

```bash
# 定期备份数据库
cp ./data/discussions.db ./data/backups/discussions_$(date +%Y%m%d).db

# 或导出为文件
python3 db_manager.py --export-excel --output ./backups/data_$(date +%Y%m%d).xlsx
```

### 4. 监控和告警

```bash
# 结合 cron 和邮件通知
python3 fetch_all.py --sources praw --days 1 || echo "Fetch failed" | mail -s "Alert" admin@example.com
```

---

**最后更新**: 2025-11-15
**版本**: 2.0
