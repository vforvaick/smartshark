# Smartshark Architecture Overview

## Architectural Goal

Smartshark should be a local/self-hosted evidence-first troubleshooting workspace. It should combine mature packet dissection with a custom product layer for Analysis Runs, Evidence Maps, Evidence Links, Bounded Investigations, report generation, redaction, and auditability.

## Accepted Architecture Decisions

- Use Wireshark tooling through a Packet Query Engine, not a raw fork of a webshark-style product interface.
- Build a custom investigation workspace optimized for Evidence Cards, deep links, reports, and an adjustable AI Investigation Panel.
- Do not send full Capture Artifacts to AI models by default.
- Use schema validation to enforce Claim Status rules.
- Use a Python/FastAPI backend, separate worker process, SQLite local storage, React/Next.js frontend, and provider-agnostic AI orchestration for MVP.

## High-Level Components

```txt
Browser UI
  ├─ Investigation Workspace
  ├─ Packet Workspace
  ├─ Timeline / Conversation Graphs
  ├─ AI Investigation Panel
  ├─ Evidence Map / Evidence Cards
  └─ Report Builder

Backend API
  ├─ Local Auth & Permissions
  ├─ Capture Artifact Service
  ├─ Analysis Run Service
  ├─ Evidence Map Service
  ├─ Report Service
  ├─ Admin Configuration Service
  └─ Audit / AI Request Log Service

Worker Runtime
  ├─ Import / Index Jobs
  ├─ Pre-Scan Jobs
  ├─ Analysis Jobs
  ├─ Capture Slice / Export Jobs
  ├─ Report Export Jobs
  └─ Cleanup Jobs

Packet Query Engine
  └─ Wireshark Adapter using tshark/sharkd/capinfos-style tooling

AI Orchestration
  ├─ Tool-Grounded Analysis
  ├─ Raw-Context Exploration
  ├─ Bounded Investigations
  ├─ Investigation Subagents
  ├─ Redaction Pipeline
  └─ Provider Adapter

Storage
  ├─ SQLite metadata DB
  ├─ Capture Artifact file store
  ├─ Derived Capture Index/cache store
  └─ Export/report store
```

## Deep Modules

### Packet Query Engine

A deep module that hides Wireshark command/tooling details behind a stable query interface.

Responsibilities:

- validate capture readability
- extract capture metadata
- run display filters
- return packet references and fields
- get frame details
- list conversations
- follow streams
- compute time series
- export capture slices
- resolve Evidence Link targets

Why it should be deep:

- It encapsulates subprocess/tool quirks, timeouts, parsing, and error categorization.
- It can be contract-tested with fixture captures.
- Analysis logic should not know how `tshark` or `sharkd` is invoked.

### Capture Artifact Service

Responsibilities:

- store immutable capture files
- compute content hash
- create Capture Artifact records
- handle archive/restore/hard-delete lifecycle
- enforce Admin-only deletion
- preserve link-resolution behavior

### Capture Indexer

Responsibilities:

- create a lightweight Capture Index
- compute top endpoints, conversations, protocol mix, time buckets, and common signals
- provide fast Pre-Scan inputs
- avoid full eager extraction of every field

### Analysis Orchestrator

Responsibilities:

- create Analysis Runs
- decompose broad requests into Investigation Tasks
- coordinate Bounded Investigations
- dispatch Investigation Subagents
- enforce budgets and cancellation
- collect Check Results
- produce base Evidence Maps

### Playbook Engine

Responsibilities:

- run generic playbooks: TCP Health, DNS Resolution, HTTP/API, TLS Handshake, Path / Visibility Sanity
- apply Analysis Profile weighting
- emit Check Results, Claims, Evidence Links, and Limitations
- avoid hiding skipped/failed checks

### Evidence Map Validator

Responsibilities:

- validate Claim Status rules
- validate Evidence Link references
- validate report eligibility
- block Unsupported Claims from exports
- ensure Hypotheses have verification steps
- ensure portable citations exist for report findings

This is a critical anti-hallucination module.

### Redaction Pipeline

Responsibilities:

- decide what packet context can be sent to AI models
- mask payload, credentials, tokens, authorization headers, card-like values, and payment-sensitive identifiers
- apply optional anonymization for IP, MAC, DNS names
- apply stricter defaults for payment-sensitive profiles
- enforce Admin policy before Analyst opt-in

### AI Provider Adapter

Responsibilities:

- keep model/provider configuration behind a stable interface
- support hosted and future local/self-hosted models
- log AI requests through AI Request Log
- avoid coupling analysis code to one provider

### Report Builder

Responsibilities:

- draft reports from Evidence Cards
- preserve report sections by Claim Status
- include Limitations and Check Results
- include active Deep Links in native reports
- include fallback textual citations in portable exports
- keep analyst edits separate from base Evidence Map

### Local Auth & Permission Service

Responsibilities:

- seed/create Admin Account
- manage Analyst Accounts
- enforce Admin vs Analyst permissions
- protect provider settings, Redaction Policy, deletion, audit visibility, and user management

## Key Data Flows

### Capture Import Flow

1. Analyst uploads PCAP/PCAPNG.
2. Backend stores temporary upload.
3. Worker validates with Packet Query Engine.
4. On success:
   - compute content hash
   - create immutable Capture Artifact
   - create Capture Index job
5. On failure:
   - create Import Diagnostic
   - show suggested next steps

### Quick Analysis Flow

1. Analyst selects Capture Artifact.
2. Analyst chooses Quick Analysis and optional Issue Brief.
3. System runs Pre-Scan.
4. Analysis Orchestrator creates default triage fan-out.
5. Playbook Engine runs checks with profile weighting.
6. Investigation Subagents may inspect bounded slices.
7. Evidence Map Validator validates output.
8. UI shows Evidence Cards and limitations.

### Deep Analysis Flow

1. Analyst selects Deep Analysis.
2. Analyst provides Issue Brief or says they do not know.
3. System runs Pre-Scan.
4. Symptom Interview asks gap-filling questions.
5. Analysis Orchestrator creates directed Investigation Tasks.
6. Checks run asynchronously with visible progress.
7. Interleaved clarifications appear when needed.
8. Evidence Map and report draft are generated.

### Scoped Analysis Flow

1. Analyst selects time window, endpoint, conversation, display filter, symptom, playbook, or combination.
2. Analysis Orchestrator creates one or more scoped Investigation Tasks.
3. Playbooks and subagents run only inside the Analysis Scope.
4. Results are returned as Evidence Cards.

### Report Flow

1. Evidence Map produces Evidence Cards.
2. AI drafts report sections from eligible cards.
3. Analyst includes/excludes/reorders cards and edits text.
4. Evidence Map Validator checks export eligibility.
5. Native report preserves Deep Links.
6. Portable export includes fallback textual citations.

### Raw-Context Exploration Flow

1. Analyst selects a snippet, stream, payload preview, or frame detail.
2. Redaction Pipeline checks Admin policy.
3. Analyst confirms sharing if policy permits.
4. AI receives redacted or approved context.
5. Output is marked exploratory.
6. Any diagnostic claim must be verified by tools before becoming Likely or Verified.

## Permission Model

### Admin

Can:

- create/disable users
- assign roles
- configure AI provider
- configure Redaction Policy
- configure storage limits
- archive/restore/hard-delete Capture Artifacts
- view AI Request Logs
- view Audit Logs

### Analyst

Can:

- upload captures
- browse packets
- run Quick/Deep/Scoped Analysis
- create annotations
- draft/edit/export reports
- delete own draft reports/annotations
- opt in to raw-context sharing only when Admin policy permits

Cannot:

- manage users
- change provider settings
- change Redaction Policy
- delete Capture Artifacts
- view global audit/admin logs unless explicitly allowed later

## Storage Model

MVP storage should support:

- local metadata DB
- capture artifact files
- capture index/cache files
- evidence maps
- analysis run records
- annotations
- reports and exports
- AI request logs
- audit logs

Capture Artifacts should be immutable. Derived indexes and caches can be rebuilt.

## Job Model

Heavy operations must be asynchronous:

- capture import/index
- pre-scan
- quick/deep/scoped analysis
- capture slicing/export
- report export
- cleanup/cache maintenance

Jobs should support:

- status
- progress messages
- cancellation where safe
- retry
- failure category
- partial results

## UI Architecture

The browser UI should be workspace-first, not chat-first.

Core areas:

- capture/session navigator
- packet table and filter bar
- packet details and payload preview
- conversations/flows list
- Timeline Graph
- Conversation Graph
- Evidence Cards / Evidence Map
- Report Builder
- adjustable/hideable AI Investigation Panel

The AI panel should never be required for basic packet navigation.

## Graph Scope

MVP graphs:

- Conversation Graph: endpoints as nodes, conversations as weighted edges.
- Timeline Graph: time-series metrics for packets, bytes, TCP retransmissions, TCP resets, DNS behavior, and protocol/conversation activity.

Out of MVP:

- physical topology inference
- L2/L3 topology mapping
- application dependency graph inference
- external topology integrations

## Analysis Profiles

### General Network Troubleshooting

Default. Runs generic network playbooks with no vendor assumptions.

### F5 Load Balancer

Tunes checks for:

- client-side vs server-side connection behavior
- VIP/pool/pool-member mapping
- SNAT
- health checks
- F5-generated resets
- one-arm/two-arm visibility ambiguity
- Capture Vantage Point

### Infoblox DNS

Tunes checks for:

- DNS response/no-response patterns
- response codes
- latency by client/server/query
- TCP/UDP 53 behavior
- endpoint capture comparison
- appliance role context when provided manually

### Verifone intelliNAC

Tunes checks for:

- terminal connectivity
- authentication/authorization path behavior
- transaction-path network reachability
- HTTP/TLS/TCP/path symptoms
- stricter payment-sensitive redaction

## Security and Privacy

MVP security posture:

- local/self-hosted by default
- simple local auth required
- no public exposure by default
- global Admin-controlled AI provider settings
- no full capture upload to LLM by default
- raw-context sharing disabled by default
- AI Request Log records model/provider/context category
- Audit Log records destructive/admin changes

Default redaction:

- mask payload/body by default
- mask credentials/tokens/cookies/API keys
- mask Authorization headers
- mask PAN/card-like values and payment-sensitive identifiers
- keep IP addresses by default, optional anonymization
- keep MAC addresses by default, optional anonymization
- keep DNS names by default, optional suffix/pattern masking
- never send raw stream content unless Admin policy permits and Analyst confirms

## Failure Modes

Smartshark should explicitly handle:

- corrupt capture
- unsupported capture format
- truncated capture
- missing Wireshark tooling
- tool crash
- indexing timeout
- capture too large
- encrypted payload limitation
- unknown Capture Vantage Point
- one-sided capture visibility
- cancelled job
- failed playbook
- skipped playbook
- redaction prevents detailed AI context

Failures and limitations should appear in Evidence Maps and Investigation Reports.

## Deployment Shape

MVP is local/self-hosted single-instance.

Post-MVP can introduce:

- Postgres
- team workspaces
- advanced RBAC
- durable share links
- external integrations
- hosted/SaaS deployment
- local model packages

## Open Implementation Questions

These can be resolved during implementation planning:

- exact worker queue technology
- exact Wireshark process management strategy
- exact SQLite schema
- capture file storage directory layout
- report export renderer
- frontend component library
- model/provider adapter interface details
