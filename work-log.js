const workLogSummary = document.querySelector("[data-work-log-summary]");
const workLogList = document.querySelector("[data-work-log-list]");
const workLogData = window.WORK_LOG_DATA || { generatedAt: null, entries: [] };

if (workLogSummary) {
  workLogSummary.textContent = buildSummary(workLogData);
}

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

function buildSummary(data) {
  if (!data.generatedAt) {
    return "No generated work log data found yet.";
  }

  const entryCount = Array.isArray(data.entries) ? data.entries.length : 0;
  const projectCount = data.projectCount || 0;
  const structuredCount = data.structuredProjectCount || 0;
  const gitFallbackCount = data.gitFallbackProjectCount || 0;

  return [
    `Updated ${formatDateTime(data.generatedAt)}.`,
    `${entryCount} chronological entries across ${projectCount} projects.`,
    structuredCount > 0
      ? `${structuredCount} project${structuredCount === 1 ? "" : "s"} using structured Codex notes.`
      : "No structured Codex notes yet.",
    gitFallbackCount > 0
      ? `${gitFallbackCount} project${gitFallbackCount === 1 ? "" : "s"} currently using git history as fallback.`
      : ""
  ]
    .filter(Boolean)
    .join(" ");
}

function renderEntry(entry) {
  const project = escapeHtml(entry.project || "Project");
  const title = escapeHtml(entry.title || "Project activity");
  const summary = entry.summary ? `<p class="log-entry-summary">${escapeHtml(entry.summary)}</p>` : "";
  const source = escapeHtml(entry.sourceLabel || "Generated activity");
  const workedOn = renderListSection("Worked on", entry.workedOn || []);
  const issues = renderIssuesSection(entry.issues || []);
  const goals = renderListSection("Goals reached", entry.goals || []);
  const repoLink = entry.repoUrl
    ? `<a class="log-entry-link" href="${escapeHtml(entry.repoUrl)}" target="_blank" rel="noopener">Repo</a>`
    : "";

  return `
    <article class="log-entry">
      <header class="log-entry-header">
        <div>
          <div class="log-entry-meta">
            <span>${formatDate(entry.date || entry.timestamp)}</span>
            <span>${project}</span>
            <span>${source}</span>
          </div>
          <h2 class="log-entry-title">${title}</h2>
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

function formatDate(value) {
  if (!value) {
    return "Unknown date";
  }

  const normalized = /^\d{4}-\d{2}-\d{2}$/.test(value) ? `${value}T12:00:00` : value;

  return new Intl.DateTimeFormat("en-AU", {
    day: "numeric",
    month: "short",
    year: "numeric"
  }).format(new Date(normalized));
}

function formatDateTime(value) {
  return new Intl.DateTimeFormat("en-AU", {
    day: "numeric",
    month: "short",
    year: "numeric",
    hour: "numeric",
    minute: "2-digit"
  }).format(new Date(value));
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}
