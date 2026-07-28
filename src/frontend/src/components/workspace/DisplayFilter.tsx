"use client";

import { useState } from "react";

interface DisplayFilterProps {
  onApplyFilter: (filter: string) => void;
  loading?: boolean;
}

export default function DisplayFilter({ onApplyFilter, loading }: DisplayFilterProps) {
  const [filterText, setFilterText] = useState("");

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    onApplyFilter(filterText.trim());
  }

  function handleClear() {
    setFilterText("");
    onApplyFilter("");
  }

  return (
    <form onSubmit={handleSubmit} className="flex items-center gap-2 bg-white p-2 border rounded shadow-sm">
      <span className="text-xs font-bold text-gray-900 uppercase px-1 font-sans">Filter:</span>
      <input
        type="text"
        placeholder="e.g. ip.src == 192.168.1.1 or tcp.flags.syn == 1"
        value={filterText}
        onChange={(e) => setFilterText(e.target.value)}
        className="flex-1 rounded border border-gray-300 px-3 py-1.5 text-sm font-mono text-gray-900 placeholder:text-gray-500 focus:border-blue-500 focus:outline-none"
      />
      <button
        type="submit"
        disabled={loading}
        className="rounded bg-blue-600 px-3 py-1 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50"
      >
        Apply
      </button>
      {filterText && (
        <button
          type="button"
          onClick={handleClear}
          className="rounded border border-gray-300 px-2 py-1 text-sm text-gray-600 hover:bg-gray-100"
        >
          Clear
        </button>
      )}
    </form>
  );
}
