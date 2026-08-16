import { FormEvent, useEffect, useRef, useState } from "react";

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
    portfolioMaxLossRate: string;
    portfolioMaxLossAmount: string;
    perSymbolMaxWeight: string;
    preferredAllocationId: string;
    decisionLogMode: "important_only" | "full_audit";
    takeProfitPercent: string;
    stopLossPercent: string;
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
    portfolioMaxLossRate:
      values.portfolioMaxLossRate.trim() === "" ? null : values.portfolioMaxLossRate,
    portfolioMaxLossAmount:
      values.portfolioMaxLossAmount.trim() === "" ? null : values.portfolioMaxLossAmount,
    perSymbolMaxWeight: values.perSymbolMaxWeight.trim() === "" ? null : values.perSymbolMaxWeight,
    preferredAllocationId:
      values.preferredAllocationId.trim() === "" ? null : values.preferredAllocationId,
    decisionLogMode: values.decisionLogMode,
    takeProfitPercent: values.takeProfitPercent.trim() === "" ? null : values.takeProfitPercent,
    stopLossPercent: values.stopLossPercent.trim() === "" ? null : values.stopLossPercent,
  };
}

function applySettingsToState(
  data: OperatorSettings,
  setValues: (v: ReturnType<typeof emptyValues>) => void,
  setStrategy: (s: StrategyConfigValue) => void,
  setPreferredStrategy: (s: StrategyConfigValue) => void,
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
    portfolioMaxLossRate: data.portfolioMaxLossRate ?? "",
    portfolioMaxLossAmount: data.portfolioMaxLossAmount ?? "",
    perSymbolMaxWeight: data.perSymbolMaxWeight ?? "",
    preferredAllocationId: data.preferredAllocationId ?? "",
    decisionLogMode: data.decisionLogMode === "full_audit" ? "full_audit" : "important_only",
    takeProfitPercent: data.takeProfitPercent ?? "",
    stopLossPercent: data.stopLossPercent ?? "",
  });
  const nextStrategy = {
    strategyId: data.strategyId,
    strategyParams: { ...data.strategyParams },
  };
  setStrategy(nextStrategy);
  setPreferredStrategy(nextStrategy);
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
    portfolioMaxLossRate: "",
    portfolioMaxLossAmount: "",
    perSymbolMaxWeight: "",
    preferredAllocationId: "",
    decisionLogMode: "important_only" as const,
    takeProfitPercent: "",
    stopLossPercent: "",
  };
}

export function SettingsPanel() {
  const [values, setValues] = useState(emptyValues);
  const [strategy, setStrategy] = useState<StrategyConfigValue>(() => defaultStrategyConfig());
  const [preferredStrategy, setPreferredStrategy] = useState<StrategyConfigValue | null>(null);
  const [strategyError, setStrategyError] = useState<string | null>(null);
  const [warning, setWarning] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [status, setStatus] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [loaded, setLoaded] = useState(false);
  // Always save the latest draft (avoids stale closure if Save races a re-render).
  const valuesRef = useRef(values);
  const strategyRef = useRef(strategy);
  valuesRef.current = values;
  strategyRef.current = strategy;

  // Load once on mount. Parent keeps this panel mounted (hidden) so unsaved
  // drafts survive Auto Trading tab switches (FR-006).
  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const data = await getSettings();
        if (cancelled) return;
        applySettingsToState(data, setValues, setStrategy, setPreferredStrategy, setWarning);
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

  function handleStrategyChange(next: StrategyConfigValue) {
    setStrategy(next);
    setStrategyError(null);
    setStatus(null);
  }

  async function handleSave(event: FormEvent) {
    event.preventDefault();
    setError(null);
    setStatus(null);
    const draftValues = valuesRef.current;
    const draftStrategy = strategyRef.current;
    const nest = validateCapitalNesting(
      draftValues.startingCapital,
      draftValues.allocatedCapital,
      draftValues.maxPositionSize,
    );
    if (nest) {
      setError(nest);
      return;
    }
    if (strategyError) {
      setError(strategyError);
      return;
    }
    if (draftValues.maxTrades.trim() !== "") {
      const n = Number(draftValues.maxTrades);
      if (!Number.isInteger(n) || n < 1) {
        setError("Max trades must be an integer ≥ 1 when set.");
        return;
      }
    }
    if (!draftStrategy.strategyId) {
      setError("Choose a strategy Rule before saving.");
      return;
    }
    setBusy(true);
    try {
      const body = toWriteBody(draftValues, draftStrategy);
      await putSettings(body);
      // Re-read from server so the UI matches what was actually persisted (incl. Rule).
      const confirmed = await getSettings();
      applySettingsToState(confirmed, setValues, setStrategy, setPreferredStrategy, setWarning);
      setStatus(
        `Settings saved (Rule: ${confirmed.strategyId}). New Simulation, Backtest, and Comparison forms will use these defaults.`,
      );
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
      applySettingsToState(saved, setValues, setStrategy, setPreferredStrategy, setWarning);
      setStatus("Settings reset to product starters.");
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
          Take-profit % (optional)
          <input
            data-testid="settings-take-profit-percent"
            value={values.takeProfitPercent}
            disabled={busy}
            placeholder="e.g. 0.02"
            onChange={(e) => setField("takeProfitPercent", e.target.value)}
          />
        </label>
        <label>
          Stop-loss % (optional)
          <input
            data-testid="settings-stop-loss-percent"
            value={values.stopLossPercent}
            disabled={busy}
            placeholder="e.g. 0.01"
            onChange={(e) => setField("stopLossPercent", e.target.value)}
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
        <label>
          Portfolio max-loss rate (optional)
          <input
            data-testid="settings-portfolio-loss-rate"
            value={values.portfolioMaxLossRate}
            disabled={busy}
            placeholder="unset"
            onChange={(e) => setField("portfolioMaxLossRate", e.target.value)}
          />
        </label>
        <label>
          Portfolio max-loss amount (optional)
          <input
            data-testid="settings-portfolio-loss-amount"
            value={values.portfolioMaxLossAmount}
            disabled={busy}
            placeholder="unset"
            onChange={(e) => setField("portfolioMaxLossAmount", e.target.value)}
          />
        </label>
        <label>
          Per-symbol max weight (optional)
          <input
            data-testid="settings-per-symbol-weight"
            value={values.perSymbolMaxWeight}
            disabled={busy}
            placeholder="unset"
            onChange={(e) => setField("perSymbolMaxWeight", e.target.value)}
          />
        </label>
        <label>
          Preferred allocation id (optional)
          <input
            data-testid="settings-preferred-allocation"
            value={values.preferredAllocationId}
            disabled={busy}
            placeholder="unset"
            onChange={(e) => setField("preferredAllocationId", e.target.value)}
          />
        </label>
        <label>
          Simulation decision log mode
          <select
            data-testid="settings-decision-log-mode"
            value={values.decisionLogMode}
            disabled={busy}
            onChange={(e) =>
              setField(
                "decisionLogMode",
                e.target.value as "important_only" | "full_audit",
              )
            }
          >
            <option value="important_only">Important decisions only</option>
            <option value="full_audit">Full audit (every candle)</option>
          </select>
        </label>
        <div className="sim-cost-fields">
          <CostRateFields
            maxPositionSize={values.maxPositionSize}
            feeRate={values.feeRate}
            slippageRate={values.slippageRate}
            disabled={busy}
            onFeeRateChange={(v) => setField("feeRate", v)}
            onSlippageRateChange={(v) => setField("slippageRate", v)}
            feeTestId="settings-fee"
            slippageTestId="settings-slippage"
          />
        </div>
      </div>

      <StrategyConfigFields
        variant="backtest"
        disabled={busy}
        value={strategy}
        onChange={handleStrategyChange}
        onValidationError={setStrategyError}
        preferredStrategy={preferredStrategy}
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
