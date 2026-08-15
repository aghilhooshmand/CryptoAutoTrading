import { useEffect, useMemo, useRef, useState, type ReactNode } from "react";

import {
  FALLBACK_STRATEGIES,
  defaultParamsFor,
  listStrategies,
  type StrategyInfo,
  type StrategyParamValue,
  validateStrategyParamsClient,
} from "../../services/strategiesApi";

export interface StrategyConfigValue {
  strategyId: string;
  strategyParams: Record<string, StrategyParamValue>;
}

interface Props {
  disabled?: boolean;
  value: StrategyConfigValue;
  onChange: (next: StrategyConfigValue) => void;
  onValidationError?: (message: string | null) => void;
  /** Visual shell: simulation sits inside a card; backtest matches fieldset sections. */
  variant?: "simulation" | "backtest";
  /**
   * When the operator picks this strategy id and no draft params were remembered
   * for it yet, restore these params instead of registry defaults (saved Settings).
   */
  preferredStrategy?: StrategyConfigValue | null;
}

function paramLabel(name: string, fallback: string): string {
  if (name === "fastPeriod") return "Fast period";
  if (name === "slowPeriod") return "Slow period";
  return fallback;
}

function FieldHint({ children }: { children: ReactNode }) {
  return <span className="field-hint">{children}</span>;
}

export function StrategyConfigFields({
  disabled = false,
  value,
  onChange,
  onValidationError,
  variant = "simulation",
  preferredStrategy = null,
}: Props) {
  const [strategies, setStrategies] = useState<StrategyInfo[]>(FALLBACK_STRATEGIES);
  const [loadError, setLoadError] = useState<string | null>(null);
  /** Draft params remembered per Rule so switching away and back does not wipe edits. */
  const paramsByStrategyRef = useRef<Record<string, Record<string, StrategyParamValue>>>({});

  useEffect(() => {
    let cancelled = false;
    listStrategies()
      .then((list) => {
        if (cancelled || list.length === 0) return;
        setStrategies(list);
        setLoadError(null);
      })
      .catch(() => {
        if (!cancelled) {
          setLoadError("Using built-in strategy defaults (strategy list unavailable).");
        }
      });
    return () => {
      cancelled = true;
    };
  }, []);

  // Keep memory in sync with the controlled value (load, Save, Reset, edits).
  useEffect(() => {
    if (!value.strategyId) return;
    paramsByStrategyRef.current[value.strategyId] = { ...value.strategyParams };
  }, [value.strategyId, value.strategyParams]);

  // Seed memory from saved preferred strategy when it arrives / changes.
  useEffect(() => {
    if (!preferredStrategy?.strategyId) return;
    paramsByStrategyRef.current[preferredStrategy.strategyId] = {
      ...preferredStrategy.strategyParams,
    };
  }, [preferredStrategy]);

  // Normalize aliases (e.g. dual_ema_9_21 → dual_ema) once the registry list is known.
  useEffect(() => {
    if (strategies.length === 0) return;
    const direct = strategies.find((s) => s.id === value.strategyId);
    if (direct) return;
    const viaAlias = strategies.find((s) => s.aliases?.includes(value.strategyId));
    if (!viaAlias) return;
    onChange({
      strategyId: viaAlias.id,
      strategyParams:
        Object.keys(value.strategyParams).length > 0
          ? value.strategyParams
          : defaultParamsFor(viaAlias),
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps -- only reconcile alias ids
  }, [strategies, value.strategyId]);

  const selected =
    strategies.find((s) => s.id === value.strategyId) ??
    strategies.find((s) => s.aliases?.includes(value.strategyId)) ??
    null;

  const clientError = useMemo(() => {
    if (!selected) return "No strategy available.";
    return validateStrategyParamsClient(selected, value.strategyParams);
  }, [selected, value.strategyParams]);

  useEffect(() => {
    onValidationError?.(clientError);
  }, [clientError, onValidationError]);

  function paramsForStrategy(id: string, strat: StrategyInfo): Record<string, StrategyParamValue> {
    const remembered = paramsByStrategyRef.current[id];
    if (remembered && Object.keys(remembered).length > 0) {
      return { ...remembered };
    }
    if (preferredStrategy && preferredStrategy.strategyId === id) {
      return { ...preferredStrategy.strategyParams };
    }
    return defaultParamsFor(strat);
  }

  function selectStrategy(id: string) {
    const strat = strategies.find((s) => s.id === id);
    if (!strat) return;
    if (id === value.strategyId) return;
    // Remember current Rule params before switching.
    paramsByStrategyRef.current[value.strategyId] = { ...value.strategyParams };
    onChange({ strategyId: id, strategyParams: paramsForStrategy(id, strat) });
  }

  function setParam(name: string, raw: string, type: StrategyInfo["parameters"][0]["type"]) {
    let next: StrategyParamValue;
    if (type === "decimal_string" || type === "string") {
      next = raw;
    } else {
      const n = Number(raw);
      next = Number.isFinite(n) ? n : (value.strategyParams[name] ?? 0);
    }
    const strategyParams = {
      ...value.strategyParams,
      [name]: next,
    };
    paramsByStrategyRef.current[value.strategyId] = strategyParams;
    onChange({
      ...value,
      strategyParams,
    });
  }

  if (!selected) {
    return <p className="note">No strategies registered.</p>;
  }

  const single = strategies.length === 1;
  const shellClass =
    variant === "backtest"
      ? "strategy-config strategy-config--backtest"
      : "strategy-config strategy-config--simulation";

  return (
    <div className={shellClass} data-testid="strategy-config-fields">
      <div className="strategy-config__head">
        <h3 className="strategy-config__title">Strategy</h3>
        <p className="strategy-config__subtitle">
          Advisory signals only — Controller and Risk still approve fills.
        </p>
      </div>

      {loadError ? <p className="hint">{loadError}</p> : null}

      <div className="strategy-config__grid">
        <div className="strategy-config__strategy">
          <span className="strategy-config__label">Rule</span>
          {single ? (
            <>
              <div
                className="strategy-config__pill"
                data-testid="strategy-id"
                data-strategy-id={selected.id}
              >
                {selected.displayName}
              </div>
              <FieldHint>Closed-candle Dual EMA crossover. Edit periods below.</FieldHint>
            </>
          ) : (
            <select
              data-testid="strategy-id"
              data-strategy-id={value.strategyId}
              name="strategyId"
              value={value.strategyId}
              disabled={disabled}
              onChange={(e) => selectStrategy(e.target.value)}
            >
              {/* Ensure current id remains selectable even if temporarily unknown */}
              {!strategies.some((s) => s.id === value.strategyId) ? (
                <option value={value.strategyId}>{value.strategyId}</option>
              ) : null}
              {strategies.map((s) => (
                <option key={s.id} value={s.id}>
                  {s.displayName}
                </option>
              ))}
            </select>
          )}
        </div>

        {selected.parameters.map((p) => {
          const current = value.strategyParams[p.name] ?? p.default;
          const isDecimal = p.type === "decimal_string";
          return (
            <label key={p.name}>
              <span className="strategy-config__label">{paramLabel(p.name, p.label)}</span>
              <input
                type={isDecimal ? "text" : "number"}
                inputMode={isDecimal ? "decimal" : "numeric"}
                data-testid={`strategy-param-${p.name}`}
                data-param-type={p.type}
                value={current}
                min={isDecimal ? undefined : p.minimum}
                max={isDecimal ? undefined : p.maximum}
                step={isDecimal ? "any" : 1}
                disabled={disabled}
                onChange={(e) => setParam(p.name, e.target.value, p.type)}
              />
            </label>
          );
        })}
      </div>

      {clientError ? (
        <p className="error strategy-config__error" data-testid="strategy-param-error" role="alert">
          {clientError}
        </p>
      ) : null}
    </div>
  );
}

export function defaultStrategyConfig(): StrategyConfigValue {
  const s = FALLBACK_STRATEGIES[0];
  return {
    strategyId: s.id,
    strategyParams: defaultParamsFor(s),
  };
}
