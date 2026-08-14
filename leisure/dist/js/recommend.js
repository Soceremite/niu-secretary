/**
 * 牛秘书闲趣集 - 推荐渲染
 */

const ACTION_API = '/niu-secretary/api/actions/execute';
const FEEDBACK_ACTIONS = {
  like: 'leisure.item.rate',
  dislike: 'leisure.item.dismiss',
  saved: 'leisure.item.save',
};

const Recommend = {
  /**
   * 加载 JSON 推荐数据
   */
  async loadData(type) {
    try {
      const res = await fetch(`data/${type}.json?t=${Date.now()}`);
      if (!res.ok) return null;
      return await res.json();
    } catch (e) {
      console.warn(`[Recommend] Failed to load ${type}:`, e);
      return null;
    }
  },

  filterByPreference(items, type) {
    return Array.isArray(items) ? items : [];
  },

  /**
   * 渲染推荐卡片到容器
   */
  renderCards(container, items, type) {
    container.innerHTML = '';
    if (!items || items.length === 0) {
      container.innerHTML = '<div class="empty-state">暂无推荐内容</div>';
      return;
    }

    items.forEach(item => {
      const card = document.createElement('div');
      card.className = 'recommend-card';
      card.dataset.id = item.id;

      card.innerHTML = `
        <div class="rec-header">
          <span class="rec-genres">${(item.genres || []).join(' · ')}</span>
          ${item.matchScore ? `<span class="rec-score">${item.matchScore}%</span>` : ''}
        </div>
        <h3 class="rec-title">${item.title}</h3>
        ${item.titleOriginal ? `<div class="rec-original">${item.titleOriginal}</div>` : ''}
        ${item.reason ? `<p class="rec-reason">${item.reason}</p>` : ''}
        <div class="rec-actions">
          <button class="rec-btn like" data-action="like" title="喜欢">👍</button>
          <button class="rec-btn skip" data-action="dislike" title="跳过">👎</button>
          <button class="rec-btn save" data-action="saved" title="收藏">⭐</button>
        </div>
        <div class="rec-feedback-status" data-feedback-status></div>
      `;

      card.querySelectorAll('.rec-btn').forEach(btn => {
        btn.addEventListener('click', async (e) => {
          e.stopPropagation();
          const action = btn.dataset.action;
          await recordFeedback(item, type, action, card, btn);
        });
      });

      container.appendChild(card);
    });
  }
};

async function recordFeedback(item, type, feedback, card, button) {
  const action = FEEDBACK_ACTIONS[feedback];
  if (!action) return;
  const status = card.querySelector('[data-feedback-status]');
  const input = {
    itemId: item.id || `${type}_${item.title || item.name || Date.now()}`,
    category: normalizeCategory(type),
    title: item.title || item.name || '未命名条目',
    rating: feedback === 'like' ? 5 : 0,
    note: `from leisure ${type} list`,
    source: 'leisure-page',
    payload: {
      genres: Array.isArray(item.genres) ? item.genres : [],
      tags: Array.isArray(item.tags) ? item.tags : [],
      mood: item.mood || '',
      score: item.matchScore || 0,
      platformUrl: item.platformUrl || item.doubanUrl || '',
    },
  };
  button.disabled = true;
  if (status) status.textContent = '写入中...';
  try {
    await postFeedbackAction(action, input);
    if (feedback === 'saved') button.textContent = '✅';
    else if (feedback === 'dislike') {
      card.style.opacity = '0.3';
      card.style.pointerEvents = 'none';
    } else {
      button.textContent = '💛';
    }
    if (status) status.textContent = '已写入后端';
  } catch (error) {
    cacheFeedback(action, input, feedback);
    button.disabled = false;
    if (status) status.textContent = '后端不可用，已离线缓存';
  }
}

async function postFeedbackAction(action, input) {
  const response = await fetch(ACTION_API, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      action,
      input,
      context: { client: 'leisure-page', confirmed: true },
    }),
  });
  const data = await response.json().catch(() => ({}));
  if (!response.ok || data.ok === false) {
    throw new Error(data.message || `反馈写入失败：${response.status}`);
  }
  return data;
}

function cacheFeedback(action, input, feedback) {
  try {
    window.LeisureOfflineFeedbackQueue.enqueue(action, input, feedback);
  } catch (error) {
    console.warn('[Recommend] Failed to cache feedback:', error);
  }
}

function normalizeCategory(type) {
  return { movies: 'movie', movie: 'movie', music: 'music', podcasts: 'podcast', podcast: 'podcast', novels: 'novel', novel: 'novel' }[type] || type;
}

export default Recommend;
