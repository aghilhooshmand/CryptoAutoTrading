import { FormEvent, useEffect, useMemo, useState } from "react";
import {
  type CandleInterval,
  MAX_BACKTEST_CANDLES,
  estimateCandleCount,
  maxWindowHint,
  oversizedHistoryMessage,
  validateCapitalNesting,
} from "../../services/backtestApi";
import {
  type CreateComparisonRequest,
  MAX_COMPARISON_LEGS,
  MIN_COMPARISON_LEGS,
  validateLegCount,
} from "../../services/comparisonApi";
import { getSettings } from "../../services/settingsApi";
import {
  comparisonSecondaryLegStarter,
  settingsToSharedSeed,
} from "../settings/mapSettingsToForm";
import { COST_DEFAULTS } from "../shared/CostRateFields";
import { CostRateFields } from "../shared/CostRateFields";
import {
  StrategyConfigFields,
  defaultStrategyConfig,
  type StrategyConfigValue,
} from "../strategy/StrategyConfigFields";

const INTERVALS: CandleInterval[] = ["1m", "5m", "15m", "1h", "4h", "1d"];

interface Props {
  disabled?: boolean;
  busy?: boolean;
  error?: string | null;
  onSubmit: (body: CreateComparisonRequest) => void;
}

function toMs(localValue: string): number | null {
  if (!localValue) return null;
  const ms = Date.parse(localValue);
  return Number.isFinite(ms) ? ms : null;
}

function emptyLeg(): StrategyConfigValue {
  return defaultStrategyConfig();
}

export function ComparisonConfigForm({ disabled, busy, error, onSubmit }: Props) {
  const [symbol, setSymbol] = useState("btc_usdt");
  const [timeframe, setTimeframe] = useState<CandleInterval>("1h");
  const [startLocal, setStartLocal] = useState("");
  const [endLocal, setEndLocal] = useState("");
  const [startingCapital, setStartingCapital] = useState("1000");
  const [allocatedCapital, setAllocatedCapital] = useState("1000");
  const [maxPositionSize, setMaxPositionSize] = useState("1000");
  const [profitRate, setProfitRate] = useState("");
  const [lossRate, setLossRate] = useState("");
  const [maxTrades, setMaxTrades] = useState("");
  const [feeRate, setFeeRate] = useState(COST_DEFAULTS.feeRate);
  const [slippageRate, setSlippageRate] = useState(COST_DEFAULTS.slippageRate);
  const [legs, setLegs] = useState<StrategyConfigValue[]>(() => [
    defaultStrategyConfig(),
    comparisonSecondaryLegStarter(),
  ]);
  const [legErrors, setLegErrors] = useState<(string | null)[]>([null, null]);
  const [localError, setLocalError] = useState<string | null>(null);
  const [seeded, setSeeded] = useState(false);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const settings = await getSettings();
        if (cancelled || seeded) return;
        const seed = settingsToSharedSeed(settings);
        setSymbol(seed.symbol);
        setTimeframe(seed.timeframe as CandleInterval);
        setStartingCapital(seed.startingCapital);
        setAllocatedCapital(seed.allocatedCapital);
        setMaxPositionSize(seed.maxPositionSize);
        setProfitRate(seed.targetNetProfitRate);
        setLossRate(seed.maxSessionLossRate);
        setMaxTrades(seed.maxTrades);
        setFeeRate(seed.feeRate);
        setSlippageRate(seed.slippageRate);
        setLegs((prev) => {
          const next = [...prev];
          next[0] = seed.strategy;
          if (next.length < 2) next.push(comparisonSecondaryLegStarter());
          return next;
        });
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

  // Stable per-index handlers so StrategyConfigFields effects do not loop.
  const legValidationHandlers = useMemo(
    () =>
      Array.from({ length: legs.length }, (_, index) => (message: string | null) => {
        setLegErrors((prev) => {
          if (prev[index] === message) return prev;
          const copy = [...prev];
          while (copy.length < legs.length) copy.push(null);
          copy[index] = message;
          return copy;
        });
      }),
    [legs.length],
  );

  const candleEstimate = useMemo(() => {
    const startTime = toMs(startLocal);
    const endTime = toMs(endLocal);
    if (startTime == null || endTime == null || endTime <= startTime) return null;
    return estimateCandleCount(startTime, endTime, timeframe);
  }, [startLocal, endLocal, timeframe]);

  function updateLeg(index: number, next: StrategyConfigValue) {
    setLegs((prev) => prev.map((leg, i) => (i === index ? next : leg)));
  }

  function addLeg() {
    if (legs.length >= MAX_COMPARISON_LEGS) return;
    setLegs((prev) => [...prev, emptyLeg()]);
    setLegErrors((prev) => [...prev, null]);
  }

  function removeLeg(index: number) {
    if (legs.length <= MIN_COMPARISON_LEGS) return;
    setLegs((prev) => prev.filter((_, i) => i !== index));
    setLegErrors((prev) => prev.filter((_, i) => i !== index));
  }

  function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setLocalError(null);
    const countErr = validateLegCount(legs.length);
    if (countErr) {
      setLocalError(countErr);
      return;
    }
    const nest = validateCapitalNesting(startingCapital, allocatedCapital, maxPositionSize);
    if (nest) {
      setLocalError(nest);
      return;
    }
    const startTime = toMs(startLocal);
    const endTime = toMs(endLocal);
    if (startTime == null || endTime == null) {
      setLocalError("Start and end date/time are required");
      return;
    }
    if (endTime <= startTime) {
      setLocalError("End must be after start");
      return;
    }
    const estimated = estimateCandleCount(startTime, endTime, timeframe);
    if (estimated > MAX_BACKTEST_CANDLES) {
      setLocalError(oversizedHistoryMessage(estimated, timeframe));
      return;
    }
    const firstStrategyError = legErrors.find((msg) => msg);
    if (firstStrategyError) {
      setLocalError(firstStrategyError);
      return;
    }
    const body: CreateComparisonRequest = {
      symbol: symbol.trim(),
      timeframe,
      startTime,
      endTime,
      startingCapital,
      allocatedCapital,
      maxPositionSize,
      legs: legs.map((leg) => ({
        strategyId: leg.strategyId,
        strategyParams: leg.strategyParams,
      })),
      feeRate,
      slippageRate,
    };
    if (profitRate) body.targetNetProfitRate = profitRate;
    if (lossRate) body.maxSessionLossRate = lossRate;
    if (maxTrades) body.maxTrades = Number(maxTrades);
    onSubmit(body);
  }

  const locked = disabled || busy;
  const oversized =
    candleEstimate != null && candleEstimate > MAX_BACKTEST_CANDLES;

  return (
    <form
      className="backtest-config comparison-config"
      onSubmit={handleSubmit}
      aria-labelledby="comparison-config-title"
    >
      <h3 id="comparison-config-title" className="visually-hidden">
        Configure strategy comparison
      </h3>

      <fieldset className="backtest-fieldset" disabled={locked}>
        <legend>Strategies ({legs.length})</legend>
        <p className="hint">
          Compare {MIN_COMPARISON_LEGS}–{MAX_COMPARISON_LEGS} registered strategies on
          one shared window. Duplicate strategies are allowed with different
          parameters.
        </p>
        {legs.map((leg, index) => (
          <div key={index} className="comparison-leg" data-testid={`comparison-leg-${index}`}>
            <div className="comparison-leg-header">
              <strong>Leg {index + 1}</strong>
              <button
                type="button"
                disabled={locked || legs.length <= MIN_COMPARISON_LEGS}
                onClick={() => removeLeg(index)}
              >
                Remove
              </button>
            </div>
            <StrategyConfigFields
              disabled={locked}
              value={leg}
              onChange={(next) => updateLeg(index, next)}
              onValidationError={legValidationHandlers[index]}
              variant="backtest"
            />
          </div>
        ))}
        <button
          type="button"
          disabled={locked || legs.length >= MAX_COMPARISON_LEGS}
          onClick={addLeg}
        >
          Add strategy
        </button>
      </fieldset>

      <fieldset className="backtest-fieldset" disabled={locked}>
        <legend>Shared market</legend>
        <div className="backtest-field-row">
          <label>
            Pair
            <input
              value={symbol}
              onChange={(e) => setSymbol(e.target.value)}
              placeholder="btc_usdt"
              autoComplete="off"
            />
          </label>
          <label>
            Timeframe
            <select
              value={timeframe}
              onChange={(e) => setTimeframe(e.target.value as CandleInterval)}
            >
              {INTERVALS.map((i) => (
                <option key={i} value={i}>
                  {i}
                </option>
              ))}
            </select>
          </label>
        </div>
      </fieldset>

      <fieldset className="backtest-fieldset" disabled={locked}>
        <legend>Shared period</legend>
        <div className="backtest-field-row">
          <label>
            Start
            <input
              type="datetime-local"
              value={startLocal}
              onChange={(e) => setStartLocal(e.target.value)}
              required
            />
          </label>
          <label>
            End
            <input
              type="datetime-local"
              value={endLocal}
              onChange={(e) => setEndLocal(e.target.value)}
              required
            />
          </label>
        </div>
        {candleEstimate != null && (
          <p
            className={oversized ? "form-error backtest-estimate" : "hint backtest-estimate"}
            role={oversized ? "alert" : undefined}
          >
            {oversized
              ? oversizedHistoryMessage(candleEstimate, timeframe)
              : `≈ ${candleEstimate.toLocaleString()} candles (max ${MAX_BACKTEST_CANDLES}; ${timeframe} ≤ ${maxWindowHint(timeframe)})`}
          </p>
        )}
      </fieldset>

      <fieldset className="backtest-fieldset" disabled={locked}>
        <legend>Shared capital</legend>
        <div className="backtest-field-row">
          <label>
            Starting
            <input
              value={startingCapital}
              onChange={(e) => setStartingCapital(e.target.value)}
              inputMode="decimal"
            />
          </label>
          <label>
            Allocated
            <input
              value={allocatedCapital}
              onChange={(e) => setAllocatedCapital(e.target.value)}
              inputMode="decimal"
            />
          </label>
        </div>
        <label className="backtest-field-full">
          Max position
          <input
            value={maxPositionSize}
            onChange={(e) => setMaxPositionSize(e.target.value)}
            inputMode="decimal"
          />
        </label>
      </fieldset>

      <details className="backtest-advanced">
        <summary>Common risk limits (optional)</summary>
        <div className="backtest-advanced-body">
          <label>
            Target net profit rate
            <input
              value={profitRate}
              onChange={(e) => setProfitRate(e.target.value)}
              disabled={locked}
              placeholder="e.g. 0.01"
              inputMode="decimal"
            />
          </label>
          <label>
            Max session loss rate
            <input
              value={lossRate}
              onChange={(e) => setLossRate(e.target.value)}
              disabled={locked}
              placeholder="e.g. 0.007"
              inputMode="decimal"
            />
          </label>
          <label>
            Max trades
            <input
              value={maxTrades}
              onChange={(e) => setMaxTrades(e.target.value)}
              disabled={locked}
              inputMode="numeric"
            />
          </label>
          <div className="backtest-cost-fields">
            <CostRateFields
              maxPositionSize={maxPositionSize}
              feeRate={feeRate}
              slippageRate={slippageRate}
              disabled={locked}
              onFeeRateChange={setFeeRate}
              onSlippageRateChange={setSlippageRate}
            />
          </div>
        </div>
      </details>

      {(localError || error) && (
        <p className="form-error" role="alert">
          {localError || error}
        </p>
      )}

      <div className="backtest-actions">
        <button type="submit" disabled={locked || oversized}>
          {busy ? "Comparing…" : "Run Comparison"}
        </button>
      </div>
    </form>
  );
}
