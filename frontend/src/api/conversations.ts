import type { Conversation, HistoryMessage } from "../types/chat";

async function parseJson<T>(resp: Response): Promise<T> {
  if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
  return (await resp.json()) as T;
}

export async function listConversations(): Promise<Conversation[]> {
  const data = await parseJson<{ items: Conversation[] }>(
    await fetch("/api/conversations"),
  );
  return data.items;
}

export async function createConversation(): Promise<Conversation> {
  return parseJson<Conversation>(
    await fetch("/api/conversations", { method: "POST" }),
  );
}

export async function deleteConversation(id: string): Promise<void> {
  const resp = await fetch(`/api/conversations/${id}`, { method: "DELETE" });
  if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
}

export async function getMessages(id: string): Promise<HistoryMessage[]> {
  const data = await parseJson<{ items: HistoryMessage[] }>(
    await fetch(`/api/conversations/${id}/messages`),
  );
  return data.items;
}
