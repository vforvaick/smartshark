"use client";

import { type ImportDiagnosticError } from "@/lib/api";

interface ImportDiagnosticModalProps {
  diagnostic: ImportDiagnosticError | null;
  onClose: () => void;
}

export default function ImportDiagnosticModal({
  diagnostic,
  onClose,
}: ImportDiagnosticModalProps) {
  if (!diagnostic) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
      <div className="w-full max-w-lg rounded-lg bg-white p-6 shadow-xl border-l-4 border-red-500">
        <div className="flex items-center justify-between pb-3 border-b">
          <div className="flex items-center gap-2">
            <span className="text-xl">⚠️</span>
            <h3 className="text-lg font-semibold text-red-700">Import Diagnostic Failure</h3>
          </div>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600 font-bold"
          >
            ✕
          </button>
        </div>

        <div className="mt-4 space-y-3 text-sm">
          <div>
            <span className="font-semibold text-gray-700">File:</span>{" "}
            <span className="text-gray-900">{diagnostic.original_filename}</span> (
            {(diagnostic.file_size_bytes / 1024).toFixed(1)} KB)
          </div>

          <div>
            <span className="font-semibold text-gray-700">Category:</span>{" "}
            <span className="inline-block rounded bg-red-100 px-2 py-0.5 text-xs font-semibold text-red-800">
              {diagnostic.category}
            </span>
          </div>

          {diagnostic.detail && (
            <div className="rounded bg-gray-50 p-3 text-xs text-gray-800 font-mono">
              {diagnostic.detail}
            </div>
          )}

          <div className="rounded bg-blue-50 p-3 text-blue-900 text-sm">
            <span className="font-semibold">Suggested Action:</span>{" "}
            {diagnostic.suggested_next_step}
          </div>
        </div>

        <div className="flex justify-end pt-4 mt-4 border-t">
          <button
            onClick={onClose}
            className="rounded-md bg-gray-800 px-4 py-2 text-sm font-medium text-white hover:bg-gray-900"
          >
            Dismiss
          </button>
        </div>
      </div>
    </div>
  );
}
