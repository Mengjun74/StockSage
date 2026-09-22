import axios from "axios";
import type { AnalysisResponse } from "../types/analysis";
import type { PriceResponse, SupportedInterval, SupportedPeriod } from "../types/prices";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8003/api/v1";

export const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30000,
});

export async function fetchPrices(
  ticker: string,
  interval: SupportedInterval,
  period: SupportedPeriod,
): Promise<PriceResponse> {
  const response = await api.get<PriceResponse>(`/stocks/${ticker}/prices`, {
    params: { interval, period },
  });
  return response.data;
}

/** Pulls the backend's `{error, message}` detail out of a failed request. */
/** Runs the agents. A POST, and slow: it spends model calls and records the result. */
export async function runAnalysis(ticker: string): Promise<AnalysisResponse> {
  const response = await api.post<AnalysisResponse>(`/stocks/${ticker}/analysis`, null, {
    timeout: 420000,
  });
  return response.data;
}

export function describeApiError(reason: unknown): string {
  if (axios.isAxiosError(reason)) {
    const detail = reason.response?.data?.detail;
    if (typeof detail === "string") return detail;
    if (detail && typeof detail.message === "string") return detail.message;
    if (reason.code === "ECONNABORTED") return "The market data request timed out.";
    if (!reason.response) return "Unable to reach the market data service.";
  }
  if (reason instanceof Error) return reason.message;
  return "Unable to load market data.";
}
