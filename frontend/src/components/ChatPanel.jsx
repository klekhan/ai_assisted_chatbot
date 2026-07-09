import { useEffect, useRef, useState } from "react";
import { ArrowUp } from "lucide-react";
import MessageBubble from "./MessageBubble";

export default function ChatPanel({ messages, sending, hasDocuments, onSend }) {
  const [input, setInput] = useState("");
  const scrollRef = useRef(null);
  const textareaRef = useRef(null);

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
  }, [messages]);

  const handleSubmit = (e) => {
    e.preventDefault();
    const trimmed = input.trim();
    if (!trimmed || sending) return;
    onSend(trimmed);
    setInput("");
    if (textareaRef.current) textareaRef.current.style.height = "auto";
  };

  const handleKeyDown = (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      handleSubmit(e);
    }
  };

  const autoGrow = (e) => {
    setInput(e.target.value);
    e.target.style.height = "auto";
    e.target.style.height = `${Math.min(e.target.scrollHeight, 160)}px`;
  };

  return (
    <main className="flex-1 flex flex-col h-full min-w-0 bg-base">
      <div ref={scrollRef} className="flex-1 overflow-y-auto">
        <div className="max-w-[720px] mx-auto px-6 py-8 flex flex-col gap-6">
          {messages.length === 0 && (
            <div className="flex flex-col items-center text-center gap-3 py-24">
              <img src="/logo.webp" alt="" className="w-12 h-12 rounded-full shadow-card" />
              <h2 className="text-[17px] font-semibold text-ink">
                {hasDocuments ? "Ask something about your documents" : "Add a document to get started"}
              </h2>
              <p className="text-[13px] text-muted max-w-[380px] leading-relaxed">
                {hasDocuments
                  ? "Every answer is grounded in what's been uploaded, with sources shown below each reply."
                  : "Use the panel on the left to upload a PDF, DOCX, TXT, or MD file — then ask away."}
              </p>
            </div>
          )}

          {messages.map((m, i) => (
            <MessageBubble key={i} {...m} />
          ))}
        </div>
      </div>

      <div className="px-6 py-4">
        <form
          onSubmit={handleSubmit}
          className="max-w-[720px] mx-auto flex items-end gap-2 rounded-2xl border border-border
            bg-surface shadow-card px-3 py-2 focus-within:border-accent/50 transition-colors"
        >
          <textarea
            ref={textareaRef}
            value={input}
            onChange={autoGrow}
            onKeyDown={handleKeyDown}
            rows={1}
            placeholder={hasDocuments ? "Ask a question about your documents…" : "Upload a document first…"}
            disabled={!hasDocuments || sending}
            className="flex-1 bg-transparent resize-none outline-none text-[14.5px] text-ink
              placeholder:text-muted py-1.5 max-h-40 disabled:cursor-not-allowed"
          />
          <button
            type="submit"
            disabled={!input.trim() || sending || !hasDocuments}
            aria-label="Send message"
            className="w-8 h-8 rounded-full flex items-center justify-center shrink-0 mb-0.5
              bg-accent text-white disabled:bg-border disabled:text-muted transition-colors"
          >
            <ArrowUp size={16} strokeWidth={2.5} />
          </button>
        </form>
      </div>
    </main>
  );
}
