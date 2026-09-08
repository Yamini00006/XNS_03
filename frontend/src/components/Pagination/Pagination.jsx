// src/components/Pagination/Pagination.jsx

/**
 * Purely reflects the backend's own pagination envelope
 * ({count, page, page_size, total_pages}) — never invents page bounds.
 */
export default function Pagination({ page, totalPages, count, onPageChange }) {
  if (!totalPages || totalPages <= 1) return null;

  const goTo = (p) => {
    if (p < 1 || p > totalPages || p === page) return;
    onPageChange(p);
  };

  return (
    <div className="flex items-center justify-between border-t border-slate-200 pt-3 text-sm">
      <span className="text-slate-500">
        Page {page} of {totalPages} ({count} total)
      </span>
      <div className="flex gap-2">
        <button className="btn-secondary" disabled={page <= 1} onClick={() => goTo(page - 1)}>
          Previous
        </button>
        <button className="btn-secondary" disabled={page >= totalPages} onClick={() => goTo(page + 1)}>
          Next
        </button>
      </div>
    </div>
  );
}
