export type Market = "NASDAQ" | "KOSDAQ" | "KOSPI_API";

export type ScreeningRun = {
  id: string;
  market: Market;
  run_date: string;
  market_bullish: boolean;
  market_regime_score?: number | null;
  market_exposure?: number | null;
  selected_count: number;
  scored_count: number;
  candidate_count: number;
  finished_at: string | null;
};

export type ScreeningResult = {
  ticker: string;
  security_name: string | null;
  close: number | null;
  adv20: number | null;
  final_score: number | null;
  rs_rank: number | null;
  trend_score: number | null;
  momentum_score: number | null;
  breakout_score: number | null;
  accumulation_score: number | null;
  vcp_score: number | null;
  atr_pct?: number | null;
  close_to_ma50_ratio?: number | null;
  entry_pivot?: number | null;
  entry_extension_pct?: number | null;
  breakout_entry?: boolean | null;
  pullback_entry?: boolean | null;
  entry_setup?: string | null;
  entry_trigger: boolean | null;
  stop_price: number | null;
  stop_basis?: string | null;
  risk_to_stop: number | null;
  is_candidate: boolean;
};

export type DashboardData = {
  market: Market;
  run: ScreeningRun | null;
  candidates: ScreeningResult[];
  scored: ScreeningResult[];
  usingSampleData: boolean;
};
