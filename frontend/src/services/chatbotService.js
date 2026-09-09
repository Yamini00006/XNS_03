// src/services/chatbotService.js
import { api } from "./api";

export const chatbotService = {
  query: (query) => api.post("/api/chatbot/query/", { query }).then((r) => r.data),
};
