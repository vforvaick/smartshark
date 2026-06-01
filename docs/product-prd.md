# Smartshark Product PRD

## Problem Statement

Network troubleshooting with packet captures is slow, fragmented, and easy to miscommunicate. Analysts move between Wireshark filters, packet tables, timelines, notes, screenshots, and incident reports while trying to prove what happened. General-purpose LLM chat makes this worse if it summarizes captures without citing packet evidence: the answer may sound plausible, but the analyst cannot click back to the frames, flows, filters, or time windows that justify it.

Smartshark solves this by making evidence the center of the workflow. The product must help network ops analysts investigate PCAP/PCAPNG files, ask AI for bounded help, and produce reports where every diagnostic claim can be traced back to clickable Evidence Links or clearly marked as a Hypothesis.

## Solution

Smartshark is an evidence-first network troubleshooting workspace that combines Wireshark-style packet analysis with bounded AI investigations and clickable evidence links.

Analysts upload an offline Capture File, which becomes an immutable Capture Artifact. They choose an Analysis Mode and a primary Analysis Profile, browse packets through a web-based investigation workspace, and run asynchronous AI-assisted Analysis Runs. The AI does not replace packet analysis; it orchestrates tool-grounded checks, creates Evidence Cards, and drafts Investigation Reports from an Evidence Map. Each claim carries a Claim Status and must follow validator rules before it can be exported.

The MVP is local/self-hosted with simple Admin and Analyst accounts. It prioritizes offline PCAP analysis, deep links, Evidence Maps, report generation, redaction, and auditability. Live capture, external integrations, team workspaces, and advanced RBAC are out of scope for the first MVP.

## User Stories

1. As a network ops analyst, I want to upload a PCAP or PCAPNG file, so that I can investigate traffic in a browser-based workspace.
2. As an analyst, I want uploaded captures to become immutable Capture Artifacts, so that Evidence Links remain stable over time.
3. As an analyst, I want Smartshark to compute a Capture Index, so that common troubleshooting views load quickly.
4. As an analyst, I want failed imports to produce an Import Diagnostic, so that I know whether the file is corrupt, unsupported, too large, truncated, or blocked by a tool/storage issue.
5. As an analyst, I want to choose Quick Analysis, so that Smartshark can immediately triage a capture without a long intake process.
6. As an analyst, I want Quick Analysis to accept an optional Issue Brief, so that I can point the analysis at a known concern without being forced into an interview.
7. As an analyst, I want to choose Deep Analysis, so that I can brain dump the issue first and let Smartshark ask only the missing follow-up questions.
8. As an analyst, I want to provide an Issue Brief in free form, so that I can describe symptoms, timing, endpoints, application behavior, and suspected causes naturally.
9. As an analyst, I want Smartshark to run a Pre-Scan before Deep Analysis questions, so that the Symptom Interview is grounded in the actual capture.
10. As an analyst, I want a Symptom Interview to ask only gap-filling questions, so that I do not repeat context I already provided.
11. As an analyst, I want Smartshark to ask interleaved clarifying questions during analysis, so that gaps in Capture Vantage Point, timing, or expected behavior can be resolved when needed.
12. As an analyst, I want to choose Scoped Analysis, so that I can investigate a specific time window, endpoint, conversation, display filter, symptom, playbook, or combination.
13. As an analyst, I want General Network Troubleshooting to be the default Analysis Profile, so that the product is understandable without vendor segmentation.
14. As an analyst, I want optional F5 Load Balancer, Infoblox DNS, and Verifone intelliNAC Analysis Profiles, so that Smartshark can tune interpretation when I know the environment context.
15. As an analyst, I want Analysis Profiles to tune playbook weighting instead of disabling checks, so that the system does not miss unexpected symptoms.
16. As an analyst, I want profile-specific mapping questions to appear progressively, so that I am not forced through a long form at upload time.
17. As an analyst, I want to record Capture Vantage Point, so that Smartshark can avoid overclaiming when the capture is from SPAN, F5 client side, F5 server side, endpoint, firewall, or an unknown location.
18. As an analyst, I want packet table browsing with display filters, so that Smartshark remains useful even when the AI Investigation Panel is hidden.
19. As an analyst, I want packet detail and dissector tree views, so that I can inspect the fields behind AI claims.
20. As an analyst, I want payload/bytes preview, so that I can inspect selected packet content when policy allows.
21. As an analyst, I want conversations and flow lists, so that I can pivot from top talkers to specific traffic paths.
22. As an analyst, I want follow-stream support, so that I can inspect TCP/UDP/application conversations from the packet workspace.
23. As an analyst, I want Timeline Graphs for packets, bytes, TCP retransmissions, TCP resets, DNS behavior, and protocol/conversation activity, so that spikes become navigable evidence.
24. As an analyst, I want a Conversation Graph, so that I can see endpoints and flow weights visually.
25. As an analyst, I want graph points, edges, and time ranges to create Evidence Links, so that visual findings can be traced to packets.
26. As an analyst, I want the AI Investigation Panel to be adjustable and hideable, so that AI assistance does not dominate packet navigation.
27. As an analyst, I want Bounded Investigations, so that AI can perform multi-step analysis without running unbounded background magic.
28. As an analyst, I want Investigation Subagents to inspect focused questions, so that large captures do not bloat context and each check stays understandable.
29. As an analyst, I want visible progress for agent tool calls, so that I can trust what the agent is doing without reading verbose logs.
30. As an analyst, I want expandable tool-call details, so that I can inspect filters, counts, Evidence Links, durations, and errors.
31. As an analyst, I want failed, skipped, cancelled, and limited checks to appear in the Evidence Map and report, so that missing evidence is not hidden.
32. As an analyst, I want partial results from cancelled Analysis Runs, so that useful Evidence Cards are not lost.
33. As an analyst, I want an Evidence Map as the canonical output of each Analysis Run, so that chat answers and reports are derived from structured evidence.
34. As an analyst, I want Evidence Cards for claims, so that I can see status, key facts, evidence links, and actions in one place.
35. As an analyst, I want Evidence Links to be URL-like deep links, so that I can click from a claim to packet subsets, frame details, flows, follow-stream views, timeline windows, graph subsets, notes, and report sections.
36. As an analyst, I want Evidence Links to include fallback textual citations, so that exported reports remain useful when the Smartshark app is not available.
37. As an analyst, I want Claim Status labels, so that I can distinguish Verified Claims, Likely Claims, Hypotheses, and Unsupported Claims.
38. As an analyst, I want schema validation to reject invalid claim statuses, so that the AI cannot create a Verified or Likely claim without evidence.
39. As an analyst, I want Hypotheses to appear only as next steps, so that speculative ideas are not mixed with findings.
40. As an analyst, I want Unsupported Claims blocked from export, so that hallucinations do not become reportable conclusions.
41. As an analyst, I want Raw-Context Exploration for selected snippets, so that the LLM can still help explore details without treating them as final conclusions.
42. As an analyst, I want Raw-Context Exploration to require verification before becoming a reportable claim, so that exploration remains separate from evidence-based findings.
43. As an analyst, I want analyst annotations on claims, links, and reports, so that I can add human context that the capture does not contain.
44. As an analyst, I want annotations to have Provenance, so that future readers can distinguish tool evidence, AI text, and human judgment.
45. As an analyst, I want base Evidence Maps to remain immutable, so that reruns and edits do not obscure what the tools originally found.
46. As an analyst, I want report drafts generated from Evidence Cards, so that I save time writing incident reports.
47. As an analyst, I want to include, exclude, reorder, and edit report findings, so that the final report reflects human judgment.
48. As an analyst, I want portable Markdown/PDF export, so that I can share findings outside Smartshark.
49. As an analyst, I want native Smartshark reports with active deep links, so that teammates on the same instance can inspect the evidence directly.
50. As an analyst, I want capture slicing by time range, filter, endpoint pair, or conversation, so that large captures can be narrowed before deep analysis.
51. As an analyst, I want exported slices to become new Capture Artifacts, so that follow-up investigations can reference stable evidence.
52. As an analyst, I want encrypted traffic limitations to be explicit, so that Smartshark does not pretend to know application payload when only TLS metadata is visible.
53. As an analyst using the F5 profile, I want Smartshark to distinguish client-side and server-side visibility, so that F5-generated behavior is not mistaken for server behavior.
54. As an analyst using the F5 profile, I want to optionally provide F5 Mapping, so that VIPs, pool members, SNAT, VLAN side, and monitor sources can sharpen the analysis.
55. As an analyst using the Infoblox profile, I want DNS checks tuned for Infoblox behavior, so that no-response, response code, latency, and vantage-point evidence are interpreted correctly.
56. As an analyst using the Verifone intelliNAC profile, I want stricter redaction and payment-sensitive handling, so that analysis does not leak sensitive transaction data.
57. As an Admin, I want to seed or create the first Admin Account, so that the local instance has an accountable owner.
58. As an Admin, I want to create Analyst Accounts, so that multiple local users can use the same project space.
59. As an Admin, I want to disable accounts and manage roles, so that local access can be controlled simply.
60. As an Admin, I want to configure the AI provider globally, so that analysts use a consistent model and endpoint.
61. As an Admin, I want to configure the Redaction Policy, so that sensitive packet data is protected before AI requests.
62. As an Admin, I want Raw-Context sharing disabled by default, so that raw payloads are not sent to AI models accidentally.
63. As an Admin, I want to allow raw snippet sharing only with Analyst confirmation, so that exploratory analysis remains governed.
64. As an Admin, I want to inspect the AI Request Log, so that I know what context was sent to which model.
65. As an Admin, I want an Audit Log for destructive and administrative actions, so that account changes, deletion, and provider changes are traceable.
66. As an Admin, I want to archive Capture Artifacts, so that captures can be hidden without immediately breaking evidence history.
67. As an Admin, I want hard delete with extra confirmation, so that sensitive captures can be permanently removed when required.
68. As an Analyst, I want capture deletion restricted to Admins, so that shared local evidence is not accidentally broken.
69. As an Analyst, I want the product to warn when hard deletion will break Evidence Links, so that evidence loss is intentional.
70. As a network ops lead, I want success metrics such as time to first evidence, evidence coverage, usefulness feedback, report time saved, and unsupported claim rate, so that MVP quality can be measured.

## Implementation Decisions

- Build Smartshark as a local/self-hosted investigation workspace, not a chat-first PCAP uploader.
- Use a hybrid architecture: mature Wireshark tooling powers packet dissection and query execution, while Smartshark owns the custom Investigation Workspace, Evidence Map, Evidence Links, AI orchestration, and report workflow.
- Introduce a deep Packet Query Engine module that exposes a stable interface for packet facts, frame details, conversations, streams, time series, capture slices, and evidence target resolution.
- Implement the first Packet Query Engine adapter with Wireshark tooling, while keeping the domain model independent of raw command strings.
- Treat each uploaded capture as an immutable Capture Artifact identified by content, with derived Capture Index data and Lazy Detail Queries.
- Use a hybrid indexing model: precompute lightweight metadata, endpoints, conversations, time buckets, protocols, and common troubleshooting signals; query detailed frame/stream/dissector data lazily.
- Use asynchronous jobs for capture import, indexing, pre-scan, analysis runs, slicing, report export, cleanup, and cache maintenance.
- Allow job cancellation and preserve partial evidence with clear Analysis Run status.
- Support three Analysis Modes: Quick Analysis, Deep Analysis, and Scoped Analysis.
- Use Issue Brief as the natural free-form input for Deep Analysis; use Symptom Interview only to fill missing context.
- Use Pre-Scan before Deep Analysis questions so questions are grounded in observed traffic.
- Use General Network Troubleshooting as the default Analysis Profile.
- Support a single primary Analysis Profile per Analysis Run in the MVP.
- Treat F5, Infoblox, and Verifone intelliNAC as optional Analysis Profiles that tune playbook weighting, questions, mappings, interpretation, and redaction behavior.
- Keep the five generic playbooks as the foundation: TCP Health, DNS Resolution, HTTP/API Latency & Errors, TLS Handshake, and Path / Visibility Sanity.
- Build Evidence Map as the canonical structured result of an Analysis Run.
- Keep base Evidence Maps immutable; store analyst edits as annotations, overrides, and report-selection layers.
- Represent claims through Evidence Cards in the UI.
- Enforce Claim Status rules through schema validation instead of relying only on prompting.
- Use URL-like Deep Links for Evidence Links, so claims can open packet subsets, frame details, flows, follow streams, timeline windows, graph subsets, claims, notes, and report sections.
- Include textual fallback citations in portable exports.
- Allow Raw-Context Exploration, but require tool-grounded verification before exploratory text can become a conclusion.
- Make the AI Investigation Panel adjustable and hideable; packet navigation must remain complete without AI visible.
- Use Bounded Investigations with visible progress and expandable details.
- Use focused Investigation Subagents for bounded checks to avoid bloated context and improve parallel investigation speed.
- Use a Python/FastAPI backend, separate worker process, SQLite for local single-instance storage, React/Next.js frontend, and provider-agnostic AI orchestration for the MVP.
- Keep AI provider configuration global and Admin-only in the MVP.
- Use a two-layer Redaction Policy: Admin sets what is allowed; Analyst can opt in per action only when policy permits.
- Do not send full capture files to LLMs by default.
- Mask payloads, credentials, tokens, authorization headers, card-like numbers, and payment-sensitive identifiers by default before AI requests.
- Keep IP addresses, MAC addresses, and DNS names available by default for network troubleshooting, with optional anonymization controls.
- Tighten redaction automatically for payment-sensitive profiles such as Verifone intelliNAC.
- Use simple local authentication with Admin and Analyst roles only for MVP.
- Restrict Capture Artifact deletion to Admins.
- Use soft-delete/archive by default; allow Admin hard delete with an additional confirmation and minimal audit record.
- Make Viewer role, team workspaces, advanced RBAC, durable share links, live capture, external integrations, TLS decryption support, and multi-profile runs post-MVP.

## Testing Decisions

- Tests should focus on externally observable behavior and domain invariants, not implementation details.
- Packet Query Engine contract tests should verify that the engine can list conversations, resolve frame details, run filters, follow streams, build time series, export slices, and resolve Evidence Links against known fixture captures.
- Capture import tests should cover valid PCAP, valid PCAPNG, corrupt files, truncated files, unsupported files, missing tool errors, tool crash errors, resource-limit errors, and Import Diagnostic output.
- Capture Artifact tests should verify immutability, content hashing, archive behavior, hard-delete warnings, and link-resolution behavior for archived/deleted artifacts.
- Capture Index tests should verify protocol summaries, endpoints, conversations, time buckets, and common troubleshooting signals against small deterministic fixture captures.
- Analysis Mode tests should verify Quick Analysis fan-out, Deep Analysis Issue Brief extraction, Symptom Interview gap detection, and Scoped Analysis boundaries.
- Analysis Profile tests should verify that profile selection changes weighting/questions/mapping/redaction without disabling generic checks.
- Evidence Map validator tests should verify every Claim Status rule, including rejection of invalid Verified/Likely claims and export blocking for Unsupported Claims.
- Evidence Link tests should verify every MVP target type resolves to the correct workspace view and produces portable textual citations.
- Evidence Card tests should verify actions such as opening packet subsets, following streams, adding to report, annotating, and marking false positives.
- Report generation tests should verify that only valid claims are exported, Hypotheses are placed in next steps, Unsupported Claims are omitted, limitations are included, and portable exports include fallback citations.
- Redaction Policy tests should verify masking of payloads, credentials, tokens, authorization headers, PAN/card-like values, optional IP/MAC/DNS anonymization, raw-sharing gating, and stricter iNAC/payment behavior.
- AI Request Log tests should verify that model, provider, user, analysis run, context summary, and raw-sharing decisions are recorded without storing unnecessary sensitive payload.
- Permission tests should verify Admin and Analyst boundaries for user management, provider configuration, capture deletion, analysis execution, annotations, report export, and audit visibility.
- Async job tests should verify progress, cancellation, partial results, retry behavior, failure reporting, and idempotent job recovery.
- UI integration tests should cover upload, mode/profile selection, packet browsing, filter navigation, Evidence Card click-through, timeline brushing, report draft editing, and export.
- End-to-end fixture tests should use small representative captures for TCP retransmission/reset, DNS no-response, HTTP error/latency, TLS handshake failure, one-sided capture visibility, F5-like client/server-side ambiguity, Infoblox-like DNS behavior, and iNAC/payment-sensitive redaction.
- Good tests should assert stable domain outcomes: claims, citations, links, limitations, permissions, and report sections. They should not assert internal prompt phrasing or subprocess implementation details unless testing a contract boundary.

## Out of Scope

- Live capture or streaming traffic analysis.
- External Evidence Links to live device CLI sessions, ticketing systems, topology platforms, SIEMs, or observability platforms.
- Infoblox Grid/API/log ingestion.
- TLS key log ingestion or decryption workflows.
- Team workspaces, shared capture libraries, advanced RBAC, multi-user comments, and permissioned durable share links.
- Viewer role.
- Multi-profile Analysis Runs.
- Full external collaboration model.
- Automatic physical topology inference.
- Application dependency graph inference.
- Hosted SaaS deployment and multi-tenant security model.
- Sending full capture files to hosted LLMs by default.
- Treating AI chat answers as canonical output.

## Further Notes

- Primary persona: network ops / network engineer L2-L3. Secondary persona: NOC/SOC L1-L2.
- Root Cause language should be conservative. Smartshark should prefer Verified Findings, Likely Causes, Hypotheses, Next Evidence Needed, and Limitations unless the evidence chain strongly supports a Root Cause.
- Success metrics: time to first evidence, evidence coverage, analyst usefulness feedback, report time saved, and unsupported claim rate.
- The product should remain useful as a web packet-analysis workspace even when the AI Investigation Panel is hidden.
- The MVP should target comfortable operation on captures around 100-500 MB, with a configurable hard limit and clear guidance for larger captures.
- Issue tracker publishing was requested by the PRD skill, but this directory is not currently a git repository with an issue tracker remote. This PRD is written locally and ready to publish once a tracker is available.
