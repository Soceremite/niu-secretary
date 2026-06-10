# Stage 4A MVP Pipeline And Static Site Design

Goal: make AIResearch deployable with one command over the local paper database and existing fact cache.

Scope:
- Add `run-mvp-pipeline` as the fast path from sync -> cards -> code links -> facts -> audit -> repair -> clusters -> review packet -> report bundle -> static site.
- Reuse existing `research_facts` unless `--refresh-facts` is supplied, so normal publishing does not call the LLM again.
- Add `generate-report-site` to convert a report bundle into `index.html` with linked Markdown/JSON artifacts.
- Keep the site static and dependency-free for local preview, nginx, or any static host.

Non-goals:
- No new human review workflow.
- No full frontend application or server.
- No broad test expansion beyond smoke coverage for the new上线入口.
