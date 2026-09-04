export type SupportedInterval = "1h" | "1d";
export type SupportedPeriod = "1m" | "3m" | "6m" | "1y" | "5y";

export interface PricePoint {
  timestamp: string;
  open: number;
  high: number;
  low: number;
  close: number;
  adjusted_close: number | null;
  volume: number;
}

export interface IndicatorSnapshot {
  current_price: number;
  return_1d: number | null;
  return_5d: number | null;
  return_20d: number | null;
  volume: number | null;
  volume_avg_20d: number | null;
  volume_ratio_20d: number | null;
  high_20d: number | null;
  low_20d: number | null;
  high_52w: number | null;
  low_52w: number | null;
  sma_20: number | null;
  sma_50: number | null;
  sma_200: number | null;
  rsi_14: number | null;
  macd: number | null;
  atr_14: number | null;
}

export interface PriceStructure {
  trend: "bullish" | "neutral" | "bearish";
  support_levels: number[];
  resistance_levels: number[];
  swing_highs: number[];
  swing_lows: number[];
  volume_state: string;
  breakout_state: string;
}

export interface PriceResponse {
  ticker: string;
  interval: SupportedInterval;
  period: SupportedPeriod;
  provider: string;
  prices: PricePoint[];
  snapshot: IndicatorSnapshot | null;
  price_structure: PriceStructure | null;
  data_quality: {
    providers_available: string[];
    providers_failed: string[];
    warnings: string[];
  };
}
