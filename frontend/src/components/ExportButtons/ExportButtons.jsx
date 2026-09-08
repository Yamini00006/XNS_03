// src/components/ExportButtons/ExportButtons.jsx
import { useState } from "react";
import { exportService } from "../../services/exportService";

export default function ExportButtons({ selectedIds = [] }) {
  const [busy, setBusy] = useState(null);
  const [error, setError] = useState("");

  const run = async (format, fn) => {
    if (busy) return; // prevent duplicate submissions
    setBusy(format);
    setError("");
    try {
      await fn(selectedIds.length ? selectedIds : undefined);
    } catch (err) {
      setError(err.message || "Export failed.");
    } finally {
      setBusy(null);
    }
  };

  return (
    <div className="flex flex-wrap items-center gap-2">
      <span className="text-xs text-slate-500">
        {selectedIds.length > 0 ? `Export ${selectedIds.length} selected` : "Export full dataset"}:
      </span>
      <button className="btn-secondary" disabled={!!busy} onClick={() => run("csv", exportService.downloadCsv)}>
        {busy === "csv" ? "Exporting..." : "CSV"}
      </button>
      <button className="btn-secondary" disabled={!!busy} onClick={() => run("xlsx", exportService.downloadXlsx)}>
        {busy === "xlsx" ? "Exporting..." : "XLSX"}
      </button>
      <button className="btn-secondary" disabled={!!busy} onClick={() => run("json", exportService.downloadJson)}>
        {busy === "json" ? "Exporting..." : "JSON"}
      </button>
      {error && <span className="text-xs text-red-600">{error}</span>}
    </div>
  );
}
