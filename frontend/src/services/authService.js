// src/services/authService.js
import { api } from "./api";

export const authService = {
  login: (username, password) =>
    api.post("/api/auth/login/", { username, password }).then((r) => r.data),

  refresh: (refresh) =>
    api.post("/api/auth/refresh/", { refresh }).then((r) => r.data),

  logout: (refresh) => api.post("/api/auth/logout/", { refresh }).then((r) => r.data),

  me: () => api.get("/api/users/me/").then((r) => r.data),
};
