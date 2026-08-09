import type { SimulationSession } from "../../services/simulationApi";
import { rateToPercentLabel } from "../../services/simulationApi";
import { SimulationBadge } from "./SimulationBadge";

interface Props {
  session: SimulationSession | null;
  busy?: boolean;
  onStop?: () => void;
  onEmergencyStop?: () => void;
}

export function SessionStatusPanel({
  session,
  busy = false,
  onStop,
  onEmergencyStop,
}: Props) {
  if (!session) {
    return (
      <section className="simulation-status" data-testid="simulation-status" aria-labelledby="sim-status-title">
        <h2 id="sim-status-title">Session status</h2>
        <p className="note">No active simulation session.</p>
      </section>
    );
  }

  const active = session.state === "RUNNING" || session.state === "STOPPING";

  return (
    <section className="simulation-status" data-testid="simulation-status" aria-labelledby="sim-status-title">
      <div className="sim-status-header">
        <h2 id="sim-status-title">Session status</h2>
        <SimulationBadge />
      </div>
      <dl className="sim-dl">
        <div>
          <dt>State</dt>
          <dd data-testid="sim-state">{session.state}</dd>
        </div>
        <div>
          <dt>Symbol</dt>
          <dd>{session.symbol}</dd>
        </div>
        <div>
          <dt>Timeframe</dt>
          <dd>{session.timeframe}</dd>
        </div>
        <div>
          <dt>Strategy</dt>
          <dd>{session.strategyId}</dd>
        </div>
        <div>
          <dt>Cash</dt>
          <dd>{session.cash} USDT</dd>
        </div>
        <div>
          <dt>Position</dt>
          <dd>
            {session.positionSide} / {session.positionQty}
          </dd>
        </div>
        <div>
          <dt>Fills</dt>
          <dd>
            strategy {session.strategyFillCount} / max {session.maxTrades}; total{" "}
            {session.tradeCount}
          </dd>
        </div>
        <div>
          <dt>Targets</dt>
          <dd>
            profit {rateToPercentLabel(session.targetNetProfitRate)} (
            {session.targetNetProfitAmount} USDT); loss{" "}
            {rateToPercentLabel(session.maxSessionLossRate)} (
            {session.maxSessionLossAmount} USDT)
          </dd>
        </div>
        {session.stopReason ? (
          <div>
            <dt>Stop reason</dt>
            <dd data-testid="sim-stop-reason">{session.stopReason}</dd>
          </div>
        ) : null}
        {session.positionFlattenStatus && session.positionFlattenStatus !== "n/a" ? (
          <div>
            <dt>Flatten</dt>
            <dd>{session.positionFlattenStatus}</dd>
          </div>
        ) : null}
      </dl>
      {active ? (
        <div className="sim-actions">
          <button
            type="button"
            data-testid="sim-stop"
            disabled={busy || session.state !== "RUNNING"}
            onClick={onStop}
          >
            Stop
          </button>
          <button
            type="button"
            className="danger"
            data-testid="sim-emergency-stop"
            disabled={busy || session.state !== "RUNNING"}
            onClick={onEmergencyStop}
          >
            Emergency stop
          </button>
        </div>
      ) : null}
    </section>
  );
}
