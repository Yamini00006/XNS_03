// src/services/api.js
//
// The ONE place that talks HTTP. Every other service file imports this
// client instead of calling fetch/axios directly (see FRONTEND_STRUCTURE
// requirement: "Do NOT scatter fetch(...) through every component").

import axios from "axios";
import { API_BASE_URL } from "../utils/constants";
import { storage } from "../utils/storage";

export const api = axios.create({
  baseURL: API_BASE_URL,
});

api.interceptors.request.use((config) => {
  const token = storage.getAccessToken();
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Normalizes every error into a plain, displayable object:
//   { status, code, message }
// Matches backend/common/exceptions.py's envelope: {"error": {"code","message"}}
function normalizeError(error) {
  if (error.response) {
    const { status, data } = error.response;
    if (data && data.error) {
      return { status, code: data.error.code, message: data.error.message };
    }
    return { status, code: "UNKNOWN_ERROR", message: "Something went wrong." };
  }
  if (error.request) {
    return { status: 0, code: "NETWORK_ERROR", message: "Could not reach the server. Check your connection." };
  }
  return { status: 0, code: "CLIENT_ERROR", message: error.message || "Unexpected error." };
}

let isRefreshing = false;
let pendingQueue = [];

function processQueue(error, token = null) {
  pendingQueue.forEach(({ resolve, reject }) => (error ? reject(error) : resolve(token)));
  pendingQueue = [];
}

api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config;
    const isAuthEndpoint = originalRequest?.url?.includes("/api/auth/");

    if (error.response?.status === 401 && !originalRequest._retry && !isAuthEndpoint) {
      const refreshToken = storage.getRefreshToken();
      if (!refreshToken) {
        storage.clearTokens();
        return Promise.reject(normalizeError(error));
      }

      if (isRefreshing) {
        return new Promise((resolve, reject) => {
          pendingQueue.push({ resolve, reject });
        }).then((token) => {
          originalRequest.headers.Authorization = `Bearer ${token}`;
          return api(originalRequest);
        });
      }

      originalRequest._retry = true;
      isRefreshing = true;

      try {
        const { data } = await axios.post(`${API_BASE_URL}/api/auth/refresh/`, {
          refresh: refreshToken,
        });
        storage.setTokens(data.access, data.refresh);
        processQueue(null, data.access);
        originalRequest.headers.Authorization = `Bearer ${data.access}`;
        return api(originalRequest);
      } catch (refreshError) {
        processQueue(refreshError, null);
        storage.clearTokens();
        window.location.href = "/login";
        return Promise.reject(normalizeError(refreshError));
      } finally {
        isRefreshing = false;
      }
    }

    return Promise.reject(normalizeError(error));
  }
);
