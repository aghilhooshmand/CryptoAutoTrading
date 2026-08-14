import { useEffect, useState } from "react";
import { Link } from "react-router-dom";

import { AllocationPanel } from "../features/portfolio/AllocationPanel";
import { PortfolioCapitalPanel } from "../features/portfolio/PortfolioCapitalPanel";
import {
  getPortfolio,
  type PortfolioApiError,
  type PortfolioSnapshot,
} from "../services/portfolioApi";
import type { SimulationSession } from "../services/simulationApi";
import { fetchActiveSession } from "../services/simulationApi";
import { SimulationBadge } from "../features/simulation/SimulationBadge";

export function PortfolioPage() {
  const [snapshot, setSnapshot] = useState<PortfolioSnapshot | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [session, setSession] = useState<SimulationSession | null>(null);

  useEffect(() => {
    let cancelled = false;
    void (async () => {
      try {
        const data = await getPortfolio();
        if (!cancelled) {
          setSnapshot(data);
          setLoadError(null);
        }
      } catch (err) {
        if (!cancelled) {
          const apiErr = err as PortfolioApiError;
          setLoadError(apiErr.message ?? "Failed to load portfolio");
        }
      }
      try {
        const active = await fetchActiveSession();
        if (!cancelled) setSession(active);
      } catch {
        if (!cancelled) setSession(null);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <section className="page" aria-labelledby="portfolio-title">
      <h1 id="portfolio-title">Portfolio</h1>
      <p>
        Local capital book for funding and allocation reservations (USDT). This is not
        real-money brokerage funding. Simulation sessions below are separate experiment
        ledgers.
      </p>

      {loadError ? (
        <p className="form-error" role="alert" data-testid="portfolio-load-error">
          {loadError}
        </p>
      ) : null}

      {snapshot ? (
        <>
          <PortfolioCapitalPanel snapshot={snapshot} onUpdated={setSnapshot} />
          <AllocationPanel snapshot={snapshot} onUpdated={setSnapshot} />
        </>
      ) : !loadError ? (
        <p className="note" data-testid="portfolio-loading">
          Loading portfolio…
        </p>
      ) : null}

      <div className="portfolio-sim-summary" data-testid="portfolio-sim-summary">
        <h2>Active simulation (separate)</h2>
        {session ? (
          <>
            <SimulationBadge />
            <p>
              Active session <strong>{session.state}</strong> on {session.symbol}: cash{" "}
              {session.cash} USDT; liquidation net {session.economics?.netPnl ?? "—"}.
            </p>
            <p>
              <Link to="/auto-trading">Open Auto Trading</Link> for journals and controls.
            </p>
          </>
        ) : (
          <p className="note" data-testid="portfolio-no-session">
            No active simulation session. Configure one under Auto Trading.
          </p>
        )}
      </div>
    </section>
  );
}
