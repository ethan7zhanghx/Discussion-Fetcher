# 🛠️ Scripts and Tools

Utility scripts and analysis tools for DiscussionFetcher v2.0

---

## 📊 Analysis Scripts

### Relevance Analysis
- **`analyze_relevance.py`** - 分析讨论内容与关键词的相关性
- **`analyze_relevance_v2.py`** - 相关性分析增强版
- **`add_value_analysis.py`** - 价值分析脚本

### Usage
```bash
# Run relevance analysis
python3 scripts/analyze_relevance_v2.py

# Run value analysis
python3 scripts/add_value_analysis.py
```

---

## 🧪 Test Scripts

### API Testing
- **`test_reddit_json_api.py`** - 测试 Reddit JSON API
- **`test_analyze.py`** - 测试分析功能

### Usage
```bash
# Test Reddit API
python3 scripts/test_reddit_json_api.py

# Test analysis
python3 scripts/test_analyze.py
```

---

## 🔧 Utility Scripts

### Data Migration
- **`migrate_add_keywords.py`** - 为现有数据添加关键词字段
- **`update_twitter_keywords.py`** - 更新 Twitter 数据的关键词标签

### HTML Parsing (Legacy)
- **`parse_reddit_html.py`** - 旧版 HTML 解析脚本（已被 Selenium 替代）

### Usage
```bash
# Migrate database to add keywords column
python3 scripts/migrate_add_keywords.py

# Update Twitter keywords
python3 scripts/update_twitter_keywords.py
```

---

## 📝 Notes

- These scripts are **utilities and tests**, not part of the main workflow
- Most users don't need to run these scripts
- Use at your own risk - some scripts may modify the database

---

返回 [项目主页](../README.md)
