export interface ChatMessage {
  role: "user" | "assistant";
  content: string;
  streaming?: boolean;
}

export interface SSEData {
  type: "message" | "done" | "error";
  content?: string;
}

/** 会话（对话）目录信息，id 同时是 LangGraph 的 thread_id */
export interface Conversation {
  id: string;
  title: string;
  created_at: string;
  updated_at: string;
}

/** 后端从 checkpoint 还原出来的历史消息 */
export interface HistoryMessage {
  role: "user" | "assistant";
  content: string;
}
