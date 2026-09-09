import { api } from "./api";

export const fileService = {
  upload: (file, onProgress) => {
    const formData = new FormData();
    formData.append("file", file);

    return api.post("/api/files/upload/", formData, {
      onUploadProgress: (event) => {
        if (!onProgress || !event.total) return;

        const percent = Math.round(
          (event.loaded * 100) / event.total
        );

        onProgress(percent);
      },
    }).then((response) => response.data);
  },

  uploadBatch: (files, onProgress) => {
    const formData = new FormData();

    files.forEach((file) => {
      formData.append("files", file);
    });

    return api.post("/api/files/upload-batch/", formData, {
      onUploadProgress: (event) => {
        if (!onProgress || !event.total) return;

        const percent = Math.round(
          (event.loaded * 100) / event.total
        );

        onProgress(percent);
      },
    }).then((response) => response.data);
  },

  discoverAttributes: (fileIds) =>
    api
      .post("/api/files/discover-attributes/", {
        file_ids: fileIds,
      })
      .then((response) => response.data),

  list: ({
    page = 1,
    pageSize = 20,
    format,
    mine,
  } = {}) =>
    api
      .get("/api/files/", {
        params: {
          page,
          page_size: pageSize,
          ...(format ? { format } : {}),
          ...(mine !== undefined ? { mine } : {}),
        },
      })
      .then((response) => response.data),

  get: (fileId) =>
    api
      .get(`/api/files/${fileId}/`)
      .then((response) => response.data),

  remove: (fileId) =>
    api
      .delete(`/api/files/${fileId}/`)
      .then((response) => response.data),
};