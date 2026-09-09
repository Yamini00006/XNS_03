// src/pages/Chatbot/Chatbot.jsx
import { useState } from "react";
import ChatWindow from "../../components/ChatWindow/ChatWindow";
import { chatbotService } from "../../services/chatbotService";

export default function Chatbot() {
  const [messages, setMessages] = useState([]);
  const [sending, setSending] = useState(false);

  const handleSend = async (text) => {
    if (sending) return; // prevent duplicate submissions
    setMessages((prev) => [...prev, { role: "user", text }]);
    setSending(true);
    try {
      const result = await chatbotService.query(text);
      setMessages((prev) => [...prev, { role: "assistant", text: result.message }]);
    } catch (err) {
      setMessages((prev) => [
        ...prev,
        { role: "assistant", text: err.message || "Sorry, something went wrong." },
      ]);
    } finally {
      setSending(false);
    }
  };

  return (
    <div className="max-w-xl space-y-4">
      <h1 className="text-lg font-semibold text-slate-800">Chatbot</h1>
      <ChatWindow messages={messages} onSend={handleSend} sending={sending} />
    </div>
  );
}
