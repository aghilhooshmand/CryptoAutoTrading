import { useState } from "react";
import { DecisionJournal } from "../features/simulation/DecisionJournal";
import { EconomicsPanel } from "../features/simulation/EconomicsPanel";
import { SessionConfigForm } from "../features/simulation/SessionConfigForm";
import { SessionStatusPanel } from "../features/simulation/SessionStatusPanel";
import { SimulationBadge } from "../features/simulation/SimulationBadge";
import { TradeJournal } from "../features/simulation/TradeJournal";
import { useSimulationSession } from "../features/simulation/useSimulationSession";
import { BacktestConfigForm } from "../features/backtest/BacktestConfigForm";
import { BacktestDecisions } from "../features/backtest/BacktestDecisions";
import { BacktestResultsPanel } from "../features/backtest/BacktestResultsPanel";
import { BacktestRunList } from "../features/backtest/BacktestRunList";
import { BacktestTrades } from "../features/backtest/BacktestTrades";
import { useBacktest } from "../features/backtest/useBacktest";

type AutoTradingTab = "simulation" | "backtest";

export function AutoTradingPage() {
  const [tab, setTab] = useState<AutoTradingTab>("simulation");

  const {
    session,
    decisions,
    trades,
    busy,
    error,
    configDisabled,
    createAndStart,
    stop,
    emergencyStop,
  } = useSimulationSession();

  const backtest = useBacktest();

  return (
    <section className="page auto-trading-page" aria-labelledby="auto-trading-title">
      <header className="sim-page-header">
        <h1 id="auto-trading-title">Auto Trading</h1>
        {tab === "simulation" ? <SimulationBadge /> : null}
      </header>

      <div
        className="auto-trading-tabs"
        role="tablist"
        aria-label="Auto Trading workflows"
      >
        <button
          type="button"
          role="tab"
          id="tab-simulation"
          aria-selected={tab === "simulation"}
          aria-controls="panel-simulation"
          className={tab === "simulation" ? "is-active" : undefined}
          onClick={() => setTab("simulation")}
        >
          Simulation
        </button>
        <button
          type="button"
          role="tab"
          id="tab-backtest"
          aria-selected={tab === "backtest"}
          aria-controls="panel-backtest"
          className={tab === "backtest" ? "is-active" : undefined}
          onClick={() => setTab("backtest")}
        >
          Backtest
        </button>
      </div>

      <div
        id="panel-simulation"
        role="tabpanel"
        aria-labelledby="tab-simulation"
        hidden={tab !== "simulation"}
        className="auto-trading-panel"
      >
        <h2 className="auto-trading-panel-title">Simulation</h2>
        <p className="auto-trading-lede">
          Configure and supervise one local simulation session. Market data comes
          from public XT quotes; no exchange trading credentials are used.
        </p>

        <SessionConfigForm
          disabled={configDisabled}
          onSubmit={(body) => {
            void createAndStart(body);
          }}
          error={error}
        />

        <SessionStatusPanel
          session={session}
          busy={busy}
          onStop={() => {
            void stop();
          }}
          onEmergencyStop={() => {
            void emergencyStop();
          }}
        />

        <EconomicsPanel
          economics={session?.economics ?? null}
          strategyFillCount={session?.strategyFillCount}
          tradeCount={session?.tradeCount}
        />

        <DecisionJournal items={decisions} />
        <TradeJournal items={trades} />
      </div>

      <div
        id="panel-backtest"
        role="tabpanel"
        aria-labelledby="tab-backtest"
        hidden={tab !== "backtest"}
        className="auto-trading-panel"
      >
        <h2 className="auto-trading-panel-title">Backtest</h2>
        <p className="auto-trading-lede">
          Test your strategy using historical market data.
          <br />
          No real orders are placed.
        </p>

        <BacktestConfigForm
          busy={backtest.busy}
          error={backtest.error}
          onSubmit={(body) => {
            void backtest.runBacktest(body);
          }}
        />

        <BacktestResultsPanel run={backtest.selected} />
        <BacktestRunList
          runs={backtest.runs}
          selectedId={backtest.selected?.id}
          onSelect={(id) => {
            void backtest.selectRun(id);
          }}
          onDelete={(id) => {
            void backtest.removeRun(id);
          }}
        />
        <BacktestTrades trades={backtest.trades} />
        <BacktestDecisions decisions={backtest.decisions} />
      </div>
    </section>
  );
}
