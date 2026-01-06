# Web 界面使用指南

## 快速启动

### 方式 1: 使用启动脚本（推荐）

```bash
./start.sh
```

启动脚本会自动：
- ✅ 检查 Python 环境
- ✅ 创建并激活虚拟环境
- ✅ 安装依赖包
- ✅ 检查配置文件
- ✅ 启动 Web 服务器

### 方式 2: 手动启动

```bash
# 1. 安装依赖（首次使用）
pip install -r requirements.txt

# 2. 启动服务器
python3 web_server.py
```

## 访问界面

启动后，在浏览器中访问：

```
http://127.0.0.1:5000
```

## 功能说明

### 📊 统计面板

实时显示：
- 总讨论数
- Reddit 数据量
- HuggingFace 数据量
- 最后更新时间

### 🚀 抓取数据

**配置选项：**
- 选择平台（Reddit / HuggingFace）
- 搜索关键词（默认: ERNIE）
- 是否获取 Reddit 评论（需要 cookies.json）

**使用步骤：**
1. 选择要抓取的平台
2. 输入搜索关键词
3. （可选）勾选"获取 Reddit 评论"
4. 点击"开始抓取"
5. 等待抓取完成

**注意：**
- 抓取任务在后台运行
- 可以实时查看进度
- 抓取完成后数据会自动保存到数据库

### 💾 导出数据

**支持格式：**
- CSV
- Excel

**筛选选项：**
- 导出全部数据
- 仅导出 Reddit 数据
- 仅导出 HuggingFace 数据

**使用：**
1. 选择导出格式
2. 选择平台筛选
3. 点击"导出数据"
4. 浏览器会自动下载文件

### 🔍 搜索讨论

**功能：**
- 搜索标题或内容中的关键词
- 实时显示搜索结果

**使用：**
1. 在搜索框中输入关键词
2. 点击"搜索"或按回车键
3. 查看搜索结果

### 📝 讨论列表

**显示内容：**
- 讨论标题
- 平台标识（Reddit / HuggingFace）
- 内容类型（Post / Comment / Discussion）
- 作者
- 评分
- 创建时间
- 内容预览

**筛选功能：**
- 按平台筛选
- 按内容类型筛选
- 分页浏览

**操作：**
- 点击"查看原文"跳转到原始链接
- 使用筛选器快速定位数据
- 翻页浏览更多内容

## 获取 Reddit 评论

如果需要获取 Reddit 评论，需要先导出 cookies：

### 1. 导出 Cookies

```bash
# 查看详细指南
python3 -m src.reddit_comments guide
```

### 2. 保存 Cookies

将导出的 cookies 保存为 `cookies.json` 文件到项目根目录。

### 3. 验证

重新加载 Web 界面，如果看到：
```
✅ cookies.json 已找到
```

则可以勾选"获取 Reddit 评论"选项。

## API 接口

Web 服务器提供了 RESTful API，可以用于自动化或集成：

### 统计数据

```bash
GET /api/stats
```

### 获取讨论列表

```bash
GET /api/discussions?platform=reddit&limit=100
```

### 搜索讨论

```bash
GET /api/search?keyword=ERNIE
```

### 开始抓取

```bash
POST /api/fetch/start
Content-Type: application/json

{
  "platforms": ["reddit", "huggingface"],
  "query": "ERNIE",
  "include_comments": false
}
```

### 抓取状态

```bash
GET /api/fetch/status
```

### 导出数据

```bash
GET /api/export?format=csv&platform=reddit
```

## 常见问题

### Q: Web 界面无法访问？

A: 检查：
1. 服务器是否正常启动
2. 端口 5000 是否被占用
3. 防火墙设置

### Q: 抓取任务失败？

A: 可能原因：
1. API 凭证未配置（检查 .env）
2. Cookies 过期（重新导出）
3. 网络连接问题
4. API 限流

### Q: 数据导出失败？

A: 确保：
1. 数据库中有数据
2. 有写入权限（data/exports 目录）
3. 磁盘空间充足

### Q: 如何停止服务器？

A: 在终端中按 `Ctrl+C`

### Q: 如何更改端口？

A: 编辑 `web_server.py`，修改最后一行：
```python
app.run(host='0.0.0.0', port=5000, debug=True)  # 改为你想要的端口
```

## 界面预览

### 主界面功能

```
┌─────────────────────────────────────────────┐
│  📊 DiscussionFetcher                       │
│  Reddit & HuggingFace 讨论数据抓取系统       │
├─────────────────────────────────────────────┤
│  [统计面板]                                  │
│  总数 | Reddit | HuggingFace | 最后更新      │
├─────────────────────────────────────────────┤
│  [抓取数据]          [导出数据]              │
│  ☑ Reddit           格式: [CSV ▼]           │
│  ☑ HuggingFace      平台: [全部 ▼]          │
│  关键词: [ERNIE]    [导出数据]              │
│  ☐ 获取评论                                 │
│  [开始抓取]                                 │
├─────────────────────────────────────────────┤
│  [搜索讨论]                                  │
│  [搜索框..................] [搜索]           │
├─────────────────────────────────────────────┤
│  [最近讨论]                                  │
│  平台: [全部 ▼] 类型: [全部 ▼] [刷新]       │
│  ┌──────────────────────────────┐           │
│  │ 讨论项 1                      │           │
│  │ 讨论项 2                      │           │
│  │ ...                           │           │
│  └──────────────────────────────┘           │
│  [上一页] 第 1 页 [下一页]                   │
└─────────────────────────────────────────────┘
```

## 技术栈

- **后端**: Flask (Python)
- **前端**: HTML5 + CSS3 + Vanilla JavaScript
- **数据库**: SQLite
- **API**: RESTful

## 性能优化

- 自动刷新统计（每 30 秒）
- 后台任务处理（抓取不阻塞界面）
- 分页加载（避免一次加载大量数据）
- 响应式设计（支持移动端）

## 安全建议

1. **不要暴露到公网**：默认绑定 0.0.0.0，仅用于本地开发
2. **保护 cookies.json**：已在 .gitignore 中排除
3. **定期更新依赖**：`pip install --upgrade -r requirements.txt`

## 进阶使用

### 定时抓取

使用 cron 或系统定时任务调用 API：

```bash
# 每天凌晨 2 点抓取
0 2 * * * curl -X POST http://127.0.0.1:5000/api/fetch/start \
  -H "Content-Type: application/json" \
  -d '{"platforms": ["reddit", "huggingface"], "query": "ERNIE"}'
```

### 集成到其他系统

Web 服务器提供标准 REST API，可以集成到：
- 数据分析工作流
- 自动化脚本
- 监控系统
- 数据仪表板

## 故障排除

### 日志查看

服务器日志会显示在终端，包括：
- 请求记录
- 错误信息
- 抓取进度

### 数据库问题

如果数据库损坏，可以重建：

```bash
rm data/discussions.db
# 重新启动服务器会自动创建新数据库
```

### 依赖问题

如果遇到依赖冲突：

```bash
# 删除虚拟环境
rm -rf venv

# 重新运行 start.sh
./start.sh
```

## 更新日志

### v2.0 (当前版本)

- ✅ 添加 Web 界面
- ✅ 支持在线抓取数据
- ✅ 实时查看统计
- ✅ 在线搜索和筛选
- ✅ 一键导出数据
- ✅ 后台任务处理
- ✅ 响应式设计

## 反馈与支持

如有问题或建议，请提交 Issue 或 Pull Request。
