#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path


def main() -> int:
  parser = argparse.ArgumentParser(
    description="Append a structured Codex work log entry for a project."
  )
  parser.add_argument("--project", required=True, help="Absolute or relative path to the project root.")
  parser.add_argument("--title", required=True, help="Short headline for the work session.")
  parser.add_argument("--summary", default="", help="One sentence summary of the session.")
  parser.add_argument("--worked-on", action="append", default=[], help="Repeat for each completed task.")
  parser.add_argument("--goal", action="append", default=[], help="Repeat for each goal or milestone reached.")
  parser.add_argument("--issue", action="append", default=[], help="Repeat for each issue encountered.")
  parser.add_argument(
    "--resolution",
    action="append",
    default=[],
    help="Repeat for each issue resolution. Must match the number of --issue flags.",
  )
  parser.add_argument(
    "--date",
    default=None,
    help="Optional ISO timestamp. Defaults to the current local time.",
  )
  parser.add_argument(
    "--log-path",
    default=".codex/work-log.jsonl",
    help="Relative path inside the project where the log file should be stored.",
  )
  args = parser.parse_args()

  if len(args.issue) != len(args.resolution):
    parser.error("--issue and --resolution must be provided the same number of times.")

  project_path = Path(args.project).expanduser().resolve()
  log_path = project_path / args.log_path
  log_path.parent.mkdir(parents=True, exist_ok=True)

  payload = {
    "date": args.date or datetime.now().astimezone().isoformat(timespec="seconds"),
    "title": args.title,
    "summary": args.summary,
    "worked_on": args.worked_on,
    "issues": [
      {"issue": issue, "resolution": resolution}
      for issue, resolution in zip(args.issue, args.resolution)
    ],
    "goals": args.goal,
  }

  with log_path.open("a", encoding="utf-8") as handle:
    handle.write(json.dumps(payload) + "\n")

  print(f"Appended structured work log entry to {log_path}")
  return 0


if __name__ == "__main__":
  raise SystemExit(main())
