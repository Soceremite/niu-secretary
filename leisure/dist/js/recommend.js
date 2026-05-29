/**
 * 牛秘书闲趣集 - 推荐渲染 + 偏好匹配
 */

import Store from './store.js';

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

  /**
   * 根据偏好过滤和排序推荐
   */
  filterByPreference(items, type) {
    const prefs = Store.getPreferences();
    const typePref = prefs[type] || {};
    const ratings = Store.getRatings();

    // Filter out disliked items
    const disliked = new Set(ratings.filter(r => r.action === 'dislike').map(r => r.id));
    let filtered = items.filter(item => !disliked.has(item.id));

    // Boost items matching preferences
    filtered = filtered.map(item => {
      let boost = 0;
      if (typePref.genres && item.genres) {
        const overlap = item.genres.filter(g => typePref.genres.includes(g));
        boost += overlap.length * 5;
      }
      if (typePref.moods && item.mood) {
        const moodOverlap = (Array.isArray(item.mood) ? item.mood : [item.mood])
          .filter(m => typePref.moods.includes(m));
        boost += moodOverlap.length * 3;
      }
      return { ...item, _boost: boost, _effectiveScore: (item.matchScore || 50) + boost };
    });

    // Sort by effective score
    filtered.sort((a, b) => b._effectiveScore - a._effectiveScore);
    return filtered;
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
      `;

      // Action buttons
      card.querySelectorAll('.rec-btn').forEach(btn => {
        btn.addEventListener('click', (e) => {
          e.stopPropagation();
          const action = btn.dataset.action;
          Store.addRating(item.id, type, action);
          if (action === 'saved') {
            Store.addToCollection(type, item);
            btn.textContent = '✅';
          } else if (action === 'dislike') {
            card.style.opacity = '0.3';
            card.style.pointerEvents = 'none';
          } else {
            btn.textContent = '💛';
          }
        });
      });

      container.appendChild(card);
    });
  }
};

export default Recommend;
