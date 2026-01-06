# 数据库使用

## 数据位置

`./data/discussions.db` - SQLite 数据库，所有数据自动保存在这里

## 查看数据

```bash
# 统计
python3 db_manager.py stats

# 查询最新 10 条
python3 db_manager.py query --limit 10

# 查询 Reddit
python3 db_manager.py query --platform reddit --limit 20

# 导出 Excel
python3 db_manager.py export --format excel --output data.xlsx

# 导出 CSV
python3 db_manager.py export --format csv --output data.csv
```

## Python API

```python
from src.database import DatabaseManager

db = DatabaseManager()

# 统计
stats = db.get_stats()
print(f"总计: {stats['total']} 条")

# 查询
df = db.get_discussions(platform='reddit', limit=100)

# 导出
db.export_to_excel('./data/export.xlsx')
```

## 自动去重

- 基于 ID 唯一
- 保留最新的 `fetched_at`
- 多次运行不会重复
