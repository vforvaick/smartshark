"use client";

import { useState } from "react";
import {
  archiveCapture,
  restoreCapture,
  hardDeleteCapture,
  type CaptureArtifact,
} from "@/lib/api";

interface CaptureLifecycleModalProps {
  token: string;
  captures: CaptureArtifact[];
  isOpen: boolean;
  onClose: () => void;
  onRefresh: () => void;
}

export default function CaptureLifecycleModal({
  token,
  captures,
  isOpen,
  onClose,
  onRefresh,
}: CaptureLifecycleModalProps) {
  const [selectedCapture, setSelectedCapture] = useState<CaptureArtifact | null>(null);
  const [confirmDelete, setConfirmDelete] = useState(false);
  const [warningMsg, setWarningMsg] = useState("");
  const [loading, setLoading] = useState(false);

  if (!isOpen) return null;

  async function handleArchive(id: number) {
    setLoading(true);
    try {
      await archiveCapture(token, id);
      setLoading(false);
      onRefresh();
    } catch {
      setLoading(false);
    }
  }

  async function handleRestore(id: number) {
    setLoading(true);
    try {
      await restoreCapture(token, id);
      setLoading(false);
      onRefresh();
    } catch {
      setLoading(false);
    }
  }

  async function handleHardDelete(id: number) {
    setLoading(true);
    try {
      const res = await hardDeleteCapture(token, id, true);
      setWarningMsg(res.warning);
      setLoading(false);
      setSelectedCapture(null);
      setConfirmDelete(false);
      onRefresh();
    } catch {
      setLoading(false);
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
      <div className="w-full max-w-2xl rounded-lg bg-white p-6 shadow-xl space-y-4">
        <div className="flex items-center justify-between border-b pb-3">
          <h3 className="text-lg font-semibold text-gray-900">Capture Artifact Lifecycle</h3>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600 font-bold">
            ✕
          </button>
        </div>

        {warningMsg && (
          <div className="rounded bg-yellow-50 p-3 text-sm text-yellow-800 border border-yellow-200">
            ⚠️ {warningMsg}
          </div>
        )}

        <div className="overflow-x-auto max-h-80 border rounded">
          <table className="min-w-full divide-y divide-gray-200 text-xs">
            <thead className="bg-gray-100 font-sans text-gray-700">
              <tr>
                <th className="px-3 py-2 text-left">Filename</th>
                <th className="px-3 py-2 text-left">Content Hash</th>
                <th className="px-3 py-2 text-left">Status</th>
                <th className="px-3 py-2 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100 bg-white">
              {captures.map((cap) => (
                <tr key={cap.id}>
                  <td className="px-3 py-2 font-medium text-gray-900">{cap.original_filename}</td>
                  <td className="px-3 py-2 font-mono text-gray-500 truncate max-w-xs">{cap.content_hash}</td>
                  <td className="px-3 py-2">
                    <span
                      className={`rounded px-1.5 py-0.5 text-[10px] font-bold uppercase ${
                        cap.status === "archived"
                          ? "bg-yellow-100 text-yellow-800"
                          : "bg-green-100 text-green-800"
                      }`}
                    >
                      {cap.status}
                    </span>
                  </td>
                  <td className="px-3 py-2 text-right space-x-2">
                    {cap.status === "archived" ? (
                      <button
                        onClick={() => handleRestore(cap.id)}
                        disabled={loading}
                        className="rounded border border-gray-300 px-2 py-1 text-xs text-blue-600 hover:bg-blue-50"
                      >
                        Restore
                      </button>
                    ) : (
                      <button
                        onClick={() => handleArchive(cap.id)}
                        disabled={loading}
                        className="rounded border border-gray-300 px-2 py-1 text-xs text-yellow-700 hover:bg-yellow-50"
                      >
                        Archive
                      </button>
                    )}
                    <button
                      onClick={() => {
                        setSelectedCapture(cap);
                        setConfirmDelete(true);
                      }}
                      disabled={loading}
                      className="rounded bg-red-50 border border-red-200 px-2 py-1 text-xs text-red-600 hover:bg-red-100 font-semibold"
                    >
                      Hard Delete
                    </button>
                  </td>
                </tr>
              ))}
              {captures.length === 0 && (
                <tr>
                  <td colSpan={4} className="px-4 py-6 text-center text-sm text-gray-500">
                    No capture artifacts found.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>

        {/* Hard Delete Confirmation Modal */}
        {confirmDelete && selectedCapture && (
          <div className="p-4 border border-red-300 rounded bg-red-50 space-y-3">
            <h4 className="font-bold text-sm text-red-800">⚠️ Confirm Hard Delete</h4>
            <p className="text-xs text-red-700">
              Are you sure you want to permanently delete capture{" "}
              <strong className="font-mono">{selectedCapture.original_filename}</strong>? All associated
              Evidence Links will be marked as unavailable.
            </p>
            <div className="flex justify-end gap-2">
              <button
                onClick={() => setConfirmDelete(false)}
                className="rounded border bg-white px-3 py-1 text-xs text-gray-700"
              >
                Cancel
              </button>
              <button
                onClick={() => handleHardDelete(selectedCapture.id)}
                disabled={loading}
                className="rounded bg-red-600 px-3 py-1 text-xs text-white font-bold hover:bg-red-700"
              >
                Permanently Delete
              </button>
            </div>
          </div>
        )}

        <div className="flex justify-end pt-3 border-t">
          <button onClick={onClose} className="rounded bg-gray-800 px-4 py-1.5 text-xs text-white">
            Close
          </button>
        </div>
      </div>
    </div>
  );
}
