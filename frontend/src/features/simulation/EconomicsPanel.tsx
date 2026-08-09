import type { SessionEconomics } from "../../services/simulationApi";
import { rateToPercentLabel } from "../../services/simulationApi";

interface Props {
  economics: SessionEconomics | null;
  strategyFillCount?: number;
  tradeCount?: number;
}

export function EconomicsPanel({
  economics,
  strategyFillCount,
  tradeCount,
}: Props) {
  if (!economics) {
    return (
      <section className="simulation-economics" data-testid="simulation-economics">
        <h2>Economics</h2>
        <p className="note">No session economics yet.</p>
      </section>
    );
  }

  return (
    <section
      className="simulation-economics"
      data-testid="simulation-economics"
      aria-labelledby="sim-econ-title"
    >
      <h2 id="sim-econ-title">Economics</h2>
      <p className="note">
        Liquidation NET drives hard stops. Mark equity is informational only.
      </p>
      <dl className="sim-dl">
        <div>
          <dt>Cash</dt>
          <dd data-testid="econ-cash">{economics.cash} USDT</dd>
        </div>
        <div>
          <dt>Liquidation equity</dt>
          <dd data-testid="econ-liq">{economics.liquidationEquity ?? "—"}</dd>
        </div>
        <div>
          <dt>Net P&amp;L (liquidation)</dt>
          <dd data-testid="econ-net">{economics.netPnl ?? "—"}</dd>
        </div>
        <div>
          <dt>Mark equity</dt>
          <dd data-testid="econ-mark">{economics.markEquity ?? "—"}</dd>
        </div>
        <div>
          <dt>Mark net P&amp;L</dt>
          <dd data-testid="econ-mark-net">{economics.markNetPnl ?? "—"}</dd>
        </div>
        <div>
          <dt>Unrealized gross</dt>
          <dd>{economics.unrealizedGross ?? "—"}</dd>
        </div>
        <div>
          <dt>Gross P&amp;L</dt>
          <dd>{economics.grossPnl}</dd>
        </div>
        <div>
          <dt>Fees</dt>
          <dd>{economics.fees}</dd>
        </div>
        <div>
          <dt>Slippage cost</dt>
          <dd>{economics.slippageCost}</dd>
        </div>
        <div>
          <dt>Profit target</dt>
          <dd>
            {rateToPercentLabel(economics.targetNetProfitRate)} /{" "}
            {economics.targetNetProfitAmount} USDT
          </dd>
        </div>
        <div>
          <dt>Max loss</dt>
          <dd>
            {rateToPercentLabel(economics.maxSessionLossRate)} /{" "}
            {economics.maxSessionLossAmount} USDT
          </dd>
        </div>
        {strategyFillCount != null || tradeCount != null ? (
          <div>
            <dt>Trade counts</dt>
            <dd>
              strategy {strategyFillCount ?? "—"} · total {tradeCount ?? "—"}
            </dd>
          </div>
        ) : null}
        <div>
          <dt>Mark safe</dt>
          <dd>{economics.markSafe ? "yes" : "no"}</dd>
        </div>
      </dl>
    </section>
  );
}
