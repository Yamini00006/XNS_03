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

function BatchProcessingDetail() {
  const params = new URLSearchParams(
    window.location.search
  );

  const rawJobIds =
    params.get("job_ids") || "";

  const jobIds = rawJobIds
    .split(",")
    .map((value) => Number(value))
    .filter(
      (value) =>
        Number.isInteger(value) &&
        value > 0
    );

  const {
    data,
    loading,
    error,
  } = usePolling(
    () =>
      processingService.batchStatus(
        jobIds
      ),
    {
      intervalMs: 3000,

      isDone: (result) =>
        result?.status ===
          "Completed" ||
        result?.status ===
          "Failed",
    }
  );

  if (
    !jobIds.length
  ) {
    return (
      <ErrorMessage
        error={
          "No valid processing jobs were supplied."
        }
      />
    );
  }

  if (
    loading &&
    !data
  ) {
    return (
      <Loading label="Starting batch processing..." />
    );
  }

  return (
    <div className="space-y-4">

      <BackButton
        label="Back to Processing"
        fallback="/processing"
      />

      <div>
        <h1 className="text-lg font-semibold text-slate-800">
          Batch Processing
        </h1>

        <p className="mt-1 text-sm text-slate-500">
          Processing {data?.total || jobIds.length} customer
          data files together.
        </p>
      </div>

      {error && (
        <ErrorMessage error={error} />
      )}

      {data && (
        <div className="card space-y-4">

          <div className="grid grid-cols-2 gap-3 md:grid-cols-4">

            <div>
              <p className="text-xs text-slate-500">
                Total
              </p>

              <p className="text-xl font-semibold">
                {data.total}
              </p>
            </div>

            <div>
              <p className="text-xs text-slate-500">
                Completed
              </p>

              <p className="text-xl font-semibold text-green-700">
                {data.completed}
              </p>
            </div>

            <div>
              <p className="text-xs text-slate-500">
                Running
              </p>

              <p className="text-xl font-semibold">
                {data.running}
              </p>
            </div>

            <div>
              <p className="text-xs text-slate-500">
                Failed
              </p>

              <p className="text-xl font-semibold text-red-700">
                {data.failed}
              </p>
            </div>

          </div>

          <div>
            <p className="text-sm font-medium text-slate-700">
              Overall status
            </p>

            <p className="mt-1 text-sm">
              {data.status}
            </p>
          </div>

          <div className="divide-y divide-slate-100">

            {data.jobs.map(
              (job) => (
                <div
                  key={job.id}
                  className="flex items-center justify-between py-3 text-sm"
                >

                  <div>
                    <p className="font-medium">
                      Job #{job.id}
                    </p>

                    <p className="text-xs text-slate-500">
                      File #{job.upload_file_id}
                    </p>
                  </div>

                  <StatusBadge
                    status={job.status}
                  />

                </div>
              )
            )}

          </div>

          {data.status ===
            "Completed" && (
            <div className="rounded-md bg-green-50 px-3 py-3 text-sm text-green-700">
              All files were processed and
              customer records were merged into
              the unified dataset.
            </div>
          )}

          {data.status ===
            "Failed" && (
            <div className="rounded-md bg-red-50 px-3 py-3 text-sm text-red-700">
              One or more files failed during
              processing. Check the individual
              processing jobs for details.
            </div>
          )}

        </div>
      )}

    </div>
  );
}
export default function Processing() {
  const { jobId } = useParams();

  const isBatch =
    window.location.pathname ===
    "/processing/batch";

  if (isBatch) {
    return <BatchProcessingDetail />;
  }

  return jobId ? (
    <ProcessingDetail jobId={jobId} />
  ) : (
    <ProcessingList />
  );
}
