import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { DecisionJournal } from "../features/simulation/DecisionJournal";
import { EconomicsPanel } from "../features/simulation/EconomicsPanel";
import { TradeJournal } from "../features/simulation/TradeJournal";
import type { SessionEconomics } from "../services/simulationApi";

const economics: SessionEconomics = {
  startEquity: "500",
  cash: "480",
  markEquity: "505",
  markNetPnl: "5",
  unrealizedGross: "8",
  liquidationEquity: "498",
  grossPnl: "10",
  fees: "1",
  slippageCost: "0.5",
  netPnl: "-2",
  targetNetProfitRate: "0.01",
  targetNetProfitAmount: "5",
  maxSessionLossRate: "0.007",
  maxSessionLossAmount: "3.5",
  markPrice: "65000",
  markSafe: true,
};

describe("simulation journals and economics", () => {
  it("distinguishes liquidation net from mark equity", () => {
    render(
      <EconomicsPanel economics={economics} strategyFillCount={2} tradeCount={2} />,
    );
    expect(screen.getByTestId("econ-net")).toHaveTextContent("-2");
    expect(screen.getByTestId("econ-mark")).toHaveTextContent("505");
    expect(screen.getByTestId("econ-mark-net")).toHaveTextContent("5");
    expect(screen.getByTestId("econ-liq")).toHaveTextContent("498");
  });

  it("renders decision and trade journal rows", () => {
    render(
      <>
        <DecisionJournal
          items={[
            {
              id: "d1",
              createdAt: "2026-08-09T12:00:00.000Z",
              candleOpenTime: 1,
              signal: "HOLD",
              outcome: "hold",
              reasonCode: "no_cross",
              reasonMessage: null,
              fastEma: "100",
              slowEma: "99",
            },
          ]}
        />
        <TradeJournal
          items={[
            {
              id: "t1",
              createdAt: "2026-08-09T12:01:00.000Z",
              symbol: "btc_usdt",
              side: "BUY",
              qty: "0.01",
              referencePrice: "65000",
              fillPrice: "65032.5",
              fee: "0.65",
              slippageCost: "0.32",
              notional: "650.325",
              cashDelta: "-651",
              isForcedClose: false,
              candleOpenTime: 1,
            },
          ]}
        />
      </>,
    );
    expect(screen.getByTestId("decision-journal")).toHaveTextContent("HOLD");
    expect(screen.getByTestId("trade-journal")).toHaveTextContent("BUY");
  });
});
