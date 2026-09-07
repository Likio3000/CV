#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT / "work-log.projects.json"
DATA_PATH = ROOT / "work-log-data.js"
UPDATE_PATH = ROOT / "scripts" / "update_work_logs.py"

RESET = "\033[0m"
BOLD = "\033[1m"
DIM = "\033[2m"
GREEN = "\033[32m"
YELLOW = "\033[33m"
RED = "\033[31m"
CYAN = "\033[36m"
BLUE = "\033[34m"


def main() -> int:
  parser = argparse.ArgumentParser(
    description="Show the current tracking status for projects feeding the Work Logs page."
  )
  parser.add_argument(
    "--refresh",
    action="store_true",
    help="Run the manual work-log sync before rendering the dashboard.",
  )
  parser.add_argument(
    "--plain",
    action="store_true",
    help="Disable ANSI colors.",
  )
  args = parser.parse_args()

  colors_enabled = supports_color() and not args.plain

  if args.refresh:
    result = subprocess.run(
      ["/usr/bin/python3", str(UPDATE_PATH)],
      cwd=str(ROOT),
      check=False,
      capture_output=True,
      text=True,
    )
    if result.stdout.strip():
      print(result.stdout.strip())
      print()
    if result.returncode != 0:
      sys.stderr.write(result.stderr)
      return result.returncode

  config = load_config()
  generated_data = load_generated_data()
  entries_by_project = group_entries_by_project(generated_data.get("entries", []))

  snapshots = [
    build_project_snapshot(
      project=project,
      logged_entries=entries_by_project.get(project["name"], []),
    )
    for project in config.get("projects", [])
  ]

  render_dashboard(snapshots=snapshots, generated_data=generated_data, colors_enabled=colors_enabled)
  return 0


def load_config() -> Dict[str, Any]:
  if not CONFIG_PATH.exists():
    raise SystemExit(
      f"Missing {CONFIG_PATH.name}. Add your tracked project paths before using the dashboard."
    )

  return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))


def load_generated_data() -> Dict[str, Any]:
  if not DATA_PATH.exists():
    return {"generatedAt": None, "entries": []}

  content = DATA_PATH.read_text(encoding="utf-8").strip()
  prefix = "window.WORK_LOG_DATA = "
  suffix = ";"
  if not content.startswith(prefix) or not content.endswith(suffix):
    raise SystemExit(f"Unexpected format in {DATA_PATH.name}")

  return json.loads(content[len(prefix):-len(suffix)])


def group_entries_by_project(entries: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
  grouped: Dict[str, List[Dict[str, Any]]] = {}
  for entry in entries:
    project_name = str(entry.get("project", "Unknown"))
    grouped.setdefault(project_name, []).append(entry)

  for project_entries in grouped.values():
    project_entries.sort(
      key=lambda entry: entry.get("timestamp") or f"{entry.get('date', '')}T12:00:00",
      reverse=True,
    )

  return grouped


def build_project_snapshot(
  *,
  project: Dict[str, Any],
  logged_entries: List[Dict[str, Any]],
) -> Dict[str, Any]:
  project_name = project["name"]
  project_path = Path(project["path"]).expanduser().resolve()
  exists = project_path.exists()
  is_git_repo = exists and git_command(project_path, ["rev-parse", "--is-inside-work-tree"]) == "true"
  latest_git = read_latest_git_commit(project_path) if is_git_repo else None
  dirty = has_dirty_worktree(project_path) if is_git_repo else None
  latest_log = logged_entries[0] if logged_entries else None
  sync_status, detail = determine_sync_status(
    exists=exists,
    is_git_repo=is_git_repo,
    latest_git=latest_git,
    latest_log=latest_log,
    logged_entries=logged_entries,
  )

  return {
    "name": project_name,
    "family": project.get("family"),
    "path": project_path,
    "exists": exists,
    "is_git_repo": is_git_repo,
    "tree_status": "DIRTY" if dirty else "CLEAN" if dirty is not None else "N/A",
    "latest_git": latest_git,
    "latest_log": latest_log,
    "sync_status": sync_status,
    "detail": detail,
    "last_item": latest_log_item(latest_log),
  }


def determine_sync_status(
  *,
  exists: bool,
  is_git_repo: bool,
  latest_git: Optional[Dict[str, str]],
  latest_log: Optional[Dict[str, Any]],
  logged_entries: List[Dict[str, Any]],
) -> tuple[str, str]:
  if not exists:
    return ("MISSING", "Configured path does not exist.")
  if not is_git_repo:
    return ("NO-REPO", "Configured path exists but is not a git repository.")
  if latest_git is None and latest_log is None:
    return ("EMPTY", "No git commits and no published log entries were found.")
  if latest_git is not None and latest_log is None:
    return ("NO-LOG", "Recent git activity exists but has not been published to the page.")
  if latest_git is None and latest_log is not None:
    return ("LOG-ONLY", "Published log data exists, but no git commit history was detected.")

  assert latest_git is not None
  assert latest_log is not None

  latest_git_timestamp = parse_timestamp(latest_git["timestamp"])
  latest_log_timestamp = parse_timestamp(
    str(latest_log.get("timestamp") or latest_log.get("date") or "")
  )

  if latest_log.get("sourceLabel") == "Git history" and commit_is_logged(
    logged_entries, latest_git["short_hash"]
  ):
    return ("SYNCED", "Latest git commit is already present in the published work log.")

  if latest_log_timestamp >= latest_git_timestamp:
    return ("SYNCED", "Published log data is at least as recent as the latest git commit.")

  if latest_log_timestamp.date() == latest_git_timestamp.date():
    return ("CHECK", "Git and published data are on the same day, but the latest commit is not explicit in the log.")

  return ("STALE", "Git activity is newer than the published work-log data.")


def read_latest_git_commit(project_path: Path) -> Optional[Dict[str, str]]:
  output = git_command(
    project_path,
    ["log", "-1", "--pretty=format:%aI%x1f%h%x1f%s"],
  )
  if not output:
    return None

  timestamp, short_hash, subject = output.split("\x1f", 2)
  return {
    "timestamp": timestamp,
    "short_hash": short_hash,
    "subject": subject,
  }


def has_dirty_worktree(project_path: Path) -> bool:
  result = subprocess.run(
    ["git", "-C", str(project_path), "status", "--porcelain"],
    check=False,
    capture_output=True,
    text=True,
  )
  if result.returncode != 0:
    return False

  return bool(result.stdout.strip())


def git_command(project_path: Path, args: List[str]) -> Optional[str]:
  result = subprocess.run(
    ["git", "-C", str(project_path), *args],
    check=False,
    capture_output=True,
    text=True,
  )
  if result.returncode != 0:
    return None

  output = result.stdout.strip()
  return output or None


def commit_is_logged(entries: List[Dict[str, Any]], short_hash: str) -> bool:
  for entry in entries:
    if str(entry.get("commitHash", "")) == short_hash:
      return True

    needle = short_hash
    if needle in str(entry.get("summary", "")):
      return True

    for item in entry.get("workedOn", []):
      if needle in str(item):
        return True

  return False


def latest_log_item(entry: Optional[Dict[str, Any]]) -> str:
  if not entry:
    return "No published work-log data"

  worked_on = entry.get("workedOn", [])
  if worked_on:
    return str(worked_on[0])

  return str(entry.get("title") or "No log item")


def render_dashboard(
  *,
  snapshots: List[Dict[str, Any]],
  generated_data: Dict[str, Any],
  colors_enabled: bool,
) -> None:
  counts = Counter(snapshot["sync_status"] for snapshot in snapshots)
  generated_at = generated_data.get("generatedAt")
  stale_count = counts.get("STALE", 0) + counts.get("NO-LOG", 0) + counts.get("CHECK", 0)
  problem_count = counts.get("MISSING", 0) + counts.get("NO-REPO", 0)
  overall_status, overall_note = overall_health_status(
    synced_count=counts.get("SYNCED", 0),
    tracked_count=len(snapshots),
    stale_count=stale_count,
    problem_count=problem_count,
  )

  print(color_text("=" * 72, DIM, colors_enabled))
  print(
    color_text("Work Logs Dashboard", BOLD, colors_enabled)
    + " "
    + color_status(overall_status, colors_enabled)
  )
  print(color_text(overall_note, status_color(overall_status), colors_enabled))
  print(
    color_label("Generated", colors_enabled)
    + " "
    + (
      format_timestamp(generated_at)
      if generated_at
      else "No generated page data yet"
    )
  )
  print(
    color_label("Tracked", colors_enabled)
    + str(len(snapshots))
    + " | "
    + color_text("Synced:", GREEN if counts.get("SYNCED", 0) else DIM, colors_enabled)
    + " "
    + color_text(str(counts.get("SYNCED", 0)), GREEN if counts.get("SYNCED", 0) else DIM, colors_enabled)
    + " | "
    + color_text("Needs review:", YELLOW if stale_count else DIM, colors_enabled)
    + " "
    + color_text(str(stale_count), YELLOW if stale_count else DIM, colors_enabled)
    + " | "
    + color_text("Problems:", RED if problem_count else DIM, colors_enabled)
    + " "
    + color_text(str(problem_count), RED if problem_count else DIM, colors_enabled)
  )
  print(color_text("=" * 72, DIM, colors_enabled))
  print()

  for snapshot in snapshots:
    render_project_card(snapshot=snapshot, colors_enabled=colors_enabled)
    print()

  print(
    color_text(
      "Tip: run `python3 scripts/update_work_logs.py` after commits you want reflected on the page.",
      DIM,
      colors_enabled,
    )
  )


def render_project_card(*, snapshot: Dict[str, Any], colors_enabled: bool) -> None:
  sync_label = color_status(snapshot["sync_status"], colors_enabled)
  tree_label = color_tree(snapshot["tree_status"], colors_enabled)
  name = color_text(snapshot["name"], BOLD, colors_enabled)
  accent = status_color(snapshot["sync_status"])

  print(color_text("-" * 72, DIM, colors_enabled))
  print(f"{sync_label} {tree_label} {name}")
  if snapshot.get("family"):
    print(f"  {color_label('Family', colors_enabled)} {snapshot['family']}")
  print(f"  {color_label('Repo', colors_enabled)} {shorten_path(snapshot['path'])}")
  print(f"  {color_label('Last git', colors_enabled)} {format_git(snapshot['latest_git'])}")
  print(f"  {color_label('Last log', colors_enabled)} {format_log(snapshot['latest_log'])}")
  print(f"  {color_label('Last item', colors_enabled)} {snapshot['last_item']}")
  print(f"  {color_text('Note:', accent, colors_enabled)} {snapshot['detail']}")


def format_git(latest_git: Optional[Dict[str, str]]) -> str:
  if not latest_git:
    return "No git commit detected"

  return (
    f"{format_timestamp(latest_git['timestamp'])} | "
    f"{latest_git['short_hash']} | "
    f"{latest_git['subject']}"
  )


def format_log(latest_log: Optional[Dict[str, Any]]) -> str:
  if not latest_log:
    return "No published work-log entry"

  timestamp = latest_log.get("timestamp") or latest_log.get("date")
  source = latest_log.get("sourceLabel") or "Unknown source"
  title = latest_log.get("title") or "Untitled entry"
  return f"{format_timestamp(str(timestamp))} | {source} | {title}"


def format_timestamp(value: str) -> str:
  timestamp = parse_timestamp(value)
  return timestamp.strftime("%d %b %Y %H:%M")


def parse_timestamp(value: str) -> datetime:
  normalized = value.replace("Z", "+00:00")
  if len(normalized) == 10:
    normalized = f"{normalized}T12:00:00"
  try:
    return datetime.fromisoformat(normalized)
  except ValueError:
    return datetime.fromisoformat(f"{normalized}T12:00:00")


def color_status(status: str, colors_enabled: bool) -> str:
  return color_text(f"[{status}]", status_color(status), colors_enabled)


def color_tree(tree_status: str, colors_enabled: bool) -> str:
  color = GREEN if tree_status == "CLEAN" else YELLOW if tree_status == "DIRTY" else DIM
  return color_text(f"[{tree_status}]", color, colors_enabled)


def status_color(status: str) -> str:
  colors = {
    "SYNCED": GREEN,
    "CHECK": CYAN,
    "STALE": YELLOW,
    "NO-LOG": YELLOW,
    "LOG-ONLY": CYAN,
    "EMPTY": CYAN,
    "NO-REPO": RED,
    "MISSING": RED,
    "GOOD": GREEN,
    "ATTENTION": YELLOW,
    "PROBLEM": RED,
  }
  return colors.get(status, "")


def overall_health_status(
  *,
  synced_count: int,
  tracked_count: int,
  stale_count: int,
  problem_count: int,
) -> tuple[str, str]:
  if problem_count:
    return ("PROBLEM", "Some tracked paths are broken or misconfigured.")
  if stale_count:
    return ("ATTENTION", "The page is mostly healthy, but some projects need review or refresh.")
  if tracked_count and synced_count == tracked_count:
    return ("GOOD", "All tracked projects look synced with the published work-log page.")
  return ("ATTENTION", "Tracking is available, but not every project is fully synced yet.")


def color_label(label: str, colors_enabled: bool) -> str:
  return color_text(f"{label}:", BLUE, colors_enabled)


def color_text(text: str, color: str, colors_enabled: bool) -> str:
  if not colors_enabled or not color:
    return text
  return f"{color}{text}{RESET}"


def shorten_path(path: Path) -> str:
  home = str(Path.home())
  path_text = str(path)
  if path_text.startswith(home):
    return path_text.replace(home, "~", 1)
  return path_text


def supports_color() -> bool:
  return sys.stdout.isatty() and os.environ.get("TERM") not in {None, "", "dumb"}


if __name__ == "__main__":
  raise SystemExit(main())
