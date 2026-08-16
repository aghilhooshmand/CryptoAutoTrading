import { useEffect, useMemo, useState, type FormEvent, type ReactNode } from "react";

import type { CandleInterval, CreateSessionRequest } from "../../services/simulationApi";
import {
  deriveAmount,
  rateToPercentLabel,
  validateCapitalNesting,
} from "../../services/simulationApi";
import { getPortfolio, type PortfolioAllocation } from "../../services/portfolioApi";
import { getSettings } from "../../services/settingsApi";
import { settingsToSharedSeed } from "../settings/mapSettingsToForm";
import { COST_DEFAULTS, CostRateFields } from "../shared/CostRateFields";
import {
  StrategyConfigFields,
  defaultStrategyConfig,
  type StrategyConfigValue,
} from "../strategy/StrategyConfigFields";
import { InfoTooltip } from "../shared/InfoTooltip";

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
  allocationId: string;
  portfolioMaxLossRate: string;
  portfolioMaxLossAmount: string;
  perSymbolMaxWeight: string;
  decisionLogMode: "important_only" | "full_audit";
  takeProfitPercent: string;
  stopLossPercent: string;
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
  startingCapital: "1000",
  allocatedCapital: "1000",
  maxPositionSize: "1000",
  targetNetProfitRate: "",
  maxSessionLossRate: "",
  maxTrades: "",
  durationSeconds: "3600",
  feeRate: COST_DEFAULTS.feeRate,
  slippageRate: COST_DEFAULTS.slippageRate,
  allocationId: "",
  portfolioMaxLossRate: "",
  portfolioMaxLossAmount: "",
  perSymbolMaxWeight: "",
  decisionLogMode: "important_only",
  takeProfitPercent: "",
  stopLossPercent: "",
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
  const [strategy, setStrategy] = useState<StrategyConfigValue>(defaultStrategyConfig());
  const [preferredStrategy, setPreferredStrategy] = useState<StrategyConfigValue | null>(null);
  const [strategyError, setStrategyError] = useState<string | null>(null);
  const [localError, setLocalError] = useState<string | null>(null);
  const [seeded, setSeeded] = useState(false);
  const [portfolioAvailable, setPortfolioAvailable] = useState<string | null>(null);
  const [allocations, setAllocations] = useState<PortfolioAllocation[]>([]);

  // Fresh open only: seed once on mount. Parent keeps form mounted across tabs.
  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const [settings, portfolio] = await Promise.all([getSettings(), getPortfolio()]);
        if (cancelled || seeded) return;
        const seed = settingsToSharedSeed(settings);
        setValues((prev) => ({
          ...prev,
          symbol: seed.symbol,
          timeframe: seed.timeframe as CandleInterval,
          startingCapital: seed.startingCapital,
          allocatedCapital: seed.allocatedCapital,
          maxPositionSize: seed.maxPositionSize,
          targetNetProfitRate: seed.targetNetProfitRate,
          maxSessionLossRate: seed.maxSessionLossRate,
          maxTrades: seed.maxTrades,
          feeRate: seed.feeRate,
          slippageRate: seed.slippageRate,
          allocationId: seed.preferredAllocationId,
          portfolioMaxLossRate: seed.portfolioMaxLossRate,
          portfolioMaxLossAmount: seed.portfolioMaxLossAmount,
          perSymbolMaxWeight: seed.perSymbolMaxWeight,
          decisionLogMode: seed.decisionLogMode,
          takeProfitPercent: seed.takeProfitPercent,
          stopLossPercent: seed.stopLossPercent,
        }));
        setStrategy(seed.strategy);
        setPreferredStrategy(seed.strategy);
        setPortfolioAvailable(portfolio.available);
        setAllocations(portfolio.allocations ?? []);
        setSeeded(true);
      } catch {
        if (!cancelled) setSeeded(true);
      }
    })();
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps -- seed once on fresh mount
  }, []);

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
    if (portfolioAvailable != null) {
      const allocated = Number(values.allocatedCapital);
      const available = Number(portfolioAvailable);
      if (Number.isFinite(allocated) && Number.isFinite(available) && allocated > available) {
        setLocalError(
          `Allocated capital (${values.allocatedCapital}) exceeds Portfolio available USDT (${portfolioAvailable}).`,
        );
        return;
      }
    }
    if (!values.targetNetProfitRate.trim() || !values.maxSessionLossRate.trim()) {
      setLocalError("Target net profit rate and max session loss rate are required for Simulation.");
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
    if (values.perSymbolMaxWeight.trim()) {
      const w = Number(values.perSymbolMaxWeight);
      if (!(w > 0 && w <= 1)) {
        setLocalError("Per-symbol max weight must be > 0 and ≤ 1 when set.");
        return;
      }
    }
    if (strategyError) {
      setLocalError(strategyError);
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
      strategyId: strategy.strategyId,
      strategyParams: strategy.strategyParams,
      allocationId: values.allocationId.trim() || null,
      portfolioMaxLossRate: values.portfolioMaxLossRate.trim() || null,
      portfolioMaxLossAmount: values.portfolioMaxLossAmount.trim() || null,
      perSymbolMaxWeight: values.perSymbolMaxWeight.trim() || null,
      decisionLogMode: values.decisionLogMode,
      takeProfitPercent: values.takeProfitPercent.trim() || null,
      stopLossPercent: values.stopLossPercent.trim() || null,
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
        rates of allocated capital; amounts update live. Allocated capital cannot
        exceed Portfolio available USDT
        {portfolioAvailable != null ? ` (currently ${portfolioAvailable})` : ""}.
      </p>

      <StrategyConfigFields
        disabled={disabled}
        value={strategy}
        onChange={setStrategy}
        onValidationError={setStrategyError}
        preferredStrategy={preferredStrategy}
        variant="simulation"
      />

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
            tipText="How much of starting capital this session is allowed to use. Cannot be higher than starting capital or Portfolio available USDT."
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
          {portfolioAvailable != null ? (
            <span className="field-hint" data-testid="sim-portfolio-available">
              Portfolio available: {portfolioAvailable} USDT
            </span>
          ) : null}
        </label>
        <label>
          <FieldLabel
            tipLabel="Bind allocation"
            tipText="Optional. When bound, BUYs are limited by this allocation’s reserved size minus what this session has already deployed."
            tipTestId="tip-allocation"
          >
            Bind allocation (optional)
          </FieldLabel>
          <select
            data-testid="sim-allocation"
            value={values.allocationId}
            disabled={disabled}
            onChange={(e) => setField("allocationId", e.target.value)}
          >
            <option value="">None</option>
            {allocations.map((a) => (
              <option key={a.id} value={a.id}>
                {a.label} ({a.reservedSize} USDT)
              </option>
            ))}
          </select>
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
            tipLabel="Take-profit %"
            tipText="Optional. Fraction of entry fill (0.02 = +2%). Absolute level is set when a long opens. Fill uses live mark, not the TP price."
            tipTestId="tip-take-profit"
          >
            Take-profit % (optional)
          </FieldLabel>
          <input
            data-testid="sim-take-profit-percent"
            inputMode="decimal"
            value={values.takeProfitPercent}
            disabled={disabled}
            placeholder="e.g. 0.02"
            onChange={(e) => setField("takeProfitPercent", e.target.value)}
          />
        </label>
        <label>
          <FieldLabel
            tipLabel="Stop-loss %"
            tipText="Optional. Fraction of entry fill (0.01 = −1%). Absolute level is set when a long opens. Fill uses live mark, not the SL price."
            tipTestId="tip-stop-loss"
          >
            Stop-loss % (optional)
          </FieldLabel>
          <input
            data-testid="sim-stop-loss-percent"
            inputMode="decimal"
            value={values.stopLossPercent}
            disabled={disabled}
            placeholder="e.g. 0.01"
            onChange={(e) => setField("stopLossPercent", e.target.value)}
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
            tipLabel="Portfolio max-loss rate"
            tipText="Optional. Stops the session when Portfolio loss from the start baseline reaches this fraction of the baseline metric."
            tipTestId="tip-portfolio-loss-rate"
          >
            Portfolio max-loss rate (optional)
          </FieldLabel>
          <input
            data-testid="sim-portfolio-loss-rate"
            inputMode="decimal"
            value={values.portfolioMaxLossRate}
            disabled={disabled}
            placeholder="unset"
            onChange={(e) => setField("portfolioMaxLossRate", e.target.value)}
          />
        </label>
        <label>
          <FieldLabel
            tipLabel="Portfolio max-loss amount"
            tipText="Optional absolute USDT Portfolio loss bound from the start baseline."
            tipTestId="tip-portfolio-loss-amount"
          >
            Portfolio max-loss amount (optional)
          </FieldLabel>
          <input
            data-testid="sim-portfolio-loss-amount"
            inputMode="decimal"
            value={values.portfolioMaxLossAmount}
            disabled={disabled}
            placeholder="unset"
            onChange={(e) => setField("portfolioMaxLossAmount", e.target.value)}
          />
        </label>
        <label>
          <FieldLabel
            tipLabel="Per-symbol max weight"
            tipText="Optional. Maximum Portfolio weight of the traded base asset after a BUY (0.2 = 20%). Quote USDT is uncapped."
            tipTestId="tip-per-symbol"
          >
            Per-symbol max weight (optional)
          </FieldLabel>
          <input
            data-testid="sim-per-symbol-weight"
            inputMode="decimal"
            value={values.perSymbolMaxWeight}
            disabled={disabled}
            placeholder="unset"
            onChange={(e) => setField("perSymbolMaxWeight", e.target.value)}
          />
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
          <FieldLabel
            tipLabel="Decision log mode"
            tipText="Important only skips ordinary HOLD rows in the Decision Journal (default). Full audit records every closed candle including HOLD. Trades and approved/rejected/forced decisions are always kept."
            tipTestId="tip-decision-log-mode"
          >
            Decision log mode
          </FieldLabel>
          <select
            data-testid="sim-decision-log-mode"
            value={values.decisionLogMode}
            disabled={disabled}
            onChange={(e) =>
              setField(
                "decisionLogMode",
                e.target.value as SessionConfigValues["decisionLogMode"],
              )
            }
          >
            <option value="important_only">Important decisions only</option>
            <option value="full_audit">Full audit (every candle)</option>
          </select>
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
