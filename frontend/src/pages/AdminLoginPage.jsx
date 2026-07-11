import { useState } from "react";
import { Lock, Loader2 } from "lucide-react";

export default function AdminLoginPage({ onLogin, verifying, error }) {
  const [key, setKey] = useState("");

  const handleSubmit = (e) => {
    e.preventDefault();
    if (key.trim()) onLogin(key.trim());
  };

  return (
    <div className="flex items-center justify-center h-screen bg-base font-sans px-4">
      <form
        onSubmit={handleSubmit}
        className="w-full max-w-sm rounded-2xl border border-border bg-surface shadow-card p-6 flex flex-col gap-4"
      >
        <div className="flex flex-col items-center gap-2 text-center">
          <div className="w-10 h-10 rounded-full bg-navy flex items-center justify-center">
            <Lock size={16} className="text-white" />
          </div>
          <h1 className="text-[16px] font-semibold text-ink">Admin Dashboard</h1>
          <p className="text-[12.5px] text-muted">Enter the admin key to manage the knowledge base.</p>
        </div>

        <input
          type="password"
          value={key}
          onChange={(e) => setKey(e.target.value)}
          placeholder="Admin key"
          autoFocus
          className="rounded-xl border border-border bg-elevated px-3.5 py-2.5 text-[14px] text-ink
            placeholder:text-muted outline-none focus:border-accent/60 transition-colors"
        />

        {error && <p className="text-[12.5px] text-danger -mt-1">{error}</p>}

        <button
          type="submit"
          disabled={!key.trim() || verifying}
          className="rounded-xl bg-navy text-white text-[14px] font-medium py-2.5
            disabled:bg-border disabled:text-muted transition-colors flex items-center justify-center gap-2"
        >
          {verifying && <Loader2 size={14} className="animate-spin" />}
          {verifying ? "Verifying…" : "Enter"}
        </button>
      </form>
    </div>
  );
}
