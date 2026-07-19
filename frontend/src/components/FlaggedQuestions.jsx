import { useEffect, useState, useCallback, useMemo } from "react";
import { AlertTriangle, CheckCircle2, Mail, MailX, Loader2, Search, TrendingUp } from "lucide-react";
import { adminListUnanswered, adminResolveUnansweredGroup } from "../lib/api";
import { groupFlaggedQuestions, filterFlaggedGroups, computeFlaggedStats } from "../lib/groupFlagged";

const FILTERS = [
  { value: "open", label: "Open" },
  { value: "resolved", label: "Resolved" },
  { value: "notified", label: "Notified" },
  { value: "unnotified", label: "Unnotified" },
  { value: "all", label: "All" },
];

function timeAgo(unixSeconds) {
  const diffMs = Date.now() - unixSeconds * 1000;
  const mins = Math.floor(diffMs / 60000);
  if (mins < 1) return "just now";
  if (mins < 60) return `${mins}m ago`;
  const hours = Math.floor(mins / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.floor(hours / 24);
  return `${days}d ago`;
}

export default function FlaggedQuestions({ adminKey, onError }) {
  const [rows, setRows] = useState([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState("open");
  const [resolvingKey, setResolvingKey] = useState(null);

  const refresh = useCallback(async () => {
    try {
      const data = await adminListUnanswered(adminKey);
      setRows(data);
    } catch (err) {
      onError?.(`Couldn't load flagged questions: ${err.message}`);
    } finally {
      setLoading(false);
    }
  }, [adminKey, onError]);

  useEffect(() => {
    refresh();
  }, [refresh]);

  const groups = useMemo(() => groupFlaggedQuestions(rows), [rows]);
  const stats = useMemo(() => computeFlaggedStats(groups), [groups]);
  const visible = useMemo(
    () => filterFlaggedGroups(groups, { search, statusFilter }).sort((a, b) => b.lastAsked - a.lastAsked),
    [groups, search, statusFilter]
  );

  const handleResolve = async (group) => {
    setResolvingKey(group.standalone_question);
    try {
      await adminResolveUnansweredGroup(adminKey, group.standalone_question);
      await refresh();
    } catch (err) {
      onError?.(`Couldn't resolve: ${err.message}`);
    } finally {
      setResolvingKey(null);
    }
  };

  return (
    <section>
      <h2 className="text-[13px] font-medium text-muted uppercase tracking-wider mb-3">Flagged Questions</h2>

      {/* Stats */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-4">
        <StatCard label="Open" value={stats.openCount} icon={AlertTriangle} />
        <StatCard label="Resolved" value={stats.resolvedCount} icon={CheckCircle2} />
        <StatCard
          label="Most asked"
          value={stats.mostFrequent ? `${stats.mostFrequent.count}×` : "—"}
          detail={stats.mostFrequent?.question}
          icon={TrendingUp}
        />
        <StatCard
          label="Avg. confidence"
          value={stats.avgConfidence != null ? `${Math.round(stats.avgConfidence * 100)}%` : "—"}
          icon={AlertTriangle}
        />
      </div>

      {/* Search + filters */}
      <div className="flex flex-col sm:flex-row gap-2 mb-3">
        <div className="relative flex-1">
          <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-muted" />
          <input
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search flagged questions…"
            className="w-full rounded-xl border border-border bg-surface pl-9 pr-3 py-2 text-[13.5px] text-ink
              placeholder:text-muted outline-none focus:border-accent/60 transition-colors"
          />
        </div>
        <div className="flex gap-1.5 flex-wrap">
          {FILTERS.map((f) => (
            <button
              key={f.value}
              onClick={() => setStatusFilter(f.value)}
              className={`px-3 py-2 rounded-xl text-[12.5px] font-medium transition-colors
                ${statusFilter === f.value
                  ? "bg-navy text-white"
                  : "bg-elevated text-muted hover:text-ink"}`}
            >
              {f.label}
            </button>
          ))}
        </div>
      </div>

      {/* List */}
      {loading && (
        <div className="flex items-center gap-2 text-muted text-[13px] py-3">
          <Loader2 size={14} className="animate-spin" /> Loading…
        </div>
      )}

      {!loading && visible.length === 0 && (
        <p className="text-[13px] text-muted py-3">
          {statusFilter === "open" ? "No open flagged questions — the knowledge base is covering everything asked so far." : "Nothing matches here."}
        </p>
      )}

      <ul className="flex flex-col gap-2">
        {visible.map((g) => (
          <li
            key={g.standalone_question}
            className="rounded-xl border border-border bg-surface shadow-card px-4 py-3 flex flex-col gap-2"
          >
            <div className="flex items-start justify-between gap-3">
              <p className="text-[14px] text-ink font-medium leading-snug">{g.question}</p>
              {g.status === "open" ? (
                <button
                  onClick={() => handleResolve(g)}
                  disabled={resolvingKey === g.standalone_question}
                  className="shrink-0 rounded-lg bg-navy text-white text-[12px] font-medium px-3 py-1.5
                    disabled:bg-border disabled:text-muted transition-colors flex items-center gap-1.5"
                >
                  {resolvingKey === g.standalone_question ? <Loader2 size={12} className="animate-spin" /> : <CheckCircle2 size={12} />}
                  Resolve
                </button>
              ) : (
                <span className="shrink-0 rounded-lg bg-elevated text-muted text-[12px] font-medium px-3 py-1.5 flex items-center gap-1.5">
                  <CheckCircle2 size={12} /> Resolved
                </span>
              )}
            </div>
            <div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-[12px] text-muted">
              <span>Asked {g.count} time{g.count === 1 ? "" : "s"}</span>
              <span>Last asked {timeAgo(g.lastAsked)}</span>
              {g.avgScore != null && <span>Confidence ~{Math.round(g.avgScore * 100)}%</span>}
              <span className="flex items-center gap-1">
                {g.notified ? <Mail size={12} /> : <MailX size={12} />}
                {g.notified ? "Notified" : "Not notified"}
              </span>
            </div>
          </li>
        ))}
      </ul>
    </section>
  );
}

function StatCard({ label, value, detail, icon: Icon }) {
  return (
    <div className="rounded-xl border border-border bg-surface shadow-card px-4 py-3 flex flex-col gap-1 min-w-0">
      <div className="flex items-center gap-1.5 text-muted">
        <Icon size={13} />
        <span className="text-[11px] uppercase tracking-wider">{label}</span>
      </div>
      <span className="text-[18px] font-semibold text-ink font-mono">{value}</span>
      {detail && <span className="text-[11px] text-muted truncate" title={detail}>{detail}</span>}
    </div>
  );
}
