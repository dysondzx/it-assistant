import type { Conversation } from "../types/chat";

interface Props {
  conversations: Conversation[];
  activeId: string;
  loading: boolean;
  onSelect: (id: string) => void;
  onNew: () => void;
  onDelete: (id: string) => void;
}

export default function ConversationList({
  conversations,
  activeId,
  loading,
  onSelect,
  onNew,
  onDelete,
}: Props) {
  return (
    <aside className="sidebar">
      <button className="sidebar-new" onClick={onNew} disabled={loading}>
        ＋ 新对话
      </button>

      <div className="sidebar-list">
        {conversations.length === 0 && !loading && (
          <div className="sidebar-empty">暂无历史记录</div>
        )}

        {conversations.map((conv) => (
          <div
            key={conv.id}
            className={`conv-item ${conv.id === activeId ? "active" : ""}`}
            onClick={() => onSelect(conv.id)}
            title={conv.title}
          >
            <span className="conv-title">{conv.title}</span>
            <button
              className="conv-delete"
              title="删除会话"
              disabled={loading}
              onClick={(e) => {
                e.stopPropagation();
                onDelete(conv.id);
              }}
            >
              ×
            </button>
          </div>
        ))}
      </div>
    </aside>
  );
}
