# Niu Secretary Brand Portal Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the 牛秘书 homepage as a usable brand portal for the existing news and fitness products.

**Architecture:** Keep the project as a static, dependency-free HTML page. The page uses local `logo.png`, inline CSS, and small progressive-enhancement JavaScript for reveal animations, hover light, and active navigation.

**Tech Stack:** HTML5, CSS Grid/Flexbox, vanilla JavaScript, nginx static deployment.

---

### Task 1: Rewrite Homepage

**Files:**
- Modify: `/home/ubuntu/.openclaw/workspace/niu-secretary/dist/index.html`

- [x] Replace the old display-only brand page with a product portal.
- [x] Keep links to `/home/news/` and `/home/fitness/` usable through relative `news/` and `fitness/` URLs.
- [x] Preserve the black-gold private steward brand direction while improving scan efficiency.

### Task 2: Deploy

**Files:**
- Source: `/home/ubuntu/.openclaw/workspace/niu-secretary/dist/index.html`
- Source: `/home/ubuntu/.openclaw/workspace/niu-secretary/dist/logo.png`
- Target: `/var/www/html/niu-secretary/index.html`
- Target: `/var/www/html/niu-secretary/logo.png`

- [ ] Back up the current nginx homepage.
- [ ] Copy the updated files into `/var/www/html/`.
- [ ] Verify `/niu-secretary/` returns the new page and `/home/` remains the original homepage.
