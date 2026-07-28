"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth";
import {
  getAIProvider,
  updateAIProvider,
  type AIProviderSettings,
} from "@/lib/api";
import AnalystManagement from "@/components/admin/AnalystManagement";
import RedactionPolicyComponent from "@/components/admin/RedactionPolicy";
import AuditLogs from "@/components/admin/AuditLogs";

export default function AdminSettingsPage() {
  const { user, token, loading } = useAuth();
  const router = useRouter();
  const [activeTab, setActiveTab] = useState<"ai" | "analysts" | "redaction" | "audit">("ai");
  const [settings, setSettings] = useState<AIProviderSettings | null>(null);
  const [provider, setProvider] = useState("");
  const [model, setModel] = useState("");
  const [apiKey, setApiKey] = useState("");
  const [baseUrl, setBaseUrl] = useState("");
  const [saved, setSaved] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!loading && (!user || user.role !== "admin")) {
      router.push("/workspace");
    }
  }, [user, loading, router]);

  useEffect(() => {
    if (token && user?.role === "admin") {
      getAIProvider(token).then((s) => {
        setSettings(s);
        setProvider(s.provider);
        setModel(s.model);
        setBaseUrl(s.base_url || "");
      });
    }
  }, [token, user]);

  if (loading || !user || user.role !== "admin") return null;

  async function handleSave(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    setSaved(false);
    try {
      const updated = await updateAIProvider(token!, {
        provider,
        model,
        api_key: apiKey,
        base_url: baseUrl || undefined,
      });
      setSettings(updated);
      setSaved(true);
    } catch {
      setError("Failed to save settings");
    }
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <nav className="bg-white shadow">
        <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
          <div className="flex h-16 justify-between">
            <div className="flex items-center gap-8">
              <h1 className="text-xl font-bold text-gray-900">Smartshark</h1>
              <span
                className="text-gray-700 hover:text-gray-900 cursor-pointer"
                onClick={() => router.push("/workspace")}
              >
                Workspace
              </span>
              <span className="text-blue-600 font-medium">Admin</span>
            </div>
            <div className="flex items-center">
              <span className="text-sm text-gray-500">
                {user.username} ({user.role})
              </span>
            </div>
          </div>
        </div>
      </nav>

      <main className="mx-auto max-w-4xl px-4 py-8">
        <div className="flex border-b border-gray-200 mb-6 gap-4 text-sm font-medium">
          <button
            onClick={() => setActiveTab("ai")}
            className={`pb-3 px-1 border-b-2 ${
              activeTab === "ai"
                ? "border-blue-600 text-blue-600 font-semibold"
                : "border-transparent text-gray-500 hover:text-gray-700"
            }`}
          >
            AI Provider
          </button>
          <button
            onClick={() => setActiveTab("analysts")}
            className={`pb-3 px-1 border-b-2 ${
              activeTab === "analysts"
                ? "border-blue-600 text-blue-600 font-semibold"
                : "border-transparent text-gray-500 hover:text-gray-700"
            }`}
          >
            Analyst Accounts
          </button>
          <button
            onClick={() => setActiveTab("redaction")}
            className={`pb-3 px-1 border-b-2 ${
              activeTab === "redaction"
                ? "border-blue-600 text-blue-600 font-semibold"
                : "border-transparent text-gray-500 hover:text-gray-700"
            }`}
          >
            Redaction Policy
          </button>
          <button
            onClick={() => setActiveTab("audit")}
            className={`pb-3 px-1 border-b-2 ${
              activeTab === "audit"
                ? "border-blue-600 text-blue-600 font-semibold"
                : "border-transparent text-gray-500 hover:text-gray-700"
            }`}
          >
            Audit Logs
          </button>
        </div>

        {activeTab === "ai" && (
          <div>
            <h2 className="text-lg font-semibold text-gray-900">
              AI Provider Settings
            </h2>
            <p className="mt-1 text-sm text-gray-600">
              Configure the AI model provider for analysis.
            </p>

            <form onSubmit={handleSave} className="mt-6 space-y-6">
              {saved && (
                <div className="rounded-md bg-green-50 p-4 text-sm text-green-700">
                  Settings saved successfully.
                </div>
              )}
              {error && (
                <div className="rounded-md bg-red-50 p-4 text-sm text-red-700">
                  {error}
                </div>
              )}
              <div className="space-y-4 rounded-md bg-white p-6 shadow-sm border">
                <div>
                  <label className="block text-sm font-medium text-gray-700">
                    Provider
                  </label>
                  <select
                    value={provider}
                    onChange={(e) => setProvider(e.target.value)}
                    className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 text-sm"
                  >
                    <option value="openai">OpenAI</option>
                    <option value="anthropic">Anthropic</option>
                    <option value="local">Local</option>
                  </select>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700">
                    Model
                  </label>
                  <input
                    type="text"
                    value={model}
                    onChange={(e) => setModel(e.target.value)}
                    className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 text-sm"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700">
                    API Key
                  </label>
                  <input
                    type="password"
                    value={apiKey}
                    onChange={(e) => setApiKey(e.target.value)}
                    placeholder={settings?.api_key_set ? "••••••••" : "Enter API key"}
                    className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 text-sm"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700">
                    Base URL (optional)
                  </label>
                  <input
                    type="text"
                    value={baseUrl}
                    onChange={(e) => setBaseUrl(e.target.value)}
                    placeholder="https://api.openai.com/v1"
                    className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 text-sm"
                  />
                </div>
              </div>
              <button
                type="submit"
                className="rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700"
              >
                Save settings
              </button>
            </form>
          </div>
        )}

        {activeTab === "analysts" && <AnalystManagement token={token!} />}
        {activeTab === "redaction" && <RedactionPolicyComponent token={token!} />}
        {activeTab === "audit" && <AuditLogs token={token!} />}
      </main>
    </div>
  );
}
