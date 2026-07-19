/**
 * Groups raw flagged-question rows (one row per time a question was asked)
 * into one entry per distinct question, with aggregated stats. Grouping by
 * standalone_question (not the raw question) so "hostel fee?" and "what's
 * the fee for hostel?" — which the backend already normalized to the same
 * standalone form during condensing — count as the same question.
 */
export function groupFlaggedQuestions(rows) {
  const groups = new Map();

  for (const row of rows) {
    const key = row.standalone_question;
    if (!groups.has(key)) {
      groups.set(key, {
        standalone_question: key,
        question: row.question, // display the first-seen original phrasing
        occurrences: [],
      });
    }
    groups.get(key).occurrences.push(row);
  }

  return Array.from(groups.values()).map((g) => {
    const occurrences = g.occurrences;
    const openRows = occurrences.filter((r) => !r.resolved);
    const scores = occurrences.map((r) => r.top_score).filter((s) => s != null);
    const avgScore = scores.length > 0 ? scores.reduce((a, b) => a + b, 0) / scores.length : null;
    const lastAsked = Math.max(...occurrences.map((r) => r.created_at));
    const anyNotified = occurrences.some((r) => r.notified_at != null);

    return {
      standalone_question: g.standalone_question,
      question: g.question,
      count: occurrences.length,
      lastAsked,
      avgScore,
      notified: anyNotified,
      status: openRows.length > 0 ? "open" : "resolved",
      openIds: openRows.map((r) => r.id),
    };
  });
}

export function filterFlaggedGroups(groups, { search, statusFilter }) {
  let result = groups;

  if (statusFilter === "open") result = result.filter((g) => g.status === "open");
  else if (statusFilter === "resolved") result = result.filter((g) => g.status === "resolved");
  else if (statusFilter === "notified") result = result.filter((g) => g.notified);
  else if (statusFilter === "unnotified") result = result.filter((g) => !g.notified);

  if (search && search.trim()) {
    const q = search.trim().toLowerCase();
    result = result.filter(
      (g) => g.question.toLowerCase().includes(q) || g.standalone_question.toLowerCase().includes(q)
    );
  }

  return result;
}

export function computeFlaggedStats(groups) {
  const openGroups = groups.filter((g) => g.status === "open");
  const resolvedGroups = groups.filter((g) => g.status === "resolved");

  const mostFrequent = openGroups.length > 0
    ? openGroups.reduce((max, g) => (g.count > max.count ? g : max), openGroups[0])
    : null;

  const openScores = openGroups.map((g) => g.avgScore).filter((s) => s != null);
  const avgConfidence = openScores.length > 0
    ? openScores.reduce((a, b) => a + b, 0) / openScores.length
    : null;

  return {
    openCount: openGroups.length,
    resolvedCount: resolvedGroups.length,
    mostFrequent,
    avgConfidence,
  };
}
