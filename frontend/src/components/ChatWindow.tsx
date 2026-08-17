import { useRef, useEffect } from "react";
import type { ChatMessage } from "../types/chat";
import MessageList from "./MessageList";

interface Props {
  messages: ChatMessage[];
}

export default function ChatWindow({ messages }: Props) {
  const endRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  return (
    <div className="chat-window">
      {messages.length === 0 && (
        <div className="empty-hint">
          试试问：
          <br />
          - ERR-4502 的处理流程是什么？
          <br />
          - ERR-4502 影响了哪些业务系统？这些系统的负责人联系方式是什么？
          <br />
          - 上个月华东区发生 ERR-4502 的次数统计
        </div>
      )}
      <MessageList messages={messages} />
      <div ref={endRef} />
    </div>
  );
}