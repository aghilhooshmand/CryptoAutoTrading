import { FormEvent, useMemo, useState } from "react";
import {
  type CandleInterval,
  type CreateBacktestRequest,
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

  return (
    <form className="backtest-config" onSubmit={handleSubmit} aria-labelledby="backtest-config-title">
      <h3 id="backtest-config-title">Configure historical backtest</h3>
      <label>
        Symbol
        <input value={symbol} onChange={(e) => setSymbol(e.target.value)} disabled={disabled || busy} />
      </label>
      <label>
        Timeframe
        <select
          value={timeframe}
          onChange={(e) => setTimeframe(e.target.value as CandleInterval)}
          disabled={disabled || busy}
        >
          {INTERVALS.map((i) => (
            <option key={i} value={i}>
              {i}
            </option>
          ))}
        </select>
      </label>
      <label>
        Start
        <input
          type="datetime-local"
          value={startLocal}
          onChange={(e) => setStartLocal(e.target.value)}
          disabled={disabled || busy}
          required
        />
      </label>
      <label>
        End
        <input
          type="datetime-local"
          value={endLocal}
          onChange={(e) => setEndLocal(e.target.value)}
          disabled={disabled || busy}
          required
        />
      </label>
      <label>
        Starting capital
        <input value={startingCapital} onChange={(e) => setStartingCapital(e.target.value)} disabled={disabled || busy} />
      </label>
      <label>
        Allocated capital
        <input value={allocatedCapital} onChange={(e) => setAllocatedCapital(e.target.value)} disabled={disabled || busy} />
      </label>
      <label>
        Max position size
        <input value={maxPositionSize} onChange={(e) => setMaxPositionSize(e.target.value)} disabled={disabled || busy} />
      </label>
      <label>
        Target net profit rate (optional)
        <input value={profitRate} onChange={(e) => setProfitRate(e.target.value)} disabled={disabled || busy} placeholder="e.g. 0.01" />
        {derivedProfit != null && <span className="hint">≈ {derivedProfit} USDT</span>}
      </label>
      <label>
        Max session loss rate (optional)
        <input value={lossRate} onChange={(e) => setLossRate(e.target.value)} disabled={disabled || busy} placeholder="e.g. 0.007" />
        {derivedLoss != null && <span className="hint">≈ {derivedLoss} USDT</span>}
      </label>
      <label>
        Max trades (optional)
        <input value={maxTrades} onChange={(e) => setMaxTrades(e.target.value)} disabled={disabled || busy} />
      </label>
      <label>
        Fee rate (optional, default 0.001)
        <input value={feeRate} onChange={(e) => setFeeRate(e.target.value)} disabled={disabled || busy} />
      </label>
      <label>
        Slippage rate (optional, default 0.0005)
        <input value={slippageRate} onChange={(e) => setSlippageRate(e.target.value)} disabled={disabled || busy} />
      </label>
      {(localError || error) && (
        <p className="form-error" role="alert">
          {localError || error}
        </p>
      )}
      <button type="submit" disabled={disabled || busy}>
        {busy ? "Running…" : "Run backtest"}
      </button>
    </form>
  );
}
