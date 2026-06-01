# Smartshark Documentation

## Core Product Docs

- [Product PRD](./product-prd.md) — full product requirements, user stories, implementation decisions, testing decisions, MVP scope, and non-goals.
- [MVP Scope](./mvp-scope.md) — concise MVP boundary and out-of-scope list.
- [Domain Model](./domain-model.md) — product concepts and relationships.
- [Evidence Map Schema](./evidence-map-schema.md) — conceptual schema, validator rules, claim status rules, and deep link targets.
- [Architecture Overview](./architecture-overview.md) — component architecture, data flows, permissions, storage, jobs, UI, profiles, and failure modes.
- [Implementation Modules](./implementation-modules.md) — module breakdown and testing priorities.
- [UX Workflows](./ux-workflows.md) — upload, analysis, AI panel, Evidence Cards, reports, graph, and failure UX.
- [Security, Permissions, and Redaction](./security-permissions-redaction.md) — Admin/Analyst permissions, deletion rules, provider config, redaction, AI request logs, and audit logs.
- [MVP Playbooks](./mvp-playbooks.md) — generic playbooks and optional Analysis Profiles.
- [Backlog](./backlog.md) — post-MVP capture modes, integrations, collaboration, and evidence link targets.

## Decisions

- [ADR 0001: Hybrid Wireshark Engine with Custom Investigation Workspace](./adr/0001-hybrid-wireshark-engine-custom-workspace.md)
- [ADR 0002: AI Context Redaction and Provider Policy](./adr/0002-ai-context-redaction-and-provider-policy.md)
- [ADR 0003: Local-First MVP Stack](./adr/0003-local-first-mvp-stack.md)
- [ADR 0004: Evidence Map Claim Status Enforcement](./adr/0004-evidence-map-claim-status-enforcement.md)

## Operational Notes

- `docs/failures/` records failed or blocked paths.
- `docs/learnings/` records reusable validated patterns.

## Glossary

See the root [CONTEXT.md](../CONTEXT.md) for canonical Smartshark language.
