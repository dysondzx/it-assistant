import { useState } from "react";
import type { ChatMessage } from "./types/chat";
import ChatWindow from "./components/ChatWindow";
import InputBar from "./components/InputBar";
import { streamChat } from "./api/client";

export default function App() {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [loading, setLoading] = useState(false);

  const handleSend = async (text: string) => {
    const userMsg: ChatMessage = { role: "user", content: text };
    const assistantMsg: ChatMessage = {
      role: "assistant",
      content: "",
      streaming: true,
    };
    setMessages((prev) => [...prev, userMsg, assistantMsg]);
    setLoading(true);

    let acc = "";
    try {
      for await (const event of streamChat(text)) {
        if (event.type === "message" && event.content) {
          acc += event.content;
          setMessages((prev) => {
            const next = [...prev];
            next[next.length - 1] = {
              role: "assistant",
              content: acc,
              streaming: true,
            };
            return next;
          });
        } else if (event.type === "error") {
          acc = event.content || "（服务端发生错误）";
        }
      }
    } catch (err) {
      acc = `（请求出错：${err instanceof Error ? err.message : "未知错误"}）`;
    }

    setMessages((prev) => {
      const next = [...prev];
      next[next.length - 1] = {
        role: "assistant",
        content: acc || "（无回复）",
        streaming: false,
      };
      return next;
    });
    setLoading(false);
  };

  return (
    <div className="app">
      <header className="app-header">Agentic RAG IT 助手</header>
      <ChatWindow messages={messages} />
      <InputBar onSend={handleSend} disabled={loading} />
    </div>
  );
}