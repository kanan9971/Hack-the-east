import { useEffect, useState } from "react";
import type { AnalyzeResponse } from "../shared/types";
import SummaryTab from "./components/SummaryTab";
import RisksTab from "./components/RisksTab";
import DetailsTab from "./components/DetailsTab";
import ForYouTab from "./components/ForYouTab";

type Tab = "summary" | "risks" | "details" | "foryou";

const TABS: { id: Tab; label: string }[] = [
  { id: "summary", label: "Summary" },
  { id: "risks", label: "Risks" },
  { id: "details", label: "Details" },
  { id: "foryou", label: "For You" },
];

function LoadingSkeleton() {
  return (
    <div className="space-y-4 animate-pulse">
      <div className="bg-white rounded-xl p-5 space-y-3">
        <div className="h-3 bg-gray-200 rounded w-1/3" />
        <div className="h-4 bg-gray-200 rounded w-full" />
        <div className="h-4 bg-gray-200 rounded w-5/6" />
        <div className="h-4 bg-gray-200 rounded w-4/6" />
      </div>
      <div className="bg-white rounded-xl p-5 space-y-3">
        <div className="h-3 bg-gray-200 rounded w-1/4" />
        <div className="h-3 bg-gray-200 rounded w-full" />
        <div className="h-3 bg-gray-200 rounded w-full" />
        <div className="h-3 bg-gray-200 rounded w-3/4" />
      </div>
      <div className="bg-white rounded-xl p-5 space-y-3">
        <div className="h-3 bg-gray-200 rounded w-1/4" />
        <div className="h-3 bg-gray-200 rounded w-5/6" />
        <div className="h-3 bg-gray-200 rounded w-2/3" />
      </div>
    </div>
  );
}

export default function App() {
  const [tab, setTab] = useState<Tab>("summary");
  const [status, setStatus] = useState<"idle" | "loading" | "done" | "error">("idle");
  const [data, setData] = useState<AnalyzeResponse | null>(null);
  const [error, setError] = useState<string>("");
  const [pasteText, setPasteText] = useState("");
  const [showPaste, setShowPaste] = useState(false);

  useEffect(() => {
    chrome.runtime.sendMessage({ type: "GET_STATE" }, (response) => {
      if (response) {
        setStatus(response.status || "idle");
        if (response.data) setData(response.data as AnalyzeResponse);
        if (response.error) setError(response.error);
      }
    });

    const listener = (message: { type: string; state?: { status: string; data?: AnalyzeResponse; error?: string } }) => {
      if (message.type === "STATE_UPDATE" && message.state) {
        setStatus(message.state.status as typeof status);
        if (message.state.data) setData(message.state.data);
        if (message.state.error) setError(message.state.error);
      }
    };

    chrome.runtime.onMessage.addListener(listener);
    return () => chrome.runtime.onMessage.removeListener(listener);
  }, []);

  const handleManualAnalyze = () => {
    if (pasteText.trim().length < 50) return;
    chrome.runtime.sendMessage({
      type: "ANALYZE_TEXT",
      text: pasteText,
    });
    setShowPaste(false);
    setPasteText("");
  };

  const handleReanalyze = (persona?: string) => {
    chrome.runtime.sendMessage({
      type: "ANALYZE_TEXT",
      text: data ? "" : pasteText,
      persona,
    });
  };

  const handleReanalyzeFromPage = () => {
    chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
      if (tabs[0]?.id) {
        chrome.tabs.sendMessage(tabs[0].id, { type: "ANALYZE_PAGE" }, (response) => {
          if (response?.text) {
            chrome.runtime.sendMessage({
              type: "ANALYZE_TEXT",
              text: response.text,
              doc_type: response.doc_type,
            });
          }
        });
      }
    });
  };

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <div className="bg-white border-b border-gray-200 sticky top-0 z-10">
        <div className="px-4 py-3 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <div className="w-7 h-7 rounded-lg bg-blue-500 flex items-center justify-center">
              <span className="text-white font-bold text-xs">CL</span>
            </div>
            <h1 className="text-base font-semibold text-gray-900">ContractLens</h1>
          </div>
          <div className="flex gap-1">
            <button
              onClick={handleReanalyzeFromPage}
              title="Re-analyze page"
              className="p-1.5 rounded-lg hover:bg-gray-100 text-gray-500"
            >
              <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
              </svg>
            </button>
            <button
              onClick={() => setShowPaste(!showPaste)}
              title="Paste text manually"
              className="p-1.5 rounded-lg hover:bg-gray-100 text-gray-500"
            >
              <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
              </svg>
            </button>
          </div>
        </div>

        {/* Tab bar */}
        {status === "done" && data && (
          <div className="flex px-2">
            {TABS.map((t) => (
              <button
                key={t.id}
                onClick={() => setTab(t.id)}
                className={`px-3 py-2 text-sm font-medium border-b-2 transition-colors ${
                  tab === t.id
                    ? "border-blue-500 text-blue-600"
                    : "border-transparent text-gray-500 hover:text-gray-700"
                }`}
              >
                {t.label}
                {t.id === "risks" && data.risks.length > 0 && (
                  <span className="ml-1 bg-red-100 text-red-600 text-xs font-semibold px-1.5 py-0.5 rounded-full">
                    {data.risks.length}
                  </span>
                )}
              </button>
            ))}
          </div>
        )}
      </div>

      {/* Paste panel */}
      {showPaste && (
        <div className="p-4 bg-blue-50 border-b border-blue-100">
          <textarea
            value={pasteText}
            onChange={(e) => setPasteText(e.target.value)}
            placeholder="Paste contract or legal text here..."
            className="w-full h-32 p-3 text-sm border border-gray-200 rounded-lg resize-none focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
          <button
            onClick={handleManualAnalyze}
            disabled={pasteText.trim().length < 50}
            className="mt-2 w-full py-2 bg-blue-500 text-white text-sm font-medium rounded-lg hover:bg-blue-600 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            Analyze Text
          </button>
        </div>
      )}

      {/* Content area */}
      <div className="p-4">
        {status === "idle" && (
          <div className="text-center py-16 px-4">
            <div className="w-16 h-16 mx-auto mb-4 rounded-2xl bg-blue-100 flex items-center justify-center">
              <svg className="w-8 h-8 text-blue-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
              </svg>
            </div>
            <h2 className="text-lg font-semibold text-gray-800 mb-1">No document analyzed yet</h2>
            <p className="text-sm text-gray-500 max-w-xs mx-auto">
              Navigate to a Terms of Service, privacy policy, or contract page and click the ContractLens icon to analyze it.
            </p>
            <button
              onClick={() => setShowPaste(true)}
              className="mt-4 text-sm text-blue-500 font-medium hover:text-blue-600"
            >
              Or paste text manually
            </button>
          </div>
        )}

        {status === "loading" && (
          <div>
            <div className="flex items-center gap-2 mb-4">
              <div className="w-4 h-4 border-2 border-blue-500 border-t-transparent rounded-full animate-spin" />
              <span className="text-sm text-gray-600 font-medium">Analyzing document...</span>
            </div>
            <LoadingSkeleton />
          </div>
        )}

        {status === "error" && (
          <div className="text-center py-12 px-4">
            <div className="w-12 h-12 mx-auto mb-3 rounded-full bg-red-100 flex items-center justify-center">
              <svg className="w-6 h-6 text-red-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L4.082 16.5c-.77.833.192 2.5 1.732 2.5z" />
              </svg>
            </div>
            <h2 className="text-base font-semibold text-gray-800 mb-1">Analysis failed</h2>
            <p className="text-sm text-gray-500">{error}</p>
            <button
              onClick={() => setShowPaste(true)}
              className="mt-3 text-sm text-blue-500 font-medium hover:text-blue-600"
            >
              Try pasting text manually
            </button>
          </div>
        )}

        {status === "done" && data && (
          <>
            {tab === "summary" && <SummaryTab data={data} />}
            {tab === "risks" && <RisksTab data={data} />}
            {tab === "details" && <DetailsTab data={data} />}
            {tab === "foryou" && (
              <ForYouTab data={data} onReanalyze={handleReanalyze} />
            )}
          </>
        )}
      </div>
    </div>
  );
}
