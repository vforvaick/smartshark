# Domain Docs

How the engineering skills should consume this repo's domain documentation when exploring the codebase.

## Layout

This is a single-context repo.

Read:

- `CONTEXT.md` at the repo root for canonical Smartshark glossary terms.
- `docs/adr/` for architectural decisions.

If either file or directory is missing in a future checkout, proceed silently. The producer skill (`/grill-with-docs`) creates domain docs lazily when terms or decisions are resolved.

## Use the glossary's vocabulary

When your output names a domain concept in an issue title, refactor proposal, hypothesis, test name, or implementation plan, use the term as defined in `CONTEXT.md`. Do not drift to synonyms the glossary explicitly avoids.

If the concept you need is not in the glossary yet, either reconsider whether the concept belongs in this domain or note the gap for `/grill-with-docs`.

## Flag ADR conflicts

If your output contradicts an existing ADR, surface it explicitly rather than silently overriding it.

Example:

> Contradicts ADR-0001 (Hybrid Wireshark Engine with Custom Investigation Workspace) — but worth reopening because...
