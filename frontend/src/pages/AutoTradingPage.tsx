import { DecisionJournal } from "../features/simulation/DecisionJournal";
import { EconomicsPanel } from "../features/simulation/EconomicsPanel";
import { SessionConfigForm } from "../features/simulation/SessionConfigForm";
import { SessionStatusPanel } from "../features/simulation/SessionStatusPanel";
import { SimulationBadge } from "../features/simulation/SimulationBadge";
import { TradeJournal } from "../features/simulation/TradeJournal";
import { useSimulationSession } from "../features/simulation/useSimulationSession";

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

  return (
    <section className="page auto-trading-page" aria-labelledby="auto-trading-title">
      <header className="sim-page-header">
        <h1 id="auto-trading-title">Auto Trading</h1>
        <SimulationBadge />
      </header>
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
  );
}
