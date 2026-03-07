# Work Logs

The `Work Logs` page is generated from project activity rather than being edited by hand.

## How it works

1. `scripts/generate_work_log.py` scans the projects listed in the local-only `work-log.projects.json`.
2. If a project contains `.codex/work-log.jsonl`, those structured Codex notes are used for that project's matching days.
3. If a project has no structured note for a day, the generator falls back to grouping recent git commits by project and date.
4. The script writes the public page data to `work-log-data.js`, which is what `work-logs.html` renders.

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

## Local project list

- Copy `work-log.projects.example.json` to `work-log.projects.json`
- Add the local absolute paths for the projects you want tracked
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
