"use client";

import { type ConversationItem } from "@/lib/api";

interface ConversationsListProps {
  conversations: ConversationItem[];
  onSelectConv?: (conv: ConversationItem) => void;
  loading?: boolean;
}

export default function ConversationsList({
  conversations,
  onSelectConv,
  loading,
}: ConversationsListProps) {
  if (loading) {
    return <div className="p-4 text-center text-xs text-gray-500">Loading conversations...</div>;
  }

  if (!conversations || conversations.length === 0) {
    return (
      <div className="p-6 text-center text-xs text-gray-400 border rounded bg-white">
        No network flows/conversations detected in this capture.
      </div>
    );
  }

  return (
    <div className="border rounded bg-white shadow-sm overflow-x-auto max-h-64">
      <div className="p-3 bg-gray-50 font-bold text-xs text-gray-700 border-b font-sans">
        Conversations / Flow Stream List ({conversations.length})
      </div>
      <table className="min-w-full divide-y divide-gray-200 text-xs font-mono">
        <thead className="bg-gray-100 font-sans text-gray-700">
          <tr>
            <th className="px-3 py-1.5 text-left">Conv ID</th>
            <th className="px-3 py-1.5 text-left">Protocol</th>
            <th className="px-3 py-1.5 text-left">Source Endpoint</th>
            <th className="px-3 py-1.5 text-left">Destination Endpoint</th>
            <th className="px-3 py-1.5 text-right">Frames</th>
            <th className="px-3 py-1.5 text-right">Bytes</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-gray-100 bg-white">
          {conversations.map((c) => (
            <tr
              key={c.id}
              onClick={() => onSelectConv?.(c)}
              className="hover:bg-gray-50 cursor-pointer transition-colors"
            >
              <td className="px-3 py-1.5 font-bold text-blue-600">{c.conv_id}</td>
              <td className="px-3 py-1.5 uppercase text-[10px] font-sans font-bold text-gray-700">{c.protocol}</td>
              <td className="px-3 py-1.5 text-gray-900">{c.src_endpoint}</td>
              <td className="px-3 py-1.5 text-gray-900">{c.dst_endpoint}</td>
              <td className="px-3 py-1.5 text-right">{c.frame_count}</td>
              <td className="px-3 py-1.5 text-right">{c.bytes_count}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
