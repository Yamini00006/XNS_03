// src/components/FilterBar/FilterBar.jsx
import { useState } from "react";
import { DATA_SORT_FIELDS } from "../../utils/constants";

export default function FilterBar({ value, onChange, disabled }) {
  const [search, setSearch] = useState(value.search || "");
  const [city, setCity] = useState(value.filters?.city || "");
  const [isDuplicate, setIsDuplicate] = useState(value.filters?.is_duplicate || "");
  const [sort, setSort] = useState(value.sort || "-created_at");
  const [error, setError] = useState("");

  const apply = (e) => {
    e.preventDefault();
    if (disabled) return; // prevent duplicate submissions while a request is in flight

    const trimmedSearch = search.trim();
    const trimmedCity = city.trim();

    if (search && !trimmedSearch) {
      setError("Search cannot be just whitespace.");
      return;
    }
    setError("");

    onChange({
      search: trimmedSearch,
      sort,
      filters: {
        ...(trimmedCity ? { city: trimmedCity } : {}),
        ...(isDuplicate ? { is_duplicate: isDuplicate } : {}),
      },
    });
  };

  return (
    <form onSubmit={apply} className="card grid grid-cols-1 gap-3 sm:grid-cols-4">
      <div className="sm:col-span-2">
        <label className="label">Search</label>
        <input
          className={`input ${error ? "input-error" : ""}`}
          placeholder="Name, email, phone, city..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
        />
        {error && <p className="field-error">{error}</p>}
      </div>

      <div>
        <label className="label">City</label>
        <input className="input" value={city} onChange={(e) => setCity(e.target.value)} placeholder="e.g. Austin" />
      </div>

      <div>
        <label className="label">Duplicate?</label>
        <select className="input" value={isDuplicate} onChange={(e) => setIsDuplicate(e.target.value)}>
          <option value="">Any</option>
          <option value="true">Duplicates only</option>
          <option value="false">Unique only</option>
        </select>
      </div>

      <div className="sm:col-span-3">
        <label className="label">Sort by</label>
        <select className="input" value={sort} onChange={(e) => setSort(e.target.value)}>
          {DATA_SORT_FIELDS.map((opt) => (
            <option key={opt.value} value={opt.value}>
              {opt.label}
            </option>
          ))}
        </select>
      </div>

      <div className="flex items-end">
        <button type="submit" className="btn-primary w-full" disabled={disabled}>
          {disabled ? "Applying..." : "Apply"}
        </button>
      </div>
    </form>
  );
}
