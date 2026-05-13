// components/llm/ConversationView.jsx — Live chat/conversation rendering
// S7-0601: renders backend-driven messages only; no demo fallback.
import React from "react";

export function ConversationView({ messages = [] }) {
  const list = Array.isArray(messages) ? messages : [];
  if (list.length === 0) {
    return (
      <div data-testid="conversation-empty" className="aw-conversation-empty">
        No messages yet.
      </div>
    );
  }
  return (
    <ul data-testid="conversation" className="aw-conversation">
      {list.map((m, i) => (
        <li
          key={m.id ?? `${m.role ?? "msg"}-${i}`}
          data-testid="conversation-message"
          data-role={m.role ?? "system"}
        >
          <span className="aw-msg-role">{m.role ?? "system"}</span>
          <span className="aw-msg-text">{m.text ?? ""}</span>
        </li>
      ))}
    </ul>
  );
}

export default ConversationView;
