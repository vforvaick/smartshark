"use client";

import { type PacketItem } from "@/lib/api";

interface PacketTableProps {
  packets: PacketItem[];
  selectedFrame: number | null;
  onSelectPacket: (packet: PacketItem) => void;
  loading?: boolean;
}

export default function PacketTable({
  packets,
  selectedFrame,
  onSelectPacket,
  loading,
}: PacketTableProps) {
  if (loading) {
    return <div className="p-4 text-center text-sm text-gray-500">Loading packets...</div>;
  }

  if (!packets || packets.length === 0) {
    return (
      <div className="p-8 text-center text-sm text-gray-500 border rounded bg-white">
        No packets found matching current display filter.
      </div>
    );
  }

  return (
    <div className="overflow-x-auto border rounded bg-white shadow-sm max-h-96 overflow-y-auto">
      <table className="min-w-full divide-y divide-gray-200 text-xs font-mono">
        <thead className="bg-gray-100 sticky top-0 font-sans text-gray-700">
          <tr>
            <th className="px-3 py-2 text-left">No.</th>
            <th className="px-3 py-2 text-left">Time</th>
            <th className="px-3 py-2 text-left">Source</th>
            <th className="px-3 py-2 text-left">Destination</th>
            <th className="px-3 py-2 text-left">Protocol</th>
            <th className="px-3 py-2 text-right">Length</th>
            <th className="px-3 py-2 text-left">Info</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-gray-100 bg-white">
          {packets.map((pkt) => {
            const isSelected = selectedFrame === pkt.frame_number;
            return (
              <tr
                key={pkt.frame_number}
                onClick={() => onSelectPacket(pkt)}
                className={`cursor-pointer transition-colors ${
                  isSelected ? "bg-blue-100 text-blue-900 font-semibold" : "hover:bg-gray-50 text-gray-800"
                }`}
              >
                <td className="px-3 py-1.5">{pkt.frame_number}</td>
                <td className="px-3 py-1.5">{pkt.timestamp}</td>
                <td className="px-3 py-1.5">{pkt.source}</td>
                <td className="px-3 py-1.5">{pkt.destination}</td>
                <td className="px-3 py-1.5">
                  <span className="rounded bg-gray-200 px-1.5 py-0.5 text-[10px] uppercase font-sans font-bold">
                    {pkt.protocol}
                  </span>
                </td>
                <td className="px-3 py-1.5 text-right">{pkt.length}</td>
                <td className="px-3 py-1.5 truncate max-w-md">{pkt.info}</td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
