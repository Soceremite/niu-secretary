/**
 * 牛秘书时务局 - 统一 localStorage 数据层
 * 所有子模块共享此存储封装
 */

const STORE_PREFIX = 'niu_schedule_';

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

  remove(name) {
    localStorage.removeItem(this._key(name));
  },

  // --- Events ---
  getEvents() {
    return this.get('events') || [];
  },
  saveEvents(events) {
    return this.set('events', events);
  },
  addEvent(event) {
    const events = this.getEvents();
    event.id = event.id || 'evt_' + Date.now();
    events.push(event);
    this.saveEvents(events);
    return event;
  },
  removeEvent(id) {
    const events = this.getEvents().filter(e => e.id !== id);
    this.saveEvents(events);
  },

  // --- Important Dates ---
  getDates() {
    return this.get('dates') || [];
  },
  saveDates(dates) {
    return this.set('dates', dates);
  },
  addDate(item) {
    const dates = this.getDates();
    item.id = item.id || 'date_' + Date.now();
    dates.push(item);
    this.saveDates(dates);
    return item;
  },
  removeDate(id) {
    const dates = this.getDates().filter(d => d.id !== id);
    this.saveDates(dates);
  },

  // --- Todos ---
  getTodos() {
    return this.get('todos') || [];
  },
  saveTodos(todos) {
    return this.set('todos', todos);
  },
  addTodo(todo) {
    const todos = this.getTodos();
    todo.id = todo.id || 'todo_' + Date.now();
    todo.done = false;
    todos.push(todo);
    this.saveTodos(todos);
    return todo;
  },
  toggleTodo(id) {
    const todos = this.getTodos();
    const t = todos.find(t => t.id === id);
    if (t) t.done = !t.done;
    this.saveTodos(todos);
  },
  removeTodo(id) {
    const todos = this.getTodos().filter(t => t.id !== id);
    this.saveTodos(todos);
  },

  // --- Goals ---
  getGoals() {
    return this.get('goals') || [];
  },
  saveGoals(goals) {
    return this.set('goals', goals);
  },
  addGoal(goal) {
    const goals = this.getGoals();
    goal.id = goal.id || 'goal_' + Date.now();
    goal.streak = 0;
    goal.history = [];
    goals.push(goal);
    this.saveGoals(goals);
    return goal;
  },
  checkInGoal(id) {
    const goals = this.getGoals();
    const g = goals.find(g => g.id === id);
    if (!g) return;
    const today = new Date().toISOString().slice(0, 10);
    if (!g.history.includes(today)) {
      g.history.push(today);
      g.streak = (g.streak || 0) + 1;
    }
    this.saveGoals(goals);
  },
  removeGoal(id) {
    const goals = this.getGoals().filter(g => g.id !== id);
    this.saveGoals(goals);
  },

  // --- Reading ---
  getBooks() {
    return this.get('books') || [];
  },
  saveBooks(books) {
    return this.set('books', books);
  },
  addBook(book) {
    const books = this.getBooks();
    book.id = book.id || 'book_' + Date.now();
    book.status = book.status || 'want';
    book.progress = book.progress || 0;
    books.push(book);
    this.saveBooks(books);
    return book;
  },
  removeBook(id) {
    const books = this.getBooks().filter(b => b.id !== id);
    this.saveBooks(books);
  },

  // --- Utility ---
  exportAll() {
    const data = {};
    ['events', 'dates', 'todos', 'goals', 'books'].forEach(name => {
      data[name] = this.get(name) || [];
    });
    return data;
  },
  importAll(data) {
    Object.keys(data).forEach(name => {
      if (Array.isArray(data[name])) {
        this.set(name, data[name]);
      }
    });
  }
};

export default Store;
