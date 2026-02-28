import { useState, useEffect } from "react";
import type { AnalyzeResponse, UserContext, ForYouInsights } from "../../shared/types";

const PERSONAS = [
  { id: "student", label: "Student" },
  { id: "employee", label: "Employee" },
  { id: "freelancer", label: "Freelancer" },
  { id: "tenant", label: "Tenant" },
];

const PRIMARY_CONCERNS = [
  { id: "privacy", label: "Privacy" },
  { id: "cost_fees", label: "Cost / Fees" },
  { id: "termination", label: "Termination" },
  { id: "ip_ownership", label: "IP ownership" },
  { id: "liability", label: "Liability" },
  { id: "data_sharing", label: "Data sharing" },
  { id: "auto_renew", label: "Auto-renewal" },
  { id: "non_compete", label: "Non-compete" },
];

const DOCUMENT_CONTEXTS = [
  { id: "new_job", label: "New job" },
  { id: "housing_lease", label: "Housing lease" },
  { id: "freelance_gig", label: "Freelance gig" },
  { id: "app_signup", label: "App signup" },
  { id: "service_agreement", label: "Service agreement" },
  { id: "other", label: "Other" },
];

const EXPERIENCE_LEVELS = [
  { id: "first_contract", label: "First contract" },
  { id: "experienced", label: "I've signed many" },
];

const DEAL_BREAKER_OPTIONS = [
  "non-compete",
  "unlimited liability",
  "mandatory arbitration",
  "data selling",
  "ip_assignment",
  "auto-renewal",
];

interface ForYouTabProps {
  data: AnalyzeResponse;
}

const defaultContext: UserContext = {
  persona: undefined,
  primary_concerns: [],
  document_context: undefined,
  experience_level: undefined,
  deal_breakers: [],
};

export default function ForYouTab({ data }: ForYouTabProps) {
  const [context, setContext] = useState<UserContext>(defaultContext);
  const [insights, setInsights] = useState<ForYouInsights | null>(null);
  const [insightsLoading, setInsightsLoading] = useState(false);
  const [insightsError, setInsightsError] = useState<string | null>(null);
  const [customDealBreaker, setCustomDealBreaker] = useState("");

  useEffect(() => {
    chrome.storage.local.get(["forYouContext"], (result) => {
      if (result.forYouContext) {
        setContext((prev) => ({ ...prev, ...result.forYouContext }));
      }
    });
  }, []);

  useEffect(() => {
    const listener = (message: {
      type: string;
      insights?: ForYouInsights | null;
      error?: string;
    }) => {
      if (message.type === "INSIGHTS_UPDATE") {
        setInsightsLoading(false);
        setInsights(message.insights ?? null);
        setInsightsError(message.error ?? null);
      }
    };
    chrome.runtime.onMessage.addListener(listener);
    return () => chrome.runtime.onMessage.removeListener(listener);
  }, []);

  const saveContext = (updates: Partial<UserContext>) => {
    const next = { ...context, ...updates };
    setContext(next);
    chrome.storage.local.set({ forYouContext: next });
  };

  const toggleConcern = (id: string) => {
    const next = context.primary_concerns.includes(id)
      ? context.primary_concerns.filter((c) => c !== id)
      : [...context.primary_concerns, id];
    saveContext({ primary_concerns: next });
  };

  const toggleDealBreaker = (item: string) => {
    const next = context.deal_breakers.includes(item)
      ? context.deal_breakers.filter((d) => d !== item)
      : [...context.deal_breakers, item];
    saveContext({ deal_breakers: next });
  };

  const addCustomDealBreaker = () => {
    const trimmed = customDealBreaker.trim().toLowerCase();
    if (trimmed && !context.deal_breakers.includes(trimmed)) {
      saveContext({ deal_breakers: [...context.deal_breakers, trimmed] });
      setCustomDealBreaker("");
    }
  };

  const handleGetInsights = () => {
    setInsightsLoading(true);
    setInsightsError(null);
    chrome.runtime.sendMessage({
      type: "GENERATE_INSIGHTS",
      analysis: data,
      user_context: context,
    });
  };

  const handlePersonaSelect = (persona: string) => {
    saveContext({ persona });
  };

  return (
    <div className="space-y-4">
      {/* Persona */}
      <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-5">
        <h2 className="text-sm font-semibold text-gray-500 uppercase tracking-wide mb-3">
          I am a...
        </h2>
        <div className="flex flex-wrap gap-2">
          {PERSONAS.map((p) => (
            <button
              key={p.id}
              onClick={() => handlePersonaSelect(p.id)}
              className={`px-4 py-2 rounded-full text-sm font-medium transition-colors ${
                context.persona === p.id
                  ? "bg-blue-500 text-white shadow-sm"
                  : "bg-gray-100 text-gray-700 hover:bg-gray-200"
              }`}
            >
              {p.label}
            </button>
          ))}
        </div>
      </div>

      {/* Primary concerns */}
      <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-5">
        <h2 className="text-sm font-semibold text-gray-500 uppercase tracking-wide mb-3">
          What matters most to you
        </h2>
        <div className="flex flex-wrap gap-2">
          {PRIMARY_CONCERNS.map((c) => (
            <button
              key={c.id}
              onClick={() => toggleConcern(c.id)}
              className={`px-3 py-1.5 rounded-full text-sm font-medium transition-colors ${
                context.primary_concerns.includes(c.id)
                  ? "bg-amber-100 text-amber-800 border border-amber-200"
                  : "bg-gray-100 text-gray-600 hover:bg-gray-200 border border-transparent"
              }`}
            >
              {c.label}
            </button>
          ))}
        </div>
      </div>

      {/* Document context */}
      <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-5">
        <h2 className="text-sm font-semibold text-gray-500 uppercase tracking-wide mb-3">
          Why are you signing this?
        </h2>
        <div className="flex flex-wrap gap-2">
          {DOCUMENT_CONTEXTS.map((d) => (
            <button
              key={d.id}
              onClick={() => saveContext({ document_context: d.id })}
              className={`px-3 py-1.5 rounded-full text-sm font-medium transition-colors ${
                context.document_context === d.id
                  ? "bg-blue-100 text-blue-800 border border-blue-200"
                  : "bg-gray-100 text-gray-600 hover:bg-gray-200 border border-transparent"
              }`}
            >
              {d.label}
            </button>
          ))}
        </div>
      </div>

      {/* Experience level */}
      <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-5">
        <h2 className="text-sm font-semibold text-gray-500 uppercase tracking-wide mb-3">
          Experience level
        </h2>
        <div className="flex gap-3">
          {EXPERIENCE_LEVELS.map((e) => (
            <button
              key={e.id}
              onClick={() => saveContext({ experience_level: e.id })}
              className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                context.experience_level === e.id
                  ? "bg-gray-800 text-white"
                  : "bg-gray-100 text-gray-600 hover:bg-gray-200"
              }`}
            >
              {e.label}
            </button>
          ))}
        </div>
      </div>

      {/* Deal-breakers */}
      <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-5">
        <h2 className="text-sm font-semibold text-gray-500 uppercase tracking-wide mb-3">
          Deal-breakers to check
        </h2>
        <div className="flex flex-wrap gap-2 mb-2">
          {DEAL_BREAKER_OPTIONS.map((db) => (
            <button
              key={db}
              onClick={() => toggleDealBreaker(db)}
              className={`px-3 py-1.5 rounded-full text-sm font-medium transition-colors ${
                context.deal_breakers.includes(db)
                  ? "bg-red-100 text-red-800 border border-red-200"
                  : "bg-gray-100 text-gray-600 hover:bg-gray-200 border border-transparent"
              }`}
            >
              {db.replace(/_/g, " ")}
            </button>
          ))}
        </div>
        <div className="flex gap-2 mt-2">
          <input
            type="text"
            value={customDealBreaker}
            onChange={(e) => setCustomDealBreaker(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && addCustomDealBreaker()}
            placeholder="Add custom..."
            className="flex-1 px-3 py-1.5 text-sm border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
          <button
            onClick={addCustomDealBreaker}
            className="px-3 py-1.5 text-sm font-medium text-blue-600 hover:bg-blue-50 rounded-lg"
          >
            Add
          </button>
        </div>
      </div>

      {/* Get insights button */}
      <button
        onClick={handleGetInsights}
        disabled={insightsLoading}
        className="w-full py-3 bg-blue-500 text-white text-sm font-semibold rounded-xl hover:bg-blue-600 disabled:opacity-60 disabled:cursor-not-allowed transition-colors shadow-sm"
      >
        {insightsLoading ? (
          <span className="flex items-center justify-center gap-2">
            <span className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
            Generating insights...
          </span>
        ) : (
          "Get personalized insights"
        )}
      </button>

      {/* Insights error */}
      {insightsError && (
        <div className="p-4 bg-red-50 border border-red-100 rounded-xl text-sm text-red-700">
          {insightsError}
        </div>
      )}

      {/* Insights display */}
      {insights && !insightsLoading && (
        <div className="space-y-4">
          <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-5">
            <h2 className="text-sm font-semibold text-gray-500 uppercase tracking-wide mb-3">
              For you
            </h2>
            <p className="text-sm text-gray-700 leading-relaxed">
              {insights.tailored_summary}
            </p>
          </div>

          {insights.top_risks_for_you.length > 0 && (
            <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-5">
              <h2 className="text-sm font-semibold text-gray-500 uppercase tracking-wide mb-3">
                Top risks for you
              </h2>
              <ul className="space-y-2">
                {insights.top_risks_for_you.map((risk, i) => (
                  <li key={i} className="flex items-start gap-3">
                    <span className="mt-1 text-amber-500 shrink-0">
                      <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
                        <path
                          fillRule="evenodd"
                          d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z"
                          clipRule="evenodd"
                        />
                      </svg>
                    </span>
                    <span className="text-sm text-gray-700">{risk}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}

          {insights.action_items.length > 0 && (
            <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-5">
              <h2 className="text-sm font-semibold text-gray-500 uppercase tracking-wide mb-3">
                Action items
              </h2>
              <ul className="space-y-2">
                {insights.action_items.map((item, i) => (
                  <li key={i} className="flex items-start gap-3">
                    <span className="mt-1 text-blue-500 shrink-0">
                      <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
                        <path
                          fillRule="evenodd"
                          d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z"
                          clipRule="evenodd"
                        />
                      </svg>
                    </span>
                    <span className="text-sm text-gray-700">{item}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}

          {insights.deal_breaker_checks.length > 0 && (
            <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-5">
              <h2 className="text-sm font-semibold text-gray-500 uppercase tracking-wide mb-3">
                Deal-breaker check
              </h2>
              <ul className="space-y-2">
                {insights.deal_breaker_checks.map((check, i) => (
                  <li key={i} className="flex items-start gap-3">
                    <span className="mt-1 text-gray-400 shrink-0">
                      <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
                        <path
                          fillRule="evenodd"
                          d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z"
                          clipRule="evenodd"
                        />
                      </svg>
                    </span>
                    <span className="text-sm text-gray-700">{check}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}

      {!insights && !insightsLoading && !insightsError && (
        <div className="text-center py-6 text-gray-400 text-sm">
          Fill in your context above and click &quot;Get personalized insights&quot; to see tailored analysis.
        </div>
      )}
    </div>
  );
}
