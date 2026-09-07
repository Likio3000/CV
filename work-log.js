const workLogList = document.querySelector("[data-work-log-list]");
const workLogHeatmap = document.querySelector("[data-work-log-heatmap]");
const workLogData = window.WORK_LOG_DATA || { entries: [] };
const archiveNote = document.querySelector("[data-archive-note]");
if (
  archiveNote &&
  workLogData.generatedAt &&
  !Number.isNaN(Date.parse(workLogData.generatedAt))
) {
  const published = new Intl.DateTimeFormat("en-AU", {
    day: "numeric",
    month: "long",
    year: "numeric",
  }).format(new Date(workLogData.generatedAt));
  archiveNote.textContent = `Historical snapshot exported ${published}. This is not a live activity feed.`;
}

if (workLogList) {
  if (!Array.isArray(workLogData.entries) || workLogData.entries.length === 0) {
    workLogList.innerHTML = `
      <article class="log-entry log-entry-empty">
        <div class="log-entry-card">
          <h2>No activity yet</h2>
          <p>The selected development history will appear here when it is published. Explore the portfolio for the current projects.</p>
        </div>
      </article>
    `;
  } else {
    workLogList.innerHTML = workLogData.entries.map(renderEntry).join("");
  }
}

if (workLogHeatmap) {
  renderHeatmap(workLogHeatmap, workLogData);
}

function renderEntry(entry) {
  const family = escapeHtml(entry.projectFamily || "");
  const project = escapeHtml(entry.project || "Project");
  const title = escapeHtml(entry.title || "Project activity");
  const summary = entry.summary
    ? `<p class="log-entry-summary">${escapeHtml(entry.summary)}</p>`
    : "";
  const workedOn = renderListSection("Worked on", entry.workedOn || []);
  const issues = renderIssuesSection(entry.issues || []);
  const goals = renderListSection("Goals reached", entry.goals || []);
  const lineStats = renderLineStats(entry.lineStats);
  const timestamp = formatTimestamp(entry.timestamp || entry.date);
  const repository = safeRepositoryUrl(entry.repoUrl);
  const repoLink = repository
    ? `<a class="log-entry-link" href="${escapeHtml(repository)}" target="_blank" rel="noopener">Repo</a>`
    : "";
  const familyPill =
    family && family !== project
      ? `<span class="log-entry-meta-family">${family}</span>`
      : "";

  return `
    <article class="log-entry">
      <div class="log-entry-stamp">${formatTimelineStamp(timestamp)}</div>
      <div class="log-entry-card">
        <header class="log-entry-header">
          <div class="log-entry-main">
            <div class="log-entry-meta">
              ${familyPill}
              <span class="log-entry-meta-project">${project}</span>
            </div>
            <div class="log-entry-title-row">
              <h2 class="log-entry-title">${title}</h2>
              ${lineStats}
            </div>
          </div>
          ${repoLink}
        </header>
        ${summary}
        ${workedOn}
        ${issues}
        ${goals}
      </div>
    </article>
  `;
}

function renderHeatmap(container, data) {
  const entries = Array.isArray(data.entries) ? data.entries : [];
  const startDate = toDateOnly(data.publishedSince || "2026-01-01");
  const today = toDateOnly(data.generatedAt || new Date().toISOString());
  const endDate = endOfYear(today);
  const dayCounts = buildDayCounts(entries, startDate, today);
  const weeks = buildWeeks(startDate, endDate, today, dayCounts);
  const totalCommits = [...dayCounts.values()].reduce(
    (sum, count) => sum + count,
    0,
  );
  const activeDays = [...dayCounts.values()].filter(
    (count) => count > 0,
  ).length;
  const monthLabels = buildMonthLabels(weeks, startDate, endDate);

  container.innerHTML = `
    <div class="worklog-heatmap-header">
      <div>
        <p class="worklog-heatmap-kicker">Commit Map</p>
        <p class="worklog-heatmap-range">${formatShortDate(startDate)} to ${formatShortDate(endDate)}</p>
      </div>
      <p class="worklog-heatmap-summary">${totalCommits} commits across ${activeDays} active days</p>
    </div>
    <div class="worklog-heatmap-scroller">
      <div class="worklog-heatmap-layout" style="--heatmap-cols:${weeks.length};">
        <div class="worklog-heatmap-months">
          ${monthLabels}
        </div>
        <div class="worklog-heatmap-body">
          <div class="worklog-heatmap-days" aria-hidden="true">
            <span></span>
            <span>Mon</span>
            <span></span>
            <span>Wed</span>
            <span></span>
            <span>Fri</span>
            <span></span>
          </div>
          <div class="worklog-heatmap-grid" role="img" aria-label="${totalCommits} recorded commits across ${activeDays} active days in this archive. A daily table follows.">
            ${weeks.map((week) => renderWeek(week)).join("")}
          </div>
        </div>
      </div>
    </div>
    <details class="activity-table">
      <summary>Read activity by day</summary>
      <table>
        <caption>Days with recorded activity in this snapshot</caption>
        <thead><tr><th scope="col">Date</th><th scope="col">Recorded commits</th></tr></thead>
        <tbody>${[...dayCounts.entries()]
          .sort(([a], [b]) => a.localeCompare(b))
          .map(
            ([date, count]) =>
              `<tr><th scope="row">${escapeHtml(formatLongDate(toDateOnly(date)))}</th><td>${count}</td></tr>`,
          )
          .join("")}</tbody>
      </table>
    </details>
  `;
}

function buildDayCounts(entries, startDate, endDate) {
  const counts = new Map();

  entries.forEach((entry) => {
    const rawDate = entry.date || entry.timestamp;
    if (!rawDate) {
      return;
    }

    const date = toDateOnly(rawDate);
    if (date < startDate || date > endDate) {
      return;
    }

    const key = formatDateKey(date);
    counts.set(key, (counts.get(key) || 0) + 1);
  });

  return counts;
}

function buildWeeks(startDate, endDate, today, dayCounts) {
  const firstCell = startOfWeek(startDate);
  const lastCell = endOfWeek(endDate);
  const weeks = [];
  let cursor = new Date(firstCell);

  while (cursor <= lastCell) {
    const week = [];

    for (let index = 0; index < 7; index += 1) {
      const current = new Date(cursor);
      const key = formatDateKey(current);
      const count = dayCounts.get(key) || 0;
      week.push({
        date: current,
        count,
        inRange: current >= startDate && current <= endDate,
        isFuture: current > today,
      });
      cursor.setDate(cursor.getDate() + 1);
    }

    weeks.push(week);
  }

  return weeks;
}

function buildMonthLabels(weeks, startDate, endDate) {
  const labels = [
    "Jan",
    "Feb",
    "Mar",
    "Apr",
    "May",
    "Jun",
    "Jul",
    "Aug",
    "Sep",
    "Oct",
    "Nov",
    "Dec",
  ];
  let lastLabel = "";

  return weeks
    .map((week, index) => {
      const anchorDay = week.find(
        (day) =>
          day.inRange &&
          day.date.getDate() <= 7 &&
          day.date >= startDate &&
          day.date <= endDate,
      );

      if (!anchorDay) {
        return "";
      }

      const label = labels[anchorDay.date.getMonth()];
      if (label === lastLabel) {
        return "";
      }

      lastLabel = label;
      return `<span style="grid-column:${index + 1}">${escapeHtml(label)}</span>`;
    })
    .join("");
}

function renderWeek(week) {
  return `
    <div class="worklog-heatmap-week">
      ${week.map((day) => renderHeatmapCell(day)).join("")}
    </div>
  `;
}

function renderHeatmapCell(day) {
  const classes = ["worklog-heatmap-cell", `level-${heatmapLevel(day.count)}`];
  if (!day.inRange) {
    classes.push("out-of-range");
  }
  if (day.isFuture) {
    classes.push("future");
  }

  const commitLabel = day.isFuture
    ? "future timeline slot"
    : day.count === 1
      ? "1 commit"
      : `${day.count} commits`;
  const label = `${formatLongDate(day.date)}: ${commitLabel}`;

  return `<span class="${classes.join(" ")}" title="${escapeHtml(label)}" aria-hidden="true"></span>`;
}

function heatmapLevel(count) {
  if (count <= 0) {
    return 0;
  }
  if (count === 1) {
    return 1;
  }
  if (count <= 2) {
    return 2;
  }
  if (count <= 4) {
    return 3;
  }
  return 4;
}

function startOfWeek(date) {
  const result = new Date(date);
  result.setDate(result.getDate() - result.getDay());
  return result;
}

function endOfWeek(date) {
  const result = new Date(date);
  result.setDate(result.getDate() + (6 - result.getDay()));
  return result;
}

function endOfYear(date) {
  return new Date(date.getFullYear(), 11, 31);
}

function toDateOnly(value) {
  const date = value instanceof Date ? new Date(value) : new Date(value);
  return new Date(date.getFullYear(), date.getMonth(), date.getDate());
}

function formatDateKey(date) {
  return [
    date.getFullYear(),
    String(date.getMonth() + 1).padStart(2, "0"),
    String(date.getDate()).padStart(2, "0"),
  ].join("-");
}

function formatShortDate(date) {
  return new Intl.DateTimeFormat("en-AU", {
    day: "numeric",
    month: "short",
    year: "numeric",
  }).format(date);
}

function formatLongDate(date) {
  return new Intl.DateTimeFormat("en-AU", {
    day: "numeric",
    month: "short",
    year: "numeric",
  }).format(date);
}

function formatTimelineStamp(value) {
  return value.replace(",", " at").replace(/\s/g, " ").toUpperCase();
}

function renderLineStats(lineStats) {
  if (!lineStats || typeof lineStats !== "object") {
    return "";
  }

  const additions = Number.isFinite(Number(lineStats.added))
    ? Number(lineStats.added)
    : null;
  const deletions = Number.isFinite(Number(lineStats.deleted))
    ? Number(lineStats.deleted)
    : null;

  if (additions === null && deletions === null) {
    return "";
  }

  return `
    <div class="log-entry-commit-stats" aria-label="Commit line counts">
      ${additions !== null ? `<span class="log-entry-stat log-entry-stat-add">+${additions}</span>` : ""}
      ${deletions !== null ? `<span class="log-entry-stat log-entry-stat-del">-${deletions}</span>` : ""}
    </div>
  `;
}

function renderListSection(label, items) {
  if (!Array.isArray(items) || items.length === 0) {
    return "";
  }

  return `
    <section class="log-entry-section">
      <h3>${escapeHtml(label)}</h3>
      <ul>
        ${items.map((item) => `<li>${escapeHtml(item)}</li>`).join("")}
      </ul>
    </section>
  `;
}

function renderIssuesSection(items) {
  if (!Array.isArray(items) || items.length === 0) {
    return "";
  }

  return `
    <section class="log-entry-section">
      <h3>Issues and resolutions</h3>
      <ul class="log-issue-list">
        ${items
          .map((item) => {
            const issue = escapeHtml(item.issue || "Issue");
            const resolution = escapeHtml(item.resolution || "");

            return `
              <li>
                <strong>${issue}</strong>
                ${resolution ? `<span>${resolution}</span>` : ""}
              </li>
            `;
          })
          .join("")}
      </ul>
    </section>
  `;
}

function formatTimestamp(value) {
  if (!value) {
    return "Unknown date";
  }

  const normalized = /^\d{4}-\d{2}-\d{2}$/.test(value)
    ? `${value}T12:00:00`
    : value;

  return new Intl.DateTimeFormat("en-AU", {
    day: "numeric",
    month: "short",
    year: "numeric",
    hour: "numeric",
    minute: "2-digit",
  }).format(new Date(normalized));
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

// Accept only canonical GitHub repository URLs, never arbitrary link schemes.
function safeRepositoryUrl(value) {
  if (typeof value !== "string") return null;
  const match = /^https:\/\/github\.com\/Likio3000\/([A-Za-z0-9_.-]+)\/?$/.exec(
    value,
  );
  return match && match[1] !== "." && match[1] !== ".."
    ? `https://github.com/Likio3000/${match[1]}`
    : null;
}
