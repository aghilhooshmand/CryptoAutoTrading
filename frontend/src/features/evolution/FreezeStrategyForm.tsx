import { useState, type FormEvent } from "react";

type Props = {
  disabled?: boolean;
  onFreeze: (displayName: string) => Promise<void>;
};

export function FreezeStrategyForm({ disabled, onFreeze }: Props) {
  const [name, setName] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [ok, setOk] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function submit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setOk(null);
    if (!name.trim()) {
      setError("Display name is required");
      return;
    }
    setBusy(true);
    try {
      await onFreeze(name.trim());
      setOk(
        `Frozen as “${name.trim()}”. Select it in Backtest / Simulation strategy list.`,
      );
      setName("");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Freeze failed");
    } finally {
      setBusy(false);
    }
  }

  const locked = disabled || busy;

  return (
    <form
      className="backtest-config"
      onSubmit={submit}
      data-testid="evolution-freeze-form"
    >
      <h3 className="visually-hidden">Freeze phenotype as named strategy</h3>
      <fieldset className="backtest-fieldset" disabled={locked}>
        <legend>Freeze as named strategy</legend>
        <p className="field-hint">
          Available after the run finishes (or is cancelled). Does not start Real
          trading.
        </p>
        <div className="backtest-field-row">
          <label>
            Display name
            <input
              value={name}
              disabled={locked}
              onChange={(e) => setName(e.target.value)}
              placeholder="e.g. UGE RSI tight 2024-H1"
              data-testid="evolution-freeze-name"
            />
          </label>
        </div>
      </fieldset>

      {error ? (
        <p className="form-error" role="alert" data-testid="evolution-freeze-error">
          {error}
        </p>
      ) : null}
      {ok ? (
        <p className="note" data-testid="evolution-freeze-ok">
          {ok}
        </p>
      ) : null}

      <div className="backtest-actions">
        <button type="submit" disabled={locked} data-testid="evolution-freeze-btn">
          {busy ? "Freezing…" : "Freeze to strategy list"}
        </button>
      </div>
    </form>
  );
}
