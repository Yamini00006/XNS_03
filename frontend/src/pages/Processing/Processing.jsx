// src/pages/Processing/Processing.jsx
import { useParams, Link } from "react-router-dom";
import { useFetch } from "../../hooks/useFetch";
import { usePolling } from "../../hooks/usePolling";
import { processingService } from "../../services/processingService";
import Loading from "../../components/Loading/Loading";
import ErrorMessage from "../../components/ErrorMessage/ErrorMessage";
import ProcessingStatus, { StatusBadge } from "../../components/ProcessingStatus/ProcessingStatus";
import BackButton from "../../components/BackButton/BackButton";
import { TERMINAL_STATUSES } from "../../utils/constants";
import { formatDateTime } from "../../utils/formatters";

function ProcessingList() {
  const { data, loading, error, refetch } = useFetch(() => processingService.list({ pageSize: 50 }), []);

  if (loading) return <Loading label="Loading processing jobs..." />;
  if (error) return <ErrorMessage error={error} onRetry={refetch} />;

  const jobs = data?.results || [];

  return (
    <div className="space-y-4">
      <h1 className="text-lg font-semibold text-slate-800">Processing Jobs</h1>
      {jobs.length === 0 ? (
        <p className="card text-sm text-slate-500">No processing jobs yet. Upload a file to get started.</p>
      ) : (
        <div className="card divide-y divide-slate-100 p-0">
          {jobs.map((job) => (
            <Link
              key={job.id}
              to={`/processing/${job.id}`}
              className="flex items-center justify-between px-4 py-3 text-sm hover:bg-slate-50"
            >
              <span>
                Job #{job.id} — File #{job.upload_file_id}
              </span>
              <span className="flex items-center gap-3">
                <span className="text-slate-400">{formatDateTime(job.started_at)}</span>
                <StatusBadge status={job.status} />
              </span>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}

function ProcessingDetail({ jobId }) {
  const { data: job, error } = usePolling(() => processingService.get(jobId), {
    intervalMs: 3000,
    isDone: (result) => TERMINAL_STATUSES.includes(result?.status),
  });

  return (
    <div className="max-w-xl space-y-4">
      <BackButton label="Back to Processing" fallback="/processing" />
      <h1 className="text-lg font-semibold text-slate-800">Processing Job #{jobId}</h1>
      {error && <ErrorMessage error={error} />}
      {!job && !error ? <Loading label="Loading job status..." /> : <ProcessingStatus job={job} />}
    </div>
  );
}

export default function Processing() {
  const { jobId } = useParams();
  return jobId ? <ProcessingDetail jobId={jobId} /> : <ProcessingList />;
}
