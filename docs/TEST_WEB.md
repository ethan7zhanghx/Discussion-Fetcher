# Web 界面测试指南

## 快速测试

### 1. 启动服务器

```bash
./start.sh
```

或者手动启动：

```bash
pip install -r requirements.txt
python3 web_server.py
```

### 2. 访问界面

打开浏览器访问：

```
http://127.0.0.1:5000
```

### 3. 测试功能

#### ✅ 查看统计

- 页面加载后应该自动显示统计数据
- 如果数据库为空，所有统计应显示 0

#### ✅ 测试抓取（无 cookies）

1. 取消勾选"获取 Reddit 评论"
2. 勾选 Reddit 和 HuggingFace
3. 输入关键词：ERNIE
4. 点击"开始抓取"
5. 应该看到：
   - 按钮变为"抓取中..."
   - 显示进度信息
   - 抓取完成后更新统计

#### ✅ 测试搜索

1. 在搜索框输入关键词（例如：ERNIE）
2. 点击"搜索"
3. 应该显示包含关键词的讨论

#### ✅ 测试筛选

1. 使用平台筛选器（Reddit / HuggingFace）
2. 使用类型筛选器（Post / Comment）
3. 点击"刷新"
4. 讨论列表应该更新

#### ✅ 测试分页

1. 点击"下一页"
2. 应该加载下一页数据
3. 点击"上一页"返回

#### ✅ 测试导出

1. 选择导出格式（CSV / Excel）
2. 选择平台筛选（可选）
3. 点击"导出数据"
4. 应该自动下载文件

## 测试 Reddit 评论（需要 cookies）

### 1. 准备 Cookies

```bash
# 查看导出指南
python3 -m src.reddit_comments guide

# 按照指南导出 cookies 并保存为 cookies.json
```

### 2. 验证 Cookies

刷新页面，应该看到：

```
✅ cookies.json 已找到
```

### 3. 测试抓取评论

1. 勾选"获取 Reddit 评论"
2. 点击"开始抓取"
3. 应该同时获取 Posts 和 Comments

## API 测试

### 测试统计 API

```bash
curl http://127.0.0.1:5000/api/stats
```

预期输出：

```json
{
  "success": true,
  "data": {
    "total": 0,
    "platforms": {},
    "content_types": {},
    "last_update": null
  }
}
```

### 测试讨论列表 API

```bash
curl http://127.0.0.1:5000/api/discussions?limit=10
```

### 测试搜索 API

```bash
curl http://127.0.0.1:5000/api/search?keyword=ERNIE
```

### 测试抓取 API

```bash
curl -X POST http://127.0.0.1:5000/api/fetch/start \
  -H "Content-Type: application/json" \
  -d '{
    "platforms": ["reddit"],
    "query": "ERNIE",
    "include_comments": false
  }'
```

### 测试抓取状态 API

```bash
curl http://127.0.0.1:5000/api/fetch/status
```

## 常见问题排查

### 问题 1: 页面无法访问

```bash
# 检查服务器是否启动
ps aux | grep web_server

# 检查端口是否被占用
lsof -i :5000

# 查看服务器日志
tail -f logs/web_server.log
```

### 问题 2: 抓取失败

```bash
# 检查 API 凭证
cat .env

# 测试 Reddit API
python3 -c "from src.reddit import RedditFetcher; f = RedditFetcher(); print('OK')"

# 测试 HuggingFace
python3 -c "from src.huggingface import HuggingFaceFetcher; f = HuggingFaceFetcher(); print('OK')"
```

### 问题 3: Cookies 不工作

```bash
# 检查 cookies 文件
cat cookies.json

# 测试 cookies
python3 -m src.reddit_comments
```

### 问题 4: 数据库错误

```bash
# 检查数据库文件
ls -lh data/discussions.db

# 测试数据库连接
python3 -c "from src.database import DatabaseManager; db = DatabaseManager(); print(db.get_stats())"

# 如果损坏，重建数据库
rm data/discussions.db
python3 web_server.py
```

## 性能测试

### 并发测试

```bash
# 使用 ab (Apache Bench) 测试
ab -n 100 -c 10 http://127.0.0.1:5000/api/stats

# 使用 curl 批量测试
for i in {1..10}; do
  curl http://127.0.0.1:5000/api/discussions &
done
wait
```

### 大数据量测试

```bash
# 导入测试数据（如果有旧数据库）
python3 -c "from src.database import DatabaseManager; db = DatabaseManager(); db.migrate_from_old_database('old_data.db')"

# 测试分页性能
curl "http://127.0.0.1:5000/api/discussions?limit=100&offset=0"
curl "http://127.0.0.1:5000/api/discussions?limit=100&offset=100"
```

## 浏览器兼容性

测试的浏览器：

- ✅ Chrome 120+
- ✅ Firefox 120+
- ✅ Safari 17+
- ✅ Edge 120+

## 移动端测试

使用浏览器开发者工具：

1. 打开开发者工具（F12）
2. 切换到移动设备模拟模式
3. 测试以下设备：
   - iPhone SE (375x667)
   - iPhone 12 Pro (390x844)
   - iPad (768x1024)

## 自动化测试脚本

```bash
#!/bin/bash
# test_web.sh - 自动化测试脚本

BASE_URL="http://127.0.0.1:5000"

echo "1. 测试首页..."
curl -s $BASE_URL > /dev/null && echo "✓ 首页正常" || echo "✗ 首页失败"

echo "2. 测试统计 API..."
curl -s $BASE_URL/api/stats | grep -q "success" && echo "✓ 统计 API 正常" || echo "✗ 统计 API 失败"

echo "3. 测试讨论 API..."
curl -s $BASE_URL/api/discussions?limit=1 | grep -q "success" && echo "✓ 讨论 API 正常" || echo "✗ 讨论 API 失败"

echo "4. 测试 Cookies 检查..."
curl -s $BASE_URL/api/cookies/check | grep -q "exists" && echo "✓ Cookies API 正常" || echo "✗ Cookies API 失败"

echo ""
echo "测试完成！"
```

保存为 `test_web.sh`，然后运行：

```bash
chmod +x test_web.sh
./test_web.sh
```

## 成功标准

所有测试通过的标志：

- ✅ 服务器成功启动
- ✅ 页面正常加载
- ✅ 统计数据正确显示
- ✅ 抓取功能正常工作
- ✅ 搜索和筛选正常
- ✅ 分页功能正常
- ✅ 数据导出成功
- ✅ 所有 API 返回正确格式
- ✅ 无 JavaScript 错误（查看浏览器控制台）
- ✅ 无 Python 错误（查看服务器日志）
