# Smartshark

Smartshark is a network troubleshooting assistant that helps analysts move between packet evidence, traffic views, and explanatory notes without losing investigative context.

## Language

**Evidence**:
A verifiable packet-level or flow-level fact that supports an analysis. Evidence must identify the specific observed traffic being referenced, not just summarize an AI conclusion.
_Avoid_: AI claim, finding without citation

**Evidence Link**:
A navigable reference from an analysis to the exact supporting evidence or related investigative note. Evidence links let analysts move back and forth between conclusions and the material that justifies them.
_Avoid_: Plain citation, static reference

**External Evidence Link**:
An evidence link whose target lives outside Smartshark, such as a device session, ticket, topology system, or external observability platform.
_Avoid_: Integration, external reference

**Capture File**:
A saved packet capture used as the stable source material for an investigation. A capture file gives evidence fixed frame numbers, timestamps, conversations, and filters that can be revisited.
_Avoid_: Dump, upload, file

**Live Traffic**:
Network traffic observed while it is still being captured or streamed. Live traffic is less stable as evidence because the observed set can change during analysis.
_Avoid_: Realtime pcap, stream

**Tool-Grounded Analysis**:
An analysis whose diagnostic claims come from explicit Smartshark queries, computations, or dissector results. Tool-grounded analysis is the authoritative form for conclusions and reports.
_Avoid_: Chat answer, LLM-only analysis

**Raw-Context Exploration**:
An exploratory interpretation of raw packet details, stream text, or selected snippets. Raw-context exploration can guide investigation, but must be verified as tool-grounded analysis before becoming a conclusion.
_Avoid_: Final diagnosis, verified finding

**Claim Status**:
A confidence label that tells the analyst how strongly an AI statement is supported by evidence. Claim statuses are Verified, Likely, Hypothesis, and Unsupported.
_Avoid_: Confidence score, certainty

**Verified Claim**:
A diagnostic claim directly supported by one or more evidence links.
_Avoid_: Proven by AI, final answer

**Likely Claim**:
A diagnostic claim supported by evidence but still missing enough context to be treated as a final root cause.
_Avoid_: Probable answer, final conclusion

**Hypothesis**:
A plausible explanation or next investigation direction that is not yet strongly supported by evidence.
_Avoid_: Guess, diagnosis

**Unsupported Claim**:
A statement that lacks sufficient evidence and must not appear as a reportable conclusion.
_Avoid_: Hallucination, speculation

**Investigation Workspace**:
The primary Smartshark interface where analysts navigate captures, traffic views, evidence links, AI assistance, and report notes together.
_Avoid_: Chat app, dashboard

**AI Investigation Panel**:
An optional, adjustable workspace panel where the AI agent explains, queries, and drafts evidence-backed analysis. The panel must never be required for basic packet navigation.
_Avoid_: Chat window, assistant sidebar

**Bounded Investigation**:
A limited multi-step AI investigation that runs a visible sequence of tool-backed checks and stops when it reaches its budget, finds sufficient evidence, or needs analyst input.
_Avoid_: Autonomous agent, background magic

**Investigation Subagent**:
A focused helper agent that investigates one bounded question or evidence slice without carrying the full workspace context.
_Avoid_: Worker, bot, parallel chat

**Analysis Scope**:
The selected boundary for a scoped analysis, such as a time window, endpoint, conversation, display filter, symptom, playbook, or combination of these.
_Avoid_: Search parameter, filter only

**Investigation Task**:
A scoped unit of AI investigation over a capture file, time window, endpoint, protocol, filter, symptom, or playbook. Broad user requests should be decomposed into investigation tasks before analysis.
_Avoid_: Analyze everything, free-form chat request

**Issue Brief**:
A free-form description from the analyst of the issue, symptoms, desired analysis, suspected causes, affected endpoints, timing, and known context for a capture artifact.
_Avoid_: Form, ticket summary

**Symptom Interview**:
A short, structured conversation that fills gaps left by the issue brief, capturing what the user experienced, when it happened, who or what was affected, and what outcome they expected. A symptom interview helps scope investigation tasks before or during capture analysis.
_Avoid_: Intake form, generic questionnaire

**Quick Analysis**:
A capture analysis mode that immediately decomposes a broad request into the default triage fan-out without interviewing the user first.
_Avoid_: Auto analysis, one-click diagnosis

**Deep Analysis**:
A capture analysis mode that starts with a symptom interview before directing the triage fan-out.
_Avoid_: Full analysis, expert mode

**Scoped Analysis**:
A capture analysis mode where the analyst chooses a specific flow, time window, filter, endpoint, or symptom before the agent investigates.
_Avoid_: Manual mode, narrow search

**Pre-Scan**:
A lightweight, tool-grounded summary of a capture file used to guide analysis mode selection and symptom interview questions. A pre-scan is not a diagnosis.
_Avoid_: Initial diagnosis, AI summary

**Analysis Run**:
A versioned execution of an analysis mode against a capture artifact using a specific analysis profile, issue brief, scope, assumptions, and tool provenance.
_Avoid_: Session, chat thread

**Evidence Map**:
The canonical structured output of an analysis run, linking claims to evidence links, filters, affected flows, time windows, and claim statuses.
_Avoid_: Report, chat answer

**Evidence Card**:
A compact presentation of one claim and its supporting evidence links, key facts, status, and analyst actions.
_Avoid_: Footnote, citation only

**Investigation Report**:
A human-readable narrative generated from an evidence map. An investigation report summarizes findings, timeline, likely causes, and recommended next steps.
_Avoid_: Evidence map, raw analysis

**Analyst Annotation**:
A human-authored note, correction, or contextual judgment attached to an evidence map. Analyst annotations are useful context but are not packet evidence by themselves.
_Avoid_: Evidence, AI claim

**Provenance**:
The recorded origin of a claim, evidence link, or annotation, including whether it came from a tool, AI agent, or analyst action.
_Avoid_: Metadata, audit field

**Packet Query Engine**:
The domain boundary that turns capture files into queryable packet facts, conversations, streams, time series, and evidence link targets.
_Avoid_: tshark wrapper, parser

**Deep Link**:
A URL-like evidence link that can reopen a specific Smartshark view, such as a packet subset, flow, timeline window, graph, report claim, or investigation note.
_Avoid_: Internal pointer, app state reference

**Capture Artifact**:
An immutable version of a capture file identified by its content. Evidence links and reports refer to capture artifacts so their packet references remain stable.
_Avoid_: Upload, mutable file

**Capture Slice**:
A scoped subset of a capture artifact selected by time range, filter, endpoint pair, or conversation. A capture slice can be used as a view or exported as a new capture artifact.
_Avoid_: Cropped file, filtered result

**Redaction Policy**:
The rules that decide which packet fields, payload snippets, and investigation context may be sent to an AI model. A redaction policy protects sensitive traffic while preserving enough detail for analysis.
_Avoid_: Privacy setting, masking

**AI Request Log**:
A provenance record of what context was sent to which AI model for an analysis action.
_Avoid_: Prompt history, chat log

**Admin Account**:
A local user account that can manage users, AI provider settings, redaction policy, storage limits, destructive actions, and audit visibility.
_Avoid_: Superuser, owner

**Analyst Account**:
A local user account that can upload captures, run analyses, annotate evidence maps, create reports, and export findings within the local project space.
_Avoid_: Regular user, operator

**Audit Log**:
A record of destructive actions, account changes, provider configuration changes, and other administrative events.
_Avoid_: Debug log, activity feed

**Archived Capture**:
A capture artifact hidden from normal analysis lists but still restorable and still resolvable by existing evidence links as archived.
_Avoid_: Deleted file, inactive upload

**Import Diagnostic**:
A structured explanation of why a capture file could not be imported or indexed, including file metadata, attempted tools, error category, safe error excerpt, and suggested next steps.
_Avoid_: Upload error, failure toast

**Capture Index**:
A lightweight derived index of a capture artifact containing searchable packet metadata, endpoints, conversations, time buckets, protocols, and common troubleshooting signals.
_Avoid_: Full parse, database copy

**Lazy Detail Query**:
A packet query performed only when detailed frame, stream, payload, or dissector information is needed.
_Avoid_: Eager extraction, full indexing

**F5 Load Balancer Behavior**:
Traffic behavior shaped by an F5 device, including client-side versus server-side connections, pool member selection, health checks, SNAT, resets, and one-arm or two-arm visibility constraints.
_Avoid_: Generic TCP behavior, server behavior

**Infoblox DNS Behavior**:
DNS behavior involving an Infoblox appliance, including query/response patterns, timeout symptoms, authoritative or recursive response codes, and appliance-side service visibility.
_Avoid_: Generic DNS only

**Verifone intelliNAC Behavior**:
Network access or transaction-path behavior involving Verifone intelliNAC, especially where authentication, authorization, terminal connectivity, or payment network reachability affects observed traffic.
_Avoid_: Generic application behavior

**Capture Vantage Point**:
The network location or path perspective from which a capture artifact was recorded. Vantage point controls what claims can be verified, especially for load balancer, SPAN, asymmetric path, and endpoint comparison analysis.
_Avoid_: Source, interface, capture place

**F5 Mapping**:
A user-provided mapping between packet-visible addresses and F5 concepts such as virtual server, VIP address, pool, pool member, VLAN side, SNAT address, or monitor source. F5 mapping sharpens load balancer analysis but is optional.
_Avoid_: F5 config import, topology

**Analysis Profile**:
A selectable analysis context that tunes Smartshark's questions, playbook weighting, field mappings, and interpretation rules for a capture artifact. General Network Troubleshooting is the default profile; F5, Infoblox, and Verifone intelliNAC are optional profiles.
_Avoid_: Product module, separate app, segmented mode
