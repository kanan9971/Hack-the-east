import { useState } from "react";
import type { AnalyzeResponse } from "../../shared/types";

const PERSONAS = [
  { id: "student", label: "Student" },
  { id: "employee", label: "Employee" },
  { id: "freelancer", label: "Freelancer" },
  { id: "tenant", label: "Tenant" },
];

interface ForYouTabProps {
  data: AnalyzeResponse;
  onReanalyze: (persona: string) => void;
}

export default function ForYouTab({ data, onReanalyze }: ForYouTabProps) {
  const [selected, setSelected] = useState<string>("");

  const handleSelect = (persona: string) => {
    setSelected(persona);
    onReanalyze(persona);
  };

  return (
    <div className="space-y-4">
      <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-5">
        <h2 className="text-sm font-semibold text-gray-500 uppercase tracking-wide mb-3">
          I am a...
        </h2>
        <div className="flex flex-wrap gap-2">
          {PERSONAS.map((p) => (
            <button
              key={p.id}
              onClick={() => handleSelect(p.id)}
              className={`px-4 py-2 rounded-full text-sm font-medium transition-colors ${
                selected === p.id
                  ? "bg-blue-500 text-white shadow-sm"
                  : "bg-gray-100 text-gray-700 hover:bg-gray-200"
              }`}
            >
              {p.label}
            </button>
          ))}
        </div>
      </div>

      {data.persona_notes && data.persona_notes.length > 0 ? (
        <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-5">
          <h2 className="text-sm font-semibold text-gray-500 uppercase tracking-wide mb-3">
            What this means for you
          </h2>
          <ul className="space-y-3">
            {data.persona_notes.map((note, i) => (
              <li key={i} className="flex items-start gap-3">
                <span className="mt-1 text-blue-500">
                  <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
                    <path
                      fillRule="evenodd"
                      d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z"
                      clipRule="evenodd"
                    />
                  </svg>
                </span>
                <span className="text-sm text-gray-700 leading-relaxed">{note}</span>
              </li>
            ))}
          </ul>
        </div>
      ) : (
        <div className="text-center py-8 text-gray-400 text-sm">
          Select a persona above to get tailored insights.
        </div>
      )}
    </div>
  );
}
