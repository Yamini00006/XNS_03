// src/pages/CustomerDetails/CustomerDetails.jsx
import { useParams } from "react-router-dom";
import { useFetch } from "../../hooks/useFetch";
import { dataService } from "../../services/dataService";
import Loading from "../../components/Loading/Loading";
import ErrorMessage from "../../components/ErrorMessage/ErrorMessage";
import BackButton from "../../components/BackButton/BackButton";
import RawDataViewer from "../../components/RawDataViewer/RawDataViewer";
import { formatDateTime } from "../../utils/formatters";

export default function CustomerDetails() {
  const { customerId } = useParams();

  const { data: customer, loading, error, refetch } = useFetch(
    () => dataService.get(customerId),
    [customerId]
  );
  const { data: raw, loading: rawLoading } = useFetch(() => dataService.raw(customerId), [customerId]);

  return (
    <div className="max-w-2xl space-y-4">
      <BackButton label="Back to Data Explorer" fallback="/data" />
      <h1 className="text-lg font-semibold text-slate-800">Customer #{customerId}</h1>

      {error && <ErrorMessage error={error} onRetry={refetch} />}
      {loading && <Loading label="Loading customer..." />}

      {customer && (
        <div className="card">
          <dl className="grid grid-cols-2 gap-3 text-sm">
            <dt className="text-slate-500">Full name</dt>
            <dd>{customer.full_name || "—"}</dd>
            <dt className="text-slate-500">Email</dt>
            <dd>{customer.email || "—"}</dd>
            <dt className="text-slate-500">Phone</dt>
            <dd>{customer.phone || "—"}</dd>
            <dt className="text-slate-500">Address</dt>
            <dd>
              {[customer.address_line1, customer.address_line2, customer.city, customer.state, customer.postal_code, customer.country]
                .filter(Boolean)
                .join(", ") || "—"}
            </dd>
            <dt className="text-slate-500">Sources</dt>
            <dd>{customer.source_count}</dd>
            <dt className="text-slate-500">Duplicate?</dt>
            <dd>{customer.is_duplicate ? "Yes" : "No"}</dd>
            <dt className="text-slate-500">Created</dt>
            <dd>{formatDateTime(customer.created_at)}</dd>
            <dt className="text-slate-500">Updated</dt>
            <dd>{formatDateTime(customer.updated_at)}</dd>
          </dl>
        </div>
      )}

      <div>
        <h2 className="mb-2 text-sm font-semibold text-slate-700">Raw Source Data</h2>
        {rawLoading ? <Loading label="Loading raw sources..." /> : <RawDataViewer sources={raw?.sources} />}
      </div>
    </div>
  );
}
