# Niu Secretary 2 Action Protocol Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the first working slice of 牛秘书 2.0: a unified HTTP Action Protocol that the home assistant and subpages can share.

**Architecture:** Add a standalone Python stdlib API under `server/` with a capability registry, SQLite-backed domain storage, action execution, and assistant message parsing. Keep existing static subpages intact; the new service becomes the canonical write path for new v2.0 actions.

**Tech Stack:** Python 3 stdlib (`http.server`, `sqlite3`, `unittest`), static HTML/CSS/JS, nginx reverse proxy later under `/niu-secretary/api/`.

---

## File Structure

- Create `server/__init__.py`: marks the unified API as an importable Python package.
- Create `server/capabilities.py`: defines action metadata and schemas for `GET /capabilities`.
- Create `server/store.py`: owns SQLite schema creation, inserts, summary reads, and action logging.
- Create `server/actions.py`: validates and executes canonical actions.
- Create `server/assistant.py`: maps simple Chinese natural-language messages to proposed actions.
- Create `server/niu_secretary_api.py`: HTTP entry point for health, capabilities, actions, and assistant routes.
- Create `server/test_niu_secretary_api.py`: stdlib unit tests for action execution, validation, and assistant parsing.
- Modify `dist/index.html`: add a compact AI assistant panel wired to the new API.
- Create `dist/assistant.js`: browser client for assistant message and action confirmation.
- Modify `SKILL.md`: document the new v2.0 API service.

## Task 1: Unified API Core

**Files:**
- Create: `server/__init__.py`
- Create: `server/capabilities.py`
- Create: `server/store.py`
- Create: `server/actions.py`
- Create: `server/assistant.py`
- Create: `server/niu_secretary_api.py`
- Create: `server/test_niu_secretary_api.py`

- [ ] **Step 1: Add capabilities registry**

Create `server/capabilities.py` with a `CAPABILITIES` list containing:

```python
CAPABILITIES = [
    {
        "name": "fitness.nutrition.create",
        "title": "记录一餐",
        "module": "fitness",
        "description": "写入塑形馆营养日志",
        "confirmByDefault": True,
        "inputSchema": {
            "type": "object",
            "required": ["food", "date"],
            "properties": {
                "food": {"type": "string"},
                "date": {"type": "string", "format": "date"},
                "calories": {"type": "number"},
                "proteinG": {"type": "number"},
                "carbsG": {"type": "number"},
                "fatG": {"type": "number"},
                "source": {"type": "string"}
            }
        }
    },
    {
        "name": "schedule.event.create",
        "title": "创建日程",
        "module": "schedule",
        "description": "写入时务局日程事件",
        "confirmByDefault": True,
        "inputSchema": {
            "type": "object",
            "required": ["title", "date"],
            "properties": {
                "title": {"type": "string"},
                "date": {"type": "string", "format": "date"},
                "time": {"type": "string"},
                "note": {"type": "string"},
                "source": {"type": "string"}
            }
        }
    },
    {
        "name": "schedule.todo.create",
        "title": "创建待办",
        "module": "schedule",
        "description": "写入时务局待办",
        "confirmByDefault": True,
        "inputSchema": {
            "type": "object",
            "required": ["title"],
            "properties": {
                "title": {"type": "string"},
                "date": {"type": "string", "format": "date"},
                "priority": {"type": "string"},
                "source": {"type": "string"}
            }
        }
    },
    {
        "name": "fitness.nutrition.today_summary",
        "title": "今日营养汇总",
        "module": "fitness",
        "description": "读取今日营养合计",
        "confirmByDefault": False,
        "inputSchema": {
            "type": "object",
            "required": ["date"],
            "properties": {
                "date": {"type": "string", "format": "date"}
            }
        }
    }
]
```

- [ ] **Step 2: Add SQLite store**

Create `server/store.py` with tables:

```sql
action_logs(id TEXT PRIMARY KEY, action TEXT NOT NULL, status TEXT NOT NULL, input_json TEXT NOT NULL, result_json TEXT NOT NULL, error TEXT NOT NULL DEFAULT '', created_at TEXT NOT NULL);
fitness_nutrition_logs(id TEXT PRIMARY KEY, food TEXT NOT NULL, date TEXT NOT NULL, calories INTEGER NOT NULL DEFAULT 0, protein_g INTEGER NOT NULL DEFAULT 0, carbs_g INTEGER NOT NULL DEFAULT 0, fat_g INTEGER NOT NULL DEFAULT 0, source TEXT NOT NULL, created_at TEXT NOT NULL, updated_at TEXT NOT NULL);
schedule_events(id TEXT PRIMARY KEY, title TEXT NOT NULL, date TEXT NOT NULL, time TEXT NOT NULL DEFAULT '', note TEXT NOT NULL DEFAULT '', source TEXT NOT NULL, created_at TEXT NOT NULL, updated_at TEXT NOT NULL);
schedule_todos(id TEXT PRIMARY KEY, title TEXT NOT NULL, date TEXT NOT NULL DEFAULT '', priority TEXT NOT NULL DEFAULT 'normal', done INTEGER NOT NULL DEFAULT 0, source TEXT NOT NULL, created_at TEXT NOT NULL, updated_at TEXT NOT NULL);
assistant_messages(id TEXT PRIMARY KEY, text TEXT NOT NULL, reply TEXT NOT NULL, proposed_actions_json TEXT NOT NULL, created_at TEXT NOT NULL);
```

Use `NIU_SECRETARY_DB_PATH` if set, otherwise default to `data/niu-secretary.sqlite3`.

- [ ] **Step 3: Add action execution**

Create `server/actions.py` with:

```python
def execute_action(action_name: str, payload: dict, context: dict | None = None) -> dict:
    ...
```

Support:
- `fitness.nutrition.create`
- `fitness.nutrition.today_summary`
- `schedule.event.create`
- `schedule.todo.create`

Return the common response shape:

```json
{"ok": true, "action": "fitness.nutrition.create", "record": {"id": "...", "createdAt": "...", "syncStatus": "synced"}, "message": "已记录到塑形馆营养。"}
```

- [ ] **Step 4: Add assistant parser**

Create `server/assistant.py` with:

```python
def handle_message(text: str, context: dict | None = None) -> dict:
    ...
```

Parse:
- Meal messages containing `吃了` / `早餐` / `午餐` / `晚餐` into `fitness.nutrition.create`.
- Reminder messages containing `提醒` / `日程` / `开会` into `schedule.event.create`.
- Todo messages containing `待办` / `记得` into `schedule.todo.create`.

All write proposals set `requiresConfirmation: true`.

- [ ] **Step 5: Add HTTP routes**

Create `server/niu_secretary_api.py` with:

- `GET /niu-secretary/api/health`
- `GET /niu-secretary/api/capabilities`
- `POST /niu-secretary/api/actions/execute`
- `POST /niu-secretary/api/assistant/message`

Also support local paths without prefix:

- `/api/health`
- `/api/capabilities`
- `/api/actions/execute`
- `/api/assistant/message`

- [ ] **Step 6: Add unit tests**

Create `server/test_niu_secretary_api.py` using `tempfile.TemporaryDirectory()` and `unittest`. Test:

- capabilities include `fitness.nutrition.create`.
- missing food returns `validation_failed`.
- creating nutrition writes a record and summary returns matching calories.
- assistant message `我今天吃了牛肉面` returns a `fitness.nutrition.create` proposal.
- assistant message `明天下午三点提醒我开会` returns a `schedule.event.create` proposal.

- [ ] **Step 7: Verify**

Run:

```bash
python3 -m unittest server.test_niu_secretary_api
python3 -m py_compile server/*.py
```

Expected: tests pass and py_compile exits 0.

## Task 2: Home Assistant UI

**Files:**
- Modify: `dist/index.html`
- Create: `dist/assistant.js`

- [ ] **Step 1: Add assistant panel markup**

Add a first-viewport AI panel to the homepage near the hero actions with:

- message list
- text input
- send button
- attachment input reserved for future image actions
- action confirmation area

- [ ] **Step 2: Add browser client**

Create `dist/assistant.js` to:

- POST text to `/niu-secretary/api/assistant/message`
- render assistant reply
- render proposed action cards
- call `/niu-secretary/api/actions/execute` after user confirmation

- [ ] **Step 3: Wire script**

Add:

```html
<script type="module" src="assistant.js"></script>
```

to `dist/index.html`.

- [ ] **Step 4: Verify static JS**

Run:

```bash
node --check dist/assistant.js
```

Expected: syntax OK.

## Task 3: Documentation, Commit, Push

**Files:**
- Modify: `SKILL.md`
- Create: `docs/superpowers/plans/2026-05-29-niu-secretary-2-action-protocol-implementation.md`

- [ ] **Step 1: Document run commands**

Add to `SKILL.md`:

```bash
NIU_SECRETARY_API_PORT=5188 python3 server/niu_secretary_api.py
```

and the three core endpoints.

- [ ] **Step 2: Commit**

Run:

```bash
git add server dist/index.html dist/assistant.js SKILL.md docs/superpowers/plans/2026-05-29-niu-secretary-2-action-protocol-implementation.md
git commit -m "feat: add niu secretary action protocol"
```

- [ ] **Step 3: Push**

Run:

```bash
git push origin main
```

Expected: GitHub `main` contains the v2.0 Phase 1 implementation.
