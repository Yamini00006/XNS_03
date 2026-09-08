// src/components/DataTable/DataTable.jsx
import { useNavigate } from "react-router-dom";

const COLUMNS = [
  { key: "id", label: "ID" },
  { key: "full_name", label: "Name" },
  { key: "email", label: "Email" },
  { key: "phone", label: "Phone" },
  { key: "city", label: "City" },
  { key: "source_count", label: "Sources" },
  { key: "is_duplicate", label: "Duplicate?" },
];

export default function DataTable({ rows, selectedIds, onToggleSelect, onToggleSelectAll }) {
  const navigate = useNavigate();

  if (!rows || rows.length === 0) {
    return <p className="py-8 text-center text-sm text-slate-500">No customer records found.</p>;
  }

  const allSelected = rows.length > 0 && rows.every((r) => selectedIds?.has(r.id));

  return (
    <div className="overflow-x-auto">
      <table className="min-w-full divide-y divide-slate-200 text-sm">
        <thead>
          <tr>
            <th className="px-3 py-2">
              <input type="checkbox" checked={allSelected} onChange={(e) => onToggleSelectAll?.(e.target.checked)} />
            </th>
            {COLUMNS.map((col) => (
              <th key={col.key} className="px-3 py-2 text-left font-medium text-slate-500">
                {col.label}
              </th>
            ))}
          </tr>
        </thead>
        <tbody className="divide-y divide-slate-100">
          {rows.map((row) => (
            <tr key={row.id} className="hover:bg-slate-50">
              <td className="px-3 py-2">
                <input
                  type="checkbox"
                  checked={!!selectedIds?.has(row.id)}
                  onChange={() => onToggleSelect?.(row.id)}
                />
              </td>
              {COLUMNS.map((col) => (
                <td
                  key={col.key}
                  className="cursor-pointer px-3 py-2 text-slate-700"
                  onClick={() => navigate(`/data/${row.id}`)}
                >
                  {col.key === "is_duplicate" ? (row[col.key] ? "Yes" : "No") : row[col.key] ?? "—"}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
