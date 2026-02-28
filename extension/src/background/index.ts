import { generateInsights as fetchInsights } from "../shared/api";

const API_BASE = "http://localhost:8000";
const MAX_RETRIES = 3;
const RETRY_DELAY_MS = 800;

interface AnalysisState {
  status: "idle" | "loading" | "done" | "error";
  data?: unknown;
  error?: string;
}

let currentState: AnalysisState = { status: "idle" };
let lastAnalyzedText = "";

function broadcastState() {
  chrome.runtime.sendMessage({
    type: "STATE_UPDATE",
    state: currentState,
  }).catch(() => {});
}

function sleep(ms: number) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

async function sendMessageWithRetry(
  tabId: number,
  message: { type: string },
  retries = MAX_RETRIES
): Promise<{ text?: string; doc_type?: string } | null> {
  for (let i = 0; i < retries; i++) {
    try {
      const response = await chrome.tabs.sendMessage(tabId, message);
      if (response) return response;
    } catch {
      if (i < retries - 1) await sleep(RETRY_DELAY_MS);
    }
  }
  return null;
}

async function runAnalysis(text: string, doc_type?: string, persona?: string) {
  lastAnalyzedText = text;
  currentState = { status: "loading" };
  broadcastState();

  try {
    const res = await fetch(`${API_BASE}/analyze`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text, doc_type, persona }),
    });

    if (!res.ok) {
      const detail = await res.text();
      throw new Error(`API error ${res.status}: ${detail}`);
    }

    const data = await res.json();
    currentState = { status: "done", data };
    await chrome.storage.session.set({ analysisResult: data });
    broadcastState();
  } catch (err: unknown) {
    const msg = err instanceof Error ? err.message : "Unknown error";
    currentState = { status: "error", error: msg };
    broadcastState();
  }
}

chrome.action.onClicked.addListener(async (tab) => {
  if (!tab.id) return;

  await chrome.sidePanel.open({ tabId: tab.id });

  const response = await sendMessageWithRetry(tab.id, { type: "ANALYZE_PAGE" });

  if (response?.text && response.text.length > 50) {
    runAnalysis(response.text, response.doc_type);
  } else {
    currentState = {
      status: "error",
      error: "Could not extract enough text from this page. Try pasting text manually.",
    };
    broadcastState();
  }
});

chrome.runtime.onMessage.addListener((message, _sender, sendResponse) => {
  if (message.type === "GET_STATE") {
    sendResponse(currentState);
    return true;
  }

  if (message.type === "ANALYZE_TEXT") {
    const text = message.text || lastAnalyzedText;
    if (text) {
      runAnalysis(text, message.doc_type, message.persona);
    }
    sendResponse({ ok: true });
    return true;
  }

  if (message.type === "GENERATE_INSIGHTS") {
    (async () => {
      try {
        const res = await fetchInsights({
          analysis: message.analysis,
          user_context: message.user_context,
        });
        chrome.runtime.sendMessage({
          type: "INSIGHTS_UPDATE",
          insights: res.insights,
        }).catch(() => {});
        sendResponse({ ok: true, insights: res.insights });
      } catch (err) {
        const msg = err instanceof Error ? err.message : "Unknown error";
        chrome.runtime.sendMessage({
          type: "INSIGHTS_UPDATE",
          insights: null,
          error: msg,
        }).catch(() => {});
        sendResponse({ ok: false, error: msg });
      }
    })();
    return true;
  }

  if (message.type === "LEGAL_PAGE_DETECTED") {
    chrome.action.setBadgeText({ text: "!" });
    chrome.action.setBadgeBackgroundColor({ color: "#3B82F6" });
    return false;
  }

  return false;
});

chrome.sidePanel
  .setPanelBehavior({ openPanelOnActionClick: true })
  .catch(() => {});
