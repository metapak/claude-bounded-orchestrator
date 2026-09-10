## Problem and resulting behavior

Describe the concrete trigger and what changes.

## Validation

- [ ] `python scripts/validate.py`
- [ ] `python -m unittest discover -s tests -v`

## Bounded-workflow check

- [ ] One writer per scope remains intact.
- [ ] No child delegation or unbounded retry was introduced.
- [ ] Ledger data remains short, local metadata without secrets or source.
- [ ] Documentation and NOTICE attribution remain accurate.
