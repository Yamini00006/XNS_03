// src/components/ChatWindow/ChatWindow.jsx
import { useState } from "react";

export default function ChatWindow({ messages, onSend, sending }) {
  const [text, setText] = useState("");
  const [error, setError] = useState("");

  const submit = (e) => {
    e.preventDefault();
    if (sending) return; // prevent duplicate submissions
    const trimmed = text.trim();
    if (!trimmed) {
      setError("Please enter a question.");
      return;
    }
    setError("");
    onSend(trimmed);
    setText("");
  };

  return (
    <div className="card flex h-[28rem] flex-col">
      <div className="flex-1 space-y-3 overflow-y-auto pr-1">
        {messages.length === 0 && (
          <p className="text-sm text-slate-400">
            Ask something like "how many customers" or "customers in Austin".
          </p>
        )}
        {messages.map((m, i) => (
          <div key={i} className={`flex ${m.role === "user" ? "justify-end" : "justify-start"}`}>
            <div
              className={`max-w-[80%] rounded-lg px-3 py-2 text-sm ${
                m.role === "user" ? "bg-brand-500 text-white" : "bg-slate-100 text-slate-700"
              }`}
            >
              {m.text}
            </div>
          </div>
        ))}
        {sending && <p className="text-xs text-slate-400">Thinking...</p>}
      </div>

      <form onSubmit={submit} className="mt-3 flex gap-2 border-t border-slate-200 pt-3">
        <div className="flex-1">
          <input
            className={`input ${error ? "input-error" : ""}`}
            placeholder="Ask about your customer data..."
            value={text}
            onChange={(e) => setText(e.target.value)}
            disabled={sending}
          />
          {error && <p className="field-error">{error}</p>}
        </div>
        <button type="submit" className="btn-primary" disabled={sending}>
          Send
        </button>
      </form>
    </div>
  );
}
