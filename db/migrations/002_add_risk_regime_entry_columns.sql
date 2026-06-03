alter table screening_runs
  add column if not exists market_regime_score numeric,
  add column if not exists market_exposure numeric;

alter table screening_results
  add column if not exists close_prev numeric,
  add column if not exists high numeric,
  add column if not exists low numeric,
  add column if not exists atr14 numeric,
  add column if not exists low20_prev numeric,
  add column if not exists low50_prev numeric,
  add column if not exists ma20 numeric,
  add column if not exists close_to_ma50_ratio numeric,
  add column if not exists market_regime_score numeric,
  add column if not exists market_exposure numeric,
  add column if not exists entry_pivot numeric,
  add column if not exists entry_extension_pct numeric,
  add column if not exists breakout_entry boolean default false,
  add column if not exists pullback_entry boolean default false,
  add column if not exists entry_setup text,
  add column if not exists stop_basis text;
