"use client";

import { useState } from "react";
import { type EvidenceCardItem } from "@/lib/api";
import EvidenceCards from "./EvidenceCards";

interface AIPanelProps {
  isOpen: boolean;
  onToggle: () => void;
  claims: EvidenceCardItem[];
  onNavigateLink?: (link: string) => void;
}

export default function AIPanel({
  isOpen,
  onToggle,
  claims,
  onNavigateLink,
}: AIPanelProps) {
  const [prompt, setPrompt] = useState("");
  const [history, setHistory] = useState<Array<{ role: string; text: string }>>([
    {
      role: "assistant",
      text: "Smartshark AI Assistant ready. Ask bounded packet queries or request triage guidance.",
    },
  ]);

  function handleSend(e: React.FormEvent) {
    e.preventDefault();
    if (!prompt.trim()) return;
    const userMsg = prompt.trim();
    setHistory((prev) => [...prev, { role: "user", text: userMsg }]);
    setPrompt("");

    setTimeout(() => {
      setHistory((prev) => [
        ...prev,
        {
          role: "assistant",
          text: `Tool-grounded analysis initiated for query: "${userMsg}". Evidence cards updated below.`,
        },
      ]);
    }, 600);
  }

  if (!isOpen) {
    return (
      <button
        onClick={onToggle}
        className="fixed right-4 bottom-4 z-40 rounded-full bg-blue-600 p-3 text-white shadow-lg hover:bg-blue-700 font-bold"
        title="Open AI Panel"
      >
        💬 AI Panel
      </button>
    );
  }

  return (
    <div className="w-96 border-l bg-gray-50 flex flex-col h-full shadow-lg">
      <div className="flex items-center justify-between p-3 border-b bg-white font-sans">
        <div className="flex items-center gap-2">
          <span className="text-lg">🤖</span>
          <h3 className="font-bold text-sm text-gray-900">AI Investigation Panel</h3>
        </div>
        <button
          onClick={onToggle}
          className="text-gray-400 hover:text-gray-600 font-bold text-sm"
        >
          ✕
        </button>
      </div>

      <div className="flex-1 overflow-y-auto p-3 space-y-4">
        {/* Chat Messages */}
        <div className="space-y-2">
          {history.map((msg, idx) => (
            <div
              key={idx}
              className={`p-2.5 rounded-lg text-xs leading-relaxed ${
                msg.role === "user"
                  ? "bg-blue-600 text-white ml-6"
                  : "bg-white text-gray-800 border shadow-sm mr-6"
              }`}
            >
              {msg.text}
            </div>
          ))}
        </div>

        {/* Evidence Cards section */}
        <div className="pt-3 border-t">
          <EvidenceCards claims={claims} onNavigateLink={onNavigateLink} />
        </div>
      </div>

      {/* Query Input Form */}
      <form onSubmit={handleSend} className="p-3 border-t bg-white flex gap-2">
        <input
          type="text"
          placeholder="Ask AI for packet insights..."
          value={prompt}
          onChange={(e) => setPrompt(e.target.value)}
          className="flex-1 rounded border border-gray-300 px-3 py-1.5 text-xs focus:border-blue-500 focus:outline-none"
        />
        <button
          type="submit"
          className="rounded bg-blue-600 px-3 py-1.5 text-xs font-semibold text-white hover:bg-blue-700"
        >
          Send
        </button>
      </form>
    </div>
  );
}
