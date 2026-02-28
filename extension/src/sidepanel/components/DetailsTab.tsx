import { useState } from "react";
import type { AnalyzeResponse } from "../../shared/types";

const LABEL_COLORS: Record<string, string> = {
  data_use: "bg-purple-100 text-purple-700",
  data_sharing: "bg-red-100 text-red-700",
  ip_assignment: "bg-orange-100 text-orange-700",
  dispute_resolution: "bg-rose-100 text-rose-700",
  auto_renew: "bg-amber-100 text-amber-700",
  termination: "bg-yellow-100 text-yellow-700",
  liability: "bg-pink-100 text-pink-700",
  non_compete: "bg-indigo-100 text-indigo-700",
  fees: "bg-emerald-100 text-emerald-700",
  confidentiality: "bg-cyan-100 text-cyan-700",
  other: "bg-gray-100 text-gray-600",
};

export default function DetailsTab({ data }: { data: AnalyzeResponse }) {
  const [expandedIdx, setExpandedIdx] = useState<number | null>(null);

  return (
    <div className="space-y-2">
      {data.sections.map((section, i) => (
        <div
          key={i}
          className="bg-white rounded-xl shadow-sm border border-gray-100 overflow-hidden"
        >
          <button
            onClick={() => setExpandedIdx(expandedIdx === i ? null : i)}
            className="w-full text-left p-4"
          >
            <div className="flex items-center justify-between">
              <span className="font-medium text-gray-800 text-sm">
                {section.title}
              </span>
              <svg
                className={`w-4 h-4 text-gray-400 transition-transform ${
                  expandedIdx === i ? "rotate-180" : ""
                }`}
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M19 9l-7 7-7-7"
                />
              </svg>
            </div>
            <div className="flex flex-wrap gap-1.5 mt-2">
              {section.labels.map((label, j) => (
                <span
                  key={j}
                  className={`text-[10px] font-semibold uppercase px-2 py-0.5 rounded-full ${
                    LABEL_COLORS[label] || LABEL_COLORS.other
                  }`}
                >
                  {label.replace(/_/g, " ")}
                </span>
              ))}
            </div>
          </button>
          {expandedIdx === i && (
            <div className="px-4 pb-4">
              <p className="text-sm text-gray-600 whitespace-pre-wrap leading-relaxed">
                {section.body}
              </p>
            </div>
          )}
        </div>
      ))}
    </div>
  );
}
