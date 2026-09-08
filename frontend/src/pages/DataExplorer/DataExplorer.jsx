// src/pages/DataExplorer/DataExplorer.jsx
import { useState } from "react";
import { useFetch } from "../../hooks/useFetch";
import { dataService } from "../../services/dataService";
import Loading from "../../components/Loading/Loading";
import ErrorMessage from "../../components/ErrorMessage/ErrorMessage";
import FilterBar from "../../components/FilterBar/FilterBar";
import DataTable from "../../components/DataTable/DataTable";
import Pagination from "../../components/Pagination/Pagination";
import ExportButtons from "../../components/ExportButtons/ExportButtons";
import { DEFAULT_PAGE_SIZE } from "../../utils/constants";

export default function DataExplorer() {
  const [page, setPage] = useState(1);
  const [query, setQuery] = useState({ search: "", sort: "-created_at", filters: {} });
  const [selectedIds, setSelectedIds] = useState(new Set());

  const { data, loading, error, refetch } = useFetch(
    () => dataService.list({ page, pageSize: DEFAULT_PAGE_SIZE, ...query }),
    [page, query]
  );

  const handleFilterChange = (next) => {
    setPage(1);
    setSelectedIds(new Set());
    setQuery(next);
  };

  const toggleSelect = (id) => {
    setSelectedIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  const toggleSelectAll = (checked) => {
    setSelectedIds((prev) => {
      const next = new Set(prev);
      const rows = data?.results || [];
      if (checked) rows.forEach((r) => next.add(r.id));
      else rows.forEach((r) => next.delete(r.id));
      return next;
    });
  };

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-lg font-semibold text-slate-800">Data Explorer</h1>
        <ExportButtons selectedIds={[...selectedIds]} />
      </div>

      <FilterBar value={query} onChange={handleFilterChange} disabled={loading} />

      {error && <ErrorMessage error={error} onRetry={refetch} />}
      {loading ? (
        <Loading label="Loading customer records..." />
      ) : (
        <div className="card space-y-3">
          <DataTable
            rows={data?.results}
            selectedIds={selectedIds}
            onToggleSelect={toggleSelect}
            onToggleSelectAll={toggleSelectAll}
          />
          <Pagination
            page={data?.page}
            totalPages={data?.total_pages}
            count={data?.count}
            onPageChange={setPage}
          />
        </div>
      )}
    </div>
  );
}
