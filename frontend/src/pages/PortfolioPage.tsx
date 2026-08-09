import { useEffect, useState } from "react";
import { Link } from "react-router-dom";

import type { SimulationSession } from "../services/simulationApi";
import { fetchActiveSession } from "../services/simulationApi";
import { SimulationBadge } from "../features/simulation/SimulationBadge";

export function PortfolioPage() {
  const [session, setSession] = useState<SimulationSession | null>(null);

  useEffect(() => {
    let cancelled = false;
    void (async () => {
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
        Thin summary of the active Auto Trading simulation only — not a full
        portfolio product.
      </p>
      {session ? (
        <div className="portfolio-sim-summary" data-testid="portfolio-sim-summary">
          <SimulationBadge />
          <p>
            Active session <strong>{session.state}</strong> on {session.symbol}: cash{" "}
            {session.cash} USDT; liquidation net{" "}
            {session.economics?.netPnl ?? "—"}.
          </p>
          <p>
            <Link to="/auto-trading">Open Auto Trading</Link> for journals and
            controls.
          </p>
        </div>
      ) : (
        <p className="note" data-testid="portfolio-no-session">
          No active simulation session. Configure one under Auto Trading.
        </p>
      )}
    </section>
  );
}
