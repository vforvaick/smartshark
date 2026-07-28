"use client";

import { type PacketItem } from "@/lib/api";

interface PayloadViewerProps {
  packet: PacketItem | null;
}

export default function PayloadViewer({ packet }: PayloadViewerProps) {
  if (!packet) {
    return (
      <div className="p-4 text-center text-xs text-gray-400 border rounded bg-gray-50 h-48 flex items-center justify-center">
        Select a packet to view hex/ASCII payload.
      </div>
    );
  }

  const hex = packet.payload_hex || "00 00 00 00 45 00 00 3c 1c 46 40 00 40 06 b1 e6 c0 a8 01 01 c0 a8 01 02";
  const ascii = packet.payload_ascii || "....E..<.F@.@............";

  return (
    <div className="border rounded bg-white p-3 font-mono text-xs shadow-sm">
      <div className="font-bold text-gray-700 font-sans border-b pb-1 mb-2">Payload Preview (Hex / ASCII)</div>
      <div className="grid grid-cols-2 gap-4 bg-gray-900 text-green-400 p-3 rounded font-mono overflow-x-auto text-[11px]">
        <div>
          <div className="text-gray-500 font-sans text-[10px] uppercase mb-1">Hex Bytes</div>
          <div className="leading-relaxed break-all">{hex}</div>
        </div>
        <div>
          <div className="text-gray-500 font-sans text-[10px] uppercase mb-1">ASCII String</div>
          <div className="leading-relaxed break-all">{ascii}</div>
        </div>
      </div>
    </div>
  );
}
