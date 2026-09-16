# AIResearch Yantao-Style Public Frontend Redesign

Date: 2026-08-15

## Scope

Redesign the public AIResearch frontend to match the playful Memphis/blog style already introduced in the deep-reading pages and paper cards. This covers the static public research site under `/niu-secretary/airesearch/` only.

Out of scope:

- 牛秘书管理台 and admin login pages.
- Backend ingestion, OCR, formula/table extraction, deep-reading generation, API credentials, and database behavior.
- Changing existing URLs or JSON API contracts.

## Reference Direction

The visual reference is https://yantao.wiki/: cream dotted background, flat cartoon colors, hard black borders, zero-radius or small-radius paper panels, offset hard shadows, light rotation for article cards, sticky article sidebars, compact metadata blocks, and playful but readable typography.

The redesign should feel like a coherent research blog/library, not a generic SaaS dashboard.

## Current State

Already close to target:

- Deep-reading article page: left article body, fixed right article catalog, tags, previous/next, comments.
- Paper list card: post-stack-like article card with left thumbnail, hard border, black/pink/teal shadows, and slight rotation.

Still inconsistent:

- Top navigation is still a quiet translucent product bar.
- Dashboard metric cards and panels are still generic white cards.
- Blog index cards are still full-width utility cards, not post-stack cards.
- Cluster/gap/digest/synthesis/narrative pages use mixed panel styles.
- Map and starmap tool surfaces need themed chrome without hurting readability.
- Form controls, pagination, chips, empty states, footer, and search results need one shared style system.

## Design System

Core theme variables:

- Background: warm cream `#fff9ee` with subtle dot pattern.
- Ink: near-black `#111` for borders and headings, warm dark gray for body copy.
- Accent set: yellow `#f7d358`, teal `#86ccca`, pink `#ff71ce`, blue `#5d8bd8`, red `#ef476f`.
- Borders: 2-3px solid near-black for primary cards, 1px near-black for internal media/controls.
- Shadows: hard offset shadows, no blurred shadows for primary cards.
- Radius: 0 for major cards and panels; 8-12px only for thumbnails, pills, and small controls where readability benefits.
- Typography: heavy display style for page titles and card titles; clean sans-serif for body and metadata.

Component rules:

- `theme-card`: shared hard-border card shell for repeated cards.
- `theme-panel`: denser hard-border panel shell for tool/workbench sections.
- `theme-chip`: square or slightly rounded chips with strong contrast.
- `theme-control`: inputs/selects/buttons with black border, white/cream fill, clear hover/focus.
- `theme-aside`: sticky or fixed right-side panels for indexes, summaries, and metadata.
- `post-stack`: vertical article/list stack with alternating black/pink/teal/yellow shadows.

## Page Plan

### 1. Global Shell

- Replace the current translucent topbar with a yantao-like solid cream header.
- Add stronger brand treatment: `牛秘书 AIResearch` as a visible first signal.
- Keep all current navigation links and language toggle.
- Make active nav a yellow/teal hard-pill tab instead of a soft green pill.
- Redesign footer as a small hard-border strip with manifest links.

### 2. Dashboard

- Convert hero/search area into a magazine-like intro band.
- Restyle metric cards as four playful statistic tickets with colored corner labels.
- Restyle recent papers using the existing `paper-post-card`.
- Restyle top clusters and gap alerts as compact side cards with hard borders and colored shadows.

### 3. Papers Page

- Keep the newly implemented post-stack paper cards.
- Restyle toolbar as a hard-border filter console.
- Restyle pagination as square bordered controls.
- Add consistent empty/loading states.

### 4. Blog Index

- Rebuild blog cards to match yantao post cards:
  - left thumbnail,
  - right title/metadata/excerpt,
  - hard border,
  - alternating hard shadows,
  - tags/action row.
- Use `post-stack` width instead of full 1240px width, with an optional right-side info column only if content exists.

### 5. Paper Detail Workbench

- Keep the deep-reading target layout intact.
- Restyle non-blog tabs, summary blocks, evidence graph, formula/table/image panels, and extraction status panels with the same hard-card system.
- Preserve dense research readability: tables, formulas, JSON/code blocks, and graph canvases get themed chrome but not decorative rotation.

### 6. Clusters, Gaps, Digest, Synthesis, Narrative

- Convert all cards/panels to the shared `theme-card` and `theme-panel` rules.
- Use color-coded section headers for method/claim/limitation/dataset/benchmark.
- Make list rows feel like notebook slips: hard top border, compact metadata, strong link affordances.
- Keep long report text readable with wide article blocks, not narrow cards.

### 7. Map and Starmap

- Keep canvas/SVG behavior unchanged.
- Frame the graph surface as a large hard-border workbench panel.
- Convert sidebars/controls/legends to themed tool panels.
- Avoid rotation on graph canvases to prevent visual distortion.

### 8. Mobile

- Collapse topbar into wrapped navigation using current links.
- Disable card rotation on narrow screens.
- Keep hard shadows but reduce offsets to avoid horizontal overflow.
- Ensure sidebars become inline panels or floating compact controls.
- Validate at 390px and 768px widths.

## Implementation Phases

Phase 1: Theme Foundation

- Introduce global theme variables and reusable CSS component classes.
- Restyle body background, topbar, footer, controls, buttons, chips, focus states.
- Keep existing HTML mostly unchanged.

Phase 2: Cards and Lists

- Normalize metric cards, cluster cards, blog cards, gap panels, related panels, search hits, pagination.
- Extend the new paper-card approach to blog and dashboard cards where appropriate.

Phase 3: Research Detail Surfaces

- Restyle paper detail tabs, summary/evidence panels, formula/table/image/OCR layout panels.
- Preserve readability for scientific content and data tables.

Phase 4: Visualization Pages

- Restyle map/starmap shells, controls, legends, and sidebars.
- Verify canvas/SVG still renders and remains usable.

Phase 5: QA and Deploy

- Generate site, publish static output, deploy to nginx.
- Use Playwright screenshots for desktop and mobile.
- Check no horizontal overflow, no clipped text, no broken dynamic imports, no broken nav/API paths.

## Acceptance Criteria

- Public site pages share one visual language with the yantao-style paper cards and deep-reading pages.
- Admin pages remain unchanged.
- Existing public URLs continue to work.
- Existing JSON APIs continue to load dynamic paper lists and search results.
- Desktop pages at 1440px have no horizontal overflow.
- Mobile pages at 390px have no horizontal overflow.
- Deep-reading article page keeps fixed right catalog on desktop.
- Map/starmap render nonblank and controls remain usable.
- Tests for `research_site.py` pass.
- Public deployment serves the new CSS asset version.

## Test Matrix

Run automated tests:

```bash
cd /home/ubuntu/vibe_proj/niu-secretary/airesearch
.venv/bin/python -m pytest tests/test_research_site.py -q
```

Generate and deploy:

```bash
cd /home/ubuntu/vibe_proj/niu-secretary/airesearch
.venv/bin/python -m airesearch.cli generate-report-site --bundle-dir exports/mvp-current/bundle
.venv/bin/python -m airesearch.cli publish-static-site --source-dir exports/mvp-current/bundle --out-dir exports/site-current
sudo bash deploy/deploy-airesearch.sh
```

Screenshot pages:

- `/niu-secretary/airesearch/`
- `/niu-secretary/airesearch/papers/index.html`
- `/niu-secretary/airesearch/blogs/index.html`
- `/niu-secretary/airesearch/papers/wall-wm.html#deep-reading`
- `/niu-secretary/airesearch/map/index.html`
- `/niu-secretary/airesearch/starmap/index.html`
- `/niu-secretary/airesearch/gaps/index.html`
- `/niu-secretary/airesearch/synthesis/index.html`
- `/niu-secretary/airesearch/narrative/index.html`

