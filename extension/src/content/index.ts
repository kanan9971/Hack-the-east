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

const MAX_TEXT_LENGTH = 15_000;

const JUNK_SELECTORS = [
  "nav", "header", "footer",
  ".nav", ".header", ".footer", ".sidebar", ".menu",
  ".cookie-banner", ".ad", ".ads", ".advert",
  "[role='navigation']", "[role='banner']", "[role='complementary']",
  "#comments", ".comments", ".comment-section",
  "#chat", ".chat", ".live-chat",
  ".feed", ".recommendations", ".related",
  ".video-player", "video", "ytd-watch-flexy #secondary",
  "ytd-comments", "#related", "#guide",
  ".share-bar", ".social-share", ".reactions",
].join(", ");

function isLegalPage(): boolean {
  const url = window.location.href.toLowerCase();
  return LEGAL_URL_PATTERNS.some((p) => p.test(url));
}

function extractPageText(): string {
  const mainContent =
    document.querySelector("main") ||
    document.querySelector("article") ||
    document.querySelector("[role='main']") ||
    document.querySelector("#content") ||
    document.querySelector(".content");

  const root = mainContent || document.body;
  if (!root) return "";

  const clone = root.cloneNode(true) as HTMLElement;

  clone.querySelectorAll(JUNK_SELECTORS).forEach((el) => el.remove());
  clone.querySelectorAll("script, style, noscript, iframe, svg, canvas, img").forEach((el) =>
    el.remove()
  );

  let text = clone.innerText || clone.textContent || "";
  text = text.replace(/\n{3,}/g, "\n\n").replace(/[ \t]{2,}/g, " ").trim();

  if (text.length > MAX_TEXT_LENGTH) {
    text = text.slice(0, MAX_TEXT_LENGTH);
  }

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
