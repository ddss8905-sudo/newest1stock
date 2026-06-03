"use client";

import { useState } from "react";
import { Play, RefreshCw } from "lucide-react";
import type { Market } from "@/lib/types";

type RunState = {
  status: "idle" | "running" | "success" | "error";
  message: string;
};

export function RunButtons({ market }: { market: Market }) {
  const [state, setState] = useState<RunState>({ status: "idle", message: "" });

  async function runNow() {
    setState({ status: "running", message: `Requesting ${market} workflow...` });
    try {
      const response = await fetch("/api/run-screener", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ market }),
      });
      const data = await response.json();
      if (!response.ok) {
        throw new Error(data.error ?? "Failed to request workflow.");
      }
      setState({
        status: "success",
        message: `${market} workflow requested. Refresh latest results after it finishes.`,
      });
    } catch (error) {
      setState({
        status: "error",
        message: error instanceof Error ? error.message : "Unknown request error.",
      });
    }
  }

  return (
    <div className="runPanel">
      <button className="primaryButton" type="button" onClick={runNow} disabled={state.status === "running"}>
        {state.status === "running" ? <RefreshCw size={16} className="spin" /> : <Play size={16} />}
        Run {market} now
      </button>
      <a className="secondaryButton" href={`/?market=${market}`}>
        <RefreshCw size={16} />
        Refresh latest
      </a>
      {state.message && <p className={`runMessage ${state.status}`}>{state.message}</p>}
    </div>
  );
}
