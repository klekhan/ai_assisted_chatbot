import { useState } from "react";
import { User, ThumbsUp, ThumbsDown } from "lucide-react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { sendFeedback } from "../lib/api";

// Assistant messages render as real Markdown (headings, bold, lists, tables,
// links, code blocks). User messages stay plain text — no reason to parse
// Markdown syntax someone typed themselves, and it keeps their input
// predictable/literal.
const MARKDOWN_CLASSES = `prose prose-sm max-w-none
  prose-p:my-1.5 prose-headings:mt-3 prose-headings:mb-1.5 prose-headings:font-semibold
  prose-ul:my-1.5 prose-ol:my-1.5 prose-li:my-0.5
  prose-a:text-accent prose-a:no-underline hover:prose-a:underline
  prose-strong:text-ink prose-strong:font-semibold
  prose-code:text-accent prose-code:bg-elevated prose-code:px-1 prose-code:py-0.5 prose-code:rounded prose-code:before:content-none prose-code:after:content-none
  prose-pre:bg-elevated prose-pre:border prose-pre:border-border prose-pre:rounded-xl
  prose-table:text-[13px] prose-th:text-ink prose-td:border-border prose-th:border-border
  prose-blockquote:border-l-accent/50 prose-blockquote:text-muted`;

export default function MessageBubble({ role, content, isStreaming, messageId }) {
  const isUser = role === "user";
  const [rating, setRating] = useState(null); // null | "up" | "down"
  const [sendingRating, setSendingRating] = useState(false);

  const rate = async (value) => {
    if (!messageId || rating || sendingRating) return;
    setSendingRating(true);
    setRating(value); // optimistic — feedback is low-stakes, no need to block on the request
    try {
      await sendFeedback(messageId, value);
    } catch {
      setRating(null); // let them retry if it genuinely failed
    } finally {
      setSendingRating(false);
    }
  };

  return (
    <div className={`flex gap-3 ${isUser ? "flex-row-reverse" : ""}`}>
      {isUser ? (
        <div className="w-7 h-7 rounded-full flex items-center justify-center shrink-0 mt-0.5 bg-elevated text-muted">
          <User size={14} />
        </div>
      ) : (
        <div className="w-7 h-7 rounded-full shrink-0 mt-0.5 ring-1 ring-border overflow-hidden">
          <img src="/logo.webp" alt="" className="w-full h-full object-cover" />
        </div>
      )}

      <div className="flex flex-col gap-1 max-w-[75%]">
        <div
          className={`rounded-2xl px-4 py-2.5 text-[14.5px] leading-relaxed
            ${isUser
              ? "bg-navy text-white whitespace-pre-wrap rounded-tr-sm"
              : "bg-surface border border-border text-ink shadow-card rounded-tl-sm"}`}
        >
          {isUser ? (
            content
          ) : (
            <div className={MARKDOWN_CLASSES}>
              <ReactMarkdown remarkPlugins={[remarkGfm]}>{content}</ReactMarkdown>
            </div>
          )}
          {isStreaming && <span className="inline-block w-1.5 h-3.5 ml-0.5 bg-accent animate-pulse_soft align-middle" />}
        </div>

        {!isUser && !isStreaming && messageId && (
          <div className="flex items-center gap-1 px-1">
            <button
              onClick={() => rate("up")}
              disabled={!!rating || sendingRating}
              aria-label="Good answer"
              className={`p-1 rounded-md transition-colors ${
                rating === "up" ? "text-emerald-600" : "text-muted hover:text-ink"
              }`}
            >
              <ThumbsUp size={13} />
            </button>
            <button
              onClick={() => rate("down")}
              disabled={!!rating || sendingRating}
              aria-label="Bad answer"
              className={`p-1 rounded-md transition-colors ${
                rating === "down" ? "text-danger" : "text-muted hover:text-ink"
              }`}
            >
              <ThumbsDown size={13} />
            </button>
            {rating && <span className="text-[11px] text-muted">Thanks for the feedback</span>}
          </div>
        )}
      </div>
    </div>
  );
}
