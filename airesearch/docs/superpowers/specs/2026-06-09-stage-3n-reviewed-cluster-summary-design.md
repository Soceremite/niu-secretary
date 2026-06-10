# Stage 3N Reviewed Cluster Summary Design

## Goal

Turn an edited Stage 3M cluster review JSON packet into a deterministic downstream summary that only treats `accepted` review items as human-approved cluster evidence.

## Scope

Stage 3N is a file-based review consumer. It does not add database tables, mutate the source review packet, or integrate accepted clusters into narrative reports yet.

The input is the JSON output from:

```bash
python -m airesearch.cli generate-cluster-review --mode semantic --format json --out exports/research-cluster-review-current.json
```

The human review loop edits each item in that JSON by setting `review_status` to one of:

- `pending`
- `accepted`
- `rejected`
- `needs_revision`

Only `accepted` items are exported as downstream-approved clusters.

## Architecture

Add a focused module, `airesearch.research_review_summary`, that owns JSON loading, status validation, accepted-item extraction, Markdown rendering, JSON serialization, and file export.

Add a CLI command:

```bash
python -m airesearch.cli summarize-cluster-review \
  --review-packet exports/research-cluster-review-current.json \
  --out exports/reviewed-cluster-summary-current.md
```

The command supports `--format markdown|json`. It returns exit code 2 for invalid JSON structure, missing item fields, or unsupported `review_status` values.

## Data Flow

1. Read the edited review packet JSON from disk.
2. Validate the top-level object and `items` list.
3. Count all review statuses.
4. Preserve full accepted cluster facts for downstream consumers.
5. Export Markdown for human scanning or JSON for later automation.

## Error Handling

Validation is strict for review status values so accidental typos do not silently enter downstream reports. Unsupported output formats raise `ValueError`. CLI catches validation and format errors and prints the error without stack traces.

## Testing

Add unit tests for accepted/rejected/pending counts, Markdown rendering, JSON export, and invalid status rejection. Add CLI coverage for the new command using a temporary edited review packet.
