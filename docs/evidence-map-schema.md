# Evidence Map Schema

## Purpose

The Evidence Map is the canonical structured output of a Smartshark Analysis Run. Chat answers and reports are derived from it. The schema must prevent evidence-free AI claims from becoming reportable findings.

This document describes the MVP-level conceptual schema and validation rules. It is intentionally technology-neutral.

## Top-Level Shape

```ts
type EvidenceMap = {
  id: string
  analysisRunId: string
  captureArtifactId: string
  generatedAt: string
  version: number
  status: 'complete' | 'partial' | 'failed' | 'cancelled'
  summary: EvidenceMapSummary
  claims: Claim[]
  evidenceLinks: EvidenceLink[]
  evidenceCards: EvidenceCard[]
  checkResults: CheckResult[]
  annotations: AnalystAnnotation[]
  provenance: Provenance[]
  limitations: Limitation[]
}
```

## Analysis Run Context

```ts
type AnalysisRunContext = {
  analysisRunId: string
  captureArtifactId: string
  mode: 'quick' | 'deep' | 'scoped'
  profile: 'general' | 'f5_load_balancer' | 'infoblox_dns' | 'verifone_intellinac'
  issueBrief?: string
  scope?: AnalysisScope
  captureVantagePoint?: CaptureVantagePoint | 'unknown'
  createdBy: string
  startedAt: string
  endedAt?: string
  status: 'running' | 'completed' | 'failed' | 'cancelled' | 'partial'
}
```

## Analysis Scope

```ts
type AnalysisScope = {
  timeRange?: TimeRange
  endpoints?: EndpointRef[]
  conversations?: FlowRef[]
  displayFilter?: string
  symptoms?: string[]
  playbooks?: string[]
}
```

A Scoped Analysis may combine multiple scope fields.

## Claim

```ts
type Claim = {
  id: string
  status: 'verified' | 'likely' | 'hypothesis' | 'unsupported'
  title: string
  explanation: string
  whyItMatters?: string
  evidenceLinkIds: string[]
  assumptions?: string[]
  missingContext?: string[]
  verificationStep?: string
  checkResultIds?: string[]
  provenanceIds: string[]
  createdAt: string
}
```

### Claim Status Rules

#### Verified

A Verified Claim must:

- have at least one Evidence Link
- have citation fields sufficient for packet or flow verification
- have no unresolved assumptions
- be produced from Tool-Grounded Analysis or analyst promotion backed by evidence

A Verified Claim must not rely only on Raw-Context Exploration.

#### Likely

A Likely Claim must:

- have at least one Evidence Link
- include assumptions or missing context
- include a recommended verification step or next evidence to collect

Likely Claims are reportable, but must remain distinct from Verified Claims.

#### Hypothesis

A Hypothesis:

- may have zero Evidence Links
- must include a verification step
- must appear only in Hypotheses / Next Steps sections when exported
- must not appear under Verified Findings or Likely Findings

#### Unsupported

An Unsupported Claim:

- may have zero Evidence Links
- cannot be exported as a report finding
- should be visible only in internal/debug analysis contexts
- should be used to capture rejected or insufficiently supported AI output

## Evidence Link

```ts
type EvidenceLink = {
  id: string
  targetType: EvidenceTargetType
  deepLink: string
  captureArtifactId?: string
  analysisRunId?: string
  reportId?: string
  citation: EvidenceCitation
  filter?: string
  timeRange?: TimeRange
  frameRefs?: FrameRef[]
  flowRefs?: FlowRef[]
  graphRefs?: GraphRef[]
  noteRef?: string
  provenanceIds: string[]
}
```

## Evidence Target Types

```ts
type EvidenceTargetType =
  | 'packet_subset'
  | 'frame_detail'
  | 'flow'
  | 'follow_stream'
  | 'timeline_window'
  | 'graph_subset'
  | 'claim'
  | 'note'
  | 'report_section'
```

### packet_subset

Opens a packet table with filter/time/frame constraints.

Required citation should include at least one of:

- frameRefs
- timeRange + filter
- flowRefs + filter

### frame_detail

Opens one exact frame.

Required:

- captureArtifactId
- frame number

### flow

Opens a conversation/flow view.

Required:

- captureArtifactId
- flow identifier or tuple

### follow_stream

Opens follow-stream view.

Required:

- captureArtifactId
- stream identifier
- protocol

### timeline_window

Opens a timeline/metric window.

Required:

- captureArtifactId
- timeRange
- metric or filter

### graph_subset

Opens a graph with selected nodes/edges or filters.

Required:

- captureArtifactId
- graph type
- node/edge/filter selection

### claim

Opens a claim inside an Evidence Map or report.

Required:

- analysisRunId
- claimId

### note

Opens an Analyst Annotation or investigation note.

Required:

- note/annotation identifier

### report_section

Opens a section or claim in an Investigation Report.

Required:

- reportId
- section or claim reference

## Evidence Citation

```ts
type EvidenceCitation = {
  text: string
  frames?: number[]
  timeRange?: TimeRange
  endpoints?: EndpointRef[]
  tuple?: FiveTuple
  protocol?: string
  filter?: string
  streamId?: string
  metric?: string
}
```

Portable exports must include `text` plus enough structured citation fields to understand the evidence without opening Smartshark.

Example textual citation:

> Frames 1204, 1211, and 1220; filter `tcp.analysis.retransmission && ip.src==10.1.1.5 && ip.dst==10.2.2.9`; TCP stream 7; 10:05:12.120-10:05:18.902.

## Evidence Card

```ts
type EvidenceCard = {
  id: string
  claimId: string
  title: string
  status: Claim['status']
  keyFacts: KeyFact[]
  evidenceLinkIds: string[]
  actions: EvidenceAction[]
  includedInReport: boolean
  reportSection?: 'verified_findings' | 'likely_findings' | 'hypotheses_next_steps' | 'limitations'
}
```

Supported actions:

- open packets
- open frame detail
- open flow
- follow stream
- open timeline window
- open graph subset
- add to report
- annotate
- mark false positive
- promote/demote status when validator permits

## Check Result

```ts
type CheckResult = {
  id: string
  playbook: string
  checkName: string
  status: 'completed' | 'skipped' | 'failed' | 'cancelled'
  summary: string
  evidenceLinkIds: string[]
  claimIds: string[]
  limitationIds?: string[]
  errorCategory?: string
  errorMessage?: string
  startedAt: string
  endedAt?: string
  provenanceIds: string[]
}
```

Reports should include completed, skipped, failed, and cancelled checks in a clear limitations/check coverage section.

## Analyst Annotation

```ts
type AnalystAnnotation = {
  id: string
  targetType: 'claim' | 'evidence_card' | 'evidence_link' | 'report' | 'analysis_run'
  targetId: string
  authorId: string
  note: string
  createdAt: string
  provenanceId: string
}
```

Annotations are not packet evidence by themselves.

## Provenance

```ts
type Provenance = {
  id: string
  sourceType: 'tool' | 'ai' | 'analyst' | 'system'
  sourceName?: string
  toolQuery?: string
  model?: string
  provider?: string
  userId?: string
  inputSummary?: string
  outputSummary?: string
  createdAt: string
}
```

Provenance should capture enough detail to audit where a claim came from without storing unnecessary sensitive payload.

## Limitation

```ts
type Limitation = {
  id: string
  category:
    | 'encrypted_payload'
    | 'unknown_vantage_point'
    | 'one_sided_capture'
    | 'resource_limit'
    | 'tool_error'
    | 'missing_context'
    | 'unsupported_protocol'
    | 'redaction_limit'
  description: string
  affectedClaimIds?: string[]
  affectedCheckResultIds?: string[]
  recommendedNextStep?: string
}
```

## Validation Rules

1. Every Evidence Map must reference exactly one Analysis Run and one Capture Artifact.
2. Every Evidence Card must reference an existing Claim.
3. Every Evidence Link referenced by a Claim or Evidence Card must exist.
4. Verified Claims must have at least one Evidence Link.
5. Verified Claims must include packet/flow/time/filter citation sufficient for verification.
6. Verified Claims must not contain unresolved assumptions.
7. Likely Claims must have at least one Evidence Link.
8. Likely Claims must include assumptions or missing context.
9. Likely Claims must include a verification step or next evidence recommendation.
10. Hypotheses must include a verification step.
11. Hypotheses must not be exported as Verified Findings or Likely Findings.
12. Unsupported Claims must not be exported as report findings.
13. Raw-Context Exploration provenance alone cannot create Verified or Likely status.
14. Any claim using AI-generated text must have AI provenance.
15. Any claim based on tool output must have tool provenance.
16. Any analyst edit must create analyst provenance.
17. Reports must include limitations for encrypted payload analysis when application payload is not visible.
18. Reports must include Capture Vantage Point if known, or explicitly state unknown.
19. Reports must include selected Analysis Profile and Analysis Mode.
20. Portable exports must include textual citations for every Evidence Link used in a report finding.

## Deep Link Examples

```txt
/captures/{captureArtifactId}/packets?filter={displayFilter}&frames=1204,1211
/captures/{captureArtifactId}/frames/1204
/captures/{captureArtifactId}/flows/{flowId}
/captures/{captureArtifactId}/streams/{protocol}/{streamId}
/captures/{captureArtifactId}/timeline?from={from}&to={to}&metric=tcp.retransmissions
/captures/{captureArtifactId}/graphs/conversations?edge={edgeId}
/analysis-runs/{analysisRunId}/claims/{claimId}
/notes/{noteId}
/reports/{reportId}#claim-{claimId}
```

## Export Rules

- Native Smartshark reports should keep active Deep Links.
- Portable Markdown/PDF exports should keep links when possible and include textual citations always.
- Unsupported Claims are omitted.
- Hypotheses appear only in Hypotheses / Next Steps.
- Failed/skipped/cancelled checks appear in Limitations or Check Coverage.
- Analyst Annotations should be visibly separate from packet evidence.
