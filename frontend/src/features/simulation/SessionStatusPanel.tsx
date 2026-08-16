import type { ReactNode } from "react";

import type { SimulationSession } from "../../services/simulationApi";
import { rateToPercentLabel } from "../../services/simulationApi";
import { InfoTooltip } from "../shared/InfoTooltip";
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
  onResume?: () => void;
}

export function SessionStatusPanel({
  session,
  busy = false,
  onStop,
  onEmergencyStop,
  onResume,
}: Props) {
  if (!session) {
    return (
      <section className="simulation-status" data-testid="simulation-status" aria-labelledby="sim-status-title">
        <h2 id="sim-status-title">Session status</h2>
        <p className="note">No active simulation session.</p>
      </section>
    );
  }

  const runningOrStopping = session.state === "RUNNING" || session.state === "STOPPING";
  const recoveryBlocked = session.state === "RECOVERY_BLOCKED";
  const showStopActions = runningOrStopping || recoveryBlocked;

  return (
    <section className="simulation-status" data-testid="simulation-status" aria-labelledby="sim-status-title">
      <div className="sim-status-header">
        <h2 id="sim-status-title">Session status</h2>
        <SimulationBadge />
      </div>
      <dl className="sim-dl">
        <div>
          <Term
            tipLabel="Session state"
            tipText="RECOVERY_BLOCKED means restart recovery could not prove a safe ledger. It is not a normal STOPPED History completion. Resume re-checks reconciliation; or stop and start a new session."
            tipTestId="tip-session-state"
          >
            State
          </Term>
          <dd data-testid="sim-state">{session.state}</dd>
        </div>
        <div>
          <Term
            tipLabel="Decision log"
            tipText="Important only skips ordinary HOLD rows. Full audit records every closed candle. Cursor advances either way."
            tipTestId="tip-decision-log"
          >
            Decision log
          </Term>
          <dd data-testid="sim-decision-log-mode">
            {session.decisionLogMode === "important_only"
              ? "Important decisions only"
              : "Full audit"}
          </dd>
        </div>
        {session.state === "RUNNING" ||
        session.state === "RECOVERY_BLOCKED" ||
        session.lastProcessedCandleOpenTime != null ? (
          <div>
            <Term>Last processed candle</Term>
            <dd data-testid="sim-last-candle">
              {session.lastProcessedCandleOpenTime ?? "—"}
            </dd>
          </div>
        ) : null}
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
        {session.positionSide === "long" ? (
          <div>
            <Term
              tipLabel="Protective levels"
              tipText="Absolute TP/SL derived from entry fill and configured percents. Not editable while long. Fills use live mark, not these levels."
              tipTestId="tip-protective-levels"
            >
              Entry / TP / SL
            </Term>
            <dd data-testid="sim-protective-levels">
              entry {session.entryFillPrice ?? "—"}
              {"; "}
              TP {session.takeProfitPrice ?? "—"}
              {session.takeProfitPercent ? ` (${rateToPercentLabel(session.takeProfitPercent)})` : ""}
              {"; "}
              SL {session.stopLossPrice ?? "—"}
              {session.stopLossPercent ? ` (${rateToPercentLabel(session.stopLossPercent)})` : ""}
            </dd>
          </div>
        ) : null}
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
        {session.recoveryReason ? (
          <div>
            <Term
              tipLabel="Recovery"
              tipText="Stable code explaining why auto-resume was blocked after backend restart or a failed resume attempt."
              tipTestId="tip-recovery-reason"
            >
              Recovery reason
            </Term>
            <dd data-testid="sim-recovery-reason">{session.recoveryReason}</dd>
          </div>
        ) : null}
        {session.recoveryDetail ? (
          <div>
            <Term>Recovery detail</Term>
            <dd data-testid="sim-recovery-detail">{session.recoveryDetail}</dd>
          </div>
        ) : null}
        {session.skippedGap ? (
          <div>
            <Term
              tipLabel="Skipped gap"
              tipText="Closed candles during downtime were not traded. The watermark advanced past that range after safe reconciliation."
              tipTestId="tip-skipped-gap"
            >
              Skipped offline gap
            </Term>
            <dd data-testid="sim-skipped-gap">
              {session.skippedGap.fromOpenTime ?? "—"} → {session.skippedGap.toOpenTime} (
              {session.skippedGap.reason})
            </dd>
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
      {showStopActions ? (
        <div className="sim-actions">
          {recoveryBlocked ? (
            <button
              type="button"
              data-testid="sim-resume"
              disabled={busy}
              onClick={onResume}
            >
              Resume
            </button>
          ) : null}
          <button
            type="button"
            data-testid="sim-stop"
            disabled={busy || (session.state !== "RUNNING" && !recoveryBlocked)}
            onClick={onStop}
          >
            Stop
          </button>
          <button
            type="button"
            className="danger"
            data-testid="sim-emergency-stop"
            disabled={busy || (session.state !== "RUNNING" && !recoveryBlocked)}
            onClick={onEmergencyStop}
          >
            Emergency stop
          </button>
        </div>
      ) : null}
    </section>
  );
}
