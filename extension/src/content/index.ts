const LEGAL_URL_PATTERNS = [
  /\/terms/i,
  /\/tos/i,
  /\/privacy/i,
  /\/legal/i,
  /\/policy/i,
  /\/contract/i,
  /\/agreement/i,
  /\/eula/i,
  /\/offer/i,
  /\/lease/i,
  /\/nda/i,
  /\/disclaimer/i,
];

function isLegalPage(): boolean {
  const url = window.location.href.toLowerCase();
  return LEGAL_URL_PATTERNS.some((p) => p.test(url));
}

function extractPageText(): string {
  const body = document.body;
  if (!body) return "";

  const selectors =
    "nav, header, footer, .nav, .header, .footer, .sidebar, .menu, .cookie-banner, .ad, [role='navigation'], [role='banner']";
  const clone = body.cloneNode(true) as HTMLElement;

  clone.querySelectorAll(selectors).forEach((el) => el.remove());
  clone.querySelectorAll("script, style, noscript, iframe").forEach((el) =>
    el.remove()
  );

  let text = clone.innerText || clone.textContent || "";
  text = text.replace(/\n{3,}/g, "\n\n").trim();

  return text;
}

function detectDocType(): string | undefined {
  const url = window.location.href.toLowerCase();
  const title = document.title.toLowerCase();
  const combined = url + " " + title;

  if (/privacy|data.?protection/.test(combined)) return "privacy";
  if (/terms.?of.?service|tos|terms.?of.?use|terms.?and.?condition/.test(combined)) return "tos";
  if (/lease|rental/.test(combined)) return "lease";
  if (/offer|employment|job/.test(combined)) return "job_offer";
  if (/nda|non.?disclosure|confidential/.test(combined)) return "nda";
  return undefined;
}

chrome.runtime.onMessage.addListener((message, _sender, sendResponse) => {
  if (message.type === "ANALYZE_PAGE") {
    const text = extractPageText();
    const doc_type = detectDocType();
    sendResponse({ type: "PAGE_TEXT", text, doc_type });
  }
  return true;
});

if (isLegalPage()) {
  chrome.runtime.sendMessage({
    type: "LEGAL_PAGE_DETECTED",
    url: window.location.href,
  });
}
