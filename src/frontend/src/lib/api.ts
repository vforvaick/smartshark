const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "";

export interface TokenResponse {
  access_token: string;
  token_type: string;
}

export interface UserResponse {
  id: number;
  username: string;
  role: "admin" | "analyst";
}

export async function login(
  username: string,
  password: string
): Promise<TokenResponse> {
  const res = await fetch(`${API_BASE}/api/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ username, password }),
  });
  if (!res.ok) {
    throw new Error("Invalid credentials");
  }
  return res.json();
}

export async function getMe(token: string): Promise<UserResponse> {
  const res = await fetch(`${API_BASE}/api/auth/me`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!res.ok) {
    throw new Error("Unauthorized");
  }
  return res.json();
}

export async function createAnalyst(
  token: string,
  username: string,
  password: string
): Promise<UserResponse> {
  const res = await fetch(`${API_BASE}/api/auth/analysts`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify({ username, password }),
  });
  if (!res.ok) {
    const data = await res.json();
    throw new Error(data.detail || "Failed to create analyst");
  }
  return res.json();
}

export interface AIProviderSettings {
  provider: string;
  model: string;
  api_key_set: boolean;
  base_url: string | null;
}

export async function getAIProvider(
  token: string
): Promise<AIProviderSettings> {
  const res = await fetch(`${API_BASE}/api/admin/ai-provider`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!res.ok) throw new Error("Failed to get AI provider settings");
  return res.json();
}

export interface CaptureArtifact {
  id: number;
  content_hash: string;
  original_filename: string;
  size_bytes: number;
  status: string;
  created_at: string;
}

export interface ImportDiagnosticError {
  original_filename: string;
  file_size_bytes: number;
  category: string;
  detail: string | null;
  suggested_next_step: string;
}

export async function uploadCapture(
  token: string,
  file: File
): Promise<CaptureArtifact> {
  const form = new FormData();
  form.append("file", file);
  const res = await fetch(`${API_BASE}/api/captures/upload`, {
    method: "POST",
    headers: { Authorization: `Bearer ${token}` },
    body: form,
  });
  if (!res.ok) {
    const data = await res.json().catch(() => ({}));
    const err: ImportDiagnosticError =
      data.detail ?? {
        original_filename: file.name,
        file_size_bytes: file.size,
        category: "tool_failure",
        detail: `HTTP ${res.status}`,
        suggested_next_step: "Check the file and try again.",
      };
    throw Object.assign(new Error("import_failed"), { diagnostic: err });
  }
  return res.json();
}

export async function updateAIProvider(
  token: string,
  settings: {
    provider: string;
    model: string;
    api_key: string;
    base_url?: string;
  }
): Promise<AIProviderSettings> {
  const res = await fetch(`${API_BASE}/api/admin/ai-provider`, {
    method: "PUT",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify(settings),
  });
  if (!res.ok) throw new Error("Failed to update AI provider settings");
  return res.json();
}

export interface RedactionPolicy {
  mask_auth_headers: boolean;
  mask_credentials: boolean;
  mask_pan_values: boolean;
  mask_payloads: boolean;
  anonymize_ips: boolean;
  anonymize_macs: boolean;
  profile: string;
}

export async function getRedactionPolicy(token: string): Promise<RedactionPolicy> {
  const res = await fetch(`${API_BASE}/api/admin/redaction-policy`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!res.ok) throw new Error("Failed to fetch redaction policy");
  return res.json();
}

export async function updateRedactionPolicy(
  token: string,
  updates: Partial<RedactionPolicy>
): Promise<RedactionPolicy> {
  const res = await fetch(`${API_BASE}/api/admin/redaction-policy`, {
    method: "PATCH",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify(updates),
  });
  if (!res.ok) throw new Error("Failed to update redaction policy");
  return res.json();
}

export async function getAnalysts(token: string): Promise<UserResponse[]> {
  const res = await fetch(`${API_BASE}/api/auth/analysts`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!res.ok) throw new Error("Failed to fetch analysts");
  return res.json();
}

export interface AuditLogEntry {
  id: number;
  user_id: number;
  username: string;
  action: string;
  target_type: string;
  target_id: number | null;
  timestamp: string;
  details: Record<string, unknown>;
}

export async function getAuditLogs(token: string): Promise<AuditLogEntry[]> {
  const res = await fetch(`${API_BASE}/api/metrics/audit-log`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!res.ok) throw new Error("Failed to fetch audit logs");
  return res.json();
}

export async function getCaptures(token: string): Promise<CaptureArtifact[]> {
  const res = await fetch(`${API_BASE}/api/captures`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!res.ok) throw new Error("Failed to fetch captures");
  return res.json();
}

export async function archiveCapture(token: string, id: number): Promise<CaptureArtifact> {
  const res = await fetch(`${API_BASE}/api/captures/${id}/archive`, {
    method: "POST",
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!res.ok) throw new Error("Failed to archive capture");
  return res.json();
}

export async function restoreCapture(token: string, id: number): Promise<CaptureArtifact> {
  const res = await fetch(`${API_BASE}/api/captures/${id}/restore`, {
    method: "POST",
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!res.ok) throw new Error("Failed to restore capture");
  return res.json();
}

export interface HardDeleteResponse {
  id: number;
  message: string;
  warning: string;
  affected_links: number;
}

export async function hardDeleteCapture(
  token: string,
  id: number,
  confirmed = true
): Promise<HardDeleteResponse> {
  const res = await fetch(`${API_BASE}/api/captures/${id}/hard-delete?confirmed=${confirmed}`, {
    method: "DELETE",
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!res.ok) throw new Error("Failed to hard-delete capture");
  return res.json();
}

export interface PacketItem {
  frame_number: number;
  timestamp: string;
  src_ip: string;
  dst_ip: string;
  protocol: string;
  length: number;
  info: string;
  dissector_tree?: Record<string, unknown>;
  payload_hex?: string;
  payload_ascii?: string;
}

export async function getPackets(
  token: string,
  artifactId: number,
  filter?: string
): Promise<PacketItem[]> {
  const url = filter
    ? `${API_BASE}/api/packets/${artifactId}?filter=${encodeURIComponent(filter)}`
    : `${API_BASE}/api/packets/${artifactId}`;
  const res = await fetch(url, {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!res.ok) throw new Error("Failed to fetch packets");
  return res.json();
}

export interface ConversationItem {
  id: number;
  conv_id: string;
  protocol: string;
  src_endpoint: string;
  dst_endpoint: string;
  frame_count: number;
  bytes_count: number;
}

export async function getConversations(
  token: string,
  artifactId: number
): Promise<ConversationItem[]> {
  const res = await fetch(`${API_BASE}/api/conversations/${artifactId}`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!res.ok) throw new Error("Failed to fetch conversations");
  return res.json();
}

export interface EvidenceCardItem {
  id: number;
  claim_text: string;
  status: "verified" | "likely" | "hypothesis" | "unsupported";
  key_facts: string[];
  evidence_refs: Array<{ link: string; type: string }>;
}

export interface EvidenceMapItem {
  id: number;
  artifact_id: number;
  claims: EvidenceCardItem[];
}

export async function getEvidenceMap(
  token: string,
  artifactId: number
): Promise<EvidenceMapItem> {
  const res = await fetch(`${API_BASE}/api/evidence/artifact/${artifactId}`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!res.ok) throw new Error("Failed to fetch evidence map");
  return res.json();
}

export interface ReportSectionItem {
  id: number;
  section_type: string;
  title: string;
  content: string;
  order_index: number;
  is_included: boolean;
  deep_links: Array<{ link: string; type: string }>;
}

export interface ReportItem {
  id: number;
  evidence_map_id: number;
  title: string;
  status: string;
  sections: ReportSectionItem[];
}

export async function draftReport(
  token: string,
  evidenceMapId: number
): Promise<ReportItem> {
  const res = await fetch(`${API_BASE}/api/reports/draft?evidence_map_id=${evidenceMapId}`, {
    method: "POST",
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!res.ok) throw new Error("Failed to draft report");
  return res.json();
}

export async function getReport(
  token: string,
  reportId: number
): Promise<ReportItem> {
  const res = await fetch(`${API_BASE}/api/reports/${reportId}`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!res.ok) throw new Error("Failed to fetch report");
  return res.json();
}

export async function updateReportSection(
  token: string,
  sectionId: number,
  updates: { title?: string; content?: string; is_included?: boolean }
): Promise<ReportSectionItem> {
  const res = await fetch(`${API_BASE}/api/reports/sections/${sectionId}`, {
    method: "PATCH",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify(updates),
  });
  if (!res.ok) throw new Error("Failed to update report section");
  return res.json();
}
