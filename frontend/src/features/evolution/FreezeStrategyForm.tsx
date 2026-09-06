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
      setOk(`Frozen as “${name.trim()}”. Select it in Backtest / Simulation strategy list.`);
      setName("");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Freeze failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <form onSubmit={submit} data-testid="evolution-freeze-form">
      <h3>Freeze best phenotype as named strategy</h3>
      <p className="auto-trading-lede">
        Only after the run is finished (or cancelled). Does not start Real trading.
      </p>
      <label>
        Display name
        <input
          value={name}
          disabled={disabled || busy}
          onChange={(e) => setName(e.target.value)}
          data-testid="evolution-freeze-name"
        />
      </label>
      <button type="submit" disabled={disabled || busy} data-testid="evolution-freeze-btn">
        Freeze to strategy list
      </button>
      {error ? (
        <p className="form-error" role="alert" data-testid="evolution-freeze-error">
          {error}
        </p>
      ) : null}
      {ok ? <p data-testid="evolution-freeze-ok">{ok}</p> : null}
    </form>
  );
}
