// src/services/dataService.js
import { api } from "./api";

export const dataService = {
  list: ({
    page = 1,
    pageSize = 20,
    search,
    sort,
    filters = {},
  } = {}) =>
    api
      .get("/api/data/", {
        params: {
          page,
          page_size: pageSize,
          ...(search ? { search } : {}),
          ...(sort ? { sort } : {}),
          ...filters,
        },
      })
      .then((r) => r.data),

  get: (id) =>
    api
      .get(`/api/data/${id}/`)
      .then((r) => r.data),

  raw: (id) =>
    api
      .get(`/api/data/${id}/raw/`)
      .then((r) => r.data),
};