# Work Logs

The `Work Logs` page is generated from project activity rather than being edited by hand.

## How it works

1. `scripts/generate_work_log.py` scans the projects listed in the local-only `work-log.projects.json`.
2. If a project contains `.codex/work-log.jsonl`, those structured Codex notes are used for that project's matching days.
3. If a project has no structured note for a day, the generator falls back to publishing one log entry per recent git commit.
4. The script writes the public page data to `work-log-data.js`, which is what `work-logs.html` renders.
5. The `max_entries` option controls how many of those generated commit entries stay published on the page.
6. If several repos belong to the same track, give each repo its own `name` and add an optional shared `family` label.

## Low-level rebuild

```bash
python3 scripts/generate_work_log.py
```

That script is still useful, but most of the time you should use the manual sync command below.

## Recommended manual workflow

This is the simplest and safest flow:

1. Work across your repos until you are happy with the commits you want represented.
2. Ask Codex to refresh the logs, or run:

```bash
python3 scripts/update_work_logs.py
```

That command:

- scans the tracked repos in `work-log.projects.json`
- rebuilds `work-log-data.js`
- tells you which new entries were added to the public log

This keeps the final decision in your hands instead of publishing activity on a timer.

## Terminal dashboard

Use the dashboard when you want a quick view of what each tracked project is doing:

```bash
python3 scripts/work_log_dashboard.py
```

It shows:

- whether each tracked path is a valid git repo
- whether the page log looks synced with the latest commit history
- whether the working tree is clean or dirty
- the latest git commit and latest published work-log entry for each project

If you want to refresh first and then inspect the dashboard:

```bash
python3 scripts/work_log_dashboard.py --refresh
```

## Local project list

- Copy `work-log.projects.example.json` to `work-log.projects.json`
- Add the local absolute paths for the projects you want tracked
- Track sibling case studies as separate repo entries rather than one parent folder
- Use an optional `family` field when several repos belong to the same area, for example multiple `Data Analyst` case studies
- `work-log.projects.json` is intentionally gitignored so local filesystem paths do not get published

## Optional richer notes

Git history is a decent fallback, but structured notes are what let the page show:

- exact work completed
- issues encountered
- resolutions
- goals or milestones reached

Append a structured entry with:

```bash
python3 scripts/append_work_log.py \
  --project /absolute/path/to/project \
  --title "Refined planner flow" \
  --summary "Reduced planner friction and closed the main onboarding bug." \
  --worked-on "Simplified the onboarding form states" \
  --worked-on "Added validation around equipment selection" \
  --issue "The intake form dropped values when stepping back" \
  --resolution "Persisted draft answers in the session store" \
  --goal "Closed the onboarding reliability pass"
```

That writes to `.codex/work-log.jsonl` inside the target project.

## Public portfolio selection

`public-projects.json` is the publication allowlist. Before reading a project's activity, the generator checks its repository URL against that selection. Unselected, private or local-only projects are skipped. Add a repository only after checking that it is public and intended for this portfolio.

The development archive identifies its export date and only contains selected entries. The browser filters this snapshot by project and displays 12 changes at a time. Repository links are additionally restricted in `work-log-model.mjs`; update that selection together with `public-projects.json` when adding a public project. Preview and review the generated file before committing it.

## Token activity image

The token panel is the unchanged screenshot supplied by Alex on 7 September 2026, stored as `assets/token-activity-2026-09-07.png`. It is independent of the development archive, which was exported on 9 March 2026. Its embedded Daily/Weekly/Cumulative labels are part of the image, not interactive controls. The full-size viewer supports keyboard dismissal and horizontal panning on narrow screens. Without JavaScript, the link opens the original image directly.

To update the panel, add the new original image, update both image references, their dimensions and alternative text, and the visible capture date. Do not derive token metrics from the commit archive or present either source as time worked or productivity.
