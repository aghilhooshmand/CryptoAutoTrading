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
import { ComparisonConfigForm } from "../features/comparison/ComparisonConfigForm";
import { ComparisonList } from "../features/comparison/ComparisonList";
import { ComparisonResultsTable } from "../features/comparison/ComparisonResultsTable";
import { useComparison } from "../features/comparison/useComparison";
import { SettingsPanel } from "../features/settings/SettingsPanel";

type AutoTradingTab = "simulation" | "backtest" | "comparison" | "settings";

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
  const comparison = useComparison();

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
        <button
          type="button"
          role="tab"
          id="tab-comparison"
          aria-selected={tab === "comparison"}
          aria-controls="panel-comparison"
          className={tab === "comparison" ? "is-active" : undefined}
          onClick={() => setTab("comparison")}
        >
          Comparison
        </button>
        <button
          type="button"
          role="tab"
          id="tab-settings"
          aria-selected={tab === "settings"}
          aria-controls="panel-settings"
          className={tab === "settings" ? "is-active" : undefined}
          onClick={() => setTab("settings")}
        >
          Settings
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
          includeComparisonOrigin={backtest.includeComparisonOrigin}
          onIncludeComparisonOriginChange={backtest.setIncludeComparisonOrigin}
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

      <div
        id="panel-comparison"
        role="tabpanel"
        aria-labelledby="tab-comparison"
        hidden={tab !== "comparison"}
        className="auto-trading-panel"
      >
        <h2 className="auto-trading-panel-title">Strategy Comparison</h2>
        <p className="auto-trading-lede">
          Compare 2–5 strategies on one shared historical window. No real orders
          are placed. Results do not designate a winner automatically.
        </p>

        <ComparisonConfigForm
          busy={comparison.busy}
          error={comparison.error}
          onSubmit={(body) => {
            void comparison.runComparison(body);
          }}
        />

        <ComparisonResultsTable
          comparison={comparison.selected}
          onInspectLeg={(runId) => {
            setTab("backtest");
            void backtest.selectRun(runId);
          }}
        />
        <ComparisonList
          comparisons={comparison.comparisons}
          selectedId={comparison.selected?.id}
          onSelect={(id) => {
            void comparison.selectComparison(id);
          }}
          onDelete={(id) => {
            void comparison.removeComparison(id);
          }}
        />
      </div>

      <div
        id="panel-settings"
        role="tabpanel"
        aria-labelledby="tab-settings"
        hidden={tab !== "settings"}
        className="auto-trading-panel"
      >
        <h2 className="auto-trading-panel-title">Settings</h2>
        <SettingsPanel />
      </div>
    </section>
  );
}
