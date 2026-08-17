export interface ChatMessage {
  role: "user" | "assistant";
  content: string;
  streaming?: boolean;
}

export interface SSEData {
  type: "message" | "done" | "error";
  content?: string;
}