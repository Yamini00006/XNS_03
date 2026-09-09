// src/pages/Dashboard/Dashboard.jsx
import { PieChart, Pie, Cell, Tooltip, ResponsiveContainer, Legend } from "recharts";
import { useFetch } from "../../hooks/useFetch";
import { dashboardService } from "../../services/dashboardService";
import Loading from "../../components/Loading/Loading";
import ErrorMessage from "../../components/ErrorMessage/ErrorMessage";
import DashboardCard from "../../components/DashboardCard/DashboardCard";
import { formatDuration, formatPercent } from "../../utils/formatters";

const STATUS_COLORS = ["#94a3b8", "#3b82f6", "#22c55e", "#ef4444"];

export default function Dashboard() {
  const { data, loading, error, refetch } = useFetch(() => dashboardService.metrics(), []);

  if (loading) return <Loading label="Loading dashboard metrics..." />;
  if (error) return <ErrorMessage error={error} onRetry={refetch} />;
  if (!data) return null;

  const jobChartData = [
    { name: "Queued", value: data.jobs.queued },
    { name: "Running", value: data.jobs.running },
    { name: "Completed", value: data.jobs.completed },
    { name: "Failed", value: data.jobs.failed },
  ].filter((d) => d.value > 0);

  return (
    <div className="space-y-6">
      <h1 className="text-lg font-semibold text-slate-800">Dashboard</h1>

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <DashboardCard label="Total Files" value={data.total_files} />
        <DashboardCard label="Completed Jobs" value={data.jobs.completed} accent="text-green-600" />
        <DashboardCard label="Failed Jobs" value={data.jobs.failed} accent="text-red-600" />
        <DashboardCard label="Avg Processing Time" value={formatDuration(data.average_processing_time_seconds)} />
        <DashboardCard label="Missing Data %" value={formatPercent(data.missing_data_percentage)} />
        <DashboardCard
          label="Validation Errors"
          value={data.validation_errors.errors}
          sublabel={`${data.validation_errors.warnings} warnings`}
        />
        <DashboardCard
          label="Duplicate Customers"
          value={data.duplicates.duplicate_customers}
          sublabel={`${data.duplicates.duplicate_rows_total} duplicate rows`}
        />
        <DashboardCard label="Total Customers" value={data.total_customers} />
      </div>

      {jobChartData.length > 0 && (
        <div className="card">
          <p className="mb-3 text-sm font-medium text-slate-600">Processing status breakdown</p>
          <ResponsiveContainer width="100%" height={260}>
            <PieChart>
              <Pie data={jobChartData} dataKey="value" nameKey="name" outerRadius={90} label>
                {jobChartData.map((entry, idx) => (
                  <Cell key={entry.name} fill={STATUS_COLORS[idx % STATUS_COLORS.length]} />
                ))}
              </Pie>
              <Tooltip />
              <Legend />
            </PieChart>
          </ResponsiveContainer>
        </div>
      )}
    </div>
  );
}
