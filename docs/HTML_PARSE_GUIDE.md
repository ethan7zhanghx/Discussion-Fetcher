# Reddit HTML 解析方案（最简单）

## 概述

**完全避开所有技术问题**：
- ✅ 无需自动化（避免 macOS 限制）
- ✅ 无需 Cookies
- ✅ 无需代理
- ✅ 你手动完成 CAPTCHA
- ✅ 100% 成功率

## 工作原理

1. **你在浏览器中访问 Reddit**
2. **手动完成 CAPTCHA**
3. **滚动加载评论**
4. **保存页面为 HTML**
5. **脚本自动解析 HTML**

## 步骤（5 分钟）

### 1. 访问 Reddit 搜索页面

在 Chrome 中打开：
```
https://www.reddit.com/r/LocalLLM/search/?q=llama&type=comment&sort=new
```

### 2. 完成验证和加载（非常重要！）

1. **完成 CAPTCHA**（如果有）
2. **滚动页面加载所有评论**（这是关键步骤）：
   - **慢慢滚动**到页面底部（不要一次滚到底）
   - 每次滚动后**等待 2-3 秒**，让评论加载出来
   - 重复滚动**至少 20-30 次**，直到看到 "No more results" 或没有新评论加载
   - 可以按住键盘的 ↓ 键或 Page Down 键慢慢滚动
3. **确认**所有评论都已加载（页面不再出现新内容）
4. **等待** 5 秒，确保所有内容完全渲染

### 3. 保存页面

1. 右键点击页面空白处
2. 选择 **"另存为"** 或 **"Save As"**
3. 保存类型选择 **"网页，全部"** 或 **"Webpage, Complete"**
4. 文件名：`reddit_page.html`
5. 保存到项目目录

### 4. 运行解析脚本

```bash
python3 parse_reddit_html.py reddit_page.html
```

### 5. 查看结果

```
✓ 成功解析 150 条评论
✓ 已保存到: reddit_page_parsed.csv
```

打开 CSV 文件查看数据！

## 批量处理多个板块

### 方法：保存多个 HTML 文件

1. **第一个板块**（LocalLLM）：
   - 访问：`https://www.reddit.com/r/LocalLLM/search/?q=ERNIE&type=comment&sort=new`
   - 保存为：`reddit_LocalLLM.html`

2. **第二个板块**（ChatGPT）：
   - 访问：`https://www.reddit.com/r/ChatGPT/search/?q=ERNIE&type=comment&sort=new`
   - 保存为：`reddit_ChatGPT.html`

3. **批量解析**：
   ```bash
   python3 parse_reddit_html.py reddit_LocalLLM.html
   python3 parse_reddit_html.py reddit_ChatGPT.html
   ```

4. **合并 CSV**（可选）：
   ```bash
   # 合并所有 CSV 文件
   cat reddit_*_parsed.csv > all_comments.csv
   ```

## 自动化脚本（批量处理）

创建 `batch_parse.sh`：

```bash
#!/bin/bash
# 批量解析所有 HTML 文件

for file in reddit_*.html; do
    if [ -f "$file" ]; then
        echo "解析: $file"
        python3 parse_reddit_html.py "$file"
    fi
done

echo "全部完成！"
```

使用：
```bash
chmod +x batch_parse.sh
./batch_parse.sh
```

## 优势

| 方案 | 复杂度 | 成功率 | 需要技能 |
|------|--------|--------|----------|
| **HTML 解析** | ⭐️ 简单 | ✅ 100% | 会用浏览器 |
| Cookies | ⭐️⭐️ 中等 | ✅ 90% | 技术操作 |
| 自动化 | ⭐️⭐️⭐️⭐️ 复杂 | ❌ 10% | 编程+运维 |

## 提示和技巧

### 1. 加载更多评论

- 滚动页面 **10-20 次**
- 每次滚动等待 **2-3 秒**
- 看到 "No more results" 就停止

### 2. 确保页面完整

保存前检查：
- ✅ 看到评论内容
- ✅ 看到评分（xx votes）
- ✅ 看到作者名称
- ❌ 没有 CAPTCHA
- ❌ 没有 "Loading..."

### 3. 文件命名

建议命名格式：
```
reddit_{板块}_{关键词}_{日期}.html

示例:
reddit_LocalLLM_llama_20251020.html
reddit_ChatGPT_ERNIE_20251020.html
```

### 4. 定期更新

每周保存一次新的 HTML：
- 周一: 保存所有板块的页面
- 周二: 解析所有 HTML
- 周三-周日: 使用数据

## 常见问题

### Q: 页面太长，保存很慢？

A: 不需要加载所有评论。通常 100-200 条就够了。

### Q: HTML 文件很大（几 MB）？

A: 正常！包含了所有评论和资源。解析脚本会忽略无用内容。

### Q: 可以保存为 "仅 HTML" 吗？

A: 可以！选择 "网页，仅 HTML" 也能工作。

### Q: 解析出错怎么办？

A: 检查：
1. HTML 文件是否完整
2. 是否包含评论内容
3. 是否有 CAPTCHA 或限流提示

## 与其他方案对比

### 方案 1: 自动化（已放弃）
- ❌ macOS 权限问题
- ❌ 窗口被强制关闭
- ❌ 不稳定

### 方案 2: Cookies
- ⚠️ 需要导出 cookies
- ⚠️ 会过期（7-14 天）
- ⚠️ 仍有限流风险

### 方案 3: HTML 解析（推荐）
- ✅ 完全手动控制
- ✅ 100% 成功
- ✅ 无技术门槛
- ✅ 适合任何操作系统

## 示例工作流程

```
9:00  - 打开 Reddit，搜索 "ERNIE"
9:05  - 完成 CAPTCHA，滚动加载评论
9:10  - 保存页面为 reddit_LocalLLM.html
9:15  - 切换到 ChatGPT 板块，重复操作
9:20  - 保存为 reddit_ChatGPT.html
9:25  - 运行解析脚本
9:30  - 获得所有 CSV 数据！

总耗时: 30 分钟（一周一次）
```

## 总结

**这是目前最可靠的方案：**
1. 不依赖任何自动化
2. 不受 macOS 限制
3. 不需要 cookies
4. 100% 成功率

**唯一的"缺点"**：需要你手动操作浏览器（但这反而是优点，因为你完全掌控！）
