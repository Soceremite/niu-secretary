# Stage 3O-3P Review Editor And Bundle Integration Design

## Goal

Accelerate the reviewed-cluster workflow by adding two adjacent features:

- Stage 3O: a CLI-safe JSON editor for setting `review_status` and `review_notes` on cluster review packets.
- Stage 3P: optional report bundle inclusion of reviewed cluster summary artifacts when a review packet is supplied.

## Design

Stage 3O adds a focused module, `research_review_editor.py`, that reads a Stage 3M review packet JSON file, validates that `items` is a list, finds one exact `cluster_id`, validates the new status against the existing status set from `research_review_summary.py`, updates `review_status`, and optionally updates `review_notes`. The editor writes to `--out`; it does not mutate the source packet in place. This keeps human review files auditable and prevents accidental loss of the original generated packet.

Stage 3P extends `generate-report-bundle` with optional `--review-packet`. Existing bundle behavior stays unchanged when this flag is absent. When present, the bundle exports `reviewed-clusters.md` and `reviewed-clusters.json` using the existing reviewed summary exporter, appends the artifact to `manifest.json` and `index.md`, and records `accepted_count`, `accepted_fact_count`, and `accepted_paper_count` as extra counts.

## Error Handling

- Invalid JSON, missing `items`, unknown `cluster_id`, and unsupported status return CLI exit code 2.
- The bundle propagates reviewed summary validation errors when `--review-packet` is supplied.
- If `--notes` is omitted, existing notes are preserved.

## Tests

- Unit tests cover status editing, note preservation, missing clusters, invalid statuses, and bundle inclusion.
- CLI tests cover the new editor command and optional bundle flag.
- Full suite should continue to pass.

