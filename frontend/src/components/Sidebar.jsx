import { useRef, useState } from "react";
import { FileText, Upload, X, Loader2, FileWarning } from "lucide-react";

function formatChunkLabel(count) {
  return `${count} chunk${count === 1 ? "" : "s"}`;
}

export default function Sidebar({ documents, loading, uploading, uploadProgress, onUpload, onDelete }) {
  const [dragOver, setDragOver] = useState(false);
  const inputRef = useRef(null);

  const handleFiles = (files) => {
    if (!files || files.length === 0) return;
    // Upload sequentially so progress reporting stays simple and predictable.
    Array.from(files).forEach((file) => onUpload(file));
  };

  return (
    <aside className="w-[300px] shrink-0 h-full flex flex-col bg-surface border-r border-border">
      <div className="px-5 pt-6 pb-4">
        <h1 className="text-[15px] font-semibold tracking-tight text-ink">Knowledge base</h1>
        <p className="text-[12.5px] text-muted mt-1 leading-relaxed">
          Answers are grounded only in what you add here.
        </p>
      </div>

      <div className="px-4">
        <label
          onDragOver={(e) => {
            e.preventDefault();
            setDragOver(true);
          }}
          onDragLeave={() => setDragOver(false)}
          onDrop={(e) => {
            e.preventDefault();
            setDragOver(false);
            handleFiles(e.dataTransfer.files);
          }}
          className={`flex flex-col items-center justify-center gap-2 rounded-xl border border-dashed
            px-4 py-6 cursor-pointer transition-colors
            ${dragOver ? "border-accent bg-accent-dim/30" : "border-border hover:border-muted"}`}
        >
          <Upload size={18} className={dragOver ? "text-accent" : "text-muted"} />
          <span className="text-[12.5px] text-muted text-center leading-relaxed">
            Drop files or <span className="text-accent-soft">browse</span>
            <br />
            PDF, DOCX, TXT, MD · 20MB max
          </span>
          <input
            ref={inputRef}
            type="file"
            multiple
            accept=".pdf,.docx,.txt,.md"
            className="hidden"
            onChange={(e) => {
              handleFiles(e.target.files);
              e.target.value = "";
            }}
          />
        </label>

        {uploading && (
          <div className="mt-3 px-1">
            <div className="flex items-center justify-between text-[11.5px] text-muted mb-1">
              <span>Indexing…</span>
              <span>{uploadProgress}%</span>
            </div>
            <div className="h-1 w-full rounded-full bg-elevated overflow-hidden">
              <div
                className="h-full bg-accent transition-all duration-200"
                style={{ width: `${uploadProgress}%` }}
              />
            </div>
          </div>
        )}
      </div>

      <div className="flex-1 overflow-y-auto px-4 mt-5 pb-4">
        <div className="text-[11px] uppercase tracking-wider text-muted/70 font-medium px-1 mb-2">
          Documents {documents.length > 0 && `(${documents.length})`}
        </div>

        {loading && (
          <div className="flex items-center gap-2 text-muted text-[13px] px-1 py-3">
            <Loader2 size={14} className="animate-spin" />
            Loading…
          </div>
        )}

        {!loading && documents.length === 0 && (
          <div className="flex flex-col items-center text-center gap-2 px-3 py-8 text-muted">
            <FileWarning size={20} className="opacity-50" />
            <p className="text-[12.5px] leading-relaxed">
              No documents yet. Add one above to start asking questions.
            </p>
          </div>
        )}

        <ul className="flex flex-col gap-1">
          {documents.map((doc) => (
            <li
              key={doc.document_id}
              className="group flex items-start gap-2.5 rounded-lg px-2.5 py-2.5 hover:bg-elevated transition-colors"
            >
              <FileText size={15} className="text-muted mt-0.5 shrink-0" />
              <div className="min-w-0 flex-1">
                <p className="text-[13px] text-ink truncate" title={doc.filename}>
                  {doc.filename}
                </p>
                <p className="text-[11.5px] text-muted mt-0.5 font-mono">
                  {formatChunkLabel(doc.chunk_count)}
                </p>
              </div>
              <button
                onClick={() => onDelete(doc.document_id)}
                aria-label={`Remove ${doc.filename}`}
                className="opacity-0 group-hover:opacity-100 transition-opacity text-muted hover:text-danger shrink-0 mt-0.5"
              >
                <X size={14} />
              </button>
            </li>
          ))}
        </ul>
      </div>
    </aside>
  );
}
