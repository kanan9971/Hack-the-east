import { useState } from "react";
import type { AnalyzeResponse, RiskFlag } from "../../shared/types";

const SEVERITY_STYLES: Record<string, { bg: string; text: string; dot: string }> = {
  high: { bg: "bg-red-50", text: "text-red-700", dot: "bg-red-500" },
  medium: { bg: "bg-amber-50", text: "text-amber-700", dot: "bg-amber-500" },
  low: { bg: "bg-green-50", text: "text-green-700", dot: "bg-green-500" },
};

function RiskCard({ risk }: { risk: RiskFlag }) {
  const [expanded, setExpanded] = useState(false);
  const style = SEVERITY_STYLES[risk.severity] || SEVERITY_STYLES.low;

  return (
    <div
      className={`${style.bg} rounded-xl border border-gray-100 overflow-hidden`}
    >
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full text-left p-4 flex items-start gap-3"
      >
        <span className={`mt-1.5 h-2.5 w-2.5 rounded-full ${style.dot} shrink-0`} />
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1">
            <span className={`text-xs font-semibold uppercase ${style.text}`}>
              {risk.severity}
            </span>
            <span className="text-xs text-gray-500 capitalize">
              {risk.category.replace(/_/g, " ")}
            </span>
          </div>
          <p className="text-sm text-gray-800">{risk.explanation}</p>
        </div>
        <svg
          className={`w-4 h-4 text-gray-400 shrink-0 transition-transform ${
            expanded ? "rotate-180" : ""
          }`}
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
        >
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
        </svg>
      </button>
      {expanded && risk.clause_excerpt && (
        <div className="px-4 pb-4 pt-0 ml-8">
          <div className="bg-white/60 rounded-lg p-3 text-xs text-gray-600 italic border border-gray-200/50">
            "{risk.clause_excerpt}"
          </div>
        </div>
      )}
    </div>
  );
}

export default function RisksTab({ data }: { data: AnalyzeResponse }) {
  if (data.risks.length === 0) {
    return (
      <div className="text-center py-12 text-gray-500">
        <p className="text-lg font-medium">No significant risks detected</p>
        <p className="text-sm mt-1">This document appears relatively standard.</p>
      </div>
    );
  }

  const high = data.risks.filter((r) => r.severity === "high");
  const medium = data.risks.filter((r) => r.severity === "medium");
  const low = data.risks.filter((r) => r.severity === "low");

  return (
    <div className="space-y-3">
      <div className="flex items-center gap-3 text-sm px-1 pb-1">
        {high.length > 0 && (
          <span className="flex items-center gap-1 text-red-600 font-medium">
            <span className="h-2 w-2 rounded-full bg-red-500" />
            {high.length} High
          </span>
        )}
        {medium.length > 0 && (
          <span className="flex items-center gap-1 text-amber-600 font-medium">
            <span className="h-2 w-2 rounded-full bg-amber-500" />
            {medium.length} Medium
          </span>
        )}
        {low.length > 0 && (
          <span className="flex items-center gap-1 text-green-600 font-medium">
            <span className="h-2 w-2 rounded-full bg-green-500" />
            {low.length} Low
          </span>
        )}
      </div>

      {data.risks.map((risk, i) => (
        <RiskCard key={i} risk={risk} />
      ))}
    </div>
  );
}
