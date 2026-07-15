import { useEffect, useRef, useState, useCallback } from "react";
import { Upload, FileText, X, Loader2, LogOut, Database, Search } from "lucide-react";
import SourceChip from "../components/SourceChip";
import {
  adminListDocuments,
  adminUploadDocument,
  adminDeleteDocument,
  adminDebugChat,
  adminGetStats,
} from "../lib/api";

export default function AdminDashboardPage({ adminKey, onLogout }) {
  const [documents, setDocuments] = useState([]);
  const [docsLoading, setDocsLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [stats, setStats] = useState(null);
  const [dragOver, setDragOver] = useState(false);
  const [error, setError] = useState(null);

  const [debugQuestion, setDebugQuestion] = useState("");
  const [debugResult, setDebugResult] = useState(null);
  const [debugLoading, setDebugLoading] = useState(false);

  const inputRef = useRef(null);

  const refresh = useCallback(async () => {
    try {
      const [docs, s] = await Promise.all([adminListDocuments(adminKey), adminGetStats(adminKey)]);
      setDocuments(docs);
      setStats(s);
    } catch (err) {
      setError(err.message);
    } finally {
      setDocsLoading(false);
    }
  }, [adminKey]);

  useEffect(() => {
    refresh();
  }, [refresh]);

  const handleFiles = async (files) => {
    if (!files || files.length === 0) return;
    for (const file of Array.from(files)) {
      setUploading(true);
      setUploadProgress(0);
      setError(null);
      try {
        await adminUploadDocument(adminKey, file, setUploadProgress);
        await refresh();
      } catch (err) {
        setError(`Upload failed for "${file.name}": ${err.message}`);
      } finally {
        setUploading(false);
        setUploadProgress(0);
      }
    }
  };

  const handleDelete = async (documentId) => {
    setDocuments((prev) => prev.filter((d) => d.document_id !== documentId));
    try {
      await adminDeleteDocument(adminKey, documentId);
      refresh();
    } catch (err) {
      setError(`Couldn't delete document: ${err.message}`);
      refresh();
    }
  };

  const handleDebugQuery = async (e) => {
    e.preventDefault();
    if (!debugQuestion.trim()) return;
    setDebugLoading(true);
    setDebugResult(null);
    setError(null);
    try {
      const res = await adminDebugChat(adminKey, debugQuestion.trim());
      setDebugResult(res);
    } catch (err) {
      setError(`Debug query failed: ${err.message}`);
    } finally {
      setDebugLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-base text-ink font-sans">
      <header className="flex items-center justify-between px-6 py-4 border-b border-border bg-surface">
        <div className="flex items-center gap-2.5">
          <img src="/logo.webp" alt="Logo" className="w-8 h-8 rounded-full" />
          <h1 className="text-[15px] font-semibold tracking-tight">Admin Dashboard</h1>
        </div>
        <button
          onClick={onLogout}
          className="flex items-center gap-1.5 text-[12.5px] text-muted hover:text-danger transition-colors"
        >
          <LogOut size={14} />
          Log out
        </button>
      </header>

      <main className="max-w-[1000px] mx-auto px-6 py-8 flex flex-col gap-8">
        {error && (
          <div className="rounded-xl border border-danger/30 bg-elevated px-4 py-3 text-[13px] text-ink flex items-start justify-between gap-3">
            <span>{error}</span>
            <button onClick={() => setError(null)} className="text-muted hover:text-ink shrink-0">×</button>
          </div>
        )}

        {/* --- KB status --- */}
        <section className="grid grid-cols-2 gap-3 max-w-md">
          <StatCard label="Documents" value={stats?.total_documents ?? "…"} icon={FileText} />
          <StatCard label="Collection status" value={stats?.status ?? "…"} icon={Database} />
        </section>

        {/* --- Upload --- */}
        <section>
          <h2 className="text-[13px] font-medium text-muted uppercase tracking-wider mb-3">
            Add or replace a document
          </h2>
          <label
            onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
            onDragLeave={() => setDragOver(false)}
            onDrop={(e) => { e.preventDefault(); setDragOver(false); handleFiles(e.dataTransfer.files); }}
            className={`flex flex-col items-center justify-center gap-2 rounded-2xl border-2 border-dashed
              px-6 py-10 cursor-pointer transition-colors
              ${dragOver ? "border-accent bg-accent-dim" : "border-border bg-elevated hover:border-accent/50"}`}
          >
            <Upload size={20} className={dragOver ? "text-accent" : "text-muted"} />
            <span className="text-[13px] text-muted text-center">
              Drop a file or <span className="text-accent font-medium">browse</span>
              <br />
              PDF, DOCX, TXT, MD · 20MB max · re-uploading a filename replaces it
            </span>
            <input
              ref={inputRef}
              type="file"
              multiple
              accept=".pdf,.docx,.txt,.md"
              className="hidden"
              onChange={(e) => { handleFiles(e.target.files); e.target.value = ""; }}
            />
          </label>

          {uploading && (
            <div className="mt-3">
              <div className="flex items-center justify-between text-[11.5px] text-muted mb-1">
                <span>Indexing…</span>
                <span>{uploadProgress}%</span>
              </div>
              <div className="h-1.5 w-full rounded-full bg-elevated overflow-hidden">
                <div className="h-full bg-accent transition-all duration-200 rounded-full" style={{ width: `${uploadProgress}%` }} />
              </div>
            </div>
          )}
        </section>

        {/* --- Document list --- */}
        <section>
          <h2 className="text-[13px] font-medium text-muted uppercase tracking-wider mb-3">
            Knowledge base {documents.length > 0 && `(${documents.length})`}
          </h2>

          {docsLoading && (
            <div className="flex items-center gap-2 text-muted text-[13px] py-3">
              <Loader2 size={14} className="animate-spin" /> Loading…
            </div>
          )}

          {!docsLoading && documents.length === 0 && (
            <p className="text-[13px] text-muted py-3">No documents yet. Add one above.</p>
          )}

          <ul className="grid sm:grid-cols-2 gap-2.5">
            {documents.map((doc) => (
              <li
                key={doc.document_id}
                className="group flex items-center gap-3 rounded-xl border border-border bg-surface px-4 py-3 shadow-card"
              >
                <FileText size={16} className="text-accent shrink-0" />
                <p className="text-[13.5px] text-ink font-medium truncate flex-1" title={doc.filename}>
                  {doc.filename}
                </p>
                <button
                  onClick={() => handleDelete(doc.document_id)}
                  aria-label={`Delete ${doc.filename}`}
                  className="opacity-0 group-hover:opacity-100 transition-opacity text-muted hover:text-danger shrink-0"
                >
                  <X size={15} />
                </button>
              </li>
            ))}
          </ul>
        </section>

        {/* --- Debug retrieval tester --- */}
        <section>
          <h2 className="text-[13px] font-medium text-muted uppercase tracking-wider mb-3">
            Debug retrieval
          </h2>
          <form onSubmit={handleDebugQuery} className="flex gap-2 mb-4">
            <input
              value={debugQuestion}
              onChange={(e) => setDebugQuestion(e.target.value)}
              placeholder="Ask a test question to inspect retrieval…"
              className="flex-1 rounded-xl border border-border bg-surface px-3.5 py-2.5 text-[14px] text-ink
                placeholder:text-muted outline-none focus:border-accent/60 transition-colors"
            />
            <button
              type="submit"
              disabled={!debugQuestion.trim() || debugLoading}
              className="rounded-xl bg-navy text-white px-4 flex items-center gap-2 text-[13.5px] font-medium
                disabled:bg-border disabled:text-muted transition-colors"
            >
              {debugLoading ? <Loader2 size={14} className="animate-spin" /> : <Search size={14} />}
              Run
            </button>
          </form>

          {debugResult && (
            <div className="flex flex-col gap-3">
              {debugResult.standalone_question !== debugQuestion && (
                <p className="text-[12px] text-muted">
                  Interpreted as: <span className="text-ink font-medium">"{debugResult.standalone_question}"</span>
                </p>
              )}
              <div className="rounded-xl border border-border bg-surface shadow-card px-4 py-3 text-[14px] text-ink">
                {debugResult.answer}
              </div>
              {debugResult.sources.length === 0 && (
                <p className="text-[12.5px] text-muted">
                  No chunks cleared the similarity threshold — the assistant answered without grounding, or gave its "don't know" fallback.
                </p>
              )}
              <div className="grid sm:grid-cols-2 gap-2">
                {debugResult.sources.map((s, i) => (
                  <SourceChip key={i} source={s} />
                ))}
              </div>
            </div>
          )}
        </section>
      </main>
    </div>
  );
}

function StatCard({ label, value, icon: Icon }) {
  return (
    <div className="rounded-xl border border-border bg-surface shadow-card px-4 py-3 flex flex-col gap-1">
      <div className="flex items-center gap-1.5 text-muted">
        <Icon size={13} />
        <span className="text-[11px] uppercase tracking-wider">{label}</span>
      </div>
      <span className="text-[18px] font-semibold text-ink font-mono">{value}</span>
    </div>
  );
}
