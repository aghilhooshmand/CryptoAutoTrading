import { FormEvent, useEffect, useState } from "react";

import {
  getSettings,
  putSettings,
  resetSettings,
  type OperatorSettings,
  type SettingsApiError,
  type SettingsWriteBody,
} from "../../services/settingsApi";
import { COST_DEFAULTS, CostRateFields } from "../shared/CostRateFields";
import {
  StrategyConfigFields,
  defaultStrategyConfig,
  type StrategyConfigValue,
} from "../strategy/StrategyConfigFields";
import { validateCapitalNesting } from "../../services/simulationApi";

const INTERVALS = ["1m", "5m", "15m", "1h", "4h", "1d"] as const;

function toWriteBody(
  values: {
    symbol: string;
    timeframe: string;
    startingCapital: string;
    allocatedCapital: string;
    maxPositionSize: string;
    feeRate: string;
    slippageRate: string;
    targetNetProfitRate: string;
    maxSessionLossRate: string;
    maxTrades: string;
  },
  strategy: StrategyConfigValue,
): SettingsWriteBody {
  return {
    symbol: values.symbol,
    timeframe: values.timeframe,
    startingCapital: values.startingCapital,
    allocatedCapital: values.allocatedCapital,
    maxPositionSize: values.maxPositionSize,
    feeRate: values.feeRate,
    slippageRate: values.slippageRate,
    targetNetProfitRate: values.targetNetProfitRate.trim() === "" ? null : values.targetNetProfitRate,
    maxSessionLossRate: values.maxSessionLossRate.trim() === "" ? null : values.maxSessionLossRate,
    maxTrades: values.maxTrades.trim() === "" ? null : Number(values.maxTrades),
    strategyId: strategy.strategyId,
    strategyParams: strategy.strategyParams,
  };
}

function applySettingsToState(
  data: OperatorSettings,
  setValues: (v: ReturnType<typeof emptyValues>) => void,
  setStrategy: (s: StrategyConfigValue) => void,
  setWarning: (w: string | null) => void,
) {
  setValues({
    symbol: data.symbol,
    timeframe: data.timeframe,
    startingCapital: data.startingCapital,
    allocatedCapital: data.allocatedCapital,
    maxPositionSize: data.maxPositionSize,
    feeRate: data.feeRate,
    slippageRate: data.slippageRate,
    targetNetProfitRate: data.targetNetProfitRate ?? "",
    maxSessionLossRate: data.maxSessionLossRate ?? "",
    maxTrades: data.maxTrades == null ? "" : String(data.maxTrades),
  });
  setStrategy({
    strategyId: data.strategyId,
    strategyParams: { ...data.strategyParams },
  });
  setWarning(data.warning);
}

function emptyValues() {
  return {
    symbol: "btc_usdt",
    timeframe: "1h",
    startingCapital: "1000",
    allocatedCapital: "1000",
    maxPositionSize: "1000",
    feeRate: COST_DEFAULTS.feeRate,
    slippageRate: COST_DEFAULTS.slippageRate,
    targetNetProfitRate: "",
    maxSessionLossRate: "",
    maxTrades: "",
  };
}

export function SettingsPanel({ onPersisted }: { onPersisted?: () => void }) {
  const [values, setValues] = useState(emptyValues);
  const [strategy, setStrategy] = useState<StrategyConfigValue>(defaultStrategyConfig);
  const [strategyError, setStrategyError] = useState<string | null>(null);
  const [warning, setWarning] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [status, setStatus] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [loaded, setLoaded] = useState(false);

  // Load once on mount. Parent keeps this panel mounted (hidden) so unsaved
  // drafts survive Auto Trading tab switches (FR-006).
  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const data = await getSettings();
        if (cancelled) return;
        applySettingsToState(data, setValues, setStrategy, setWarning);
      } catch (err) {
        if (!cancelled) {
          setError((err as SettingsApiError).message ?? "Failed to load Settings");
        }
      } finally {
        if (!cancelled) setLoaded(true);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  function setField<K extends keyof ReturnType<typeof emptyValues>>(key: K, value: string) {
    setValues((prev) => ({ ...prev, [key]: value }));
    setStatus(null);
  }

  async function handleSave(event: FormEvent) {
    event.preventDefault();
    setError(null);
    setStatus(null);
    const nest = validateCapitalNesting(
      values.startingCapital,
      values.allocatedCapital,
      values.maxPositionSize,
    );
    if (nest) {
      setError(nest);
      return;
    }
    if (strategyError) {
      setError(strategyError);
      return;
    }
    if (values.maxTrades.trim() !== "") {
      const n = Number(values.maxTrades);
      if (!Number.isInteger(n) || n < 1) {
        setError("Max trades must be an integer ≥ 1 when set.");
        return;
      }
    }
    setBusy(true);
    try {
      const saved = await putSettings(toWriteBody(values, strategy));
      applySettingsToState(saved, setValues, setStrategy, setWarning);
      setStatus("Settings saved. New Simulation, Backtest, and Comparison forms will use these defaults.");
      onPersisted?.();
    } catch (err) {
      const message =
        err && typeof err === "object" && "message" in err && typeof (err as SettingsApiError).message === "string"
          ? (err as SettingsApiError).message
          : "Save failed";
      setError(message);
    } finally {
      setBusy(false);
    }
  }

  async function handleReset() {
    const ok = window.confirm(
      "Reset Settings to product starter defaults? This does not start or stop any trading.",
    );
    if (!ok) return;
    setBusy(true);
    setError(null);
    setStatus(null);
    try {
      const saved = await resetSettings();
      applySettingsToState(saved, setValues, setStrategy, setWarning);
      setStatus("Settings reset to product starters.");
      onPersisted?.();
    } catch (err) {
      const message =
        err && typeof err === "object" && "message" in err && typeof (err as SettingsApiError).message === "string"
          ? (err as SettingsApiError).message
          : "Reset failed";
      setError(message);
    } finally {
      setBusy(false);
    }
  }

  if (!loaded) {
    return <p className="auto-trading-lede">Loading Settings…</p>;
  }

  return (
    <form className="settings-form" onSubmit={handleSave} data-testid="settings-form">
      <p className="auto-trading-lede">
        Defaults for new Simulation, Backtest, and Comparison forms. Explicit Save
        required. Changing Settings never starts or stops trading.
      </p>

      {warning ? (
        <p className="form-warning" role="status" data-testid="settings-warning">
          {warning}
        </p>
      ) : null}
      {error ? (
        <p className="form-error" role="alert" data-testid="settings-error">
          {error}
        </p>
      ) : null}
      {status ? (
        <p className="form-status" role="status" data-testid="settings-status">
          {status}
        </p>
      ) : null}

      <div className="sim-grid">
        <label>
          Symbol
          <input
            data-testid="settings-symbol"
            value={values.symbol}
            disabled={busy}
            onChange={(e) => setField("symbol", e.target.value)}
          />
        </label>
        <label>
          Timeframe
          <select
            data-testid="settings-timeframe"
            value={values.timeframe}
            disabled={busy}
            onChange={(e) => setField("timeframe", e.target.value)}
          >
            {INTERVALS.map((i) => (
              <option key={i} value={i}>
                {i}
              </option>
            ))}
          </select>
        </label>
        <label>
          Starting capital
          <input
            data-testid="settings-starting"
            value={values.startingCapital}
            disabled={busy}
            onChange={(e) => setField("startingCapital", e.target.value)}
          />
        </label>
        <label>
          Allocated capital
          <input
            data-testid="settings-allocated"
            value={values.allocatedCapital}
            disabled={busy}
            onChange={(e) => setField("allocatedCapital", e.target.value)}
          />
        </label>
        <label>
          Max position size
          <input
            data-testid="settings-max-pos"
            value={values.maxPositionSize}
            disabled={busy}
            onChange={(e) => setField("maxPositionSize", e.target.value)}
          />
        </label>
        <label>
          Target net profit rate (optional)
          <input
            data-testid="settings-profit-rate"
            value={values.targetNetProfitRate}
            disabled={busy}
            placeholder="unset"
            onChange={(e) => setField("targetNetProfitRate", e.target.value)}
          />
        </label>
        <label>
          Max session loss rate (optional)
          <input
            data-testid="settings-loss-rate"
            value={values.maxSessionLossRate}
            disabled={busy}
            placeholder="unset"
            onChange={(e) => setField("maxSessionLossRate", e.target.value)}
          />
        </label>
        <label>
          Max trades (optional)
          <input
            data-testid="settings-max-trades"
            value={values.maxTrades}
            disabled={busy}
            placeholder="unset"
            onChange={(e) => setField("maxTrades", e.target.value)}
          />
        </label>
      </div>

      <CostRateFields
        maxPositionSize={values.maxPositionSize}
        feeRate={values.feeRate}
        slippageRate={values.slippageRate}
        disabled={busy}
        onFeeRateChange={(v) => setField("feeRate", v)}
        onSlippageRateChange={(v) => setField("slippageRate", v)}
      />

      <StrategyConfigFields
        variant="backtest"
        disabled={busy}
        value={strategy}
        onChange={setStrategy}
        onValidationError={setStrategyError}
      />

      <div className="sim-actions settings-actions">
        <button type="submit" data-testid="settings-save" disabled={busy}>
          {busy ? "Saving…" : "Save"}
        </button>
        <button
          type="button"
          data-testid="settings-reset"
          disabled={busy}
          onClick={() => {
            void handleReset();
          }}
        >
          Reset to starters
        </button>
      </div>
      {status ? (
        <p className="form-status" role="status" data-testid="settings-status-footer">
          {status}
        </p>
      ) : null}
      {error ? (
        <p className="form-error" role="alert" data-testid="settings-error-footer">
          {error}
        </p>
      ) : null}
    </form>
  );
}
