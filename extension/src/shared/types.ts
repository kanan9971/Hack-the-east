export interface RiskFlag {
  category: string;
  severity: "high" | "medium" | "low";
  clause_excerpt: string;
  explanation: string;
}

export interface SectionOut {
  title: string;
  body: string;
  labels: string[];
}

export interface AnalyzeResponse {
  summary: string;
  key_points: string[];
  risks: RiskFlag[];
  sections: SectionOut[];
  entities: {
    parties?: string[];
    dates?: string[];
    amounts?: string[];
    obligations?: string[];
  };
  persona_notes: string[] | null;
}

export interface AnalyzeRequest {
  text: string;
  doc_type?: string;
  persona?: string;
}

export interface UserContext {
  persona?: string;
  primary_concerns: string[];
  document_context?: string;
  experience_level?: string;
  deal_breakers: string[];
}

export interface ForYouInsights {
  top_risks_for_you: string[];
  action_items: string[];
  deal_breaker_checks: string[];
  tailored_summary: string;
}

export interface InsightsRequest {
  analysis: AnalyzeResponse;
  user_context: UserContext;
}

export interface InsightsResponse {
  insights: ForYouInsights;
}

export interface VaultReceipt {
  vault_id: string;
  content_hash: string;
  timestamp: string;
  vault_address: string;
  network: string;
  algorithm: string;
  status: string;
  expires: string | null;
  message: string;
}

export type MessageType =
  | { type: "ANALYZE_PAGE" }
  | { type: "ANALYZE_TEXT"; text: string; doc_type?: string; persona?: string }
  | { type: "GENERATE_INSIGHTS"; analysis: AnalyzeResponse; user_context: UserContext }
  | { type: "ANALYSIS_STARTED" }
  | { type: "ANALYSIS_COMPLETE"; data: AnalyzeResponse }
  | { type: "ANALYSIS_ERROR"; error: string }
  | { type: "INSIGHTS_UPDATE"; insights: ForYouInsights | null; error?: string }
  | { type: "PAGE_TEXT"; text: string };
