import { useMemo, useState, type FormEvent, type ReactNode } from "react";

import type { CandleInterval, CreateSessionRequest } from "../../services/simulationApi";
import {
  deriveAmount,
  rateToPercentLabel,
  validateCapitalNesting,
} from "../../services/simulationApi";
import { COST_DEFAULTS, CostRateFields } from "../shared/CostRateFields";
import { InfoTooltip } from "./InfoTooltip";

export interface SessionConfigValues {
  symbol: string;
  timeframe: CandleInterval;
  startingCapital: string;
  allocatedCapital: string;
  maxPositionSize: string;
  targetNetProfitRate: string;
  maxSessionLossRate: string;
  maxTrades: string;
  durationSeconds: string;
  feeRate: string;
  slippageRate: string;
}

interface Props {
  disabled?: boolean;
  defaultSymbol?: string;
  onSubmit: (body: CreateSessionRequest) => void;
  error?: string | null;
}

const DEFAULTS: SessionConfigValues = {
  symbol: "btc_usdt",
  timeframe: "1h",
  startingCapital: "500",
  allocatedCapital: "500",
  maxPositionSize: "500",
  targetNetProfitRate: "0.01",
  maxSessionLossRate: "0.007",
  maxTrades: "20",
  durationSeconds: "3600",
  feeRate: COST_DEFAULTS.feeRate,
  slippageRate: COST_DEFAULTS.slippageRate,
};

function FieldLabel({
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
    <span className="field-label-row">
      <span>{children}</span>
      {tipLabel && tipText ? (
        <InfoTooltip label={tipLabel} text={tipText} testId={tipTestId} />
      ) : null}
    </span>
  );
}

export function SessionConfigForm({
  disabled = false,
  defaultSymbol = "btc_usdt",
  onSubmit,
  error,
}: Props) {
  const [values, setValues] = useState<SessionConfigValues>({
    ...DEFAULTS,
    symbol: defaultSymbol,
  });
  const [localError, setLocalError] = useState<string | null>(null);

  const profitAmount = useMemo(
    () => deriveAmount(values.allocatedCapital, values.targetNetProfitRate),
    [values.allocatedCapital, values.targetNetProfitRate],
  );
  const lossAmount = useMemo(
    () => deriveAmount(values.allocatedCapital, values.maxSessionLossRate),
    [values.allocatedCapital, values.maxSessionLossRate],
  );

  function setField<K extends keyof SessionConfigValues>(key: K, value: string) {
    setValues((prev) => ({ ...prev, [key]: value }));
  }

  function handleSubmit(event: FormEvent) {
    event.preventDefault();
    const nest = validateCapitalNesting(
      values.startingCapital,
      values.allocatedCapital,
      values.maxPositionSize,
    );
    if (nest) {
      setLocalError(nest);
      return;
    }
    const maxTrades = Number(values.maxTrades);
    const duration = Number(values.durationSeconds);
    if (!Number.isInteger(maxTrades) || maxTrades < 1) {
      setLocalError("Max trades must be an integer ≥ 1.");
      return;
    }
    if (!Number.isInteger(duration) || duration < 1) {
      setLocalError("Duration must be an integer ≥ 1 second.");
      return;
    }
    setLocalError(null);
    onSubmit({
      symbol: values.symbol.trim(),
      timeframe: values.timeframe,
      startingCapital: values.startingCapital,
      allocatedCapital: values.allocatedCapital,
      maxPositionSize: values.maxPositionSize,
      targetNetProfitRate: values.targetNetProfitRate,
      maxSessionLossRate: values.maxSessionLossRate,
      maxTrades,
      durationSeconds: duration,
      feeRate: values.feeRate || undefined,
      slippageRate: values.slippageRate || undefined,
    });
  }

  const displayError = localError ?? error;

  return (
    <form
      className="simulation-config"
      onSubmit={handleSubmit}
      data-testid="simulation-config-form"
      aria-labelledby="simulation-config-title"
    >
      <h2 id="simulation-config-title">Configure session</h2>
      <p className="note">
        Simulation only — real-money trading is unavailable. Profit and loss are
        rates of allocated capital; amounts update live.
      </p>

      <div className="sim-grid">
        <label>
          <FieldLabel>Symbol</FieldLabel>
          <input
            data-testid="sim-symbol"
            value={values.symbol}
            disabled={disabled}
            onChange={(e) => setField("symbol", e.target.value)}
            required
          />
        </label>
        <label>
          <FieldLabel
            tipLabel="Timeframe"
            tipText="Chart candle size. The strategy only decides after each candle finishes—not tick by tick."
            tipTestId="tip-timeframe"
          >
            Timeframe
          </FieldLabel>
          <select
            data-testid="sim-timeframe"
            value={values.timeframe}
            disabled={disabled}
            onChange={(e) => setField("timeframe", e.target.value as CandleInterval)}
          >
            <option value="1m">1m</option>
            <option value="5m">5m</option>
            <option value="15m">15m</option>
            <option value="1h">1h</option>
            <option value="4h">4h</option>
            <option value="1d">1d</option>
          </select>
        </label>
        <label>
          <FieldLabel>Starting capital (USDT)</FieldLabel>
          <input
            data-testid="sim-starting"
            inputMode="decimal"
            value={values.startingCapital}
            disabled={disabled}
            onChange={(e) => setField("startingCapital", e.target.value)}
            required
          />
        </label>
        <label>
          <FieldLabel
            tipLabel="Allocated capital"
            tipText="How much of starting capital this session is allowed to use. Cannot be higher than starting capital."
            tipTestId="tip-allocated"
          >
            Allocated capital (USDT)
          </FieldLabel>
          <input
            data-testid="sim-allocated"
            inputMode="decimal"
            value={values.allocatedCapital}
            disabled={disabled}
            onChange={(e) => setField("allocatedCapital", e.target.value)}
            required
          />
        </label>
        <label>
          <FieldLabel
            tipLabel="Max position size"
            tipText="Largest single long trade size allowed. Cannot be higher than allocated capital."
            tipTestId="tip-max-position"
          >
            Max position size (USDT)
          </FieldLabel>
          <input
            data-testid="sim-max-position"
            inputMode="decimal"
            value={values.maxPositionSize}
            disabled={disabled}
            onChange={(e) => setField("maxPositionSize", e.target.value)}
            required
          />
        </label>
        <label>
          <FieldLabel
            tipLabel="Target net profit rate"
            tipText="Profit goal as a decimal of allocated capital (0.01 means 1%). Session stops when net profit hits the USDT amount shown."
            tipTestId="tip-profit-rate"
          >
            Target net profit rate
          </FieldLabel>
          <input
            data-testid="sim-profit-rate"
            inputMode="decimal"
            value={values.targetNetProfitRate}
            disabled={disabled}
            onChange={(e) => setField("targetNetProfitRate", e.target.value)}
            required
          />
          <span className="field-hint" data-testid="sim-profit-derived">
            {rateToPercentLabel(values.targetNetProfitRate)} ≈ {profitAmount ?? "—"} USDT
          </span>
        </label>
        <label>
          <FieldLabel
            tipLabel="Max session loss rate"
            tipText="Loss limit as a decimal of allocated capital (0.007 means 0.7%). Session stops if net loss reaches the USDT amount shown."
            tipTestId="tip-loss-rate"
          >
            Max session loss rate
          </FieldLabel>
          <input
            data-testid="sim-loss-rate"
            inputMode="decimal"
            value={values.maxSessionLossRate}
            disabled={disabled}
            onChange={(e) => setField("maxSessionLossRate", e.target.value)}
            required
          />
          <span className="field-hint" data-testid="sim-loss-derived">
            {rateToPercentLabel(values.maxSessionLossRate)} ≈ {lossAmount ?? "—"} USDT
          </span>
        </label>
        <label>
          <FieldLabel
            tipLabel="Max trades"
            tipText="How many strategy buys/sells are allowed. A safety close when stopping may add one extra trade."
            tipTestId="tip-max-trades"
          >
            Max trades (strategy fills)
          </FieldLabel>
          <input
            data-testid="sim-max-trades"
            inputMode="numeric"
            value={values.maxTrades}
            disabled={disabled}
            onChange={(e) => setField("maxTrades", e.target.value)}
            required
          />
        </label>
        <label>
          <FieldLabel>Duration (seconds)</FieldLabel>
          <input
            data-testid="sim-duration"
            inputMode="numeric"
            value={values.durationSeconds}
            disabled={disabled}
            onChange={(e) => setField("durationSeconds", e.target.value)}
            required
          />
        </label>
        <div className="sim-cost-fields">
          <CostRateFields
            maxPositionSize={values.maxPositionSize}
            feeRate={values.feeRate}
            slippageRate={values.slippageRate}
            disabled={disabled}
            onFeeRateChange={(rate) => setField("feeRate", rate)}
            onSlippageRateChange={(rate) => setField("slippageRate", rate)}
            feeTestId="sim-fee"
            slippageTestId="sim-slippage"
          />
        </div>
      </div>

      {displayError ? (
        <p className="form-error" role="alert" data-testid="sim-config-error">
          {displayError}
        </p>
      ) : null}

      <div className="sim-actions">
        <button type="submit" disabled={disabled} data-testid="sim-create-start">
          Create &amp; start
        </button>
        <button type="button" disabled aria-disabled="true" data-testid="sim-real-money-disabled">
          Real money (unavailable)
        </button>
      </div>
    </form>
  );
}
