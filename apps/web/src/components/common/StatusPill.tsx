import { formatStatus, statusTone } from "../../utils/format";

export function StatusPill({ status }: { status: string }) {
  return <span className={`status-pill tone-${statusTone(status)}`}>{formatStatus(status)}</span>;
}
