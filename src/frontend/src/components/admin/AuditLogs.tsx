"use client";

import { useEffect, useState } from "react";
import { getAuditLogs, type AuditLogEntry } from "@/lib/api";

interface AuditLogsProps {
  token: string;
}

export default function AuditLogs({ token }: AuditLogsProps) {
  const [logs, setLogs] = useState<AuditLogEntry[]>([]);
  const [error, setError] = useState("");

  useEffect(() => {
    let active = true;
    getAuditLogs(token)
      .then((data) => {
        if (active) setLogs(data);
      })
      .catch(() => {
        if (active) setError("Failed to load audit logs");
      });
    return () => {
      active = false;
    };
  }, [token]);

  return (
    <div className="rounded-lg bg-white p-6 shadow-sm border space-y-4">
      <div>
        <h3 className="text-md font-semibold text-gray-900">Audit Logs & AI Request Provenance</h3>
        <p className="text-xs text-gray-500 mt-1">
          Historical log of administrative actions, capture lifecycle events, and AI requests.
        </p>
      </div>

      {error && <div className="rounded bg-red-50 p-3 text-sm text-red-700">{error}</div>}

      <div className="overflow-x-auto">
        <table className="min-w-full divide-y divide-gray-200 text-xs font-mono">
          <thead className="bg-gray-50 font-sans text-gray-700">
            <tr>
              <th className="px-3 py-2 text-left">Time</th>
              <th className="px-3 py-2 text-left">User</th>
              <th className="px-3 py-2 text-left">Action</th>
              <th className="px-3 py-2 text-left">Target</th>
              <th className="px-3 py-2 text-left">Details</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100 bg-white">
            {logs.map((log) => (
              <tr key={log.id} className="hover:bg-gray-50">
                <td className="px-3 py-2 text-gray-500 whitespace-nowrap">{log.timestamp}</td>
                <td className="px-3 py-2 font-semibold text-gray-900 font-sans">{log.username || log.user_id}</td>
                <td className="px-3 py-2">
                  <span className="rounded bg-gray-100 px-1.5 py-0.5 text-xs font-bold text-gray-800">
                    {log.action}
                  </span>
                </td>
                <td className="px-3 py-2 text-gray-600 font-sans">
                  {log.target_type} {log.target_id ? `#${log.target_id}` : ""}
                </td>
                <td className="px-3 py-2 text-gray-700 truncate max-w-xs font-sans">
                  {JSON.stringify(log.details)}
                </td>
              </tr>
            ))}
            {logs.length === 0 && (
              <tr>
                <td colSpan={5} className="px-4 py-6 text-center text-sm text-gray-500 font-sans">
                  No audit logs recorded yet.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
