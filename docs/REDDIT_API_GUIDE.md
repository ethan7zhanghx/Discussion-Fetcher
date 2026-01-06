# Reddit API 凭证获取指南

## 📋 前提条件

- 一个 Reddit 账号（如果没有，先注册一个：https://www.reddit.com/register）
- 已登录 Reddit

## 🚀 获取步骤（5分钟）

### 第一步：访问 Reddit Apps 页面

1. 登录 Reddit
2. 访问：https://www.reddit.com/prefs/apps
   - 或者：Reddit 首页 → 右上角头像 → User Settings → Safety & Privacy → Authorized Applications

### 第二步：创建应用

1. 在页面底部找到 **"are you a developer? create an app..."** 按钮
2. 点击 **"create app"** 或 **"create another app"**

### 第三步：填写应用信息

填写以下信息：

| 字段 | 填写内容 | 说明 |
|------|---------|------|
| **name** | `DiscussionFetcher` | 应用名称（随意填写） |
| **App type** | ✅ **script** | ⚠️ 必须选择这个！ |
| **description** | `Fetch ERNIE discussions` | 描述（可选） |
| **about url** | 留空 | 不需要填写 |
| **permissions** | 默认 | 不需要修改 |
| **redirect uri** | `http://localhost:8080` | 必须填写一个URL |

**重要提示**：
- ⚠️ **App type** 必须选择 **script**（不是 web app）
- redirect uri 随便填一个本地地址即可（如 `http://localhost:8080`）

### 第四步：创建应用

点击 **"create app"** 按钮

### 第五步：获取凭证

创建成功后，你会看到应用信息：

```
DiscussionFetcher                    [edit] [delete]
personal use script by your_username

(一串随机字符，这是你的 client_id)
⬆️ 这个就是 client_id

secret: (另一串随机字符)
       ⬆️ 这个就是 client_secret
```

**获取的信息**：
- **client_id**：在应用名称下方的一串字符（大约14个字符）
- **client_secret**：在 "secret:" 后面的字符串（大约27个字符）

### 第六步：保存凭证

在项目根目录创建 `.env` 文件：

```bash
# 方式1：使用命令行
cd /Users/zhanghaoxin/Desktop/Baidu/DiscussionFetcher_v2.0

cat > .env << 'EOF'
# Reddit API 凭证
REDDIT_CLIENT_ID=你的_client_id_这里粘贴
REDDIT_CLIENT_SECRET=你的_client_secret_这里粘贴
REDDIT_USER_AGENT=DiscussionFetcher/2.0

# HuggingFace Token（可选，如果没有可以不填）
HUGGINGFACE_TOKEN=
EOF

# 方式2：手动创建
# 创建文件 .env，内容如下：
```

**`.env` 文件示例**：

```env
# Reddit API 凭证
REDDIT_CLIENT_ID=abcdefghijklmn
REDDIT_CLIENT_SECRET=xyzabcdefghijklmnopqrstuv
REDDIT_USER_AGENT=DiscussionFetcher/2.0

# HuggingFace Token（可选）
HUGGINGFACE_TOKEN=
```

### 第七步：验证配置

运行测试命令：

```bash
python3 -c "
from src.config import Config
config = Config()
print('✓ 配置加载成功！')
print(f'Client ID: {config.REDDIT_CLIENT_ID[:5]}...')
print(f'Client Secret: {config.REDDIT_CLIENT_SECRET[:5]}...')
"
```

如果看到类似输出，说明配置成功：
```
✓ 配置加载成功！
Client ID: abcde...
Client Secret: xyzab...
```

---

## 🎯 完整流程图解

```
1. 访问 https://www.reddit.com/prefs/apps
   ↓
2. 点击 "create app" 或 "create another app"
   ↓
3. 填写信息：
   - name: DiscussionFetcher
   - type: ✅ script  ⚠️ 必须选这个
   - redirect uri: http://localhost:8080
   ↓
4. 点击 "create app"
   ↓
5. 复制凭证：
   - client_id: 应用名称下方的字符串
   - client_secret: "secret:" 后面的字符串
   ↓
6. 创建 .env 文件，粘贴凭证
   ↓
7. 运行 python3 fetch_all.py
```

---

## 📸 图文说明

### 1. Reddit Apps 页面

访问 https://www.reddit.com/prefs/apps，页面底部有：

```
are you a developer? create an app...

[create app] [create another app]
```

点击其中一个按钮。

### 2. 创建应用表单

```
┌─────────────────────────────────────────┐
│ name: [DiscussionFetcher          ]    │
│                                         │
│ App type:                               │
│ ○ web app                               │
│ ● script           ⬅️ 选择这个           │
│ ○ installed app                         │
│                                         │
│ description:                            │
│ [Fetch ERNIE discussions          ]    │
│                                         │
│ about url:                              │
│ [                                  ]    │
│                                         │
│ redirect uri:                           │
│ [http://localhost:8080            ]    │
│                                         │
│           [create app]                  │
└─────────────────────────────────────────┘
```

### 3. 创建成功后的页面

```
┌─────────────────────────────────────────┐
│ DiscussionFetcher     [edit] [delete]  │
│ personal use script by your_username    │
│                                         │
│ abcdefghijklmn     ⬅️ 这是 client_id    │
│                                         │
│ secret: xyzabcdefghijklmnopqrstuv      │
│         ⬆️ 这是 client_secret            │
│                                         │
│ redirect uri: http://localhost:8080    │
└─────────────────────────────────────────┘
```

---

## ⚠️ 常见问题

### Q1: 找不到 "create app" 按钮？

**解决**：
1. 确保已经登录 Reddit
2. 滚动到页面最底部
3. 如果还是找不到，直接访问：https://old.reddit.com/prefs/apps

### Q2: App type 选错了怎么办？

**解决**：
1. 点击应用旁边的 [delete] 删除
2. 重新创建，确保选择 **script**

### Q3: client_id 和 client_secret 在哪里？

**client_id**：
- 位置：应用名称正下方的一串字符
- 长度：约14个字符
- 格式：类似 `abcdefghijklmn`

**client_secret**：
- 位置："secret:" 后面的字符串
- 长度：约27个字符
- 格式：类似 `xyzabcdefghijklmnopqrstuv-_`

### Q4: .env 文件放在哪里？

放在项目根目录：
```
DiscussionFetcher_v2.0/
├── .env                  ⬅️ 放这里
├── fetch_all.py
├── src/
└── ...
```

**检查方法**：
```bash
cd /Users/zhanghaoxin/Desktop/Baidu/DiscussionFetcher_v2.0
ls -la .env
```

如果提示 "No such file"，说明文件不存在或位置不对。

### Q5: 凭证会过期吗？

**不会过期**（除非你删除应用或修改密码）

但如果出现认证失败：
1. 检查凭证是否复制正确
2. 检查 .env 文件格式是否正确（没有多余空格）
3. 重新生成凭证（删除旧应用，创建新应用）

---

## 🔒 安全提示

1. **不要分享你的凭证**
   - client_id 和 client_secret 是敏感信息
   - 不要提交到 Git 仓库
   - 不要截图或公开分享

2. **添加到 .gitignore**
   ```bash
   echo ".env" >> .gitignore
   ```

3. **如果泄露了怎么办？**
   - 访问 https://www.reddit.com/prefs/apps
   - 点击应用旁边的 [delete]
   - 重新创建新应用

---

## ✅ 验证是否配置成功

运行完整测试：

```bash
cd /Users/zhanghaoxin/Desktop/Baidu/DiscussionFetcher_v2.0

python3 -c "
from src.reddit import RedditFetcher
from src.models import ContentType

print('测试 Reddit API 连接...\n')

try:
    fetcher = RedditFetcher(verbose=True)

    # 测试获取1个post和评论
    discussions = fetcher.fetch(
        query='Python',
        fetch_comments=True,
        limit=1
    )

    posts = [d for d in discussions if d.content_type == ContentType.POST]
    comments = [d for d in discussions if d.content_type == ContentType.COMMENT]

    print(f'\n✅ 测试成功！')
    print(f'Posts: {len(posts)} 条')
    print(f'Comments: {len(comments)} 条')
    print(f'\n配置正确，可以正常使用！')

except Exception as e:
    print(f'\n❌ 测试失败: {e}')
    print('\n请检查：')
    print('1. .env 文件是否在项目根目录')
    print('2. client_id 和 client_secret 是否正确')
    print('3. App type 是否选择了 script')
"
```

---

## 📚 相关链接

- **Reddit Apps 管理页面**：https://www.reddit.com/prefs/apps
- **Reddit API 文档**：https://www.reddit.com/dev/api
- **PRAW 文档**：https://praw.readthedocs.io/

---

## 🎉 下一步

配置成功后，就可以运行完整抓取了：

```bash
# 基础抓取（Posts + Post评论）
python3 fetch_all.py

# 完整抓取（Posts + Post评论 + 搜索页面评论）
python3 fetch_all.py --reddit-comments
```

祝使用愉快！🚀
