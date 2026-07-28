"use client";

import { useEffect, useState } from "react";
import { createAnalyst, getAnalysts, type UserResponse } from "@/lib/api";

interface AnalystManagementProps {
  token: string;
}

export default function AnalystManagement({ token }: AnalystManagementProps) {
  const [analysts, setAnalysts] = useState<UserResponse[]>([]);
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  useEffect(() => {
    fetchAnalysts();
  }, [token]);

  async function fetchAnalysts() {
    try {
      const list = await getAnalysts(token);
      setAnalysts(list);
    } catch {
      // handled
    }
  }

  async function handleCreate(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    setSuccess("");
    setLoading(true);
    try {
      await createAnalyst(token, username, password);
      setSuccess(`Analyst '${username}' created successfully.`);
      setUsername("");
      setPassword("");
      setLoading(false);
      fetchAnalysts();
    } catch (err: unknown) {
      setLoading(false);
      setError((err as Error).message || "Failed to create analyst");
    }
  }

  return (
    <div className="space-y-6">
      <div className="rounded-lg bg-white p-6 shadow-sm border">
        <h3 className="text-md font-semibold text-gray-900 mb-4">Create New Analyst Account</h3>

        {success && <div className="mb-4 rounded bg-green-50 p-3 text-sm text-green-700">{success}</div>}
        {error && <div className="mb-4 rounded bg-red-50 p-3 text-sm text-red-700">{error}</div>}

        <form onSubmit={handleCreate} className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          <div>
            <label className="block text-xs font-medium text-gray-700">Username</label>
            <input
              type="text"
              required
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              className="mt-1 block w-full rounded border border-gray-300 px-3 py-1.5 text-sm shadow-sm focus:border-blue-500 focus:outline-none"
            />
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-700">Password</label>
            <input
              type="password"
              required
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="mt-1 block w-full rounded border border-gray-300 px-3 py-1.5 text-sm shadow-sm focus:border-blue-500 focus:outline-none"
            />
          </div>
          <div className="flex items-end">
            <button
              type="submit"
              disabled={loading}
              className="w-full rounded bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50"
            >
              {loading ? "Creating..." : "Create Analyst"}
            </button>
          </div>
        </form>
      </div>

      <div className="rounded-lg bg-white p-6 shadow-sm border">
        <h3 className="text-md font-semibold text-gray-900 mb-4">Existing Analyst Accounts</h3>
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-gray-200 text-sm">
            <thead className="bg-gray-50 text-gray-700 font-sans">
              <tr>
                <th className="px-4 py-2 text-left">ID</th>
                <th className="px-4 py-2 text-left">Username</th>
                <th className="px-4 py-2 text-left">Role</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100 bg-white">
              {analysts.map((a) => (
                <tr key={a.id}>
                  <td className="px-4 py-2 text-gray-500">{a.id}</td>
                  <td className="px-4 py-2 font-medium text-gray-900">{a.username}</td>
                  <td className="px-4 py-2">
                    <span className="rounded bg-blue-50 px-2 py-0.5 text-xs font-semibold text-blue-700">
                      {a.role}
                    </span>
                  </td>
                </tr>
              ))}
              {analysts.length === 0 && (
                <tr>
                  <td colSpan={3} className="px-4 py-4 text-center text-sm text-gray-500">
                    No analysts created yet.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
