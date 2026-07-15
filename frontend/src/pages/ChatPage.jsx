import { useEffect, useRef, useState } from "react";
import { ArrowUp, Sparkles } from "lucide-react";
import MessageBubble from "../components/MessageBubble";
import AmbientOrb from "../components/AmbientOrb";
import { askQuestion, getTopics } from "../lib/api";

export default function ChatPage() {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [sending, setSending] = useState(false);
  const [topics, setTopics] = useState([]);
  const [error, setError] = useState(null);

  const scrollRef = useRef(null);
  const textareaRef = useRef(null);

  useEffect(() => {
    getTopics()
      .then((res) => setTopics(res.topics || []))
      .catch(() => setTopics([]));
  }, []);

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
  }, [messages]);

  const send = async (question) => {
    const trimmed = question.trim();
    if (!trimmed || sending) return;

    setMessages((prev) => [...prev, { role: "user", content: trimmed }]);
    setInput("");
    if (textareaRef.current) textareaRef.current.style.height = "auto";
    setSending(true);
    setError(null);

    try {
      // Send recent history (before this new message) so the backend can
      // rewrite follow-up questions like "what about that?" into a
      // standalone question before retrieval.
      const recentHistory = messages.slice(-6).map(({ role, content }) => ({ role, content }));
      const res = await askQuestion(trimmed, recentHistory);
      setMessages((prev) => [...prev, { role: "assistant", content: res.answer }]);
    } catch (err) {
      setError(err.message);
      setMessages((prev) => [
        ...prev,
        { role: "assistant", content: "Sorry, something went wrong answering that. Please try again." },
      ]);
    } finally {
      setSending(false);
    }
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    send(input);
  };

  const handleKeyDown = (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      send(input);
    }
  };

  const autoGrow = (e) => {
    setInput(e.target.value);
    e.target.style.height = "auto";
    e.target.style.height = `${Math.min(e.target.scrollHeight, 160)}px`;
  };

  return (
    <div className="relative flex flex-col h-screen bg-[#0B0710] text-white font-sans overflow-hidden">
      <AmbientOrb />

      <header className="relative flex items-center gap-2.5 px-6 py-4 border-b border-white/10 bg-white/[0.02] backdrop-blur-xl">
        <div className="w-8 h-8 rounded-full ring-1 ring-white/20 overflow-hidden shrink-0">
          <img src="/logo.webp" alt="Logo" className="w-full h-full object-cover" />
        </div>
        <h1 className="text-[15px] font-semibold tracking-tight">Knowledge Assistant</h1>
        <span className="ml-auto flex items-center gap-1.5 text-[11px] text-white/40">
          <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 shadow-[0_0_6px_rgba(52,211,153,0.8)]" />
          Online
        </span>
      </header>

      <div ref={scrollRef} className="relative flex-1 overflow-y-auto">
        <div className="max-w-[720px] mx-auto px-6 py-8 flex flex-col gap-6">
          {messages.length === 0 && (
            <div className="flex flex-col items-center text-center gap-4 py-20">
              <div className="w-14 h-14 rounded-full ring-1 ring-white/20 overflow-hidden shadow-[0_0_40px_rgba(242,118,31,0.3)]">
                <img src="/logo.webp" alt="" className="w-full h-full object-cover" />
              </div>
              <div className="flex items-center gap-1.5 text-white/50 text-[12.5px]">
                <Sparkles size={12} />
                Ask anything about
              </div>
              {topics.length > 0 && (
                <ul className="flex flex-wrap justify-center gap-2 max-w-[440px]">
                  {topics.map((t) => (
                    <li key={t}>
                      <button
                        onClick={() => send(`Tell me about ${t.toLowerCase()}`)}
                        className="rounded-full border border-white/10 bg-white/[0.05] backdrop-blur-xl px-3.5 py-1.5 text-[13px]
                          text-white/80 hover:border-accent/40 hover:bg-white/[0.09] hover:text-white transition-colors"
                      >
                        {t}
                      </button>
                    </li>
                  ))}
                </ul>
              )}
            </div>
          )}

          {messages.map((m, i) => (
            <MessageBubble key={i} {...m} />
          ))}
        </div>
      </div>

      <div className="relative px-6 py-4">
        <form
          onSubmit={handleSubmit}
          className="max-w-[720px] mx-auto flex items-end gap-2 rounded-3xl border border-white/10
            bg-white/[0.05] backdrop-blur-xl px-4 py-2.5 focus-within:border-accent/40 transition-colors
            shadow-[0_8px_32px_rgba(0,0,0,0.4)]"
        >
          <textarea
            ref={textareaRef}
            value={input}
            onChange={autoGrow}
            onKeyDown={handleKeyDown}
            rows={1}
            placeholder="Ask anything…"
            disabled={sending}
            className="flex-1 bg-transparent resize-none outline-none text-[14.5px] text-white
              placeholder:text-white/40 py-1.5 max-h-40 disabled:cursor-not-allowed"
          />
          <button
            type="submit"
            disabled={!input.trim() || sending}
            aria-label="Send message"
            className="w-9 h-9 rounded-full flex items-center justify-center shrink-0 mb-0.5
              bg-gradient-to-br from-accent to-fuchsia-600 text-white
              disabled:bg-white/10 disabled:text-white/30 disabled:bg-none transition-colors
              shadow-[0_4px_16px_rgba(242,118,31,0.35)] disabled:shadow-none"
          >
            <ArrowUp size={16} strokeWidth={2.5} />
          </button>
        </form>
        {error && <p className="max-w-[720px] mx-auto mt-2 text-[12px] text-red-400">{error}</p>}
      </div>
    </div>
  );
}
