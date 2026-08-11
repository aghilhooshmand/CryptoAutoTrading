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

export function AutoTradingPage() {
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
        <SimulationBadge />
      </header>

      <section className="simulation-section" aria-labelledby="simulation-heading">
        <h2 id="simulation-heading">Live simulation</h2>
        <p>
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
      </section>

      <section className="backtest-section" aria-labelledby="backtest-heading">
        <h2 id="backtest-heading">Historical backtest</h2>
        <p>
          Offline Dual EMA evaluation on historical candles. Does not place real
          orders and does not change a live simulation session.
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
      </section>
    </section>
  );
}
