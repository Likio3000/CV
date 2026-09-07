import {
  normalizeEntries,
  selectEntries,
  formatDate,
} from "./work-log-model.mjs";

const data = window.WORK_LOG_DATA || {};
const entries = normalizeEntries(data.entries);
const list = document.querySelector("[data-work-log-list]");
const filters = document.querySelector("[data-project-filters]");
const controls = document.querySelector("[data-archive-controls]");
const count = document.querySelector("[data-results-count]");
const more = document.querySelector("[data-load-more]");
const projects = [
  ...new Map(entries.map((entry) => [entry.slug, entry.project])).entries(),
];
let selected = new URL(location.href).searchParams.get("project") || "all";
if (!projects.some(([slug]) => slug === selected)) selected = "all";
let limit = 12;

const archiveDate = formatDate(data.generatedAt);
if (archiveDate)
  document.querySelector("[data-archive-note]").textContent =
    `Selected changes from public projects. Exported ${archiveDate}.`;

function escapeHtml(value) {
  return String(value).replace(
    /[&<>"']/g,
    (char) =>
      ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[
        char
      ],
  );
}
const arrow =
  '<svg class="icon" viewBox="0 0 20 20" fill="none" aria-hidden="true"><path d="M4 10h12m-5-5 5 5-5 5" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/></svg>';
function details(entry) {
  const sections = [
    ["Worked on", entry.workedOn],
    ["Issues & resolutions", entry.issues],
    ["Goals reached", entry.goals],
  ];
  const html = sections
    .filter(([, items]) => items.length)
    .map(
      ([label, items]) =>
        `<h4>${label}</h4><ul>${items.map((item) => `<li>${escapeHtml(item)}</li>`).join("")}</ul>`,
    )
    .join("");
  return html
    ? `<details class="log-details"><summary>Read development notes</summary>${html}</details>`
    : "";
}
function renderEntry(entry) {
  const stats = entry.lineStats
    ? `<span class="log-change" aria-label="${entry.lineStats.added} lines added, ${entry.lineStats.deleted} lines deleted">+${entry.lineStats.added.toLocaleString("en-AU")} / −${entry.lineStats.deleted.toLocaleString("en-AU")}</span>`
    : '<span class="log-change"></span>';
  return `<article class="log-entry"><time class="log-date" datetime="${entry.date}">${formatDate(entry.date).toUpperCase()}</time><div><span class="log-project">${entry.project}</span><h3 class="log-title" tabindex="-1">${escapeHtml(entry.title)}</h3>${entry.summary ? `<p class="log-summary">${escapeHtml(entry.summary)}</p>` : ""}${details(entry)}</div>${stats}<a class="text-link log-commit" href="${entry.link}" target="_blank" rel="noopener" aria-label="${entry.commitHash ? "View commit" : "View repository"}: ${escapeHtml(entry.title)}">${entry.commitHash ? "View commit" : "Repository"} ${arrow}</a></article>`;
}
function render(append = false) {
  const page = selectEntries(entries, selected, limit);
  const previous = append ? list.children.length : 0;
  if (!append) list.innerHTML = "";
  list.insertAdjacentHTML(
    "beforeend",
    page.visible.slice(previous).map(renderEntry).join(""),
  );
  if (!page.total)
    list.innerHTML =
      '<div class="empty-state"><h3>No changes in this archive yet.</h3><p>Explore the portfolio for project summaries and repositories.</p></div>';
  count.textContent = `Showing ${page.visible.length} of ${page.total} changes`;
  more.hidden = !page.hasMore;
  filters
    .querySelectorAll("button")
    .forEach((button) =>
      button.setAttribute(
        "aria-pressed",
        String(button.dataset.project === selected),
      ),
    );
  if (append) list.children[previous]?.querySelector("h3")?.focus();
}
if (list && filters && controls) {
  filters.innerHTML = [["all", "All projects"], ...projects]
    .map(
      ([slug, name]) =>
        `<button type="button" data-project="${slug}" aria-pressed="${slug === selected}">${name}</button>`,
    )
    .join("");
  filters.hidden = !entries.length;
  controls.hidden = false;
  filters.addEventListener("click", (event) => {
    const button = event.target.closest("button[data-project]");
    if (!button) return;
    selected = button.dataset.project;
    limit = 12;
    const url = new URL(location.href);
    if (selected === "all") url.searchParams.delete("project");
    else url.searchParams.set("project", selected);
    history.replaceState(null, "", url);
    render();
  });
  more.addEventListener("click", () => {
    limit += 12;
    render(true);
  });
  render();
}

const dialog = document.querySelector("#snapshot-dialog");
const opener = document.querySelector("[data-view-image]");
if (dialog && typeof dialog.showModal === "function" && opener) {
  opener.addEventListener("click", (event) => {
    event.preventDefault();
    dialog.showModal();
    dialog.querySelector(".image-scroll").scrollLeft = 0;
  });
  dialog
    .querySelector("[data-close-image]")
    .addEventListener("click", () => dialog.close());
  dialog.addEventListener("click", (event) => {
    if (event.target !== dialog) return;
    const rect = dialog.getBoundingClientRect();
    if (
      event.clientX < rect.left ||
      event.clientX > rect.right ||
      event.clientY < rect.top ||
      event.clientY > rect.bottom
    )
      dialog.close();
  });
  dialog.addEventListener("close", () => opener.focus());
}
