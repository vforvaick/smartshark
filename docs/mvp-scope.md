# Smartshark MVP Scope

## Positioning

Smartshark is an evidence-first network troubleshooting workspace that combines Wireshark-style packet analysis with bounded AI investigations and clickable evidence links.

## MVP Goal

Smartshark MVP is a local/self-hosted investigation workspace for offline PCAP/PCAPNG troubleshooting. It combines Wireshark-style packet navigation with bounded, evidence-based AI analysis.

## In Scope

1. **Local authentication**
   - Seed/admin setup.
   - Admin can create Analyst accounts.
   - Admin and Analyst roles only.

2. **Capture artifacts**
   - Upload PCAP/PCAPNG.
   - Store as immutable Capture Artifacts identified by content.
   - Support soft-delete/archive by Admin and hard-delete by Admin with confirmation.

3. **Analysis modes**
   - Quick Analysis: optional brief, then immediate triage fan-out.
   - Deep Analysis: Issue Brief first, gap-filling Symptom Interview, then directed triage.
   - Scoped Analysis: user selects a time window, endpoint, conversation, display filter, symptom, playbook, or combination.

4. **Analysis profiles**
   - General Network Troubleshooting as default.
   - Optional single primary profile per Analysis Run: F5 Load Balancer, Infoblox DNS, Verifone intelliNAC.
   - Profiles tune weighting, questions, mapping, and interpretation; they do not disable generic checks.

5. **Packet workspace baseline**
   - Packet table with display filter.
   - Packet detail/dissector tree.
   - Payload/bytes preview.
   - Conversations/flows list.
   - Follow stream.
   - Timeline/graph with packet, byte, TCP retransmission, TCP reset, DNS, and protocol/conversation activity metrics.

6. **Async analysis jobs**
   - Capture import/index.
   - Pre-scan.
   - Quick/Deep/Scoped Analysis Runs.
   - Capture slicing/export.
   - Report export.
   - Job progress, cancellation, retry, and partial results.

7. **Evidence-based AI analysis**
   - Tool-grounded analysis is authoritative.
   - Raw-context exploration is allowed but must be verified before becoming a conclusion.
   - Bounded multi-step investigations can use focused Investigation Subagents.
   - Claim status rules are enforced by schema validation.

8. **Evidence Maps and Evidence Cards**
   - Evidence Map is the canonical structured output of an Analysis Run.
   - Evidence Cards present claim, status, key facts, and Evidence Links.
   - Base Evidence Map is immutable; analyst edits are annotations/revisions.

9. **Deep links and export**
   - Evidence Links use URL-like deep links to packets, flows, timeline windows, graph subsets, notes, and report claims.
   - Native reports keep active Smartshark links.
   - Portable Markdown/PDF exports include fallback textual citations: frames, timestamps, filters, endpoint tuples.

10. **Report workflow**
    - AI drafts report from Evidence Cards.
    - Analyst approves/edits included cards, wording, annotations, and ordering.
    - Hypotheses appear only in a Hypotheses / Next Steps section.
    - Unsupported claims cannot be exported as report findings.

11. **Admin configuration**
    - Global AI provider configuration by Admin.
    - Redaction Policy by Admin.
    - Raw-context sharing controlled by Admin policy and Analyst per-action confirmation when permitted.
    - AI Request Log and Audit Log.

12. **Capture slicing**
    - Slice by time range, display/BPF-like filter, endpoint pair, or conversation.
    - Slices can be used as views or exported as new Capture Artifacts.

## Out of Scope for MVP

- Live capture / streaming analysis.
- External Evidence Links to live device CLI, ticketing, topology, SIEM, or observability platforms.
- Infoblox Grid/API/log integration.
- Team workspaces, advanced RBAC, shared capture libraries, multi-user comments, and durable permissioned share links.
- Viewer role.
- Multi-profile Analysis Runs.
- Full external collaboration/link permission model.
