/**
 * 牛秘书闲趣集 - localStorage 数据层
 * 管理用户偏好、收藏、评分
 */

const STORE_PREFIX = 'niu_leisure_';

const Store = {
  _key(name) {
    return STORE_PREFIX + name;
  },

  get(name) {
    try {
      const raw = localStorage.getItem(this._key(name));
      return raw ? JSON.parse(raw) : null;
    } catch (e) {
      console.warn(`[Store] Failed to read "${name}":`, e);
      return null;
    }
  },

  set(name, value) {
    try {
      localStorage.setItem(this._key(name), JSON.stringify(value));
      return true;
    } catch (e) {
      console.warn(`[Store] Failed to write "${name}":`, e);
      return false;
    }
  },

  // --- Preferences ---
  getPreferences() {
    return this.get('preferences') || {
      movies: { genres: [], regions: [], moods: [], eras: [] },
      music: { genres: [], languages: [], scenes: [], moods: [] },
      podcasts: { genres: [], durations: [] }
    };
  },
  savePreferences(prefs) {
    return this.set('preferences', prefs);
  },

  // --- Ratings ---
  getRatings() {
    return this.get('ratings') || [];
  },
  addRating(itemId, type, action) {
    // action: 'like' | 'dislike' | 'skip' | 'watched' | 'saved'
    const ratings = this.getRatings();
    const existing = ratings.find(r => r.id === itemId);
    if (existing) {
      existing.action = action;
      existing.updatedAt = new Date().toISOString();
    } else {
      ratings.push({
        id: itemId,
        type, // 'movie' | 'music' | 'podcast'
        action,
        createdAt: new Date().toISOString()
      });
    }
    this.set('ratings', ratings);
  },

  // --- Collections ---
  getCollection(type) {
    return this.get(`collection_${type}`) || [];
  },
  addToCollection(type, item) {
    const col = this.getCollection(type);
    if (!col.find(c => c.id === item.id)) {
      col.push({ ...item, savedAt: new Date().toISOString() });
      this.set(`collection_${type}`, col);
    }
  },
  removeFromCollection(type, itemId) {
    const col = this.getCollection(type).filter(c => c.id !== itemId);
    this.set(`collection_${type}`, col);
  },

  // --- Export ---
  exportAll() {
    return {
      preferences: this.getPreferences(),
      ratings: this.getRatings(),
      collection_movies: this.getCollection('movies'),
      collection_music: this.getCollection('music'),
      collection_podcasts: this.getCollection('podcasts')
    };
  }
};

export default Store;
