# Documentation-First Rule for Major Changes

When making major changes to the model (new policy logic, climate physics, monetary rules, or reward mechanics):

1. **Document first.** Update `assumptions.md` and the relevant `docs/AGENT_*.md` or design docs **before** changing code.
2. **Explain the intent.** Write a short, plain-English rationale for the change in the doc (what problem it solves, what behavior should change).
3. **Keep docs aligned.** After code changes, verify documentation still matches the code. The code is the source of truth.

This keeps reviews straightforward for central-bank and policy stakeholders.
