import type { ReactNode } from "react";

import type { SimulationSession } from "../../services/simulationApi";
import { rateToPercentLabel } from "../../services/simulationApi";
import { InfoTooltip } from "./InfoTooltip";
import { SimulationBadge } from "./SimulationBadge";

function Term({
  children,
  tipLabel,
  tipText,
  tipTestId,
}: {
  children: ReactNode;
  tipLabel?: string;
  tipText?: string;
  tipTestId?: string;
}) {
  return (
    <dt>
      <span className="field-label-row">
        <span>{children}</span>
        {tipLabel && tipText ? (
          <InfoTooltip label={tipLabel} text={tipText} testId={tipTestId} />
        ) : null}
      </span>
    </dt>
  );
}

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
          <Term>State</Term>
          <dd data-testid="sim-state">{session.state}</dd>
        </div>
        <div>
          <Term>Symbol</Term>
          <dd>{session.symbol}</dd>
        </div>
        <div>
          <Term>Timeframe</Term>
          <dd>{session.timeframe}</dd>
        </div>
        <div>
          <Term
            tipLabel="Strategy"
            tipText="Registered strategy used for this session (id and effective parameters)."
            tipTestId="tip-strategy"
          >
            Strategy
          </Term>
          <dd data-testid="session-strategy">
            {session.strategyId}
            {session.strategyParams
              ? ` · ${Object.entries(session.strategyParams)
                  .map(([k, v]) => `${k}=${v}`)
                  .join(", ")}`
              : null}
          </dd>
        </div>
        <div>
          <Term>Cash</Term>
          <dd>{session.cash} USDT</dd>
        </div>
        <div>
          <Term
            tipLabel="Position"
            tipText="This simulation only holds cash or one full long. A sell always closes the whole position."
            tipTestId="tip-position"
          >
            Position
          </Term>
          <dd>
            {session.positionSide} / {session.positionQty}
          </dd>
        </div>
        <div>
          <Term
            tipLabel="Fills"
            tipText="Strategy fills count toward max trades. Total can include one extra safety close when stopping."
            tipTestId="tip-fills"
          >
            Fills
          </Term>
          <dd>
            strategy {session.strategyFillCount} / max {session.maxTrades}; total{" "}
            {session.tradeCount}
          </dd>
        </div>
        <div>
          <Term>Targets</Term>
          <dd>
            profit {rateToPercentLabel(session.targetNetProfitRate)} (
            {session.targetNetProfitAmount} USDT); loss{" "}
            {rateToPercentLabel(session.maxSessionLossRate)} (
            {session.maxSessionLossAmount} USDT)
          </dd>
        </div>
        {session.stopReason ? (
          <div>
            <Term>Stop reason</Term>
            <dd data-testid="sim-stop-reason">{session.stopReason}</dd>
          </div>
        ) : null}
        {session.positionFlattenStatus && session.positionFlattenStatus !== "n/a" ? (
          <div>
            <Term
              tipLabel="Flatten"
              tipText='Shows if an open long was closed safely when the session stopped. "unsafe_unflattened" means no trustworthy exit price was available.'
              tipTestId="tip-flatten"
            >
              Flatten
            </Term>
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
