// components/trace/TraceFilters.jsx — Trace filters/search (local-only UI)
// S7-0902: local-only filter state; no backend dispatch.
import React, { useState } from "react";

export function TraceFilters({ types = [], onChange }) {
  const [query, setQuery] = useState("");
  const [activeType, setActiveType] = useState("all");

  const emit = (next) => {
    if (typeof onChange === "function") onChange(next);
  };

  return (
    <div data-testid="trace-filters" className="aw-trace-filters">
      <input
        data-testid="trace-search"
        placeholder="Search trace…"
        value={query}
        onChange={(e) => {
          setQuery(e.target.value);
          emit({ query: e.target.value, type: activeType });
        }}
      />
      <select
        data-testid="trace-filter-type"
        value={activeType}
        onChange={(e) => {
          setActiveType(e.target.value);
          emit({ query, type: e.target.value });
        }}
      >
        <option value="all">all</option>
        {types.map((t) => (
          <option key={t} value={t}>
            {t}
          </option>
        ))}
      </select>
    </div>
  );
}

export default TraceFilters;
