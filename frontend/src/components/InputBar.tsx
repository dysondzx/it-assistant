import { useState } from "react";

interface Props {
  onSend: (text: string) => void;
  disabled: boolean;
}

export default function InputBar({ onSend, disabled }: Props) {
  const [text, setText] = useState("");

  const handleSubmit = () => {
    const trimmed = text.trim();
    if (!trimmed || disabled) return;
    onSend(trimmed);
    setText("");
  };

  return (
    <div className="input-bar">
      <textarea
        value={text}
        onChange={(e) => setText(e.target.value)}
        onKeyDown={(e) => {
          if (e.key === "Enter" && !e.shiftKey) {
            e.preventDefault();
            handleSubmit();
          }
        }}
        placeholder="输入你的问题，Enter 发送，Shift+Enter 换行"
        rows={2}
      />
      <button onClick={handleSubmit} disabled={disabled}>
        {disabled ? "回复中..." : "发送"}
      </button>
    </div>
  );
}