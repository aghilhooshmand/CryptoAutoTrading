import type { ReactNode } from "react";

import type { SessionEconomics } from "../../services/simulationApi";
import { rateToPercentLabel } from "../../services/simulationApi";
import { InfoTooltip } from "../shared/InfoTooltip";

interface Props {
  economics: SessionEconomics | null;
  strategyFillCount?: number;
  tradeCount?: number;
}

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
          <Term>Cash</Term>
          <dd data-testid="econ-cash">{economics.cash} USDT</dd>
        </div>
        <div>
          <Term
            tipLabel="Liquidation equity"
            tipText="What your account would be worth if the open long were sold now, after fees and slippage."
            tipTestId="tip-liq-equity"
          >
            Liquidation equity
          </Term>
          <dd data-testid="econ-liq">{economics.liquidationEquity ?? "—"}</dd>
        </div>
        <div>
          <Term
            tipLabel="Net P&L (liquidation)"
            tipText="Profit or loss used for hard stops: liquidation equity minus starting capital."
            tipTestId="tip-net-pnl"
          >
            Net P&amp;L (liquidation)
          </Term>
          <dd data-testid="econ-net">{economics.netPnl ?? "—"}</dd>
        </div>
        <div>
          <Term
            tipLabel="Mark equity"
            tipText="Account value at the latest market price. For display only—stops use liquidation net instead."
            tipTestId="tip-mark-equity"
          >
            Mark equity
          </Term>
          <dd data-testid="econ-mark">{economics.markEquity ?? "—"}</dd>
        </div>
        <div>
          <Term
            tipLabel="Mark net P&L"
            tipText="Mark equity minus starting capital. Helpful context, not the hard-stop number."
            tipTestId="tip-mark-net"
          >
            Mark net P&amp;L
          </Term>
          <dd data-testid="econ-mark-net">{economics.markNetPnl ?? "—"}</dd>
        </div>
        <div>
          <Term
            tipLabel="Unrealized gross"
            tipText="Paper gain or loss on an open position before fees and slippage."
            tipTestId="tip-unrealized"
          >
            Unrealized gross
          </Term>
          <dd>{economics.unrealizedGross ?? "—"}</dd>
        </div>
        <div>
          <Term>Gross P&amp;L</Term>
          <dd>{economics.grossPnl}</dd>
        </div>
        <div>
          <Term>Fees</Term>
          <dd>{economics.fees}</dd>
        </div>
        <div>
          <Term
            tipLabel="Slippage cost"
            tipText="Extra simulated cost from fills that were slightly worse than the quote."
            tipTestId="tip-slippage-cost"
          >
            Slippage cost
          </Term>
          <dd>{economics.slippageCost}</dd>
        </div>
        <div>
          <Term>Profit target</Term>
          <dd>
            {rateToPercentLabel(economics.targetNetProfitRate)} /{" "}
            {economics.targetNetProfitAmount} USDT
          </dd>
        </div>
        <div>
          <Term>Max loss</Term>
          <dd>
            {rateToPercentLabel(economics.maxSessionLossRate)} /{" "}
            {economics.maxSessionLossAmount} USDT
          </dd>
        </div>
        {strategyFillCount != null || tradeCount != null ? (
          <div>
            <Term
              tipLabel="Trade counts"
              tipText='"Strategy" counts toward the max-trades limit. "Total" also includes a safety close when stopping.'
              tipTestId="tip-trade-counts"
            >
              Trade counts
            </Term>
            <dd>
              strategy {strategyFillCount ?? "—"} · total {tradeCount ?? "—"}
            </dd>
          </div>
        ) : null}
        <div>
          <Term
            tipLabel="Mark safe"
            tipText="Yes means the latest price quote is fresh enough to trust for decisions."
            tipTestId="tip-mark-safe"
          >
            Mark safe
          </Term>
          <dd>{economics.markSafe ? "yes" : "no"}</dd>
        </div>
      </dl>
    </section>
  );
}
