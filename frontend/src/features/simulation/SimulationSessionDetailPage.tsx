import { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";

import type {
  DecisionItem,
  SimulationSession,
  TradeItem,
} from "../../services/simulationApi";
import {
  deleteSession,
  fetchDecisions,
  fetchSession,
  fetchTrades,
  rateToPercentLabel,
  startSession,
} from "../../services/simulationApi";
import { DecisionJournal } from "./DecisionJournal";
import { SimulationBadge } from "./SimulationBadge";
import { TradeJournal } from "./TradeJournal";

export function SimulationSessionDetailPage() {
  const { sessionId = "" } = useParams();
  const navigate = useNavigate();
  const [session, setSession] = useState<SimulationSession | null>(null);
  const [decisions, setDecisions] = useState<DecisionItem[]>([]);
  const [trades, setTrades] = useState<TradeItem[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      if (!sessionId) return;
      setBusy(true);
      setError(null);
      try {
        const [s, d, t] = await Promise.all([
          fetchSession(sessionId),
          fetchDecisions(sessionId),
          fetchTrades(sessionId),
        ]);
        if (cancelled) return;
        setSession(s);
        setDecisions(d);
        setTrades(t);
      } catch (err) {
        if (!cancelled) setError((err as Error).message);
      } finally {
        if (!cancelled) setBusy(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [sessionId]);

  async function handleStart() {
    if (!session) return;
    setBusy(true);
    setError(null);
    try {
      const started = await startSession(session.id);
      setSession(started);
      navigate("/auto-trading");
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setBusy(false);
    }
  }

  async function handleDelete() {
    if (!session) return;
    const ok = window.confirm(
      "Delete this Simulation session and its journals? This cannot be undone. Portfolio capital is never released by this action.",
    );
    if (!ok) return;
    setBusy(true);
    setError(null);
    try {
      await deleteSession(session.id);
      navigate("/auto-trading");
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setBusy(false);
    }
  }

  if (!session && !error) {
    return <p className="auto-trading-lede">Loading session…</p>;
  }

  if (!session) {
    return (
      <section className="page" data-testid="simulation-detail">
        <p className="form-error" role="alert">
          {error ?? "Session not found"}
        </p>
        <Link to="/auto-trading">Back to Auto Trading</Link>
      </section>
    );
  }

  const fr = session.finalResult;
  const stopped = session.state === "STOPPED";
  const configured = session.state === "CONFIGURED";
  const canDelete = stopped || configured;

  return (
    <section className="page simulation-detail-page" data-testid="simulation-detail">
      <header className="sim-page-header">
        <div>
          <p className="note">
            <Link to="/auto-trading">← Auto Trading</Link>
          </p>
          <h1>Simulation session</h1>
        </div>
        <SimulationBadge />
      </header>

      {error ? (
        <p className="form-error" role="alert" data-testid="sim-detail-error">
          {error}
        </p>
      ) : null}

      <section className="simulation-status" aria-labelledby="sim-detail-config-title">
        <h2 id="sim-detail-config-title">Configuration</h2>
        <dl className="sim-dl">
          <div>
            <dt>State</dt>
            <dd data-testid="sim-detail-state">{session.state}</dd>
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
            <dd data-testid="sim-detail-strategy">{session.strategyId}</dd>
          </div>
          <div>
            <dt>Decision log</dt>
            <dd data-testid="sim-detail-decision-log-mode">
              {session.decisionLogMode === "important_only"
                ? "Important decisions only"
                : "Full audit"}
            </dd>
          </div>
          <div>
            <dt>Starting / allocated</dt>
            <dd>
              {session.startingCapital} / {session.allocatedCapital} USDT
            </dd>
          </div>
          <div>
            <dt>Fee / slippage</dt>
            <dd>
              {session.feeRate} / {session.slippageRate}
            </dd>
          </div>
          <div>
            <dt>Started</dt>
            <dd>{session.startedAt ?? "—"}</dd>
          </div>
          <div>
            <dt>Stopped</dt>
            <dd>{session.stoppedAt ?? "—"}</dd>
          </div>
          <div>
            <dt>Stop reason</dt>
            <dd data-testid="sim-detail-stop-reason">{session.stopReason ?? "—"}</dd>
          </div>
        </dl>
      </section>

      {stopped && fr ? (
        <section
          className="simulation-final-result"
          data-testid="sim-final-result"
          aria-labelledby="sim-final-title"
        >
          <h2 id="sim-final-title">Final results</h2>
          <p data-testid="sim-final-complete">
            {fr.complete ? "Complete valuation" : "Incomplete valuation — some metrics unavailable"}
          </p>
          <dl className="sim-dl">
            <div>
              <dt>Ending equity</dt>
              <dd>{fr.endingEquity ?? "—"}</dd>
            </div>
            <div>
              <dt>Net P&amp;L</dt>
              <dd data-testid="sim-final-net">{fr.netPnl ?? "—"}</dd>
            </div>
            <div>
              <dt>Return</dt>
              <dd>
                {fr.returnPct != null ? rateToPercentLabel(fr.returnPct) : "—"}
              </dd>
            </div>
            <div>
              <dt>Fees / slippage</dt>
              <dd>
                {fr.fees} / {fr.slippageCost}
              </dd>
            </div>
            <div>
              <dt>Frozen at</dt>
              <dd>{fr.frozenAt}</dd>
            </div>
            <div>
              <dt>Source</dt>
              <dd>{fr.source}</dd>
            </div>
          </dl>
        </section>
      ) : null}

      <div className="sim-actions">
        {configured ? (
          <button
            type="button"
            data-testid="sim-detail-start"
            disabled={busy}
            onClick={() => {
              void handleStart();
            }}
          >
            Start
          </button>
        ) : null}
        {canDelete ? (
          <button
            type="button"
            className="danger"
            data-testid="sim-detail-delete"
            disabled={busy}
            onClick={() => {
              void handleDelete();
            }}
          >
            Delete
          </button>
        ) : null}
        {stopped ? (
          <p className="note" data-testid="sim-detail-no-restart">
            STOPPED sessions are inspect and delete only — no restart or resume.
          </p>
        ) : null}
      </div>

      <DecisionJournal items={decisions} decisionLogMode={session.decisionLogMode} />
      <TradeJournal items={trades} />
    </section>
  );
}
