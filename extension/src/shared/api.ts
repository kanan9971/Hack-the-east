import type { AnalyzeRequest, AnalyzeResponse, VaultReceipt } from "./types";

const API_BASE = "http://localhost:8000";

export const DASHBOARD_URL = `${API_BASE}/dashboard`;

export async function analyzeDocument(
  req: AnalyzeRequest
): Promise<AnalyzeResponse> {
  const res = await fetch(`${API_BASE}/analyze`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(req),
  });

  if (!res.ok) {
    const detail = await res.text();
    throw new Error(`API error ${res.status}: ${detail}`);
  }

  return res.json();
}

export async function vaultAnalysis(
  analysis: Record<string, unknown>
): Promise<VaultReceipt> {
  const res = await fetch(`${API_BASE}/vault`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ analysis }),
  });

  if (!res.ok) {
    const detail = await res.text();
    throw new Error(`Vault error ${res.status}: ${detail}`);
  }

  return res.json();
}
