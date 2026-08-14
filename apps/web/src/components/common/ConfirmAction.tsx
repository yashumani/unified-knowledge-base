import { useEffect, useState } from "react";

/**
 * Two-stage inline confirmation.
 *
 * Inline rather than a modal: a dialog would need a hand-rolled focus trap,
 * and this project ships no UI library to provide one.
 */
export function ConfirmAction({
  label,
  confirmLabel,
  tone = "primary",
  disabled = false,
  disabledReason,
  onConfirm
}: {
  label: string;
  confirmLabel: string;
  tone?: "primary" | "secondary";
  disabled?: boolean;
  disabledReason?: string;
  onConfirm: () => void;
}) {
  const [armed, setArmed] = useState(false);

  useEffect(() => {
    if (!armed) return;
    const timer = window.setTimeout(() => setArmed(false), 4000);
    return () => window.clearTimeout(timer);
  }, [armed]);

  useEffect(() => {
    if (disabled) setArmed(false);
  }, [disabled]);

  if (armed) {
    return (
      <span className="confirm-pair">
        <button type="button" className="confirm-yes" onClick={() => { setArmed(false); onConfirm(); }}>
          {confirmLabel}
        </button>
        <button type="button" className="secondary" onClick={() => setArmed(false)}>
          Cancel
        </button>
      </span>
    );
  }

  return (
    <button
      type="button"
      className={tone === "secondary" ? "secondary" : undefined}
      disabled={disabled}
      title={disabled ? disabledReason : undefined}
      onClick={() => setArmed(true)}
    >
      {label}
    </button>
  );
}
