import { useCallback, useEffect, useState } from "react";

import type {
  CreateSessionRequest,
  DecisionItem,
  SimulationSession,
  TradeItem,
} from "../../services/simulationApi";
import {
  createSession,
  emergencyStopSession,
  fetchActiveSession,
  fetchDecisions,
  fetchSession,
  fetchTrades,
  startSession,
  stopSession,
} from "../../services/simulationApi";

const POLL_MS = 3000;

export function useSimulationSession() {
  const [session, setSession] = useState<SimulationSession | null>(null);
  const [decisions, setDecisions] = useState<DecisionItem[]>([]);
  const [trades, setTrades] = useState<TradeItem[]>([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [trackedId, setTrackedId] = useState<string | null>(null);

  const loadJournals = useCallback(async (id: string) => {
    const [d, t] = await Promise.all([fetchDecisions(id), fetchTrades(id)]);
    setDecisions(d);
    setTrades(t);
  }, []);

  const poll = useCallback(async () => {
    try {
      const active = await fetchActiveSession();
      if (active) {
        const fresh = await fetchSession(active.id);
        setSession(fresh);
        setTrackedId(fresh.id);
        await loadJournals(fresh.id);
        return;
      }
      if (trackedId) {
        const fresh = await fetchSession(trackedId);
        setSession(fresh);
        await loadJournals(fresh.id);
      }
    } catch (err) {
      setError((err as Error).message);
    }
  }, [loadJournals, trackedId]);

  useEffect(() => {
    void poll();
    const id = window.setInterval(() => {
      void poll();
    }, POLL_MS);
    return () => window.clearInterval(id);
  }, [poll]);

  async function createAndStart(body: CreateSessionRequest): Promise<boolean> {
    setBusy(true);
    setError(null);
    try {
      const created = await createSession(body);
      const started = await startSession(created.id);
      setSession(started);
      setTrackedId(started.id);
      await loadJournals(started.id);
      return true;
    } catch (err) {
      setError((err as Error).message);
      return false;
    } finally {
      setBusy(false);
    }
  }

  async function stop() {
    if (!session) return;
    setBusy(true);
    setError(null);
    try {
      const stopped = await stopSession(session.id);
      setSession(stopped);
      await loadJournals(stopped.id);
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setBusy(false);
    }
  }

  async function emergencyStop() {
    if (!session) return;
    setBusy(true);
    setError(null);
    try {
      const stopped = await emergencyStopSession(session.id);
      setSession(stopped);
      await loadJournals(stopped.id);
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setBusy(false);
    }
  }

  const configDisabled =
    busy || session?.state === "RUNNING" || session?.state === "STOPPING";

  return {
    session,
    decisions,
    trades,
    busy,
    error,
    configDisabled,
    createAndStart,
    stop,
    emergencyStop,
  };
}
