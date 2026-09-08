// src/components/ErrorMessage/ErrorMessage.jsx
export default function ErrorMessage({ error, onRetry }) {
  if (!error) return null;
  const message = typeof error === "string" ? error : error.message || "Something went wrong.";
  return (
    <div className="card border-red-200 bg-red-50 flex items-start justify-between gap-4">
      <div>
        <p className="text-sm font-medium text-red-700">Error</p>
        <p className="text-sm text-red-600">{message}</p>
      </div>
      {onRetry && (
        <button className="btn-secondary" onClick={onRetry}>
          Retry
        </button>
      )}
    </div>
  );
}
