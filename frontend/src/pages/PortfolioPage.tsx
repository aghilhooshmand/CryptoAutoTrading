import { useEffect, useState } from "react";
import { Link } from "react-router-dom";

import { AllocationPanel } from "../features/portfolio/AllocationPanel";
import { HoldingsPanel } from "../features/portfolio/HoldingsPanel";
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
      <div className="portfolio-title-row">
        <h1 id="portfolio-title">Simulation Portfolio</h1>
        <SimulationBadge />
      </div>

      {loadError ? (
        <p className="form-error" role="alert" data-testid="portfolio-load-error">
          {loadError}
        </p>
      ) : null}

      {snapshot ? (
        <>
          <PortfolioCapitalPanel snapshot={snapshot} onUpdated={setSnapshot} />
          <HoldingsPanel snapshot={snapshot} />
          <AllocationPanel snapshot={snapshot} onUpdated={setSnapshot} />
        </>
      ) : !loadError ? (
        <p className="note" data-testid="portfolio-loading">
          Loading portfolio…
        </p>
      ) : null}

      <div className="portfolio-sim-summary" data-testid="portfolio-sim-summary">
        <h2>Active simulation session</h2>
        {session ? (
          <>
            <p>
              Session <strong>{session.state}</strong> on {session.symbol}. Journals live on Auto
              Trading.
            </p>
            <p>
              <Link to="/auto-trading">Open Auto Trading</Link>
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
