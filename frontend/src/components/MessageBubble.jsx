import { User } from "lucide-react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

// Assistant messages render as real Markdown (headings, bold, lists, tables,
// links, code blocks). User messages stay plain text — no reason to parse
// Markdown syntax someone typed themselves, and it keeps their input
// predictable/literal.
const MARKDOWN_CLASSES = `prose prose-invert prose-sm max-w-none
  prose-p:my-1.5 prose-headings:mt-3 prose-headings:mb-1.5 prose-headings:font-semibold
  prose-ul:my-1.5 prose-ol:my-1.5 prose-li:my-0.5
  prose-a:text-accent prose-a:no-underline hover:prose-a:underline
  prose-strong:text-white prose-strong:font-semibold
  prose-code:text-accent-soft prose-code:bg-black/30 prose-code:px-1 prose-code:py-0.5 prose-code:rounded prose-code:before:content-none prose-code:after:content-none
  prose-pre:bg-black/30 prose-pre:border prose-pre:border-white/10 prose-pre:rounded-xl
  prose-table:text-[13px] prose-th:text-white/90 prose-td:border-white/10 prose-th:border-white/10
  prose-blockquote:border-l-accent/50 prose-blockquote:text-white/70`;

export default function MessageBubble({ role, content, isStreaming }) {
  const isUser = role === "user";

  return (
    <div className={`flex gap-3 ${isUser ? "flex-row-reverse" : ""}`}>
      {isUser ? (
        <div className="w-7 h-7 rounded-full flex items-center justify-center shrink-0 mt-0.5 bg-white/10 text-white/70">
          <User size={14} />
        </div>
      ) : (
        <div className="w-7 h-7 rounded-full shrink-0 mt-0.5 ring-1 ring-white/20 overflow-hidden">
          <img src="/logo.webp" alt="" className="w-full h-full object-cover" />
        </div>
      )}

      <div
        className={`max-w-[75%] rounded-3xl px-4 py-2.5 text-[14.5px] leading-relaxed
          ${isUser
            ? "bg-gradient-to-br from-accent to-fuchsia-600 text-white whitespace-pre-wrap rounded-tr-md shadow-[0_8px_24px_rgba(242,118,31,0.25)]"
            : "bg-white/[0.06] backdrop-blur-xl border border-white/10 text-white/90 rounded-tl-md"}`}
      >
        {isUser ? (
          content
        ) : (
          <div className={MARKDOWN_CLASSES}>
            <ReactMarkdown remarkPlugins={[remarkGfm]}>{content}</ReactMarkdown>
          </div>
        )}
        {isStreaming && <span className="inline-block w-1.5 h-3.5 ml-0.5 bg-white/70 animate-pulse_soft align-middle" />}
      </div>
    </div>
  );
}
