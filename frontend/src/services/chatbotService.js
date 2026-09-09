import { api } from "./api";

export const chatbotService = {
  query: (query, batchId = null) => {
    const payload = {
      query,
    };

    if (batchId !== null && batchId !== undefined) {
      payload.batch_id = Number(batchId);
    }

    return api
      .post("/api/chatbot/query/", payload)
      .then((response) => response.data);
  },
};