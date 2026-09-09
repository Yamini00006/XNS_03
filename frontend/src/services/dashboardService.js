// src/services/dashboardService.js
import { api } from "./api";

export const dashboardService = {
  metrics: () => api.get("/api/dashboard/metrics/").then((r) => r.data),
};
