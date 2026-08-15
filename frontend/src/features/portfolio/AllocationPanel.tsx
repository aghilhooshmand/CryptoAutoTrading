import { FormEvent, useState } from "react";

import {
  createAllocation,
  releaseAllocation,
  resizeAllocation,
  type PortfolioApiError,
  type PortfolioAllocation,
  type PortfolioSnapshot,
} from "../../services/portfolioApi";
import { formatUsdt } from "./capitalDisplay";

interface Props {
  snapshot: PortfolioSnapshot;
  onUpdated: (next: PortfolioSnapshot) => void;
}

export function AllocationPanel({ snapshot, onUpdated }: Props) {
  const [open, setOpen] = useState(snapshot.allocations.length > 0);
  const [label, setLabel] = useState("");
  const [reservedSize, setReservedSize] = useState("");
  const [targetRef, setTargetRef] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [status, setStatus] = useState<string | null>(null);
  const [resizeDrafts, setResizeDrafts] = useState<Record<string, string>>({});
  const [rowBusy, setRowBusy] = useState<string | null>(null);

  async function onCreate(event: FormEvent) {
    event.preventDefault();
    if (busy) return;
    setBusy(true);
    setError(null);
    setStatus(null);
    try {
      const next = await createAllocation({
        label: label.trim(),
        reservedSize: reservedSize.trim(),
        targetRef: targetRef.trim() || null,
      });
      onUpdated(next);
      setLabel("");
      setReservedSize("");
      setTargetRef("");
      setStatus("Allocation created.");
      setOpen(true);
    } catch (err) {
      const apiErr = err as PortfolioApiError;
      setError(apiErr.message ?? "Could not create allocation");
    } finally {
      setBusy(false);
    }
  }

  async function onResize(allocation: PortfolioAllocation) {
    if (rowBusy) return;
    const nextSize = (resizeDrafts[allocation.id] ?? allocation.reservedSize).trim();
    setRowBusy(allocation.id);
    setError(null);
    setStatus(null);
    try {
      const next = await resizeAllocation(allocation.id, nextSize);
      onUpdated(next);
      setStatus(`Resized “${allocation.label}”.`);
    } catch (err) {
      const apiErr = err as PortfolioApiError;
      setError(apiErr.message ?? "Could not resize allocation");
    } finally {
      setRowBusy(null);
    }
  }

  async function onRelease(allocation: PortfolioAllocation) {
    if (rowBusy) return;
    const ok = window.confirm(
      `Release allocation “${allocation.label}” (${formatUsdt(allocation.reservedSize)})? Reserved capital returns to available.`,
    );
    if (!ok) return;
    setRowBusy(allocation.id);
    setError(null);
    setStatus(null);
    try {
      const next = await releaseAllocation(allocation.id);
      onUpdated(next);
      setStatus(`Released “${allocation.label}”.`);
    } catch (err) {
      const apiErr = err as PortfolioApiError;
      setError(apiErr.message ?? "Could not release allocation");
    } finally {
      setRowBusy(null);
    }
  }

  return (
    <div className="portfolio-allocations" data-testid="portfolio-allocations">
      <button
        type="button"
        className="allocation-toggle"
        onClick={() => setOpen((value) => !value)}
        aria-expanded={open}
        data-testid="allocation-toggle"
      >
        Allocations {open ? "▾" : "▸"}
      </button>

      {open ? (
        <>
          <ul className="allocation-list" data-testid="allocation-list">
            {snapshot.allocations.length === 0 ? (
              <li className="note">No allocations yet.</li>
            ) : (
              snapshot.allocations.map((allocation) => (
                <li
                  key={allocation.id}
                  className="allocation-card"
                  data-testid={`allocation-card-${allocation.id}`}
                >
                  <div className="allocation-card__header">
                    <strong data-testid={`allocation-label-${allocation.id}`}>
                      {allocation.label}
                    </strong>
                  </div>
                  <p data-testid={`allocation-reserved-${allocation.id}`}>
                    Reserved: {formatUsdt(allocation.reservedSize)}
                  </p>
                  <p data-testid={`allocation-target-${allocation.id}`}>
                    Target: {allocation.targetRef ?? "—"}
                  </p>
                  <div className="allocation-card__actions">
                    <label htmlFor={`resize-${allocation.id}`}>
                      Resize (USDT)
                      <input
                        id={`resize-${allocation.id}`}
                        inputMode="decimal"
                        value={resizeDrafts[allocation.id] ?? allocation.reservedSize}
                        onChange={(e) =>
                          setResizeDrafts((prev) => ({
                            ...prev,
                            [allocation.id]: e.target.value,
                          }))
                        }
                        disabled={rowBusy === allocation.id}
                        data-testid={`resize-input-${allocation.id}`}
                      />
                    </label>
                    <button
                      type="button"
                      disabled={rowBusy === allocation.id}
                      onClick={() => void onResize(allocation)}
                      data-testid={`resize-btn-${allocation.id}`}
                    >
                      {rowBusy === allocation.id ? "Working…" : "Resize"}
                    </button>
                    <button
                      type="button"
                      className="danger"
                      disabled={rowBusy === allocation.id}
                      onClick={() => void onRelease(allocation)}
                      data-testid={`release-btn-${allocation.id}`}
                    >
                      Release
                    </button>
                  </div>
                </li>
              ))
            )}
          </ul>

          <form className="allocation-create" onSubmit={onCreate} data-testid="allocation-create">
            <h3>Create allocation</h3>
            <label htmlFor="alloc-label">
              Label
              <input
                id="alloc-label"
                value={label}
                onChange={(e) => setLabel(e.target.value)}
                disabled={busy}
                required
                data-testid="alloc-label-input"
              />
            </label>
            <label htmlFor="alloc-size">
              Reserved size (USDT)
              <input
                id="alloc-size"
                inputMode="decimal"
                value={reservedSize}
                onChange={(e) => setReservedSize(e.target.value)}
                disabled={busy}
                required
                data-testid="alloc-size-input"
              />
            </label>
            <label htmlFor="alloc-target">
              Target ref (optional)
              <input
                id="alloc-target"
                value={targetRef}
                onChange={(e) => setTargetRef(e.target.value)}
                disabled={busy}
                data-testid="alloc-target-input"
              />
            </label>
            {error ? (
              <p className="form-error" role="alert" data-testid="allocation-error">
                {error}
              </p>
            ) : null}
            {status ? (
              <p className="form-status" data-testid="allocation-status">
                {status}
              </p>
            ) : null}
            <button type="submit" disabled={busy} data-testid="alloc-create-submit">
              {busy ? "Creating…" : "Create allocation"}
            </button>
          </form>
        </>
      ) : null}
    </div>
  );
}
