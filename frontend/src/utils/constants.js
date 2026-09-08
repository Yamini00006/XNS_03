// src/utils/constants.js
// Values here mirror the ACTUAL backend contract (backend/apps/*) —
// do not add formats/statuses the API doesn't support.

export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

// Matches database.schema.models.FileFormat via backend/apps/files/validators.py
export const SUPPORTED_FILE_EXTENSIONS = [".csv", ".json", ".ndjson", ".xlsx", ".xml", ".pdf"];
export const SUPPORTED_FILE_ACCEPT = SUPPORTED_FILE_EXTENSIONS.join(",");

// Matches apps/processing/services.STATUS_DISPLAY
export const JOB_STATUSES = ["Queued", "Running", "Completed", "Failed"];
export const TERMINAL_STATUSES = ["Completed", "Failed"];

export const STATUS_COLORS = {
  Queued: "bg-slate-100 text-slate-700",
  Running: "bg-blue-100 text-blue-700",
  Completed: "bg-green-100 text-green-700",
  Failed: "bg-red-100 text-red-700",
};

export const DEFAULT_PAGE_SIZE = 20;
export const MAX_PAGE_SIZE = 200;

// Matches common/query_params.py in apps/data
export const DATA_SORT_FIELDS = [
  { value: "-created_at", label: "Newest first" },
  { value: "created_at", label: "Oldest first" },
  { value: "email", label: "Email (A–Z)" },
  { value: "-email", label: "Email (Z–A)" },
  { value: "full_name", label: "Name (A–Z)" },
  { value: "-full_name", label: "Name (Z–A)" },
  { value: "-source_count", label: "Most sources" },
];

export const ACCESS_TOKEN_KEY = "cdp_access_token";
export const REFRESH_TOKEN_KEY = "cdp_refresh_token";
