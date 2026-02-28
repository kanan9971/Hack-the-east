import type { AnalyzeResponse } from "../../shared/types";

export default function SummaryTab({ data }: { data: AnalyzeResponse }) {
  return (
    <div className="space-y-4">
      <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-5">
        <h2 className="text-sm font-semibold text-gray-500 uppercase tracking-wide mb-2">
          Summary
        </h2>
        <p className="text-gray-800 leading-relaxed">{data.summary}</p>
      </div>

      <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-5">
        <h2 className="text-sm font-semibold text-gray-500 uppercase tracking-wide mb-3">
          Key Points
        </h2>
        <ul className="space-y-2">
          {data.key_points.map((point, i) => (
            <li key={i} className="flex items-start gap-2">
              <span className="mt-1.5 h-2 w-2 rounded-full bg-blue-500 shrink-0" />
              <span className="text-gray-700">{point}</span>
            </li>
          ))}
        </ul>
      </div>

      {data.entities && (
        <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-5">
          <h2 className="text-sm font-semibold text-gray-500 uppercase tracking-wide mb-3">
            Entities
          </h2>
          <div className="grid grid-cols-2 gap-3 text-sm">
            {data.entities.parties && data.entities.parties.length > 0 && (
              <div>
                <span className="font-medium text-gray-600">Parties</span>
                <p className="text-gray-800">{data.entities.parties.join(", ")}</p>
              </div>
            )}
            {data.entities.dates && data.entities.dates.length > 0 && (
              <div>
                <span className="font-medium text-gray-600">Dates</span>
                <p className="text-gray-800">{data.entities.dates.join(", ")}</p>
              </div>
            )}
            {data.entities.amounts && data.entities.amounts.length > 0 && (
              <div>
                <span className="font-medium text-gray-600">Amounts</span>
                <p className="text-gray-800">{data.entities.amounts.join(", ")}</p>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
