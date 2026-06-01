# Smartshark Domain Model

## Purpose

This document explains the core Smartshark domain concepts and their relationships. It expands the glossary in `CONTEXT.md` into a product model while keeping implementation details separate.

## Core Concepts

### Account

Smartshark MVP uses simple local accounts.

- **Admin Account** manages users, AI provider settings, Redaction Policy, storage limits, destructive actions, and audit visibility.
- **Analyst Account** uploads captures, runs analyses, annotates Evidence Maps, creates reports, and exports findings.

### Capture Artifact

A Capture Artifact is an immutable version of an uploaded Capture File. It is identified by content so packet references remain stable.

Key relationships:

- A Capture Artifact can have one Capture Index.
- A Capture Artifact can have many Analysis Runs.
- A Capture Artifact can have many Capture Slices.
- Evidence Links point back to Capture Artifacts.
- Archived or hard-deleted artifacts change how Evidence Links resolve.

### Capture Index

A Capture Index is a lightweight derived index of a Capture Artifact. It contains searchable metadata and common troubleshooting signals.

Expected contents:

- capture time range
- packet count and byte count
- protocols
- endpoints
- conversations and flows
- time buckets
- common troubleshooting signals such as retransmissions, resets, DNS no-response candidates, HTTP statuses, TLS alerts, and visibility anomalies

The Capture Index is not a full replacement for packet detail. Detailed frame, stream, payload, and dissector information comes from Lazy Detail Queries.

### Import Diagnostic

An Import Diagnostic explains why a Capture File could not become a Capture Artifact or could not be indexed.

Common categories:

- corrupt or invalid capture
- unsupported format
- truncated capture
- permission or storage error
- dissector/tool crash
- too large or resource-limited

An Import Diagnostic is not an AI diagnosis. It is a structured operational artifact.

### Capture Slice

A Capture Slice is a scoped subset of a Capture Artifact selected by time range, filter, endpoint pair, or conversation.

A slice can be:

- a view over the original Capture Artifact
- an exported new Capture Artifact

Evidence Links should clearly identify whether they reference the original artifact or an exported slice artifact.

### Analysis Profile

An Analysis Profile tunes Smartshark's interpretation of a Capture Artifact.

MVP profiles:

- General Network Troubleshooting
- F5 Load Balancer
- Infoblox DNS
- Verifone intelliNAC

Profiles tune:

- playbook weighting
- interview questions
- field mappings
- assumptions
- redaction behavior
- interpretation rules

Profiles do not disable generic checks. The MVP supports a single primary profile per Analysis Run.

### Analysis Mode

An Analysis Mode controls how the Analysis Run is started.

- **Quick Analysis**: optional Issue Brief, then immediate triage fan-out.
- **Deep Analysis**: Issue Brief first, Pre-Scan, gap-filling Symptom Interview, then directed triage.
- **Scoped Analysis**: analyst chooses an Analysis Scope before the agent investigates.

### Issue Brief

An Issue Brief is a free-form description from the analyst of the issue, symptoms, desired analysis, suspected causes, affected endpoints, timing, and known context.

The Issue Brief is the main human context input for Deep Analysis.

### Symptom Interview

A Symptom Interview fills gaps left by the Issue Brief. It should ask targeted questions about missing context rather than forcing the analyst through a long form.

Typical gaps:

- issue timing
- affected endpoint
- application/protocol
- expected behavior
- Capture Vantage Point
- recent changes
- desired outcome

### Analysis Scope

An Analysis Scope defines the boundary of a Scoped Analysis.

Supported MVP scope types:

- time window
- endpoint
- conversation or flow
- display filter
- symptom or playbook
- combinations of the above

### Analysis Run

An Analysis Run is a versioned execution of an Analysis Mode against a Capture Artifact.

An Analysis Run records:

- Capture Artifact
- Analysis Mode
- Analysis Profile
- Issue Brief
- Analysis Scope
- Capture Vantage Point
- assumptions
- status
- user who created it
- start/end time
- tool and AI provenance

Statuses:

- Running
- Completed
- Failed
- Cancelled
- Partial

Changing the Analysis Profile creates a new Analysis Run rather than mutating an existing one.

### Investigation Task

An Investigation Task is a scoped unit of AI investigation. Broad requests such as “analyze this PCAP” should be decomposed into Investigation Tasks.

Example tasks:

- inspect TCP health for a time window
- investigate DNS failures for one endpoint
- explain reset behavior for a flow
- run F5 visibility checks with a known VIP

### Bounded Investigation

A Bounded Investigation is a limited multi-step AI investigation. It stops when it reaches its budget, finds sufficient evidence, fails, is cancelled, or needs analyst input.

Boundaries include:

- max tool calls
- max runtime
- max context budget
- explicit scope
- visible progress
- cancellability

### Investigation Subagent

An Investigation Subagent investigates one bounded question or evidence slice without carrying the full workspace context.

Subagents are useful for parallel checks such as TCP health, DNS behavior, TLS handshake, timeline anomalies, and profile-specific interpretation.

### Evidence Map

An Evidence Map is the canonical structured output of an Analysis Run.

It links:

- claims
- Evidence Links
- filters
- affected flows
- time windows
- Claim Status
- Check Results
- provenance
- annotations

The base Evidence Map is immutable. Analyst edits become annotations, overrides, or report-selection layers.

### Claim

A Claim is a diagnostic statement produced or curated during analysis.

Claim statuses:

- Verified
- Likely
- Hypothesis
- Unsupported

Claims must obey the validator rules described in the Evidence Map schema.

### Evidence Link

An Evidence Link is a navigable reference from a claim to supporting evidence or related context.

Evidence Links should support both:

- active Deep Links inside Smartshark
- fallback textual citations in exported reports

### Deep Link

A Deep Link is a URL-like Evidence Link that reopens a specific Smartshark view.

MVP targets include:

- packet subset
- frame detail
- flow
- follow stream
- timeline window
- graph subset
- claim
- note
- report section

### Evidence Card

An Evidence Card is the main UI presentation of one claim and its supporting evidence.

It contains:

- claim status
- short claim
- explanation
- why it matters
- key facts
- Evidence Links
- actions
- report inclusion state

### Analyst Annotation

An Analyst Annotation is a human-authored note, correction, or contextual judgment attached to an Evidence Map, claim, Evidence Card, note, or report.

Annotations are valuable but are not packet evidence by themselves.

### Provenance

Provenance records the origin of claims, links, annotations, tool results, and AI text.

Source types:

- tool
- AI
- analyst
- system

### Check Result

A Check Result records the result of a playbook or sub-check.

Statuses:

- completed
- skipped
- failed
- cancelled

Check Results are visible in Evidence Maps and reports so limitations are explicit.

### Investigation Report

An Investigation Report is a human-readable narrative generated from an Evidence Map and edited by an analyst.

Suggested sections:

- Executive Summary
- Verified Findings
- Likely Findings
- Timeline / Evidence
- Hypotheses & Recommended Next Steps
- Limitations / Assumptions
- Appendix: filters and Evidence Links

### Redaction Policy

A Redaction Policy controls which packet fields, payload snippets, and investigation context may be sent to an AI model.

It is configured by Admin. Analysts can opt in per action only when policy allows.

### AI Request Log

An AI Request Log records what context category was sent to which model/provider for an analysis action.

It should support auditability without storing unnecessary sensitive payload.

### Audit Log

An Audit Log records destructive actions, account changes, provider configuration changes, redaction policy changes, and other administrative events.

### Archived Capture

An Archived Capture is a Capture Artifact hidden from normal analysis lists but still restorable. Existing Evidence Links should resolve to an archived state instead of failing silently.

## Relationship Summary

- An Admin Account creates Analyst Accounts and configures system policy.
- An Analyst Account uploads a Capture File.
- A successful import creates a Capture Artifact.
- A failed import creates an Import Diagnostic.
- A Capture Artifact has a Capture Index and may have Capture Slices.
- An Analyst starts an Analysis Run against a Capture Artifact.
- An Analysis Run uses one Analysis Mode and one Analysis Profile.
- An Analysis Run may decompose into many Investigation Tasks.
- Investigation Tasks may be executed by Investigation Subagents.
- Tool results become Check Results, Claims, Evidence Links, and Evidence Cards.
- These form the base Evidence Map.
- Analyst edits become Analyst Annotations and report-selection layers.
- Investigation Reports are generated from Evidence Maps and analyst edits.
- AI Request Logs and Audit Logs preserve system accountability.
