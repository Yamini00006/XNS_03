import { useMemo, useState } from "react";
import { useSearchParams } from "react-router-dom";

import ChatWindow from "../../components/ChatWindow/ChatWindow";
import { chatbotService } from "../../services/chatbotService";

export default function Chatbot() {
  const [searchParams] = useSearchParams();

  const batchId = searchParams.get("batch_id");

  const [messages, setMessages] = useState([]);
  const [sending, setSending] = useState(false);

  const batchLabel = useMemo(() => {
    if (!batchId) {
      return "All available customer data";
    }

    return `Processing Batch ${batchId}`;
  }, [batchId]);

  const handleSend = async (text) => {
    const query = (text || "").trim();

    if (!query || sending) {
      return;
    }

    setMessages((prev) => [
      ...prev,
      {
        role: "user",
        text: query,
      },
    ]);

    setSending(true);

    try {
      const result = await chatbotService.query(
        query,
        batchId
      );

      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          text: result.message || "No response received.",
          results: result.results || [],
          count: result.count ?? 0,
          intent: result.intent,
        },
      ]);
    } catch (err) {
      console.error(err);

      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          text:
            err?.message ||
            "Sorry, something went wrong.",
        },
      ]);
    } finally {
      setSending(false);
    }
  };

  return (
    <div className="max-w-3xl space-y-4">
      <div>
        <h1 className="text-lg font-semibold text-slate-800">
          Chatbot
        </h1>

        <p className="mt-1 text-sm text-slate-500">
          {batchLabel}
        </p>
      </div>

      {batchId && (
        <div className="rounded border border-blue-200 bg-blue-50 px-4 py-3 text-sm text-blue-800">
          Chatbot queries are restricted to Processing Batch{" "}
          <strong>{batchId}</strong>.
        </div>
      )}

      {!batchId && (
        <div className="rounded border border-yellow-200 bg-yellow-50 px-4 py-3 text-sm text-yellow-800">
          No processing batch was selected. You can still use
          the chatbot, but queries are not restricted to a
          specific batch.
        </div>
      )}

      <ChatWindow
        messages={messages}
        onSend={handleSend}
        sending={sending}
      />
    </div>
  );
}