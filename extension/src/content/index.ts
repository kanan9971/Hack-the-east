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

  const extractionTargets = [
    "main",
    "article",
    "[role='main']",
    "[data-testid*='legal']",
    "[class*='legal']",
    "[class*='terms']",
    "[class*='policy']",
    "[id*='legal']",
    "[id*='terms']",
    "[id*='policy']",
  ];

  const selectorsToRemove =
    "nav, header, footer, .nav, .header, .footer, .sidebar, .menu, .cookie-banner, .ad, [role='navigation'], [role='banner'], [aria-hidden='true'], [hidden]";

  const candidateRoots: HTMLElement[] = [];
  for (const s of extractionTargets) {
    document.querySelectorAll(s).forEach((el) => {
      if (el instanceof HTMLElement) candidateRoots.push(el);
    });
  }
  candidateRoots.push(body);

  let best = "";
  for (const root of candidateRoots) {
    const clone = root.cloneNode(true) as HTMLElement;
    clone.querySelectorAll(selectorsToRemove).forEach((el) => el.remove());
    clone.querySelectorAll("script, style, noscript, iframe, svg").forEach((el) =>
      el.remove()
    );

    let text = clone.innerText || clone.textContent || "";
    text = text.replace(/\n{3,}/g, "\n\n").replace(/[ \t]{2,}/g, " ").trim();
    if (text.length > best.length) best = text;
  }

  return best;
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
    const collect = () => {
      const text = extractPageText();
      const doc_type = detectDocType();
      sendResponse({ type: "PAGE_TEXT", text, doc_type });
    };

    // Some sites (including legal pages with heavy hydration) finish rendering late.
    const initial = extractPageText();
    if (initial.length >= 200) {
      const doc_type = detectDocType();
      sendResponse({ type: "PAGE_TEXT", text: initial, doc_type });
      return true;
    }

    window.setTimeout(collect, 1200);
  }
  return true;
});

chrome.runtime.sendMessage({
  type: "LEGAL_PAGE_STATUS",
  isLegal: isLegalPage(),
  url: window.location.href,
});
