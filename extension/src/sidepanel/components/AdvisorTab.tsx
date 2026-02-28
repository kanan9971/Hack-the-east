import { useMemo, useState } from "react";
import { askAdvisor } from "../../shared/api";
import type { AnalyzeResponse } from "../../shared/types";

interface ChatMessage {
  role: "user" | "assistant";
  content: string;
}

interface AdvisorTabProps {
  data: AnalyzeResponse | null;
}

function escapeHtml(text: string): string {
  return text
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;");
}

function renderSimpleMarkdown(text: string): string {
  const escaped = escapeHtml(text);
  const withInline = escaped
    .replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>")
    .replace(/`(.+?)`/g, "<code>$1</code>");

  const lines = withInline.split("\n");
  const rendered = lines.map((line) => {
    if (line.startsWith("### ")) return `<h3>${line.slice(4)}</h3>`;
    if (line.startsWith("## ")) return `<h2>${line.slice(3)}</h2>`;
    if (line.startsWith("# ")) return `<h1>${line.slice(2)}</h1>`;
    if (line.startsWith("- ")) return `<li>${line.slice(2)}</li>`;
    if (!line.trim()) return "<br/>";
    return `<p>${line}</p>`;
  });

  const html = rendered.join("");
  return html.replace(/(<li>.*?<\/li>)+/g, (match) => `<ul>${match}</ul>`);
}

const STARTER_PROMPTS = [
  "What risks does this clause pose for a HK student?",
  "Draft an email to negotiate this auto-renewal clause.",
  "Compare this ToS with Google's and tell me which is better.",
  "Check whether this handling of personal data may conflict with HK PDPO.",
];

export default function AdvisorTab({ data }: AdvisorTabProps) {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [query, setQuery] = useState("");
  const [sessionId, setSessionId] = useState<string | undefined>(undefined);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const contextHint = useMemo(() => {
    if (!data) return "";
    const topRisks = data.risks
      .slice(0, 3)
      .map((r) => `${r.category} (${r.severity})`)
      .join(", ");
    return `Context from latest analysis: ${data.summary}\nTop risks: ${topRisks || "none detected"}.`;
  }, [data]);

  const sendMessage = async (text: string) => {
    const trimmed = text.trim();
    if (!trimmed || loading) return;

    setError("");
    setLoading(true);
    setMessages((prev) => [...prev, { role: "user", content: trimmed }]);

    try {
      const fullQuery = contextHint ? `${contextHint}\n\nUser question: ${trimmed}` : trimmed;
      const res = await askAdvisor({
        query: fullQuery,
        session_id: sessionId,
      });

      setSessionId(res.session_id);
      setMessages((prev) => [...prev, { role: "assistant", content: res.response }]);
      setQuery("");
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Unknown error";
      setError(msg);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-3">
      <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-4">
        <h2 className="text-sm font-semibold text-gray-700 mb-2">Ask Advisor</h2>
        <p className="text-xs text-gray-500">
          HK-focused guidance for students, freelancers, and fintech users. This is informational and not legal advice.
        </p>
      </div>

      {messages.length === 0 && (
        <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-4">
          <p className="text-xs text-gray-500 mb-2">Try one of these:</p>
          <div className="flex flex-wrap gap-2">
            {STARTER_PROMPTS.map((prompt) => (
              <button
                key={prompt}
                onClick={() => sendMessage(prompt)}
                className="px-3 py-1.5 text-xs rounded-full bg-blue-50 text-blue-700 hover:bg-blue-100"
              >
                {prompt}
              </button>
            ))}
          </div>
        </div>
      )}

      <div className="space-y-2">
        {messages.map((m, idx) => (
          <div
            key={`${m.role}-${idx}`}
            className={`rounded-xl px-3 py-2 text-sm ${
              m.role === "user"
                ? "bg-blue-500 text-white ml-8"
                : "bg-white border border-gray-100 text-gray-800 mr-4"
            }`}
          >
            {m.role === "assistant" ? (
              <div
                className="prose prose-sm max-w-none"
                dangerouslySetInnerHTML={{ __html: renderSimpleMarkdown(m.content) }}
              />
            ) : (
              <p className="whitespace-pre-wrap">{m.content}</p>
            )}
          </div>
        ))}

        {loading && (
          <div className="bg-white border border-gray-100 rounded-xl px-3 py-2 text-sm text-gray-500 mr-4">
            Advisor is thinking...
          </div>
        )}
      </div>

      {error && <div className="text-xs text-red-600">{error}</div>}

      <div className="bg-white rounded-xl border border-gray-100 p-3">
        <textarea
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Ask about risks, negotiation emails, comparisons, or HK PDPO..."
          className="w-full h-24 p-2 text-sm border border-gray-200 rounded-lg resize-none focus:outline-none focus:ring-2 focus:ring-blue-500"
        />
        <button
          onClick={() => sendMessage(query)}
          disabled={query.trim().length < 5 || loading}
          className="mt-2 w-full py-2 bg-blue-500 text-white text-sm font-medium rounded-lg hover:bg-blue-600 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {loading ? "Sending..." : "Send"}
        </button>
      </div>
    </div>
  );
}
