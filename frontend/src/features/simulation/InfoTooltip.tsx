import {
  useCallback,
  useEffect,
  useId,
  useRef,
  useState,
  type KeyboardEvent,
  type MouseEvent,
} from "react";
import { CircleHelp } from "lucide-react";

interface Props {
  /** Short field name used in the accessible button label. */
  label: string;
  /** Short beginner-friendly explanation. */
  text: string;
  testId?: string;
}

function supportsHover(): boolean {
  if (typeof window === "undefined" || typeof window.matchMedia !== "function") {
    return true;
  }
  return window.matchMedia("(hover: hover) and (pointer: fine)").matches;
}

/**
 * Compact help icon for non-obvious Auto Trading labels.
 * Desktop: hover + keyboard focus. Mobile: tap. UI-only — no trading side effects.
 */
export function InfoTooltip({ label, text, testId }: Props) {
  const tipId = useId();
  const rootRef = useRef<HTMLSpanElement>(null);
  const [open, setOpen] = useState(false);
  const [pinned, setPinned] = useState(false);

  const close = useCallback(() => {
    setOpen(false);
    setPinned(false);
  }, []);

  useEffect(() => {
    if (!open) return;

    function onPointerDown(event: PointerEvent) {
      if (!rootRef.current?.contains(event.target as Node)) {
        close();
      }
    }

    function onKeyDown(event: globalThis.KeyboardEvent) {
      if (event.key === "Escape") {
        close();
      }
    }

    document.addEventListener("pointerdown", onPointerDown);
    document.addEventListener("keydown", onKeyDown);
    return () => {
      document.removeEventListener("pointerdown", onPointerDown);
      document.removeEventListener("keydown", onKeyDown);
    };
  }, [open, close]);

  function handleClick(event: MouseEvent<HTMLButtonElement>) {
    event.preventDefault();
    event.stopPropagation();
    if (pinned) {
      close();
      return;
    }
    setPinned(true);
    setOpen(true);
  }

  function handleKeyDown(event: KeyboardEvent<HTMLButtonElement>) {
    if (event.key === "Escape") {
      event.stopPropagation();
      close();
    }
  }

  return (
    <span className="info-tooltip" ref={rootRef} data-testid={testId}>
      <button
        type="button"
        className="info-tooltip__trigger"
        aria-label={`About ${label}`}
        aria-expanded={open}
        aria-controls={tipId}
        onClick={handleClick}
        onKeyDown={handleKeyDown}
        onMouseEnter={() => {
          if (supportsHover()) setOpen(true);
        }}
        onMouseLeave={() => {
          if (supportsHover() && !pinned) setOpen(false);
        }}
        onFocus={() => setOpen(true)}
        onBlur={(event) => {
          if (!rootRef.current?.contains(event.relatedTarget as Node)) {
            close();
          }
        }}
      >
        <CircleHelp className="info-tooltip__icon" aria-hidden="true" />
      </button>
      {open ? (
        <span
          id={tipId}
          role="tooltip"
          className="info-tooltip__bubble"
          data-testid={testId ? `${testId}-bubble` : undefined}
        >
          {text}
        </span>
      ) : null}
    </span>
  );
}
