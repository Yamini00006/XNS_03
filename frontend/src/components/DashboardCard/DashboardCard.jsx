// src/components/DashboardCard/DashboardCard.jsx
export default function DashboardCard({ label, value, sublabel, accent = "text-slate-800" }) {
  return (
    <div className="card">
      <p className="text-xs font-medium uppercase tracking-wide text-slate-500">{label}</p>
      <p className={`mt-1 text-2xl font-semibold ${accent}`}>{value ?? "—"}</p>
      {sublabel && <p className="mt-1 text-xs text-slate-400">{sublabel}</p>}
    </div>
  );
}
