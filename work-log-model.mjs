const projects = new Map([
  ["Alpha_Evolve", "Alpha Evolve"],
  ["vic-energy-demand-case-study", "VIC Energy Demand"],
  ["typing-quest", "Typing Quest"],
  ["pomodoroAPP", "Senda"],
]);

export function safeRepositoryUrl(value) {
  const match =
    typeof value === "string" &&
    /^https:\/\/github\.com\/Likio3000\/([\w.-]+)\/?$/.exec(value);
  return match && projects.has(match[1])
    ? `https://github.com/Likio3000/${match[1]}`
    : null;
}

export function dateOnly(value) {
  if (typeof value !== "string") return null;
  const match = /^(\d{4}-\d{2}-\d{2})(?:T.*)?$/.exec(value);
  if (!match || !Number.isFinite(Date.parse(value))) return null;
  const date = new Date(`${match[1]}T12:00:00Z`);
  return Number.isFinite(date.getTime()) &&
    date.toISOString().slice(0, 10) === match[1]
    ? match[1]
    : null;
}

export function formatDate(value) {
  const date = dateOnly(value);
  return date
    ? new Intl.DateTimeFormat("en-AU", {
        day: "numeric",
        month: "short",
        year: "numeric",
        timeZone: "UTC",
      }).format(new Date(`${date}T12:00:00Z`))
    : null;
}

const text = (value) => (typeof value === "string" ? value.trim() : "");
const textList = (value) =>
  Array.isArray(value) ? value.map(text).filter(Boolean) : [];

export function normalizeEntries(source) {
  if (!Array.isArray(source)) return [];
  return source
    .flatMap((entry) => {
      if (!entry || typeof entry !== "object") return [];
      const repoUrl = safeRepositoryUrl(entry.repoUrl);
      const date = dateOnly(entry.date || entry.timestamp);
      if (!repoUrl || !date) return [];
      const slug = repoUrl.split("/").at(-1);
      const commitHash =
        typeof entry.commitHash === "string" &&
        /^[a-f\d]{7,40}$/i.test(entry.commitHash)
          ? entry.commitHash
          : null;
      const stats = entry.lineStats;
      const lineStats =
        stats &&
        ["added", "deleted"].every(
          (key) => Number.isSafeInteger(stats[key]) && stats[key] >= 0,
        )
          ? { added: stats.added, deleted: stats.deleted }
          : null;
      return [
        {
          date,
          slug,
          repoUrl,
          commitHash,
          lineStats,
          project: projects.get(slug),
          link: commitHash ? `${repoUrl}/commit/${commitHash}` : repoUrl,
          title: text(entry.title) || "Project activity",
          summary: text(entry.summary),
          workedOn: textList(entry.workedOn),
          goals: textList(entry.goals),
          issues: Array.isArray(entry.issues)
            ? entry.issues.flatMap((issue) =>
                issue && typeof issue === "object"
                  ? [text(issue.issue), text(issue.resolution)]
                      .filter(Boolean)
                      .join(" — ") || []
                  : [],
              )
            : [],
          sortTime: Date.parse(entry.timestamp || date) || Date.parse(date),
        },
      ];
    })
    .sort((a, b) => b.date.localeCompare(a.date) || b.sortTime - a.sortTime);
}

export function selectEntries(entries, selected = "all", limit = 12) {
  const filtered =
    selected === "all"
      ? entries
      : entries.filter((entry) => entry.slug === selected);
  const size = Number.isSafeInteger(limit) && limit > 0 ? limit : 12;
  return {
    visible: filtered.slice(0, size),
    total: filtered.length,
    hasMore: filtered.length > size,
  };
}
