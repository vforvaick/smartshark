const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

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
