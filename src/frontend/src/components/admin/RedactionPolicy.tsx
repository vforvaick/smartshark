"use client";

import { useEffect, useState } from "react";
import { getRedactionPolicy, updateRedactionPolicy, type RedactionPolicy } from "@/lib/api";

interface RedactionPolicyProps {
  token: string;
}

export default function RedactionPolicyComponent({ token }: RedactionPolicyProps) {
  const [policy, setPolicy] = useState<RedactionPolicy | null>(null);
  const [success, setSuccess] = useState("");
  const [error, setError] = useState("");

  useEffect(() => {
    let active = true;
    getRedactionPolicy(token)
      .then((p) => {
        if (active) setPolicy(p);
      })
      .catch(() => {
        if (active) setError("Failed to load redaction policy");
      });
    return () => {
      active = false;
    };
  }, [token]);

  async function handleToggle(key: keyof RedactionPolicy, value: boolean) {
    if (!policy) return;
    const updated = { ...policy, [key]: value };
    setPolicy(updated);
    try {
      await updateRedactionPolicy(token, { [key]: value });
      setSuccess("Redaction policy updated.");
    } catch {
      setError("Failed to update policy");
    }
  }

  async function handleProfileChange(profile: string) {
    if (!policy) return;
    setPolicy({ ...policy, profile });
    try {
      await updateRedactionPolicy(token, { profile });
      setSuccess(`Profile set to '${profile}'.`);
    } catch {
      setError("Failed to update profile");
    }
  }

  if (!policy) return <div className="p-4 text-center text-sm text-gray-500">Loading policy...</div>;

  return (
    <div className="rounded-lg bg-white p-6 shadow-sm border space-y-6">
      <div>
        <h3 className="text-md font-semibold text-gray-900">Admin Redaction Policy & Masking Rules</h3>
        <p className="text-xs text-gray-700 font-medium mt-1">
          Configure masking rules applied to raw packet payloads before sending data to AI providers.
        </p>
      </div>

      {success && <div className="rounded bg-green-50 p-3 text-sm text-green-700">{success}</div>}
      {error && <div className="rounded bg-red-50 p-3 text-sm text-red-700">{error}</div>}

      <div className="space-y-4 border-t pt-4">
        <div className="flex items-center justify-between">
          <div>
            <div className="text-sm font-semibold text-gray-900">Mask Authorization Headers</div>
            <div className="text-xs text-gray-700 font-medium">Redacts `Authorization: ...` header tokens.</div>
          </div>
          <input
            type="checkbox"
            checked={policy.mask_auth_headers}
            onChange={(e) => handleToggle("mask_auth_headers", e.target.checked)}
            className="h-4 w-4 rounded border-gray-300 text-blue-600 focus:ring-blue-500"
          />
        </div>

        <div className="flex items-center justify-between border-t pt-3">
          <div>
            <div className="text-sm font-semibold text-gray-900">Mask Credentials & Cookies</div>
            <div className="text-xs text-gray-700 font-medium">Redacts tokens, API keys, and Cookie headers.</div>
          </div>
          <input
            type="checkbox"
            checked={policy.mask_credentials}
            onChange={(e) => handleToggle("mask_credentials", e.target.checked)}
            className="h-4 w-4 rounded border-gray-300 text-blue-600 focus:ring-blue-500"
          />
        </div>

        <div className="flex items-center justify-between border-t pt-3">
          <div>
            <div className="text-sm font-semibold text-gray-900">Mask Payment Card Numbers (PAN)</div>
            <div className="text-xs text-gray-700 font-medium">Redacts 16-digit credit card PAN strings.</div>
          </div>
          <input
            type="checkbox"
            checked={policy.mask_pan_values}
            onChange={(e) => handleToggle("mask_pan_values", e.target.checked)}
            className="h-4 w-4 rounded border-gray-300 text-blue-600 focus:ring-blue-500"
          />
        </div>

        <div className="flex items-center justify-between border-t pt-3">
          <div>
            <div className="text-sm font-semibold text-gray-900">Anonymize IP Addresses</div>
            <div className="text-xs text-gray-700 font-medium">Replaces IPv4 addresses with persistent tokens (e.g. `[IP-A]`).</div>
          </div>
          <input
            type="checkbox"
            checked={policy.anonymize_ips}
            onChange={(e) => handleToggle("anonymize_ips", e.target.checked)}
            className="h-4 w-4 rounded border-gray-300 text-blue-600 focus:ring-blue-500"
          />
        </div>

        <div className="border-t pt-3">
          <label className="block text-sm font-semibold text-gray-900">Payment Profile Tightening</label>
          <select
            value={policy.profile}
            onChange={(e) => handleProfileChange(e.target.value)}
            className="mt-1 block w-full rounded border border-gray-300 px-3 py-2 text-sm shadow-sm focus:border-blue-500 focus:outline-none"
          >
            <option value="standard">Standard Network Profile</option>
            <option value="verifone-intellinac">Verifone intelliNAC (Strict Terminal ID & Auth Code Masking)</option>
          </select>
        </div>
      </div>
    </div>
  );
}
