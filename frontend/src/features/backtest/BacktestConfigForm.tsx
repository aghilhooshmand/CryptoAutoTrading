import { FormEvent, useMemo, useState } from "react";
import {
  type CandleInterval,
  type CreateBacktestRequest,
  MAX_BACKTEST_CANDLES,
  estimateCandleCount,
  maxWindowHint,
  oversizedHistoryMessage,
  validateCapitalNesting,
} from "../../services/backtestApi";

const INTERVALS: CandleInterval[] = ["1m", "5m", "15m", "1h", "4h", "1d"];

interface Props {
  disabled?: boolean;
  busy?: boolean;
  error?: string | null;
  onSubmit: (body: CreateBacktestRequest) => void;
}

function toMs(localValue: string): number | null {
  if (!localValue) return null;
  const ms = Date.parse(localValue);
  return Number.isFinite(ms) ? ms : null;
}

export function BacktestConfigForm({ disabled, busy, error, onSubmit }: Props) {
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
  const [feeRate, setFeeRate] = useState("");
  const [slippageRate, setSlippageRate] = useState("");
  const [localError, setLocalError] = useState<string | null>(null);

  const derivedProfit = useMemo(() => {
    const a = Number(allocatedCapital);
    const r = Number(profitRate);
    if (!profitRate || !Number.isFinite(a) || !Number.isFinite(r)) return null;
    return (a * r).toFixed(8).replace(/\.?0+$/, "");
  }, [allocatedCapital, profitRate]);

  const derivedLoss = useMemo(() => {
    const a = Number(allocatedCapital);
    const r = Number(lossRate);
    if (!lossRate || !Number.isFinite(a) || !Number.isFinite(r)) return null;
    return (a * r).toFixed(8).replace(/\.?0+$/, "");
  }, [allocatedCapital, lossRate]);

  const candleEstimate = useMemo(() => {
    const startTime = toMs(startLocal);
    const endTime = toMs(endLocal);
    if (startTime == null || endTime == null || endTime <= startTime) return null;
    return estimateCandleCount(startTime, endTime, timeframe);
  }, [startLocal, endLocal, timeframe]);

  function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setLocalError(null);
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
    const body: CreateBacktestRequest = {
      symbol: symbol.trim(),
      timeframe,
      startTime,
      endTime,
      startingCapital,
      allocatedCapital,
      maxPositionSize,
    };
    if (profitRate) body.targetNetProfitRate = profitRate;
    if (lossRate) body.maxSessionLossRate = lossRate;
    if (maxTrades) body.maxTrades = Number(maxTrades);
    if (feeRate) body.feeRate = feeRate;
    if (slippageRate) body.slippageRate = slippageRate;
    onSubmit(body);
  }

  const locked = disabled || busy;
  const oversized =
    candleEstimate != null && candleEstimate > MAX_BACKTEST_CANDLES;

  return (
    <form
      className="backtest-config"
      onSubmit={handleSubmit}
      aria-labelledby="backtest-config-title"
    >
      <h3 id="backtest-config-title" className="visually-hidden">
        Configure backtest
      </h3>

      <fieldset className="backtest-fieldset" disabled={locked}>
        <legend>Market</legend>
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
        <legend>Period</legend>
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
        <legend>Capital</legend>
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
        <summary>Advanced settings</summary>
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
            {derivedProfit != null && (
              <span className="hint">≈ {derivedProfit} USDT</span>
            )}
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
            {derivedLoss != null && (
              <span className="hint">≈ {derivedLoss} USDT</span>
            )}
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
          <label>
            Fee rate
            <input
              value={feeRate}
              onChange={(e) => setFeeRate(e.target.value)}
              disabled={locked}
              placeholder="default 0.001"
              inputMode="decimal"
            />
          </label>
          <label>
            Slippage rate
            <input
              value={slippageRate}
              onChange={(e) => setSlippageRate(e.target.value)}
              disabled={locked}
              placeholder="default 0.0005"
              inputMode="decimal"
            />
          </label>
        </div>
      </details>

      {(localError || error) && (
        <p className="form-error" role="alert">
          {localError || error}
        </p>
      )}

      <div className="backtest-actions">
        <button type="submit" disabled={locked || oversized}>
          {busy ? "Running…" : "Run Backtest"}
        </button>
      </div>
    </form>
  );
}
