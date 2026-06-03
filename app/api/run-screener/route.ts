import { NextRequest, NextResponse } from "next/server";
import type { Market } from "@/lib/types";

const WORKFLOWS: Record<Market, string> = {
  NASDAQ: "nasdaq.yml",
  KOSDAQ: "kosdaq.yml",
  KOSPI_API: "kospi-api.yml",
};

function asMarket(value: unknown): Market | null {
  return value === "NASDAQ" || value === "KOSDAQ" || value === "KOSPI_API" ? value : null;
}

export async function POST(request: NextRequest) {
  const token = process.env.GITHUB_ACTIONS_TOKEN ?? process.env.GITHUB_TOKEN_FOR_DISPATCH;
  const repository = process.env.GITHUB_REPOSITORY ?? "ddss8905-sudo/newest1stock";
  const branch = process.env.GITHUB_DISPATCH_BRANCH ?? "main";

  if (!token) {
    return NextResponse.json(
      { error: "Missing GITHUB_ACTIONS_TOKEN environment variable." },
      { status: 500 },
    );
  }

  const body = await request.json().catch(() => ({}));
  const market = asMarket(body.market);
  if (!market) {
    return NextResponse.json({ error: "market must be NASDAQ, KOSDAQ, or KOSPI_API." }, { status: 400 });
  }

  const workflow = WORKFLOWS[market];
  const response = await fetch(
    `https://api.github.com/repos/${repository}/actions/workflows/${workflow}/dispatches`,
    {
      method: "POST",
      headers: {
        Accept: "application/vnd.github+json",
        Authorization: `Bearer ${token}`,
        "Content-Type": "application/json",
        "X-GitHub-Api-Version": "2022-11-28",
      },
      body: JSON.stringify({ ref: branch }),
    },
  );

  if (!response.ok) {
    const detail = await response.text();
    return NextResponse.json(
      { error: `GitHub dispatch failed: ${response.status}`, detail: detail.slice(0, 1000) },
      { status: response.status },
    );
  }

  return NextResponse.json({ ok: true, market, workflow, branch });
}
