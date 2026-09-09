// src/components/ProcessingStatus/ProcessingStatus.jsx
import { STATUS_COLORS } from "../../utils/constants";
import { formatDuration, formatDateTime } from "../../utils/formatters";

export function StatusBadge({ status }) {
  const classes = STATUS_COLORS[status] || "bg-slate-100 text-slate-700";
  return <span className={`inline-block rounded-full px-2.5 py-0.5 text-xs font-medium ${classes}`}>{status}</span>;
}

export default function ProcessingStatus({ job }) {
  if (!job) return null;
  return (
    <div className="card space-y-3">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-semibold text-slate-700">Job #{job.id}</h3>
        <StatusBadge status={job.status} />
      </div>

      <dl className="grid grid-cols-2 gap-3 text-sm">
        <div>
          <dt className="text-slate-500">Started</dt>
          <dd>{formatDateTime(job.started_at)}</dd>
        </div>
        <div>
          <dt className="text-slate-500">Completed</dt>
          <dd>{formatDateTime(job.completed_at)}</dd>
        </div>
        <div>
          <dt className="text-slate-500">Duration</dt>
          <dd>{formatDuration(job.duration_seconds)}</dd>
        </div>
        <div>
          <dt className="text-slate-500">Rows extracted</dt>
          <dd>{job.rows_extracted ?? "—"}</dd>
        </div>
        <div>
          <dt className="text-slate-500">Valid rows</dt>
          <dd>{job.rows_valid ?? "—"}</dd>
        </div>
        <div>
          <dt className="text-slate-500">Invalid rows</dt>
          <dd>{job.rows_invalid ?? "—"}</dd>
        </div>
        <div>
          <dt className="text-slate-500">Merged rows</dt>
          <dd>{job.rows_merged ?? "—"}</dd>
        </div>
      </dl>

      {job.status === "Failed" && job.error_message && (
        <div className="rounded-md bg-red-50 px-3 py-2 text-sm text-red-700">{job.error_message}</div>
      )}
    </div>
  );
}
