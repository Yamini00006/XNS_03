// src/services/fileService.js
import { api } from "./api";

export const fileService = {
  upload: (file, onProgress) => {
    const formData = new FormData();
    formData.append("file", file);
    return api
      .post("/api/files/upload/", formData, {
        headers: { "Content-Type": "multipart/form-data" },
        onUploadProgress: (evt) => {
          if (onProgress && evt.total) {
            onProgress(Math.round((evt.loaded / evt.total) * 100));
          }
        },
      })
      .then((r) => r.data);
  },

  list: ({ page = 1, pageSize = 20 } = {}) =>
    api.get("/api/files/", { params: { page, page_size: pageSize } }).then((r) => r.data),

  get: (id) => api.get(`/api/files/${id}/`).then((r) => r.data),

  remove: (id) => api.delete(`/api/files/${id}/`).then((r) => r.data),
};
