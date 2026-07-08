import { FileText } from "lucide-react";

// Signature element: a small relevance bar next to each cited source,
// so the person can see at a glance how strongly each chunk matched
// their question, not just that it was "used."
export default function SourceChip({ source }) {
  const percent = Math.round(source.score * 100);

  return (
    <div className="flex items-center gap-2 rounded-lg border border-border bg-elevated px-2.5 py-1.5 text-[12px]">
      <FileText size={12} className="text-muted shrink-0" />
      <span className="text-ink/90 truncate max-w-[140px]" title={source.filename}>
        {source.filename}
      </span>
      <div className="flex items-center gap-1.5 ml-auto">
        <div className="w-10 h-1 rounded-full bg-border overflow-hidden">
          <div className="h-full bg-accent" style={{ width: `${percent}%` }} />
        </div>
        <span className="text-muted font-mono text-[10.5px] tabular-nums">{percent}%</span>
      </div>
    </div>
  );
}
