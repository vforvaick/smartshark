# Security, Permissions, and Redaction

## Purpose

Smartshark handles sensitive packet captures. The MVP is local/self-hosted, but it still needs simple authentication, clear permissions, auditability, and conservative AI data-sharing rules.

## Account Roles

### Admin Account

Admin can:

- create Analyst accounts
- disable accounts
- assign roles
- configure AI provider settings
- configure Redaction Policy
- configure storage limits
- archive, restore, and hard-delete Capture Artifacts
- view AI Request Logs
- view Audit Logs

### Analyst Account

Analyst can:

- upload captures
- browse packet workspace
- run Quick, Deep, and Scoped Analysis
- create Analyst Annotations
- draft and export reports
- delete own draft reports and annotations
- opt in to raw-context sharing only when Admin policy permits

Analyst cannot:

- manage users
- configure AI provider
- configure Redaction Policy
- delete Capture Artifacts
- hard-delete data
- view global admin/audit logs by default

## Capture Deletion Rules

- Capture Artifact deletion is Admin-only.
- Default deletion action is archive/soft-delete.
- Archived Captures are hidden from normal lists but restorable.
- Evidence Links to archived captures should resolve to an archived state.
- Hard delete requires an extra confirmation.
- Hard delete removes files, indexes, and caches.
- Hard delete keeps a minimal Audit Log record without sensitive payload.
- UI must warn when deletion will make Evidence Links unavailable.

## AI Provider Configuration

MVP AI provider configuration is global and Admin-only.

Admin configures:

- provider
- model
- endpoint/API key
- Redaction Policy
- max tool calls
- token/context budget
- raw-context sharing defaults
- local/self-hosted endpoint if used

Analysts choose analysis mode/profile/scope but do not change provider configuration.

## Redaction Policy

Default policy:

- Do not send full Capture Artifacts to AI models.
- Send tool-grounded summaries, selected fields, and redacted snippets.
- Mask payload/body by default.
- Mask credentials, tokens, cookies, and API keys.
- Mask Authorization headers.
- Mask PAN/card-like numbers and payment-sensitive identifiers.
- Keep IP addresses by default because troubleshooting depends on them; allow optional anonymization.
- Keep MAC addresses by default; allow optional anonymization.
- Keep DNS query names by default; allow suffix/pattern masking.
- Never send raw stream content unless Admin policy permits and Analyst confirms.

## Raw-Context Sharing Policy

Raw-context sharing has two layers:

1. Admin policy decides whether raw sharing is disabled, allowed with confirmation, or allowed only for local models.
2. Analyst can opt in per action only if Admin policy allows it.

Every raw-context opt-in records:

- user
- analysis run
- provider/model
- context category
- timestamp
- whether the context was redacted or raw

## Profile-Specific Tightening

Verifone intelliNAC and other payment-sensitive profiles should tighten Redaction Policy automatically:

- raw stream sharing disabled by default
- stricter PAN/card-like detection
- stricter auth/token/header masking
- payload snippets disabled unless explicitly allowed by Admin and confirmed by Analyst
- report export warns if annotations appear to contain sensitive values
- AI Request Log records that a payment-sensitive profile was active

## AI Request Log

AI Request Log records provenance for AI calls.

It should include:

- user
- analysis run
- model/provider
- context category sent
- redaction policy applied
- raw-sharing decision
- timestamp
- brief input/output summary

It should avoid storing unnecessary sensitive payload.

## Audit Log

Audit Log records:

- account creation/disablement/role changes
- AI provider configuration changes
- Redaction Policy changes
- storage limit changes
- capture archive/restore/hard-delete
- hard-delete confirmations
- other destructive/admin actions

## Security Defaults

- Local/self-hosted deployment by default.
- Do not expose server publicly by default.
- Store provider secrets via environment/secrets mechanism, not plain UI-visible text after save.
- Require Admin setup before use.
- Use secure session management appropriate for local deployment.
- Treat Capture Artifacts as sensitive by default.
