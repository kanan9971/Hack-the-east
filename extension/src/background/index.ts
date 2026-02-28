import { API_BASE } from "../shared/config";

interface AnalysisState {
  status: "idle" | "loading" | "done" | "error";
  data?: unknown;
  error?: string;
}

let currentState: AnalysisState = { status: "idle" };
let lastAnalyzedText = "";

async function restoreCachedState() {
  const { analysisResult } = await chrome.storage.session.get("analysisResult");
  if (analysisResult) {
    currentState = { status: "done", data: analysisResult };
  }
}

function broadcastState() {
  chrome.runtime.sendMessage({
    type: "STATE_UPDATE",
    state: currentState,
  }).catch(() => {
    // Side panel may not be open yet
  });
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

async function extractByInjectedScript(tabId: number): Promise<{ text: string; doc_type?: string }> {
  const results = await chrome.scripting.executeScript({
    target: { tabId },
    world: "ISOLATED",
    func: () => {
      const url = window.location.href.toLowerCase();
      const title = document.title.toLowerCase();
      const combined = `${url} ${title}`;

      let doc_type: string | undefined;
      if (/privacy|data.?protection/.test(combined)) doc_type = "privacy";
      else if (/terms.?of.?service|tos|terms.?of.?use|terms.?and.?condition/.test(combined)) doc_type = "tos";
      else if (/lease|rental/.test(combined)) doc_type = "lease";
      else if (/offer|employment|job/.test(combined)) doc_type = "job_offer";
      else if (/nda|non.?disclosure|confidential/.test(combined)) doc_type = "nda";

      const roots: HTMLElement[] = [];
      const targetSelectors = [
        "main",
        "article",
        "[role='main']",
        "[class*='legal']",
        "[class*='terms']",
        "[class*='policy']",
        "[id*='legal']",
        "[id*='terms']",
        "[id*='policy']",
      ];

      for (const s of targetSelectors) {
        document.querySelectorAll(s).forEach((el) => {
          if (el instanceof HTMLElement) roots.push(el);
        });
      }
      if (document.body) roots.push(document.body);

      const removeSelectors =
        "nav, header, footer, .nav, .header, .footer, .sidebar, .menu, .cookie-banner, .ad, [role='navigation'], [role='banner'], [aria-hidden='true'], [hidden]";

      let best = "";
      for (const root of roots) {
        const clone = root.cloneNode(true) as HTMLElement;
        clone.querySelectorAll(removeSelectors).forEach((el) => el.remove());
        clone.querySelectorAll("script, style, noscript, iframe, svg").forEach((el) =>
          el.remove()
        );

        let text = clone.innerText || clone.textContent || "";
        text = text.replace(/\n{3,}/g, "\n\n").replace(/[ \t]{2,}/g, " ").trim();
        if (text.length > best.length) best = text;
      }

      return { text: best, doc_type };
    },
  });

  const payload = results?.[0]?.result as { text?: string; doc_type?: string } | undefined;
  return {
    text: payload?.text || "",
    doc_type: payload?.doc_type,
  };
}

async function getPagePayload(tabId: number): Promise<{ text: string; doc_type?: string }> {
  try {
    const response = await chrome.tabs.sendMessage(tabId, {
      type: "ANALYZE_PAGE",
    });
    const text = response?.text || "";
    if (text.length >= 120) {
      return { text, doc_type: response?.doc_type };
    }
  } catch {
    // Fallback to direct extraction.
  }

  return extractByInjectedScript(tabId);
}

chrome.action.onClicked.addListener(async (tab) => {
  if (!tab.id) return;

  await chrome.sidePanel.open({ tabId: tab.id });

  try {
    const payload = await getPagePayload(tab.id);

    if (payload.text && payload.text.length > 50) {
      await runAnalysis(payload.text, payload.doc_type);
    } else {
      currentState = {
        status: "error",
        error: "Could not extract enough text from this page. Try pasting text manually.",
      };
      broadcastState();
    }
  } catch {
    currentState = {
      status: "error",
      error: "Could not connect to the page. Refresh and try again.",
    };
    broadcastState();
  }
});

chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (message.type === "GET_STATE") {
    sendResponse(currentState);
    return false;
  }

  if (message.type === "ANALYZE_TEXT") {
    (async () => {
      const text = message.text || lastAnalyzedText;
      if (!text) {
        sendResponse({ ok: false, error: "No text available to analyze." });
        return;
      }

      await runAnalysis(text, message.doc_type, message.persona);
      sendResponse({ ok: true });
    })().catch((err: unknown) => {
      const msg = err instanceof Error ? err.message : "Unknown error";
      sendResponse({ ok: false, error: msg });
    });
    return true;
  }

  if (message.type === "LEGAL_PAGE_STATUS") {
    if (!sender.tab?.id) return false;

    const tabId = sender.tab.id;
    const badgeText = message.isLegal ? "!" : "";
    chrome.action.setBadgeText({ tabId, text: badgeText });
    chrome.action.setBadgeBackgroundColor({ tabId, color: "#3B82F6" });
    return false;
  }

  return false;
});

chrome.sidePanel
  .setPanelBehavior({ openPanelOnActionClick: true })
  .catch(() => {});

restoreCachedState().catch(() => {});
