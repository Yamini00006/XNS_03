// src/pages/Processing/Processing.jsx
import { useParams } from "react-router-dom";
import { Link } from "react-router-dom";
import { useFetch } from "../../hooks/useFetch";
import { usePolling } from "../../hooks/usePolling";
import { processingService } from "../../services/processingService";
import Loading from "../../components/Loading/Loading";
import ErrorMessage from "../../components/ErrorMessage/ErrorMessage";
import ProcessingStatus, {
  StatusBadge,
} from "../../components/ProcessingStatus/ProcessingStatus";
import BackButton from "../../components/BackButton/BackButton";
import { TERMINAL_STATUSES } from "../../utils/constants";
import { formatDateTime } from "../../utils/formatters";

function ProcessingList() {
  const {
    data,
    loading,
    error,
    refetch,
  } = useFetch(
    () => processingService.list({ pageSize: 50 }),
    []
  );

  if (loading) {
    return <Loading label="Loading processing jobs..." />;
  }

  if (error) {
    return (
      <ErrorMessage
        error={error}
        onRetry={refetch}
      />
    );
  }

  const jobs = data?.results || [];

  return (
    <div className="space-y-4">
      <h1 className="text-lg font-semibold text-slate-800">
        Processing Jobs
      </h1>

      {jobs.length === 0 ? (
        <p className="card text-sm text-slate-500">
          No processing jobs yet. Upload a file to get started.
        </p>
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
                <span className="text-slate-400">
                  {formatDateTime(job.started_at)}
                </span>

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
  const {
    data: job,
    error,
  } = usePolling(
    () => processingService.get(jobId),
    {
      intervalMs: 3000,

      isDone: (result) =>
        TERMINAL_STATUSES.includes(
          result?.status
        ),
    }
  );

  return (
    <div className="max-w-xl space-y-4">
      <BackButton
        label="Back to Processing"
        fallback="/processing"
      />

      <h1 className="text-lg font-semibold text-slate-800">
        Processing Job #{jobId}
      </h1>

      {error && (
        <ErrorMessage error={error} />
      )}

      {!job && !error ? (
        <Loading label="Loading job status..." />
      ) : (
        <ProcessingStatus job={job} />
      )}
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

      /*
       * The batch-status API does not return
       * a top-level "status" field.
       *
       * It returns:
       * total
       * completed
       * failed
       * running
       * queued
       * results
       */
      isDone: (result) => {
        if (!result) {
          return false;
        }

        const total = Number(
          result.total || 0
        );

        const completed = Number(
          result.completed || 0
        );

        const failed = Number(
          result.failed || 0
        );

        const running = Number(
          result.running || 0
        );

        const queued = Number(
          result.queued || 0
        );

        return (
          total > 0 &&
          completed + failed === total &&
          running === 0 &&
          queued === 0
        );
      },
    }
  );

  if (!jobIds.length) {
    return (
      <ErrorMessage
        error={
          "No valid processing jobs were supplied."
        }
      />
    );
  }

  if (loading && !data) {
    return (
      <Loading
        label="Starting batch processing..."
      />
    );
  }

  /*
   * The backend returns the jobs inside
   * "results", not "jobs".
   *
   * Always fall back to an empty array so
   * the UI can never crash because of
   * .map() on undefined.
   */
  const jobs = Array.isArray(
    data?.results
  )
    ? data.results
    : [];

  const total =
    Number(data?.total || 0);

  const completed =
    Number(data?.completed || 0);

  const failed =
    Number(data?.failed || 0);

  const running =
    Number(data?.running || 0);

  const queued =
    Number(data?.queued || 0);

  /*
   * Calculate the overall batch status
   * because the API response does not
   * contain data.status.
   */
  let overallStatus = "Queued";

  if (
    completed + failed === total &&
    total > 0
  ) {
    if (failed > 0) {
      overallStatus = "Failed";
    } else {
      overallStatus = "Completed";
    }
  } else if (running > 0) {
    overallStatus = "Running";
  } else if (queued > 0) {
    overallStatus = "Queued";
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
          Processing{" "}
          {total || jobIds.length} files
          together.
        </p>
      </div>

      {error && (
        <ErrorMessage error={error} />
      )}

      {data && (
        <div className="card space-y-4">
          {/* Batch summary */}
          <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
            <div>
              <p className="text-xs text-slate-500">
                Total
              </p>

              <p className="text-xl font-semibold">
                {total}
              </p>
            </div>

            <div>
              <p className="text-xs text-slate-500">
                Completed
              </p>

              <p className="text-xl font-semibold text-green-700">
                {completed}
              </p>
            </div>

            <div>
              <p className="text-xs text-slate-500">
                Running
              </p>

              <p className="text-xl font-semibold">
                {running}
              </p>
            </div>

            <div>
              <p className="text-xs text-slate-500">
                Failed
              </p>

              <p className="text-xl font-semibold text-red-700">
                {failed}
              </p>
            </div>
          </div>

          {/* Overall status */}
          <div>
            <p className="text-sm font-medium text-slate-700">
              Overall status
            </p>

            <div className="mt-1">
              <StatusBadge
                status={overallStatus}
              />
            </div>
          </div>

          {/* Individual jobs */}
          <div>
            <p className="mb-2 text-sm font-medium text-slate-700">
              Processing Jobs
            </p>

            <div className="divide-y divide-slate-100">
              {jobs.length === 0 ? (
                <p className="py-3 text-sm text-slate-500">
                  No processing jobs available.
                </p>
              ) : (
                jobs.map((job) => (
                  <div
                    key={job.id}
                    className="flex items-center justify-between py-3 text-sm"
                  >
                    <div>
                      <p className="font-medium">
                        Job #{job.id}
                      </p>

                      <p className="text-xs text-slate-500">
                        File #
                        {job.upload_file_id}
                      </p>
                    </div>

                    <StatusBadge
                      status={job.status}
                    />
                  </div>
                ))
              )}
            </div>
          </div>

          {/* Completed message */}
          {overallStatus ===
            "Completed" && (
            <div className="rounded-md bg-green-50 px-3 py-3 text-sm text-green-700">
              All files were processed
              successfully and the resulting
              records were merged into the
              unified dataset for this processing
              batch.
            </div>
          )}

          {/* Failed message */}
          {overallStatus ===
            "Failed" && (
            <div className="rounded-md bg-red-50 px-3 py-3 text-sm text-red-700">
              One or more files failed during
              processing. Check the individual
              processing jobs for details.
            </div>
          )}

          {/* Running message */}
          {overallStatus ===
            "Running" && (
            <div className="rounded-md bg-blue-50 px-3 py-3 text-sm text-blue-700">
              The files are currently being
              processed. This page will update
              automatically.
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