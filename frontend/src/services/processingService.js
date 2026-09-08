// src/services/processingService.js
import { api } from "./api";

export const processingService = {
  start: (fileId) => api.post(`/api/processing/${fileId}/start/`).then((r) => r.data),

  get: (jobId) => api.get(`/api/processing/${jobId}/`).then((r) => r.data),

  list: ({ page = 1, pageSize = 20, status, uploadFileId } = {}) =>
    api
      .get("/api/processing/", {
        params: {
          page,
          page_size: pageSize,
          ...(status ? { status } : {}),
          ...(uploadFileId ? { upload_file_id: uploadFileId } : {}),
        },
      })
      .then((r) => r.data),

  errors: (jobId, { page = 1, pageSize = 20 } = {}) =>
    api
      .get(`/api/processing/${jobId}/errors/`, { params: { page, page_size: pageSize } })
      .then((r) => r.data),
};
