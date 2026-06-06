/* ====== 牛秘书闲趣集 · 公共导航 + 数据 ====== */

const COLOR_MAP = { '影视': '#66848e', '音乐': '#c9975f', '播客': '#243746', '小说': '#7f8a6a' };
const ICON_MAP = { '影视': '影', '音乐': '乐', '播客': '播', '小说': '书' };

// 详情弹窗
function closeDetail(e) {
  if (!e || e.target === document.getElementById('detail-overlay')) {
    document.getElementById('detail-overlay').classList.remove('active');
    document.getElementById('detail-content').innerHTML = '';
  }
}

function showDetail(item, rawItem) {
  const overlay = document.getElementById('detail-overlay');
  const content = document.getElementById('detail-content');
  let html = `<h3>${item.title}</h3>`;
  html += `<div class="sub">${item.reason || ''}</div>`;

  if (item.type === '影视' && rawItem) {
    html += '<div class="detail-grid">';
    html += `<div class="dg-item"><div class="dg-label">🎬 类型</div><div class="dg-value">${(rawItem.genres || []).join(', ') || '-'}</div></div>`;
    html += `<div class="dg-item"><div class="dg-label">📅 年份</div><div class="dg-value">${rawItem.year || '-'}</div></div>`;
    html += `<div class="dg-item"><div class="dg-label">🌍 地区</div><div class="dg-value">${rawItem.region || '-'}</div></div>`;
    html += `<div class="dg-item"><div class="dg-label">⏱️ 时长</div><div class="dg-value">${rawItem.duration || item.duration || '-'}</div></div>`;
    html += `<div class="dg-item"><div class="dg-label">⭐ 豆瓣评分</div><div class="dg-value">${rawItem.doubanRating || '暂无'}</div></div>`;
    html += `<div class="dg-item"><div class="dg-label">📊 匹配度</div><div class="dg-value">${item.score || rawItem.matchScore || 80}%</div></div>`;
    html += '</div>';
    if (rawItem.description) html += `<p style="font-size:14px;line-height:1.7;color:var(--ink)">${rawItem.description}</p>`;
    if (rawItem.actors) html += `<p style="font-size:13px;color:var(--muted);margin-top:8px"><strong>主演：</strong>${rawItem.actors}</p>`;
    if (rawItem.director) html += `<p style="font-size:13px;color:var(--muted);"><strong>导演：</strong>${rawItem.director}</p>`;
    html += '<div class="detail-actions">';
    if (rawItem.doubanUrl) html += `<a class="primary-link" href="${rawItem.doubanUrl}" target="_blank">📺 豆瓣详情</a>`;
    html += '<a href="#" onclick="closeDetail();return false">关闭</a>';
    html += '</div>';
  } else if (item.type === '音乐' && rawItem) {
    html += `<p style="font-size:14px;margin-bottom:12px;color:var(--muted)"><strong>类型：</strong>${rawItem.genre || '-'} · <strong>语言：</strong>${rawItem.language || '-'} · <strong>${rawItem.trackCount || 0}首</strong></p>`;
    if (rawItem.tracks && rawItem.tracks.length) {
      html += '<ul class="track-list">';
      rawItem.tracks.forEach((t, i) => {
        html += `<li><span class="track-num">${i+1}</span>${t.name || t}<span style="margin-left:auto;color:var(--muted);font-size:12px">${t.artist || t.duration || ''}</span></li>`;
      });
      html += '</ul>';
    }
    html += `<p style="font-size:14px;line-height:1.7;color:var(--ink)">${rawItem.description || rawItem.reason || ''}</p>`;
    html += '<div class="detail-actions">';
    if (rawItem.platformUrl) html += `<a class="primary-link" href="${rawItem.platformUrl}" target="_blank">🎵 在线聆听</a>`;
    html += '<a href="#" onclick="closeDetail();return false">关闭</a>';
    html += '</div>';
  } else if (item.type === '播客' && rawItem) {
    html += `<p style="font-size:14px;margin-bottom:12px;color:var(--muted)"><strong>播客：</strong>${rawItem.podcast || '-'} · <strong>单集：</strong>${rawItem.episode || rawItem.title || '-'}</p>`;
    html += `<p style="font-size:14px;line-height:1.7;color:var(--ink)">${rawItem.description || rawItem.reason || ''}</p>`;
    html += '<div class="detail-grid">';
    html += `<div class="dg-item"><div class="dg-label">🎙️ 类型</div><div class="dg-value">${(rawItem.genres || []).join(', ') || '-'}</div></div>`;
    html += `<div class="dg-item"><div class="dg-label">⏱️ 时长</div><div class="dg-value">${rawItem.duration || item.duration || '-'}</div></div>`;
    html += `<div class="dg-item"><div class="dg-label">📊 匹配度</div><div class="dg-value">${item.score || rawItem.matchScore || 80}%</div></div>`;
    html += '</div>';
    html += '<div class="detail-actions">';
    if (rawItem.platformUrl) html += `<a class="primary-link" href="${rawItem.platformUrl}" target="_blank">🎧 喜马拉雅</a>`;
    html += '<a href="#" onclick="closeDetail();return false">关闭</a>';
    html += '</div>';
  } else if (item.type === '小说' && rawItem) {
    html += '<div class="detail-grid">';
    html += `<div class="dg-item"><div class="dg-label">📚 类型</div><div class="dg-value">${(rawItem.genres || []).join(', ') || '-'}</div></div>`;
    html += `<div class="dg-item"><div class="dg-label">✍️ 作者</div><div class="dg-value">${rawItem.author || '-'}</div></div>`;
    html += `<div class="dg-item"><div class="dg-label">📖 字数</div><div class="dg-value">${rawItem.wordCount || '-'}</div></div>`;
    html += `<div class="dg-item"><div class="dg-label">📊 匹配度</div><div class="dg-value">${item.score || rawItem.matchScore || 80}%</div></div>`;
    html += '</div>';
    if (rawItem.description) html += `<p style="font-size:14px;line-height:1.7;color:var(--ink);margin-bottom:12px">${rawItem.description}</p>`;
    html += '<div class="detail-actions">';
    html += '<a class="primary-link" href="https://www.qidian.com" target="_blank">📖 起点读书</a>';
    if (rawItem.platformUrl) html += `<a href="${rawItem.platformUrl}" target="_blank">🔗 在线阅读</a>`;
    html += '<a href="#" onclick="closeDetail();return false">关闭</a>';
    html += '</div>';
  } else {
    html += `<p style="font-size:14px;line-height:1.7;color:var(--ink)">${item.reason || ''}</p>`;
    html += '<div class="detail-actions"><a href="#" onclick="closeDetail();return false">关闭</a></div>';
  }

  content.innerHTML = html;
  overlay.classList.add('active');
}

// Scroll reveal
function initScrollReveal() {
  const observer = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
      if (entry.isIntersecting) {
        entry.target.classList.add('visible');
        observer.unobserve(entry.target);
      }
    });
  }, { threshold: 0.1, rootMargin: '0px 0px -50px 0px' });
  document.querySelectorAll('.reveal').forEach(el => observer.observe(el));
}

// 数据加载（兼容 [..] 和 {items:[..]}）
function getItems(data) {
  if (Array.isArray(data)) return data;
  if (data && Array.isArray(data.items)) return data.items;
  return [];
}

async function loadSectionData(key, file) {
  try {
    const res = await fetch(file);
    if (!res.ok) return [];
    const data = await res.json();
    return getItems(data);
  } catch (e) { return []; }
}

function normalize(item, type, href, fallbackDuration, index) {
  let dur = item.duration || fallbackDuration;
  if (typeof dur === 'number') dur = dur + '分钟';
  if (typeof dur === 'string' && /^\d+$/.test(dur)) dur = dur + '分钟';
  return {
    type, href,
    title: item.title || item.name || type,
    reason: item.reason || '',
    score: item.matchScore || 80,
    duration: dur,
    rawIndex: index || 0,
  };
}

// 渲染卡片网格
function renderCardGrid(items, type, containerId) {
  const container = document.getElementById(containerId);
  if (!container) return;
  let html = '';
  items.forEach((item, i) => {
    const norm = normalize(item, type, '#', '30分钟', i);
    html += `<div class="sec-card reveal" onclick="showDetail(${JSON.stringify(norm).replace(/"/g, '&quot;')}, ${JSON.stringify(item).replace(/"/g, '&quot;')})">
      <div class="sec-card-inner">
        ${item.posterUrl ? `<div style="width:100%;height:140px;border-radius:10px;background:url(${item.posterUrl}) center/cover no-repeat;margin-bottom:10px"></div>` : ''}
        <h4>${item.title || item.name}</h4>
        <div class="card-tags">${(item.genres || []).slice(0, 3).map(g => `<span>${g}</span>`).join('')}</div>
        <div class="card-reason">${item.reason || ''}</div>
        <div class="card-score">匹配度 ${item.matchScore || 80}%</div>
      </div>
    </div>`;
  });
  container.innerHTML = html;
  initScrollReveal();
}

// 高亮当前页面的导航菜单
function highlightNav() {
  const page = document.body.getAttribute('data-page') || 'index';
  document.querySelectorAll('.nav-menu a').forEach(a => {
    if (a.getAttribute('data-nav') === page) {
      a.classList.add('active');
    }
  });
}

document.addEventListener('DOMContentLoaded', () => {
  highlightNav();
  initScrollReveal();
});
