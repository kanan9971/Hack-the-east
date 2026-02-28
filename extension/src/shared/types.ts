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

export type MessageType =
  | { type: "ANALYZE_PAGE" }
  | { type: "ANALYZE_TEXT"; text: string; doc_type?: string; persona?: string }
  | { type: "ANALYSIS_STARTED" }
  | { type: "ANALYSIS_COMPLETE"; data: AnalyzeResponse }
  | { type: "ANALYSIS_ERROR"; error: string }
  | { type: "PAGE_TEXT"; text: string };
