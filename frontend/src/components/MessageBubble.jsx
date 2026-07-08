import { Sparkles, User } from "lucide-react";
import SourceChip from "./SourceChip";

export default function MessageBubble({ role, content, sources, isStreaming }) {
  const isUser = role === "user";

  return (
    <div className={`flex gap-3 ${isUser ? "flex-row-reverse" : ""}`}>
      <div
        className={`w-7 h-7 rounded-full flex items-center justify-center shrink-0 mt-0.5
          ${isUser ? "bg-elevated text-muted" : "bg-accent-dim text-accent-soft"}`}
      >
        {isUser ? <User size={14} /> : <Sparkles size={14} />}
      </div>

      <div className={`flex flex-col gap-2 max-w-[70%] ${isUser ? "items-end" : "items-start"}`}>
        <div
          className={`rounded-2xl px-4 py-2.5 text-[14.5px] leading-relaxed whitespace-pre-wrap
            ${isUser ? "bg-elevated text-ink rounded-tr-sm" : "bg-surface border border-border text-ink rounded-tl-sm"}`}
        >
          {content}
          {isStreaming && <span className="inline-block w-1.5 h-3.5 ml-0.5 bg-accent animate-pulse_soft align-middle" />}
        </div>

        {sources && sources.length > 0 && (
          <div className="flex flex-wrap gap-1.5">
            {sources.map((s, i) => (
              <SourceChip key={i} source={s} />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
