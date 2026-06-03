alter table screening_runs
  drop constraint if exists screening_runs_market_check;

alter table screening_runs
  add constraint screening_runs_market_check
  check (market in ('NASDAQ', 'KOSDAQ', 'KOSPI_API'));

alter table screening_results
  drop constraint if exists screening_results_market_check;

alter table screening_results
  add constraint screening_results_market_check
  check (market in ('NASDAQ', 'KOSDAQ', 'KOSPI_API'));
