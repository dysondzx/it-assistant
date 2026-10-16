import { useEffect, useState } from "react";
import type { ChatMessage, Conversation } from "./types/chat";
import ChatWindow from "./components/ChatWindow";
import ConversationList from "./components/ConversationList";
import InputBar from "./components/InputBar";
import { streamChat } from "./api/client";
import {
  createConversation,
  deleteConversation,
  getMessages,
  listConversations,
} from "./api/conversations";

const TITLE_MAX_LEN = 20;

/** 用首条用户消息截断生成标题（与后端 derive_title 保持一致） */
function deriveTitle(text: string): string {
  const normalized = text.trim().split(/\s+/).join(" ");
  return normalized.slice(0, TITLE_MAX_LEN) || "新对话";
}

export default function App() {
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [activeId, setActiveId] = useState("");
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [loading, setLoading] = useState(false);
  const [booting, setBooting] = useState(true);

  /** 切换会话：先清空视图，再从 checkpoint 回显历史消息 */
  const openConversation = async (id: string) => {
    setActiveId(id);
    setMessages([]);
    try {
      const history = await getMessages(id);
      setMessages(history.map((m) => ({ role: m.role, content: m.content })));
    } catch (err) {
      console.error("加载历史消息失败", err);
    }
  };

  // 首次加载：拉会话列表，默认选中最近一条
  useEffect(() => {
    (async () => {
      try {
        const list = await listConversations();
        setConversations(list);
        if (list.length > 0) await openConversation(list[0].id);
      } catch (err) {
        console.error("加载会话列表失败", err);
      } finally {
        setBooting(false);
      }
    })();
  }, []);

  const handleNew = async () => {
    try {
      const conv = await createConversation();
      setConversations((prev) => [conv, ...prev]);
      setActiveId(conv.id);
      setMessages([]);
    } catch (err) {
      console.error("新建会话失败", err);
    }
  };

  const handleSelect = (id: string) => {
    if (loading || id === activeId) return;
    void openConversation(id);
  };

  const handleDelete = async (id: string) => {
    if (loading) return;
    try {
      await deleteConversation(id);
      const rest = conversations.filter((c) => c.id !== id);
      setConversations(rest);
      if (id !== activeId) return;
      if (rest.length > 0) await openConversation(rest[0].id);
      else {
        setActiveId("");
        setMessages([]);
      }
    } catch (err) {
      console.error("删除会话失败", err);
    }
  };

  const handleSend = async (text: string) => {
    if (loading) return;

    let convId = activeId;
    if (!convId) {
      // 列表为空时直接提问，自动开一个新会话
      try {
        const conv = await createConversation();
        convId = conv.id;
        setActiveId(conv.id);
        setConversations((prev) => [conv, ...prev]);
      } catch (err) {
        console.error("创建会话失败", err);
        return;
      }
    }

    // 乐观更新：首条消息命名标题，并把该会话置顶
    const isFirst = messages.length === 0;
    setConversations((prev) => {
      const target = prev.find((c) => c.id === convId);
      if (!target) return prev;
      const updated = isFirst
        ? {
            ...target,
            title: deriveTitle(text),
            updated_at: new Date().toISOString(),
          }
        : target;
      return [updated, ...prev.filter((c) => c.id !== convId)];
    });

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
      for await (const event of streamChat(text, convId)) {
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
      <ConversationList
        conversations={conversations}
        activeId={activeId}
        loading={loading || booting}
        onSelect={handleSelect}
        onNew={handleNew}
        onDelete={handleDelete}
      />
      <div className="main-col">
        <header className="app-header">Agentic RAG IT 助手</header>
        <ChatWindow messages={messages} />
        <InputBar onSend={handleSend} disabled={loading} />
      </div>
    </div>
  );
}
