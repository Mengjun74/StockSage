export interface CasePoint {
  claim: string;
  evidence: string;
}

export interface AnalysisCase {
  side: string;
  case_strength: "strong" | "moderate" | "weak";
  summary: string;
  points: CasePoint[];
  strongest_counterpoint: string;
}

export interface AnalysisLevel {
  label: string;
  price: number;
  basis: string;
}

export interface AnalysisResponse {
  ticker: string;
  created_at: string;
  model: string;
  price_at_analysis: number;
  action: string;
  confidence: "high" | "medium" | "low";
  horizon_days: number;
  entry: AnalysisLevel;
  target: AnalysisLevel;
  stop: AnalysisLevel;
  risk_reward: number | null;
  reasoning: string;
  invalidation: string;
  disagreement: string;
  bull: AnalysisCase;
  bear: AnalysisCase;
  articles_considered: number;
  disclaimer: string;
}
