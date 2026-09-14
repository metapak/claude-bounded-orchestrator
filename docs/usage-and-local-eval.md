[English](usage-and-local-eval.md) | [Türkçe](usage-and-local-eval.tr.md)

# Usage reporting and optional local evaluation

The tool does not parse Claude transcript files and does not enable telemetry. Without an explicitly supplied sanitized OpenTelemetry export it reports `unavailable`; Claude Code's `/usage` remains the manual fallback.

```bash
python .claude/tools/usage_report.py
python .claude/tools/usage_report.py --input sanitized-otlp.json --json
```

Only token/cost metric points in the supplied OTLP JSON or JSONL are summarized. Reported values are not automatically quota percentages or billing totals.
Only OTLP Sum metrics with explicit delta or cumulative temporality are accepted. Delta points are added; cumulative points are differenced per resource/attribute stream, with a lower value treated as a counter reset. Unknown temporality is skipped and reported.

Copy `.claude/bounded-orchestrator.eval.example.json`, edit its explicit `argv`, then invoke it yourself:

```bash
python .claude/tools/local_eval.py .claude/local-eval.json
python .claude/tools/task_ledger.py require-eval --label focused-tests
python .claude/tools/task_ledger.py check
```

The shell-free runner is bounded by a timeout and stores an ignored digest summary. This is a project-specific check, not a universal benchmark. The ledger records stable attempts/events, interruption states, one bounded retry, and route-back ownership.
Each pass is bound to a privacy-safe fingerprint of HEAD plus relevant tracked and untracked worktree content. A later candidate change makes the pass stale; ignored evaluation summaries are excluded from the fingerprint.
