// DiscussionFetcher - Frontend JavaScript

const API_BASE = '/api';
let currentPage = 1;
const pageSize = 20;
let currentFilters = {
    platform: '',
    contentType: '',
    searchKeywords: ''
};

// 初始化
document.addEventListener('DOMContentLoaded', () => {
    loadStats();
    loadKeywords();
    loadDiscussions();
    checkCookies();
    setupEventListeners();
    startAutoRefresh();
});

// 设置事件监听器
function setupEventListeners() {
    // Reddit 平台选择变化时，显示/隐藏搜索方式选项
    document.getElementById('platform-reddit').addEventListener('change', (e) => {
        const redditModeGroup = document.getElementById('reddit-search-mode-group');
        redditModeGroup.style.display = e.target.checked ? 'block' : 'none';
    });

    // 抓取按钮
    document.getElementById('start-fetch-btn').addEventListener('click', startFetch);

    // 导出按钮
    document.getElementById('export-btn').addEventListener('click', exportData);

    // Twitter 导入
    const twitterFileInput = document.getElementById('twitter-csv-file');
    const importBtn = document.getElementById('import-twitter-btn');

    twitterFileInput.addEventListener('change', () => {
        importBtn.disabled = twitterFileInput.files.length === 0;
    });

    importBtn.addEventListener('click', importTwitterCSV);

    // 搜索按钮
    document.getElementById('search-btn').addEventListener('click', searchDiscussions);
    document.getElementById('search-input').addEventListener('keypress', (e) => {
        if (e.key === 'Enter') searchDiscussions();
    });

    // 筛选器
    document.getElementById('filter-platform').addEventListener('change', (e) => {
        currentFilters.platform = e.target.value;
        currentPage = 1;
        loadDiscussions();
    });

    document.getElementById('filter-type').addEventListener('change', (e) => {
        currentFilters.contentType = e.target.value;
        currentPage = 1;
        loadDiscussions();
    });

    document.getElementById('filter-keywords').addEventListener('change', (e) => {
        currentFilters.searchKeywords = e.target.value;
        currentPage = 1;
        loadDiscussions();
    });

    // 刷新按钮
    document.getElementById('refresh-btn').addEventListener('click', () => {
        loadStats();
        loadDiscussions();
    });

    // 分页
    document.getElementById('prev-page').addEventListener('click', () => {
        if (currentPage > 1) {
            currentPage--;
            loadDiscussions();
        }
    });

    document.getElementById('next-page').addEventListener('click', () => {
        currentPage++;
        loadDiscussions();
    });
}

// 加载统计数据
async function loadStats() {
    try {
        const response = await fetch(`${API_BASE}/stats`);
        const result = await response.json();

        if (result.success) {
            const data = result.data;

            document.getElementById('total-count').textContent = data.total || 0;
            document.getElementById('reddit-count').textContent = data.platforms?.reddit || 0;
            document.getElementById('huggingface-count').textContent = data.platforms?.huggingface || 0;
            document.getElementById('twitter-count').textContent = data.platforms?.twitter || 0;

            // 最后更新时间
            if (data.last_update) {
                const date = new Date(data.last_update);
                document.getElementById('last-update').textContent = formatDate(date);
            } else {
                document.getElementById('last-update').textContent = '无数据';
            }
        }
    } catch (error) {
        console.error('加载统计失败:', error);
    }
}

// 加载关键词列表
async function loadKeywords() {
    try {
        const response = await fetch(`${API_BASE}/keywords`);
        const result = await response.json();

        if (result.success) {
            // 更新筛选器的关键词下拉框
            const filterSelect = document.getElementById('filter-keywords');
            filterSelect.innerHTML = '<option value="">全部关键词</option>';

            // 更新导出的关键词下拉框
            const exportSelect = document.getElementById('export-keywords');
            exportSelect.innerHTML = '<option value="">全部关键词</option>';

            // 添加关键词选项到两个下拉框
            result.data.forEach(keyword => {
                // 筛选器下拉框
                const filterOption = document.createElement('option');
                filterOption.value = keyword;
                filterOption.textContent = keyword;
                filterSelect.appendChild(filterOption);

                // 导出下拉框
                const exportOption = document.createElement('option');
                exportOption.value = keyword;
                exportOption.textContent = keyword;
                exportSelect.appendChild(exportOption);
            });
        }
    } catch (error) {
        console.error('加载关键词失败:', error);
    }
}

// 加载讨论列表
async function loadDiscussions() {
    const listEl = document.getElementById('discussions-list');
    listEl.innerHTML = '<p class="loading">加载中...</p>';

    try {
        const params = new URLSearchParams({
            limit: pageSize,
            offset: (currentPage - 1) * pageSize,
            ...(currentFilters.platform && { platform: currentFilters.platform }),
            ...(currentFilters.contentType && { content_type: currentFilters.contentType }),
            ...(currentFilters.searchKeywords && { search_keywords: currentFilters.searchKeywords })
        });

        const response = await fetch(`${API_BASE}/discussions?${params}`);
        const result = await response.json();

        if (result.success && result.data.length > 0) {
            renderDiscussions(result.data);

            // 更新分页
            document.getElementById('page-info').textContent = `第 ${currentPage} 页`;
            document.getElementById('prev-page').disabled = currentPage === 1;
            document.getElementById('next-page').disabled = result.data.length < pageSize;
        } else {
            listEl.innerHTML = '<p class="loading">暂无数据</p>';
        }
    } catch (error) {
        console.error('加载讨论失败:', error);
        listEl.innerHTML = '<p class="loading">加载失败</p>';
    }
}

// 渲染讨论列表
function renderDiscussions(discussions) {
    const listEl = document.getElementById('discussions-list');
    listEl.innerHTML = '';

    discussions.forEach(item => {
        const div = document.createElement('div');
        div.className = 'discussion-item';

        // Platform badge
        let platformBadge = 'badge-huggingface';
        if (item.platform === 'reddit') platformBadge = 'badge-reddit';
        if (item.platform === 'twitter') platformBadge = 'badge-twitter';

        const typeBadge = item.content_type === 'post' ? 'badge-post' : 'badge-comment';

        div.innerHTML = `
            <div class="discussion-header">
                <div>
                    <div class="discussion-title">${escapeHtml(item.title || '无标题')}</div>
                    <div class="discussion-meta">
                        <span class="badge ${platformBadge}">${item.platform}</span>
                        <span class="badge ${typeBadge}">${item.content_type}</span>
                        <span>作者: ${escapeHtml(item.author || '未知')}</span>
                        ${item.score !== null && item.score !== undefined ? `<span>⭐ ${item.score}</span>` : ''}
                        ${item.likes !== null && item.likes !== undefined ? `<span>❤️ ${item.likes}</span>` : ''}
                        ${item.retweets !== null && item.retweets !== undefined ? `<span>🔁 ${item.retweets}</span>` : ''}
                        <span>📅 ${formatDate(new Date(item.created_at))}</span>
                    </div>
                </div>
            </div>
            <div class="discussion-content">
                ${escapeHtml(item.content || '无内容').substring(0, 200)}...
            </div>
            <div class="discussion-footer">
                <span>抓取时间: ${formatDate(new Date(item.fetched_at))}</span>
                ${item.url ? `<a href="${item.url}" target="_blank" class="discussion-link">查看原文 →</a>` : ''}
            </div>
        `;

        listEl.appendChild(div);
    });
}

// 开始抓取
async function startFetch() {
    const btn = document.getElementById('start-fetch-btn');
    const statusEl = document.getElementById('fetch-status');

    // 获取参数
    const platforms = [];
    if (document.getElementById('platform-reddit').checked) platforms.push('reddit');
    if (document.getElementById('platform-huggingface').checked) platforms.push('huggingface');

    if (platforms.length === 0) {
        showStatus(statusEl, 'error', '请至少选择一个平台');
        return;
    }

    const query = document.getElementById('search-query').value.trim();
    if (!query) {
        showStatus(statusEl, 'error', '请输入搜索关键词');
        return;
    }

    const includeComments = document.getElementById('include-comments').checked;

    // 获取 Reddit 搜索方式
    const redditSearchMode = document.querySelector('input[name="reddit-search-mode"]:checked')?.value || 'subreddits';

    // 清空日志并添加初始消息
    clearLog();
    addLogEntry(`开始抓取任务...`, 'info');
    addLogEntry(`平台: ${platforms.join(', ')}`, 'info');
    addLogEntry(`关键词: ${query}`, 'info');
    addLogEntry(`Reddit 搜索方式: ${redditSearchMode === 'global' ? '全局搜索' : '特定子版块'}`, 'info');
    if (includeComments) {
        addLogEntry(`将获取评论`, 'info');
    }

    // 禁用按钮
    btn.disabled = true;
    btn.textContent = '抓取中...';
    showStatus(statusEl, 'loading', '正在抓取数据，请稍候...');

    try {
        const response = await fetch(`${API_BASE}/fetch/start`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                platforms,
                query,
                include_comments: includeComments,
                reddit_search_mode: redditSearchMode
            })
        });

        const result = await response.json();

        if (result.success) {
            showStatus(statusEl, 'success', '抓取任务已启动！');
            monitorFetchStatus(statusEl);
        } else {
            throw new Error(result.error);
        }
    } catch (error) {
        showStatus(statusEl, 'error', `抓取失败: ${error.message}`);
        btn.disabled = false;
        btn.textContent = '开始抓取';
    }
}

// 添加日志条目
function addLogEntry(message, type = 'info') {
    const logContainer = document.getElementById('fetch-log-container');
    const logDiv = document.getElementById('fetch-log');

    // 显示日志容器
    logContainer.style.display = 'block';

    // 创建日志条目
    const entry = document.createElement('div');
    entry.className = `log-entry log-${type}`;

    const timestamp = new Date().toLocaleTimeString('zh-CN');
    entry.innerHTML = `<span class="log-timestamp">[${timestamp}]</span>${message}`;

    logDiv.appendChild(entry);

    // 自动滚动到底部
    logDiv.scrollTop = logDiv.scrollHeight;
}

// 清空日志
function clearLog() {
    const logDiv = document.getElementById('fetch-log');
    logDiv.innerHTML = '';
    document.getElementById('fetch-log-container').style.display = 'none';
}

// 监控抓取状态
async function monitorFetchStatus(statusEl) {
    const btn = document.getElementById('start-fetch-btn');
    let lastProgress = '';

    const checkStatus = async () => {
        try {
            const response = await fetch(`${API_BASE}/fetch/status`);
            const result = await response.json();

            if (result.success) {
                const status = result.data;

                if (status.running) {
                    showStatus(statusEl, 'loading', `运行中...`);

                    // 如果进度有更新，添加到日志
                    if (status.progress && status.progress !== lastProgress) {
                        addLogEntry(status.progress, 'info');
                        lastProgress = status.progress;
                    }

                    setTimeout(checkStatus, 1000); // 1秒检查一次，更快响应
                } else {
                    if (status.error) {
                        showStatus(statusEl, 'error', `错误: ${status.error}`);
                        addLogEntry(`错误: ${status.error}`, 'error');
                    } else {
                        showStatus(statusEl, 'success', '✅ 抓取完成！');
                        addLogEntry('✅ 抓取完成！', 'success');
                        loadStats();
                        loadDiscussions();
                        loadKeywords(); // 刷新关键词列表
                    }
                    btn.disabled = false;
                    btn.textContent = '开始抓取';
                }
            }
        } catch (error) {
            console.error('状态检查失败:', error);
        }
    };

    checkStatus();
}

// 导出数据
async function exportData() {
    const format = document.getElementById('export-format').value;
    const platform = document.getElementById('export-platform').value;
    const keywords = document.getElementById('export-keywords').value;

    const params = new URLSearchParams({ format });
    if (platform) params.append('platform', platform);
    if (keywords) params.append('search_keywords', keywords);

    try {
        window.location.href = `${API_BASE}/export?${params}`;
    } catch (error) {
        alert('导出失败: ' + error.message);
    }
}

// 搜索讨论
async function searchDiscussions() {
    const keyword = document.getElementById('search-input').value.trim();
    if (!keyword) {
        loadDiscussions();
        return;
    }

    const listEl = document.getElementById('discussions-list');
    listEl.innerHTML = '<p class="loading">搜索中...</p>';

    try {
        const params = new URLSearchParams({
            keyword,
            limit: 100,
            ...(currentFilters.platform && { platform: currentFilters.platform })
        });

        const response = await fetch(`${API_BASE}/search?${params}`);
        const result = await response.json();

        if (result.success && result.data.length > 0) {
            renderDiscussions(result.data);
        } else {
            listEl.innerHTML = '<p class="loading">未找到相关结果</p>';
        }
    } catch (error) {
        console.error('搜索失败:', error);
        listEl.innerHTML = '<p class="loading">搜索失败</p>';
    }
}

// 检查 cookies 文件
async function checkCookies() {
    try {
        const response = await fetch(`${API_BASE}/cookies/check`);
        const result = await response.json();

        const statusEl = document.getElementById('cookies-status');
        if (result.exists) {
            statusEl.textContent = '✅ cookies.json 已找到';
            statusEl.style.color = 'var(--primary-color)';
        } else {
            statusEl.textContent = '❌ cookies.json 未找到（评论功能不可用）';
            statusEl.style.color = 'var(--danger-color)';
            document.getElementById('include-comments').disabled = true;
        }
    } catch (error) {
        console.error('检查 cookies 失败:', error);
    }
}

// 自动刷新统计
function startAutoRefresh() {
    setInterval(() => {
        loadStats();
    }, 30000); // 每 30 秒刷新一次
}

// 工具函数
function showStatus(element, type, message) {
    element.style.display = 'block';
    element.className = `status-message ${type}`;
    element.textContent = message;
}

function formatDate(date) {
    const now = new Date();
    const diff = now - date;
    const minutes = Math.floor(diff / 60000);
    const hours = Math.floor(diff / 3600000);
    const days = Math.floor(diff / 86400000);

    if (minutes < 1) return '刚刚';
    if (minutes < 60) return `${minutes} 分钟前`;
    if (hours < 24) return `${hours} 小时前`;
    if (days < 7) return `${days} 天前`;

    return date.toLocaleDateString('zh-CN');
}

function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// Twitter CSV 导入
async function importTwitterCSV() {
    const fileInput = document.getElementById('twitter-csv-file');
    const keywordsInput = document.getElementById('twitter-keywords');
    const statusEl = document.getElementById('import-status');
    const btn = document.getElementById('import-twitter-btn');

    if (!fileInput.files || fileInput.files.length === 0) {
        showStatus(statusEl, 'error', '请选择至少一个 CSV 文件');
        return;
    }

    const formData = new FormData();
    for (let file of fileInput.files) {
        formData.append('files', file);
    }

    // 添加搜索关键词（如果有）
    const keywords = keywordsInput.value.trim();
    if (keywords) {
        formData.append('keywords', keywords);
    }

    btn.disabled = true;
    btn.textContent = '导入中...';
    const statusMsg = keywords
        ? `正在导入 ${fileInput.files.length} 个文件（标记为: ${keywords}），请稍候...`
        : `正在导入 ${fileInput.files.length} 个文件，请稍候...`;
    showStatus(statusEl, 'loading', statusMsg);

    try {
        const response = await fetch(`${API_BASE}/twitter/import`, {
            method: 'POST',
            body: formData
        });

        const result = await response.json();

        if (result.success) {
            showStatus(statusEl, 'success', `✅ 成功导入 ${result.data.success_count} 条记录！`);
            fileInput.value = '';
            btn.disabled = true;

            // 刷新统计和列表
            setTimeout(() => {
                loadStats();
                loadDiscussions();
            }, 1000);
        } else {
            throw new Error(result.error || '导入失败');
        }
    } catch (error) {
        showStatus(statusEl, 'error', `导入失败: ${error.message}`);
    } finally {
        btn.disabled = fileInput.files.length === 0;
        btn.textContent = '导入 Twitter CSV';
    }
}
