# Examples

## Bug repair

```text
Find why checkout sometimes creates duplicate orders. Use the bounded workflow:
map the affected flow, make one focused repair, run the relevant checks, freeze the
candidate, and have a separate reviewer inspect it before you report completion.
```

Likely routing: explorer → implementer → verifier → reviewer. The main session owns decisions and the result.

## Current API migration

```text
Update this integration to the current provider API. Verify the official migration
requirements first, then implement only the approved changes and test the affected flow.
```

Likely routing: researcher and explorer → implementer → verifier → reviewer.

## Opt-in UI design expertise

```text
Use /ui-design for this task. Improve the empty state while preserving our existing
components and accessibility conventions. Implement and verify the approved result.
```

The skill adds a design checklist. It grants no tools and does not make a second writer.

## Opt-in security expertise

```text
Use /secure-change while reviewing this authentication change. Identify trust boundaries,
choose the smallest approved repair, test denial paths, and disclose residual risk.
```

The skill adds security reasoning. External effects and security-sensitive decisions still remain with the main session and user authority.

## Task ledger walkthrough

```bash
python .claude/tools/task_ledger.py init
python .claude/tools/task_ledger.py add MAP --summary "Map affected checkout paths" --role explorer
python .claude/tools/task_ledger.py add FIX --summary "Apply approved checkout repair" --role implementer --depends-on MAP
python .claude/tools/task_ledger.py add VERIFY --summary "Run focused checkout checks" --role verifier --depends-on FIX
python .claude/tools/task_ledger.py start MAP
python .claude/tools/task_ledger.py complete MAP --evidence "Checkout service and tests identified"
python .claude/tools/task_ledger.py show
python .claude/tools/task_ledger.py check
```

`check` fails until every task is complete. Evidence must be a short conclusion, not copied command output.
