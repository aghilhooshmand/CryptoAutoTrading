import { useEffect, useState } from "react";
import {
  DEFAULT_SLIPPAGE_RATE,
  XT_SPOT_FEE_LABEL,
  XT_SPOT_FEE_RATE,
  rateToPercentPointsLabel,
  rateToUsdtAmount,
  usdtAmountToRate,
} from "../../services/tradingCosts";

interface CostRateFieldsProps {
  maxPositionSize: string;
  feeRate: string;
  slippageRate: string;
  disabled?: boolean;
  onFeeRateChange: (rate: string) => void;
  onSlippageRateChange: (rate: string) => void;
  feeTestId?: string;
  slippageTestId?: string;
}

/**
 * Dual rate / USDT editors for fee and slippage.
 * Engine still receives fraction rates; USDT is a conversion aid vs max position.
 */
export function CostRateFields({
  maxPositionSize,
  feeRate,
  slippageRate,
  disabled,
  onFeeRateChange,
  onSlippageRateChange,
  feeTestId,
  slippageTestId,
}: CostRateFieldsProps) {
  const [feeUsdt, setFeeUsdt] = useState(
    () => rateToUsdtAmount(feeRate, maxPositionSize) ?? "",
  );
  const [slipUsdt, setSlipUsdt] = useState(
    () => rateToUsdtAmount(slippageRate, maxPositionSize) ?? "",
  );

  // Keep USDT mirrors in sync when rate or max position changes from outside.
  useEffect(() => {
    const next = rateToUsdtAmount(feeRate, maxPositionSize);
    if (next != null) setFeeUsdt(next);
  }, [feeRate, maxPositionSize]);

  useEffect(() => {
    const next = rateToUsdtAmount(slippageRate, maxPositionSize);
    if (next != null) setSlipUsdt(next);
  }, [slippageRate, maxPositionSize]);

  return (
    <div className="cost-rate-fields">
      <p className="hint cost-rate-basis">
        USDT amounts convert against <strong>max position</strong> (per-trade
        notional). Fee default: {XT_SPOT_FEE_LABEL} (changeable for your VIP /
        XT token discount).
      </p>

      <div className="cost-rate-pair">
        <label>
          Fee rate
          <input
            data-testid={feeTestId}
            inputMode="decimal"
            value={feeRate}
            disabled={disabled}
            onChange={(e) => onFeeRateChange(e.target.value)}
            aria-describedby="cost-fee-hint"
          />
          <span id="cost-fee-hint" className="hint">
            {rateToPercentPointsLabel(feeRate)} of fill notional
          </span>
        </label>
        <label>
          Fee (USDT)
          <input
            data-testid={feeTestId ? `${feeTestId}-usdt` : undefined}
            inputMode="decimal"
            value={feeUsdt}
            disabled={disabled}
            onChange={(e) => {
              const v = e.target.value;
              setFeeUsdt(v);
              const rate = usdtAmountToRate(v, maxPositionSize);
              if (rate != null) onFeeRateChange(rate);
            }}
            placeholder="e.g. 2"
          />
          <span className="hint">≈ fee on a full max-position fill</span>
        </label>
      </div>

      <div className="cost-rate-pair">
        <label>
          Slippage rate
          <input
            data-testid={slippageTestId}
            inputMode="decimal"
            value={slippageRate}
            disabled={disabled}
            onChange={(e) => onSlippageRateChange(e.target.value)}
          />
          <span className="hint">
            {rateToPercentPointsLabel(slippageRate)} adverse fill model (not an
            XT schedule fee)
          </span>
        </label>
        <label>
          Slippage (USDT)
          <input
            data-testid={slippageTestId ? `${slippageTestId}-usdt` : undefined}
            inputMode="decimal"
            value={slipUsdt}
            disabled={disabled}
            onChange={(e) => {
              const v = e.target.value;
              setSlipUsdt(v);
              const rate = usdtAmountToRate(v, maxPositionSize);
              if (rate != null) onSlippageRateChange(rate);
            }}
            placeholder="e.g. 0.5"
          />
          <span className="hint">≈ cost on a full max-position fill</span>
        </label>
      </div>
    </div>
  );
}

export const COST_DEFAULTS = {
  feeRate: XT_SPOT_FEE_RATE,
  slippageRate: DEFAULT_SLIPPAGE_RATE,
} as const;
