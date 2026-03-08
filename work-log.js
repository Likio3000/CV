const workLogList = document.querySelector("[data-work-log-list]");
const workLogData = window.WORK_LOG_DATA || { entries: [] };

if (workLogList) {
  if (!Array.isArray(workLogData.entries) || workLogData.entries.length === 0) {
    workLogList.innerHTML = `
      <article class="log-entry log-entry-empty">
        <h2>No activity yet</h2>
        <p>Run the work log generator after adding project paths to start publishing activity here.</p>
      </article>
    `;
  } else {
    workLogList.innerHTML = workLogData.entries.map(renderEntry).join("");
  }
}

function renderEntry(entry) {
  const project = escapeHtml(entry.project || "Project");
  const title = escapeHtml(entry.title || "Project activity");
  const summary = entry.summary ? `<p class="log-entry-summary">${escapeHtml(entry.summary)}</p>` : "";
  const workedOn = renderListSection("Worked on", entry.workedOn || []);
  const issues = renderIssuesSection(entry.issues || []);
  const goals = renderListSection("Goals reached", entry.goals || []);
  const lineStats = renderLineStats(entry.lineStats);
  const repoLink = entry.repoUrl
    ? `<a class="log-entry-link" href="${escapeHtml(entry.repoUrl)}" target="_blank" rel="noopener">Repo</a>`
    : "";

  return `
    <article class="log-entry">
      <header class="log-entry-header">
        <div class="log-entry-main">
          <div class="log-entry-meta">
            <span>${formatTimestamp(entry.timestamp || entry.date)}</span>
            <span>${project}</span>
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
    </article>
  `;
}

function renderLineStats(lineStats) {
  if (!lineStats || typeof lineStats !== "object") {
    return "";
  }

  const additions = Number.isFinite(Number(lineStats.added)) ? Number(lineStats.added) : null;
  const deletions = Number.isFinite(Number(lineStats.deleted)) ? Number(lineStats.deleted) : null;

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

  const normalized = /^\d{4}-\d{2}-\d{2}$/.test(value) ? `${value}T12:00:00` : value;

  return new Intl.DateTimeFormat("en-AU", {
    day: "numeric",
    month: "short",
    year: "numeric",
    hour: "numeric",
    minute: "2-digit"
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
