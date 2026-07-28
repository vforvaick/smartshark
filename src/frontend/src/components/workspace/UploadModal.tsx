"use client";

import { useState } from "react";
import { uploadCapture, type CaptureArtifact, type ImportDiagnosticError } from "@/lib/api";

interface UploadModalProps {
  token: string;
  isOpen: boolean;
  onClose: () => void;
  onSuccess: (artifact: CaptureArtifact) => void;
  onErrorDiagnostic: (err: ImportDiagnosticError) => void;
}

const PROFILES = [
  { id: "general", name: "General Network Troubleshooting" },
  { id: "f5-loadbalancer", name: "F5 Load Balancer" },
  { id: "infoblox-dns", name: "Infoblox DNS" },
  { id: "verifone-intellinac", name: "Verifone intelliNAC" },
];

export default function UploadModal({
  token,
  isOpen,
  onClose,
  onSuccess,
  onErrorDiagnostic,
}: UploadModalProps) {
  const [file, setFile] = useState<File | null>(null);
  const [profile, setProfile] = useState("general");
  const [vantagePoint, setVantagePoint] = useState("");
  const [loading, setLoading] = useState(false);

  if (!isOpen) return null;

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!file) return;
    setLoading(true);
    try {
      const artifact = await uploadCapture(token, file);
      setLoading(false);
      onSuccess(artifact);
      onClose();
    } catch (err: unknown) {
      setLoading(false);
      const diagErr = (err as { diagnostic?: ImportDiagnosticError })?.diagnostic;
      if (diagErr) {
        onErrorDiagnostic(diagErr);
      } else {
        onErrorDiagnostic({
          original_filename: file.name,
          file_size_bytes: file.size,
          category: "upload_failure",
          detail: (err as Error).message || "Unknown error during upload",
          suggested_next_step: "Please verify network connection and try again.",
        });
      }
      onClose();
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
      <div className="w-full max-w-md rounded-lg bg-white p-6 shadow-xl">
        <div className="flex items-center justify-between border-b pb-3">
          <h3 className="text-lg font-semibold text-gray-900">Upload Capture File</h3>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600 font-bold"
          >
            ✕
          </button>
        </div>

        <form onSubmit={handleSubmit} className="mt-4 space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700">
              PCAP / PCAPNG File
            </label>
            <input
              type="file"
              accept=".pcap,.pcapng,.cap"
              required
              onChange={(e) => setFile(e.target.files?.[0] || null)}
              className="mt-1 block w-full text-sm text-gray-500 file:mr-4 file:rounded-md file:border-0 file:bg-blue-50 file:px-4 file:py-2 file:text-sm file:font-semibold file:text-blue-700 hover:file:bg-blue-100"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700">
              Analysis Profile
            </label>
            <select
              value={profile}
              onChange={(e) => setProfile(e.target.value)}
              className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 text-sm shadow-sm focus:border-blue-500 focus:outline-none"
            >
              {PROFILES.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.name}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700">
              Vantage Point (Optional)
            </label>
            <input
              type="text"
              placeholder="e.g. Core Switch SPAN port, Client Firewall"
              value={vantagePoint}
              onChange={(e) => setVantagePoint(e.target.value)}
              className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 text-sm shadow-sm focus:border-blue-500 focus:outline-none"
            />
          </div>

          <div className="flex justify-end gap-3 pt-4 border-t">
            <button
              type="button"
              onClick={onClose}
              className="rounded-md border border-gray-300 px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={loading || !file}
              className="rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50"
            >
              {loading ? "Uploading..." : "Upload"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
