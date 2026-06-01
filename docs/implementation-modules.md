# Implementation Modules

## Purpose

This document lists the major modules needed for Smartshark MVP and identifies deep modules that should be tested in isolation.

## Deep Modules to Prioritize

### Packet Query Engine

Stable interface over Wireshark tooling.

Core capabilities:

- import validation
- capture metadata extraction
- display filter query
- packet subset query
- frame detail lookup
- conversation listing
- follow stream
- timeline metrics
- capture slicing/export
- Evidence Link target resolution

Testing priority: highest.

### Evidence Map Validator

Enforces anti-hallucination rules.

Core capabilities:

- validate Claim Status rules
- validate Evidence Links
- validate report eligibility
- block Unsupported Claims from export
- enforce Hypothesis placement
- verify portable citation coverage

Testing priority: highest.

### Redaction Pipeline

Protects sensitive context before AI calls.

Core capabilities:

- apply Admin Redaction Policy
- detect/mask payload, tokens, auth headers, card-like values
- optional anonymization for IP/MAC/DNS
- stricter payment-sensitive profile handling
- raw-sharing gate with Analyst confirmation

Testing priority: highest.

### Analysis Orchestrator

Coordinates Analysis Runs and Bounded Investigations.

Core capabilities:

- create Analysis Run
- decompose broad requests into Investigation Tasks
- run profile-weighted playbooks
- coordinate subagents
- enforce budgets
- handle cancellation/partial results
- collect Check Results and Evidence Cards

Testing priority: high.

### Playbook Engine

Runs troubleshooting checks.

MVP playbooks:

- TCP Health
- DNS Resolution
- HTTP/API Latency & Errors
- TLS Handshake
- Path / Visibility Sanity

Profile tuning:

- F5 Load Balancer
- Infoblox DNS
- Verifone intelliNAC

Testing priority: high.

### Capture Artifact Service

Owns immutable captures and lifecycle.

Core capabilities:

- create artifact
- hash content
- archive/restore
- hard-delete flow
- rebuild derived data
- link availability state

Testing priority: high.

### Capture Indexer

Creates lightweight derived capture metadata.

Core capabilities:

- protocol mix
- top endpoints
- conversations
- time buckets
- common troubleshooting flags
- Pre-Scan summary

Testing priority: high.

## Supporting Modules

### Local Auth & Permission Service

- Admin/Analyst accounts
- login/session management
- role enforcement
- first Admin setup

### Admin Configuration Service

- AI provider settings
- Redaction Policy
- storage limits
- raw-context sharing policy

### AI Provider Adapter

- provider-agnostic model calls
- hosted/local endpoint support
- request metadata
- error categories

### AI Request Log Service

- records AI request provenance
- stores context category and redaction info
- avoids unnecessary sensitive payload storage

### Audit Log Service

- destructive/admin action log
- account changes
- provider/redaction/storage changes

### Report Builder

- AI draft from Evidence Cards
- analyst edits
- export validation
- native and portable export

### Deep Link Resolver

- parse Smartshark URLs
- resolve archived/deleted/unavailable states
- open packet/flow/timeline/graph/report/note targets

### Job Runtime

- async job dispatch
- progress
- cancellation
- retry
- partial-result persistence

### UI Workspace Components

- capture navigator
- upload/import diagnostic
- packet table/filter
- packet detail
- payload preview
- conversation list
- Timeline Graph
- Conversation Graph
- Evidence Cards
- Evidence Map view
- report builder
- AI Investigation Panel
- admin settings

## Test Ownership Recommendation

Write strong unit/contract tests for:

- Packet Query Engine
- Evidence Map Validator
- Redaction Pipeline
- Capture Artifact Service
- Analysis Orchestrator
- Playbook Engine
- Deep Link Resolver

Write integration/e2e tests for:

- upload to Evidence Card
- Quick Analysis
- Deep Analysis with Issue Brief
- Scoped Analysis from timeline brush
- report export
- permission boundaries
- redaction opt-in

## Module Boundary Rule

Analysis logic should consume domain interfaces and Evidence Map entities, not raw Wireshark subprocess output. UI should consume Evidence Cards, Evidence Links, and query APIs, not internal tool-call details.
