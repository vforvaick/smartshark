# Smartshark UX Workflows

## UX Principle

Smartshark is workspace-first and chat-assisted. The AI Investigation Panel is useful, adjustable, and hideable, but packet navigation must remain complete without it.

## Main Workspace

Core regions:

- Capture/session navigator
- Packet table and display filter
- Packet detail/dissector tree
- Payload/bytes preview
- Conversations/flows list
- Timeline Graph
- Conversation Graph
- Evidence Cards / Evidence Map
- Report Builder
- AI Investigation Panel

## Upload Flow

1. User logs in.
2. User uploads PCAP/PCAPNG.
3. User selects Analysis Profile; default is General Network Troubleshooting.
4. User optionally records Capture Vantage Point.
5. Import job runs.
6. On success, Capture Artifact and Capture Index are created.
7. On failure, Import Diagnostic appears.

## Analysis Mode Selection

After import, user chooses:

1. Quick Analysis
2. Deep Analysis
3. Scoped Analysis

### Quick Analysis

- Optional prompt: “Anything specific to look for?”
- Can be skipped.
- Runs Pre-Scan and default triage fan-out immediately.

### Deep Analysis

- Starts with Issue Brief.
- Prompt: “Ceritakan singkat issue yang terjadi atau apa yang ingin dianalisis dari PCAP ini. Boleh brain dump bebas: gejala, waktu kejadian, IP/host, aplikasi, error, lokasi capture, atau dugaan awal.”
- System extracts known fields from the brief.
- Pre-Scan runs.
- Symptom Interview asks only missing questions.
- Analysis proceeds with profile-weighted triage.

### Scoped Analysis

User selects one or more Analysis Scope items:

- time window
- endpoint
- conversation/flow
- display filter
- symptom/playbook

Scoped Analysis runs checks only within that boundary.

## AI Investigation Panel

Panel requirements:

- adjustable width
- hide/show toggle
- visible progress log
- expandable tool-call details
- cancellation control
- interleaved clarification prompts
- Evidence Card creation feedback

Progress log examples:

- “Running TCP Health checks…”
- “Found 42 retransmission candidates.”
- “Checking DNS response gaps…”
- “F5 profile limitation: capture vantage point unknown.”
- “Created 5 Evidence Cards.”

Expandable details should show:

- tool/check name
- filter/query
- counts
- Evidence Links
- duration
- error/limitation

## Evidence Card UX

Each Evidence Card should show:

- Claim Status
- short claim
- why it matters
- key facts
- Evidence Links
- actions

Actions:

- open packet subset
- open frame detail
- open flow
- follow stream
- open timeline window
- open graph subset
- add to report
- annotate
- mark false positive
- promote/demote status when valid

## Deep Link UX

Deep Links should work from:

- AI panel
- Evidence Cards
- Evidence Map
- report builder
- native reports
- exported Markdown/PDF when app is accessible

If target is unavailable:

- archived capture: show archived state and restore guidance
- hard-deleted capture: show unavailable state and textual citation
- permission denied: show permission message
- missing index/cache: offer rebuild where possible

## Report Builder UX

1. AI drafts report from Evidence Cards.
2. Cards are grouped by status:
   - Verified Findings
   - Likely Findings
   - Hypotheses / Next Steps
   - Limitations / Assumptions
3. Analyst selects cards to include.
4. Analyst edits wording and adds annotations.
5. Validator checks export eligibility.
6. User exports native report or portable Markdown/PDF.

Unsupported Claims must not appear in final report findings.

## Graph UX

### Timeline Graph

Metrics:

- packets per second
- bytes per second
- TCP retransmissions over time
- TCP resets over time
- DNS queries/responses/timeouts over time
- protocol/conversation activity over time

Interactions:

- click spike to open packet subset
- brush time range to create Scoped Analysis
- turn graph point into Evidence Link

### Conversation Graph

- nodes are endpoints
- edges are conversations/flows
- edge weight represents packets/bytes/errors
- click edge to open flow or packet subset
- selected subgraph can become Evidence Link

## Failure UX

Failed/skipped/cancelled checks should be explicit.

Examples:

- “TLS Handshake playbook skipped: no TLS traffic detected.”
- “HTTP/API playbook failed: query timed out. Suggested next step: slice capture by time window.”
- “F5 profile limitation: capture vantage point unknown, so client-side/server-side attribution remains Hypothesis.”

## Encrypted Traffic UX

When payload is encrypted, report visible limitation:

> Application payload is encrypted; analysis is limited to transport/TLS metadata unless keys/decrypted capture are provided.

AI should not infer HTTP body/path/status from encrypted payload.
