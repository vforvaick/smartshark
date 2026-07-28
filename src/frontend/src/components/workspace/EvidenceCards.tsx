"use client";

import { type EvidenceCardItem } from "@/lib/api";

interface EvidenceCardsProps {
  claims: EvidenceCardItem[];
  onNavigateLink?: (link: string) => void;
}

export default function EvidenceCards({ claims, onNavigateLink }: EvidenceCardsProps) {
  if (!claims || claims.length === 0) {
    return (
      <div className="p-6 text-center text-xs text-gray-400 border rounded bg-gray-50">
        No evidence cards generated yet for this analysis run.
      </div>
    );
  }

  const statusColors = {
    verified: "bg-green-100 text-green-800 border-green-300",
    likely: "bg-yellow-100 text-yellow-800 border-yellow-300",
    hypothesis: "bg-blue-100 text-blue-800 border-blue-300",
    unsupported: "bg-gray-100 text-gray-800 border-gray-300",
  };

  return (
    <div className="space-y-3">
      <div className="font-bold text-xs text-gray-700 uppercase tracking-wider font-sans">
        Evidence Cards ({claims.length})
      </div>
      {claims.map((claim) => (
        <div
          key={claim.id}
          className="border rounded-lg bg-white p-4 shadow-sm hover:shadow transition-shadow space-y-2"
        >
          <div className="flex items-start justify-between gap-2">
            <p className="text-sm font-semibold text-gray-900">{claim.claim_text}</p>
            <span
              className={`rounded border px-2 py-0.5 text-[10px] font-bold uppercase ${
                statusColors[claim.status] || "bg-gray-100 text-gray-800"
              }`}
            >
              {claim.status}
            </span>
          </div>

          {claim.key_facts && claim.key_facts.length > 0 && (
            <ul className="pl-4 list-disc text-xs text-gray-600 space-y-0.5">
              {claim.key_facts.map((fact, idx) => (
                <li key={idx}>{fact}</li>
              ))}
            </ul>
          )}

          {claim.evidence_refs && claim.evidence_refs.length > 0 && (
            <div className="pt-2 border-t flex flex-wrap gap-2 text-xs">
              <span className="font-semibold text-gray-500 font-sans">Evidence Links:</span>
              {claim.evidence_refs.map((ref, idx) => (
                <button
                  key={idx}
                  onClick={() => onNavigateLink?.(ref.link)}
                  className="rounded bg-blue-50 px-2 py-0.5 text-xs text-blue-700 hover:bg-blue-100 font-mono underline"
                >
                  🔗 {ref.type || "smartshark://"}
                </button>
              ))}
            </div>
          )}
        </div>
      ))}
    </div>
  );
}
