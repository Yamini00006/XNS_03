// src/services/exportService.js
import { api } from "./api";

const FORMAT_CONFIG = {
  csv: { path: "/api/exports/csv/", filename: "customers_export.csv" },
  xlsx: { path: "/api/exports/xlsx/", filename: "customers_export.xlsx" },
  json: { path: "/api/exports/json/", filename: "customers_export.json" },
};

async function download(format, ids) {
  const config = FORMAT_CONFIG[format];
  if (!config) throw new Error(`Unsupported export format: ${format}`);

  const params = ids && ids.length ? { ids: ids.join(",") } : {};
  const response = await api.get(config.path, { params, responseType: "blob" });

  const url = window.URL.createObjectURL(new Blob([response.data]));
  const link = document.createElement("a");
  link.href = url;
  link.setAttribute("download", config.filename);
  document.body.appendChild(link);
  link.click();
  link.remove();
  window.URL.revokeObjectURL(url);
}

export const exportService = {
  downloadCsv: (ids) => download("csv", ids),
  downloadXlsx: (ids) => download("xlsx", ids),
  downloadJson: (ids) => download("json", ids),
};
