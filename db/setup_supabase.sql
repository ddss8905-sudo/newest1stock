create extension if not exists pgcrypto;

create table if not exists screening_runs (
  id uuid primary key default gen_random_uuid(),
  market text not null check (market in ('NASDAQ', 'KOSDAQ', 'KOSPI_API')),
  run_date date not null,
  status text not null default 'completed',
  market_bullish boolean not null default false,
  market_regime_score numeric,
  market_exposure numeric,
  selected_count integer not null default 0,
  scored_count integer not null default 0,
  candidate_count integer not null default 0,
  started_at timestamptz,
  finished_at timestamptz,
  created_at timestamptz not null default now()
);

create table if not exists screening_results (
  id bigserial primary key,
  run_id uuid not null references screening_runs(id) on delete cascade,
  market text not null check (market in ('NASDAQ', 'KOSDAQ', 'KOSPI_API')),
  run_date date not null,
  ticker text not null,
  security_name text,
  close numeric,
  close_prev numeric,
  high numeric,
  low numeric,
  adv20 numeric,
  atr14 numeric,
  atr_pct numeric,
  high50_prev numeric,
  low20_prev numeric,
  low50_prev numeric,
  vol_ma50 numeric,
  volume numeric,
  ma20 numeric,
  ma50 numeric,
  ma200 numeric,
  high252 numeric,
  close_to_52w_high_ratio numeric,
  close_to_ma50_ratio numeric,
  trend_raw numeric,
  rs_raw numeric,
  momentum_raw numeric,
  breakout_raw numeric,
  accumulation_raw numeric,
  vcp_raw numeric,
  fundamental_proxy_raw numeric,
  risk_liquidity_raw numeric,
  trend_score numeric,
  rs_score numeric,
  momentum_score numeric,
  breakout_score numeric,
  accumulation_score numeric,
  vcp_score numeric,
  fundamental_proxy_score numeric,
  risk_liquidity_score numeric,
  final_score numeric,
  rs_rank numeric,
  market_regime_score numeric,
  market_exposure numeric,
  entry_pivot numeric,
  entry_extension_pct numeric,
  breakout_entry boolean default false,
  pullback_entry boolean default false,
  entry_setup text,
  entry_trigger boolean default false,
  stop_price numeric,
  stop_basis text,
  risk_to_stop numeric,
  is_candidate boolean not null default false,
  created_at timestamptz not null default now()
);

create index if not exists screening_runs_market_date_idx
  on screening_runs (market, run_date desc, created_at desc);

create index if not exists screening_results_run_score_idx
  on screening_results (run_id, final_score desc);

create index if not exists screening_results_candidates_idx
  on screening_results (market, run_date desc, is_candidate, entry_trigger);
