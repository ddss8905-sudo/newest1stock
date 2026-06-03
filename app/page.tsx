import type { ReactNode } from "react";
import { Activity, ArrowDownRight, ArrowUpRight, Clock, Database, Filter } from "lucide-react";
import { getDashboardData } from "@/lib/data";
import type { Market, ScreeningResult } from "@/lib/types";
import { RunButtons } from "./run-buttons";

type PageProps = {
  searchParams?: Promise<{ market?: string }>;
};

const markets: Market[] = ["NASDAQ", "KOSDAQ", "KOSPI_API"];

function asMarket(value: string | undefined): Market {
  if (value === "KOSPI_API") return "KOSPI_API";
  return value === "KOSDAQ" ? "KOSDAQ" : "NASDAQ";
}

function number(value: number | null | undefined, digits = 1) {
  if (value === null || value === undefined || Number.isNaN(Number(value))) return "-";
  return Number(value).toLocaleString("ko-KR", { maximumFractionDigits: digits });
}

function percent(value: number | null | undefined, digits = 1) {
  if (value === null || value === undefined || Number.isNaN(Number(value))) return "-";
  return `${(Number(value) * 100).toLocaleString("ko-KR", { maximumFractionDigits: digits })}%`;
}

function setupLabel(value: string | null | undefined) {
  if (value === "breakout") return "Breakout";
  if (value === "pullback") return "Pullback";
  return "Watch";
}

function regimeLabel(score: number | null | undefined) {
  if (score === null || score === undefined || Number.isNaN(Number(score))) return "-";
  if (score >= 70) return "Bullish";
  if (score >= 55) return "Constructive";
  if (score >= 40) return "Cautious";
  return "Defensive";
}

function dateTime(value: string | null | undefined) {
  if (!value) return "-";
  return new Intl.DateTimeFormat("ko-KR", {
    timeZone: "Asia/Seoul",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
  }).format(new Date(value));
}

function MarketTabs({ active }: { active: Market }) {
  return (
    <div className="tabs" aria-label="Market selector">
      {markets.map((market) => (
        <a className={market === active ? "tab active" : "tab"} href={`/?market=${market}`} key={market}>
          {market}
        </a>
      ))}
    </div>
  );
}

function Stat({ label, value, icon }: { label: string; value: string; icon: ReactNode }) {
  return (
    <div className="stat">
      <div className="statIcon">{icon}</div>
      <div>
        <div className="statLabel">{label}</div>
        <div className="statValue">{value}</div>
      </div>
    </div>
  );
}

function ResultTable({ rows, compact = false }: { rows: ScreeningResult[]; compact?: boolean }) {
  return (
    <div className="tableWrap">
      <table>
        <thead>
          <tr>
            <th>Ticker</th>
            {!compact && <th>Setup</th>}
            <th>Name</th>
            <th>Close</th>
            <th>Final</th>
            <th>RS</th>
            <th>Trend</th>
            <th>Breakout</th>
            <th>ADV20</th>
            {!compact && <th>Risk</th>}
            {!compact && <th>Ext</th>}
            {!compact && <th>Stop</th>}
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <tr key={`${row.ticker}-${row.final_score}`}>
              <td className="mono">
                <span className={row.entry_trigger ? "triggerDot on" : "triggerDot"} />
                {row.ticker}
              </td>
              {!compact && <td>{setupLabel(row.entry_setup)}</td>}
              <td className="nameCell">{row.security_name ?? "-"}</td>
              <td>{number(row.close, 0)}</td>
              <td className="strong">{number(row.final_score, 1)}</td>
              <td>{number(row.rs_rank, 1)}</td>
              <td>{number(row.trend_score, 1)}</td>
              <td>{number(row.breakout_score, 1)}</td>
              <td>{number(row.adv20, 0)}</td>
              {!compact && <td>{percent(row.risk_to_stop, 1)}</td>}
              {!compact && <td>{percent(row.entry_extension_pct, 1)}</td>}
              {!compact && <td>{number(row.stop_price, 0)}</td>}
            </tr>
          ))}
          {rows.length === 0 && (
            <tr>
              <td className="empty" colSpan={compact ? 8 : 12}>No results to display.</td>
            </tr>
          )}
        </tbody>
      </table>
    </div>
  );
}

export default async function Page({ searchParams }: PageProps) {
  const params = await searchParams;
  const market = asMarket(params?.market);
  const data = await getDashboardData(market);
  const latestRun = dateTime(data.run?.finished_at) || data.run?.run_date || "-";
  const regimeValue = data.run
    ? `${regimeLabel(data.run.market_regime_score)} ${number(data.run.market_regime_score, 0)}`
    : "-";
  const regimeTradable = Number(data.run?.market_regime_score ?? 0) >= 55;

  return (
    <main>
      <section className="topbar">
        <div>
          <p className="eyebrow">Trend Following Screener</p>
          <h1>Market Screener</h1>
        </div>
        <MarketTabs active={market} />
      </section>

      {data.usingSampleData && (
        <div className="notice">
          Supabase environment variables are missing, so sample rows are shown. Connect Supabase to display live screening results.
        </div>
      )}

      <section className="stats">
        <Stat label="Market" value={market} icon={<Database size={18} />} />
        <Stat label="Latest run" value={latestRun} icon={<Clock size={18} />} />
        <Stat label="Run mode" value={market === "KOSPI_API" ? "KIS API" : "On demand"} icon={<Activity size={18} />} />
        <Stat label="Candidates" value={String(data.run?.candidate_count ?? data.candidates.length)} icon={<Filter size={18} />} />
        <Stat
          label="Regime"
          value={regimeValue}
          icon={regimeTradable ? <ArrowUpRight size={18} /> : <ArrowDownRight size={18} />}
        />
      </section>

      <section className="section">
        <div className="sectionHead">
          <div>
            <h2>Run on demand</h2>
            <p>Trigger the selected market workflow in GitHub Actions, then refresh after it completes.</p>
          </div>
        </div>
        <RunButtons market={market} />
      </section>

      <section className="section">
        <div className="sectionHead">
          <div>
            <h2>Candidate List</h2>
            <p>Stocks that passed score, relative strength, liquidity, high proximity, and stop-risk filters.</p>
          </div>
        </div>
        <ResultTable rows={data.candidates} />
      </section>

      <section className="section">
        <div className="sectionHead">
          <div>
            <h2>Full Scoreboard</h2>
            <p>Ranked scoring table for the current screening universe.</p>
          </div>
        </div>
        <ResultTable rows={data.scored} compact />
      </section>
    </main>
  );
}
