const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "";

export interface PacketSummary {
  frame_number: number;
  timestamp: string;
  source: string;
  destination: string;
  protocol: string;
  length: number;
  info: string;
}

export interface LayerField {
  name: string;
  value: string;
}

export interface FrameDetail {
  frame_number: number;
  timestamp: string;
  protocols: string[];
  layers: LayerField[];
}

export interface PayloadPreview {
  hex_dump: string;
  ascii: string;
  length: number;
}

export async function listPackets(
  token: string,
  artifactId: number,
  opts: { filter?: string; limit?: number; offset?: number } = {}
): Promise<PacketSummary[]> {
  const params = new URLSearchParams();
  if (opts.filter) params.set("filter", opts.filter);
  params.set("limit", String(opts.limit ?? 100));
  params.set("offset", String(opts.offset ?? 0));

  const res = await fetch(
    `${API_BASE}/api/captures/${artifactId}/packets?${params}`,
    { headers: { Authorization: `Bearer ${token}` } }
  );
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail ?? "Failed to load packets");
  }
  return res.json();
}

export async function getFrameDetail(
  token: string,
  artifactId: number,
  frameNumber: number
): Promise<FrameDetail> {
  const res = await fetch(
    `${API_BASE}/api/captures/${artifactId}/frames/${frameNumber}`,
    { headers: { Authorization: `Bearer ${token}` } }
  );
  if (!res.ok) throw new Error("Frame not found");
  return res.json();
}

export async function getPayloadPreview(
  token: string,
  artifactId: number,
  frameNumber: number
): Promise<PayloadPreview> {
  const res = await fetch(
    `${API_BASE}/api/captures/${artifactId}/frames/${frameNumber}/payload`,
    { headers: { Authorization: `Bearer ${token}` } }
  );
  if (!res.ok) throw new Error("Payload not found");
  return res.json();
}
