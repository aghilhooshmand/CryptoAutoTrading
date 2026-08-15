import { useEffect, useState } from "react";
import {
  DEFAULT_SLIPPAGE_RATE,
  XT_SPOT_FEE_LABEL,
  XT_SPOT_FEE_RATE,
  percentPointsToRate,
  rateToPercentPoints,
  rateToPercentPointsLabel,
  rateToUsdtAmount,
  usdtAmountToRate,
} from "../../services/tradingCosts";

export type CostInputMode = "percent" | "usdt";

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
 * Fee / slippage editors with a Percent ↔ USDT toggle.
 * Engine always stores fraction rates; USDT converts against max position.
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
  const [mode, setMode] = useState<CostInputMode>("percent");
  const [feePercent, setFeePercent] = useState(
    () => rateToPercentPoints(feeRate) ?? "",
  );
  const [slipPercent, setSlipPercent] = useState(
    () => rateToPercentPoints(slippageRate) ?? "",
  );
  const [feeUsdt, setFeeUsdt] = useState(
    () => rateToUsdtAmount(feeRate, maxPositionSize) ?? "",
  );
  const [slipUsdt, setSlipUsdt] = useState(
    () => rateToUsdtAmount(slippageRate, maxPositionSize) ?? "",
  );

  useEffect(() => {
    const next = rateToPercentPoints(feeRate);
    if (next != null) setFeePercent(next);
  }, [feeRate]);

  useEffect(() => {
    const next = rateToPercentPoints(slippageRate);
    if (next != null) setSlipPercent(next);
  }, [slippageRate]);

  useEffect(() => {
    const next = rateToUsdtAmount(feeRate, maxPositionSize);
    if (next != null) setFeeUsdt(next);
  }, [feeRate, maxPositionSize]);

  useEffect(() => {
    const next = rateToUsdtAmount(slippageRate, maxPositionSize);
    if (next != null) setSlipUsdt(next);
  }, [slippageRate, maxPositionSize]);

  const feeUsdtHint = rateToUsdtAmount(feeRate, maxPositionSize);
  const slipUsdtHint = rateToUsdtAmount(slippageRate, maxPositionSize);

  return (
    <div className="cost-rate-fields">
      <div className="cost-rate-mode" role="group" aria-label="Fee and slippage input unit">
        <span className="cost-rate-mode__label">Enter as</span>
        <label className="cost-rate-mode__option">
          <input
            type="radio"
            name="cost-input-mode"
            value="percent"
            checked={mode === "percent"}
            disabled={disabled}
            data-testid="cost-mode-percent"
            onChange={() => setMode("percent")}
          />
          Percent (%)
        </label>
        <label className="cost-rate-mode__option">
          <input
            type="radio"
            name="cost-input-mode"
            value="usdt"
            checked={mode === "usdt"}
            disabled={disabled}
            data-testid="cost-mode-usdt"
            onChange={() => setMode("usdt")}
          />
          USDT amount
        </label>
      </div>

      <p className="field-hint cost-rate-basis">
        {mode === "usdt" ? (
          <>
            USDT converts against <strong>max position</strong> (per-trade
            notional). Equivalent % updates automatically.
          </>
        ) : (
          <>
            Enter percent points (e.g. <strong>0.20</strong> for 0.20%). Default
            fee: {XT_SPOT_FEE_LABEL}. Equivalent USDT uses max position.
          </>
        )}
      </p>

      <div className="cost-rate-pair">
        {mode === "percent" ? (
          <label>
            Fee (%)
            <input
              data-testid={feeTestId}
              inputMode="decimal"
              value={feePercent}
              disabled={disabled}
              placeholder="e.g. 0.20"
              onChange={(e) => {
                const v = e.target.value;
                setFeePercent(v);
                const rate = percentPointsToRate(v);
                if (rate != null) onFeeRateChange(rate);
              }}
              aria-describedby="cost-fee-hint"
            />
            <span id="cost-fee-hint" className="field-hint">
              {feeUsdtHint != null
                ? `≈ ${feeUsdtHint} USDT on a full max-position fill`
                : "Set max position to see USDT equivalent"}
            </span>
          </label>
        ) : (
          <label>
            Fee (USDT)
            <input
              data-testid={feeTestId ? `${feeTestId}-usdt` : "cost-fee-usdt"}
              inputMode="decimal"
              value={feeUsdt}
              disabled={disabled}
              placeholder="e.g. 2"
              onChange={(e) => {
                const v = e.target.value;
                setFeeUsdt(v);
                const rate = usdtAmountToRate(v, maxPositionSize);
                if (rate != null) onFeeRateChange(rate);
              }}
              aria-describedby="cost-fee-hint"
            />
            <span id="cost-fee-hint" className="field-hint">
              ≈ {rateToPercentPointsLabel(feeRate)} of fill notional
            </span>
          </label>
        )}

        {mode === "percent" ? (
          <label>
            Slippage (%)
            <input
              data-testid={slippageTestId}
              inputMode="decimal"
              value={slipPercent}
              disabled={disabled}
              placeholder="e.g. 0.05"
              onChange={(e) => {
                const v = e.target.value;
                setSlipPercent(v);
                const rate = percentPointsToRate(v);
                if (rate != null) onSlippageRateChange(rate);
              }}
            />
            <span className="field-hint">
              {slipUsdtHint != null
                ? `≈ ${slipUsdtHint} USDT adverse-fill model`
                : "Set max position to see USDT equivalent"}
            </span>
          </label>
        ) : (
          <label>
            Slippage (USDT)
            <input
              data-testid={
                slippageTestId ? `${slippageTestId}-usdt` : "cost-slippage-usdt"
              }
              inputMode="decimal"
              value={slipUsdt}
              disabled={disabled}
              placeholder="e.g. 0.5"
              onChange={(e) => {
                const v = e.target.value;
                setSlipUsdt(v);
                const rate = usdtAmountToRate(v, maxPositionSize);
                if (rate != null) onSlippageRateChange(rate);
              }}
            />
            <span className="field-hint">
              ≈ {rateToPercentPointsLabel(slippageRate)} adverse fill model (not
              an XT schedule fee)
            </span>
          </label>
        )}
      </div>
    </div>
  );
}

export const COST_DEFAULTS = {
  feeRate: XT_SPOT_FEE_RATE,
  slippageRate: DEFAULT_SLIPPAGE_RATE,
} as const;
