"use client";

import { useState } from "react";
import { type PacketItem, type FrameDetail } from "@/lib/api";

interface DissectorTreeProps {
  packet: PacketItem | null;
  frameDetail?: FrameDetail | null;
}

export default function DissectorTree({ packet, frameDetail }: DissectorTreeProps) {
  const [openSections, setOpenSections] = useState<Record<string, boolean>>({
    frame: true,
    ip: true,
    proto: true,
    detail: true,
  });

  if (!packet) {
    return (
      <div className="p-4 text-center text-xs text-gray-400 border rounded bg-gray-50 h-48 flex items-center justify-center">
        Select a packet to view header details.
      </div>
    );
  }

  function toggle(key: string) {
    setOpenSections((prev) => ({ ...prev, [key]: !prev[key] }));
  }

  return (
    <div className="border rounded bg-white p-3 font-mono text-xs space-y-2 overflow-y-auto max-h-64 shadow-sm">
      <div className="font-bold text-gray-700 font-sans border-b pb-1">Packet Dissector Tree</div>

      {/* Frame Layer */}
      <div>
        <button
          onClick={() => toggle("frame")}
          className="flex items-center gap-1 font-semibold text-gray-800 hover:text-blue-600"
        >
          <span>{openSections.frame ? "▼" : "▶"}</span> Frame {packet.frame_number}: {packet.length} bytes on wire
        </button>
        {openSections.frame && (
          <div className="pl-4 text-gray-600 space-y-0.5 mt-1 border-l-2 border-gray-200">
            <div>Arrival Time: {packet.timestamp}</div>
            <div>Frame Length: {packet.length} bytes</div>
            <div>Capture Length: {packet.length} bytes</div>
          </div>
        )}
      </div>

      {/* IP Layer */}
      <div>
        <button
          onClick={() => toggle("ip")}
          className="flex items-center gap-1 font-semibold text-gray-800 hover:text-blue-600"
        >
          <span>{openSections.ip ? "▼" : "▶"}</span> Internet Protocol Version 4, Src: {packet.source}, Dst: {packet.destination}
        </button>
        {openSections.ip && (
          <div className="pl-4 text-gray-600 space-y-0.5 mt-1 border-l-2 border-gray-200">
            <div>Source Address: {packet.source}</div>
            <div>Destination Address: {packet.destination}</div>
            <div>Protocol: {packet.protocol}</div>
          </div>
        )}
      </div>

      {/* Frame Detail Layers if available */}
      {frameDetail && frameDetail.layers && frameDetail.layers.length > 0 && (
        <div>
          <button
            onClick={() => toggle("detail")}
            className="flex items-center gap-1 font-semibold text-gray-800 hover:text-blue-600"
          >
            <span>{openSections.detail ? "▼" : "▶"}</span> Protocols: {frameDetail.protocols?.join(", ")}
          </button>
          {openSections.detail && (
            <div className="pl-4 text-gray-600 space-y-0.5 mt-1 border-l-2 border-gray-200">
              {frameDetail.layers.map((l, idx) => (
                <div key={idx}>
                  <span className="font-semibold text-gray-700">{l.name}:</span> {l.value}
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Application / Info Layer */}
      <div>
        <button
          onClick={() => toggle("proto")}
          className="flex items-center gap-1 font-semibold text-gray-800 hover:text-blue-600"
        >
          <span>{openSections.proto ? "▼" : "▶"}</span> {packet.protocol} Protocol Layer
        </button>
        {openSections.proto && (
          <div className="pl-4 text-gray-600 space-y-0.5 mt-1 border-l-2 border-gray-200">
            <div>Info Summary: {packet.info}</div>
          </div>
        )}
      </div>
    </div>
  );
}
