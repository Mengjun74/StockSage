import axios from "axios";
import type { PriceResponse, SupportedInterval, SupportedPeriod } from "../types/prices";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000/api/v1";

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
