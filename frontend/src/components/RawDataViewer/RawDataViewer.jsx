// src/components/RawDataViewer/RawDataViewer.jsx

export default function RawDataViewer({ sources }) {
  if (!sources || sources.length === 0) {
    return <p className="text-sm text-slate-500">No raw source data available for this record.</p>;
  }

  return (
    <div className="space-y-4">
      {sources.map((s) => (
        <div key={s.id} className="card">
          <div className="mb-2 flex items-center justify-between text-xs text-slate-500">
            <span>Source row #{s.source_row_num ?? s.id} (job #{s.job_id})</span>
            <span className={s.is_valid ? "text-green-600" : "text-red-600"}>
              {s.is_valid ? "Valid" : "Invalid"}
            </span>
          </div>
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
            <div>
              <p className="mb-1 text-xs font-medium text-slate-500">Original fields</p>
              <pre className="max-h-48 overflow-auto rounded-md bg-slate-50 p-2 text-xs">
                {JSON.stringify(s.raw_data, null, 2)}
              </pre>
            </div>
            <div>
              <p className="mb-1 text-xs font-medium text-slate-500">Standardized fields</p>
              <pre className="max-h-48 overflow-auto rounded-md bg-slate-50 p-2 text-xs">
                {JSON.stringify(s.mapped_data, null, 2)}
              </pre>
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}
