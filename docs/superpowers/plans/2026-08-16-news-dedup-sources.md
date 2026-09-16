# News Dedup Sources Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Reduce duplicate news topics across the five news sections and document broader source coverage for daily generation.

**Architecture:** Extend `news-daily/tools/audit_news_sources.py` with a generic event fingerprint that groups similar titles and summaries across sections, while preserving existing URL and title checks. Add tests in `news-daily/tests/test_audit_news_sources.py` for AI/tech overlap and acceptable distinct stories.

**Tech Stack:** Python 3.12, stdlib `re`, `Counter`, pytest.

---

### Task 1: Generic Cross-Section Event Fingerprints

**Files:**
- Modify: `news-daily/tools/audit_news_sources.py`
- Test: `news-daily/tests/test_audit_news_sources.py`

- [ ] **Step 1: Write failing tests**

Add tests that expect an AI infrastructure story duplicated in `tech` and `ai` to be reported, but distinct AI-adjacent stories to pass.

- [ ] **Step 2: Implement event fingerprint**

Add helper functions that normalize title/summary, extract meaningful Chinese bigrams and alphanumeric entities, and return an `auto:<tokens>` key when enough signal exists.

- [ ] **Step 3: Preserve specific rules**

Keep existing hand-written `EVENT_GROUP_RULES`; use them before the generic fingerprint.

- [ ] **Step 4: Run targeted tests**

Run:

```bash
PYTHONPATH=news-daily/tools pytest news-daily/tests/test_audit_news_sources.py -q
```

Expected: all tests pass.

### Task 2: Source Coverage Notes

**Files:**
- Modify: `news-daily/SKILL.md`

- [ ] **Step 1: Add recommended source channels**

Expand the technology/AI source list with IT之家、量子位、雷峰网、晚点、MIT Technology Review、VentureBeat、Hugging Face、arXiv、Papers with Code.

- [ ] **Step 2: Add generation instruction**

Document that five-section generation should avoid reusing the same event across sections, with AI/tech/finance priority rules.

### Task 3: Current Dist Audit Smoke Test

**Files:**
- Read: `news-daily/dist/sections/*.html`

- [ ] **Step 1: Run no-network audit**

Run:

```bash
PYTHONPATH=news-daily/tools python3 news-daily/tools/audit_news_sources.py --dist news-daily/dist --no-network
```

Expected: either pass, or report concrete duplicate groups to fix in the next content generation.
