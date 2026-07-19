import { FileText, TrendingUp, TrendingDown } from "lucide-react";

export default function SourceChip({ source }) {
  const percent = Math.round(source.score * 100);
  const boost = source.boost || 0;

  return (
    <div className="flex flex-col gap-1 rounded-xl border border-border bg-elevated px-3 py-2 text-[12px]">
      <div className="flex items-center gap-2">
        <FileText size={12} className="text-accent shrink-0" />
        <span className="text-ink/90 font-medium truncate" title={source.filename}>
          {source.filename}
        </span>
        <span className="ml-auto flex items-center gap-1.5 text-muted font-mono text-[10.5px] tabular-nums">
          chunk #{source.chunk_index} · {percent}%
          {boost !== 0 && (
            <span className={`flex items-center gap-0.5 ${boost > 0 ? "text-emerald-500" : "text-danger"}`}>
              {boost > 0 ? <TrendingUp size={10} /> : <TrendingDown size={10} />}
              {boost > 0 ? `+${boost}` : boost}
            </span>
          )}
        </span>
      </div>
      <div className="h-1 w-full rounded-full bg-border overflow-hidden">
        <div className="h-full bg-accent rounded-full" style={{ width: `${percent}%` }} />
      </div>
      <p className="text-muted text-[11.5px] leading-relaxed line-clamp-3 font-mono">{source.text}</p>
    </div>
  );
}
