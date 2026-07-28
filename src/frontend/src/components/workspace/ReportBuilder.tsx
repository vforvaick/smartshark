"use client";

import { useState } from "react";
import { type ReportItem, type ReportSectionItem } from "@/lib/api";

interface ReportBuilderProps {
  report: ReportItem | null;
  onUpdateSection?: (sectionId: number, updates: { title?: string; content?: string }) => void;
  onExportMarkdown?: () => void;
  onExportPDF?: () => void;
}

export default function ReportBuilder({
  report,
  onUpdateSection,
  onExportMarkdown,
  onExportPDF,
}: ReportBuilderProps) {
  const [editingSectionId, setEditingSectionId] = useState<number | null>(null);
  const [editTitle, setEditTitle] = useState("");
  const [editContent, setEditContent] = useState("");

  if (!report) {
    return (
      <div className="p-8 text-center text-xs text-gray-400 border rounded bg-gray-50">
        No report drafted yet. Run capture analysis to generate an Evidence Map and draft report.
      </div>
    );
  }

  function startEdit(section: ReportSectionItem) {
    setEditingSectionId(section.id);
    setEditTitle(section.title);
    setEditContent(section.content);
  }

  function handleSave(sectionId: number) {
    onUpdateSection?.(sectionId, { title: editTitle, content: editContent });
    setEditingSectionId(null);
  }

  return (
    <div className="border rounded-lg bg-white p-6 shadow-sm space-y-6">
      <div className="flex items-center justify-between border-b pb-4">
        <div>
          <h2 className="text-lg font-bold text-gray-900">{report.title}</h2>
          <span className="rounded bg-blue-50 px-2 py-0.5 text-xs font-semibold text-blue-700">
            Status: {report.status}
          </span>
        </div>
        <div className="flex gap-2">
          <button
            onClick={onExportMarkdown}
            className="rounded border border-gray-300 px-3 py-1.5 text-xs font-medium text-gray-700 hover:bg-gray-50"
          >
            Export Markdown
          </button>
          <button
            onClick={onExportPDF}
            className="rounded bg-blue-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-blue-700"
          >
            Export PDF
          </button>
        </div>
      </div>

      <div className="space-y-4">
        {report.sections
          .filter((s) => s.is_included)
          .sort((a, b) => a.order_index - b.order_index)
          .map((section) => {
            const isEditing = editingSectionId === section.id;
            return (
              <div key={section.id} className="border rounded p-4 bg-gray-50 space-y-2">
                {isEditing ? (
                  <div className="space-y-3">
                    <input
                      type="text"
                      value={editTitle}
                      onChange={(e) => setEditTitle(e.target.value)}
                      className="w-full rounded border px-3 py-1 text-sm font-bold"
                    />
                    <textarea
                      rows={4}
                      value={editContent}
                      onChange={(e) => setEditContent(e.target.value)}
                      className="w-full rounded border px-3 py-2 text-xs font-mono"
                    />
                    <div className="flex justify-end gap-2">
                      <button
                        onClick={() => setEditingSectionId(null)}
                        className="rounded border px-3 py-1 text-xs text-gray-600"
                      >
                        Cancel
                      </button>
                      <button
                        onClick={() => handleSave(section.id)}
                        className="rounded bg-blue-600 px-3 py-1 text-xs text-white"
                      >
                        Save Section
                      </button>
                    </div>
                  </div>
                ) : (
                  <div>
                    <div className="flex items-center justify-between border-b pb-1 mb-2">
                      <h3 className="font-bold text-sm text-gray-800">{section.title}</h3>
                      <button
                        onClick={() => startEdit(section)}
                        className="text-xs text-blue-600 hover:underline font-sans"
                      >
                        Edit Section
                      </button>
                    </div>
                    <pre className="text-xs text-gray-700 font-mono whitespace-pre-wrap leading-relaxed">
                      {section.content}
                    </pre>
                  </div>
                )}
              </div>
            );
          })}
      </div>
    </div>
  );
}
