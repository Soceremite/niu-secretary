/* 牛秘书闲趣集 · 离线反馈队列 */
(function() {
  const KEY = 'niu_leisure_pending_feedback';
  const MAX_ITEMS = 100;

  function readRaw() {
    try {
      const items = JSON.parse(localStorage.getItem(KEY) || '[]');
      return Array.isArray(items) ? items : [];
    } catch {
      return [];
    }
  }

  function writeRaw(items) {
    const normalized = Array.isArray(items) ? items.slice(-MAX_ITEMS) : [];
    if (normalized.length) localStorage.setItem(KEY, JSON.stringify(normalized));
    else localStorage.removeItem(KEY);
  }

  window.LeisureOfflineFeedbackQueue = {
    key: KEY,
    enqueue(action, input, feedback) {
      const items = readRaw();
      items.push({ action, input, feedback, cachedAt: new Date().toISOString() });
      writeRaw(items);
    },
    list() {
      return readRaw();
    },
    replace(items) {
      writeRaw(items);
    }
  };
})();
