#!/usr/bin/env python3
from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT / "work-log.projects.json"
EXAMPLE_CONFIG_PATH = ROOT / "work-log.projects.example.json"
OUTPUT_PATH = ROOT / "work-log-data.js"


def main() -> int:
  config = load_config()
  options = config.get("options", {})
  git_max_commits = int(options.get("git_max_commits_per_project", 24))
  max_entries = int(
    options.get("max_entries", max(60, len(config.get("projects", [])) * git_max_commits))
  )
  git_since_days = int(options.get("git_since_days", 180))
  structured_log_paths = options.get(
    "structured_log_paths",
    [".codex/work-log.jsonl", "work-log.jsonl"],
  )

  entries: List[Dict[str, Any]] = []
  structured_project_count = 0
  git_fallback_project_count = 0

  for project in config.get("projects", []):
    project_path = Path(project["path"]).expanduser().resolve()
    if not project_path.exists():
      print(f"Skipping missing project path: {project_path}", file=sys.stderr)
      continue

    repo_url = project.get("repo_url") or read_repo_url(project_path)
    structured_entries = read_structured_entries(
      project_name=project["name"],
      project_path=project_path,
      repo_url=repo_url,
      structured_log_paths=structured_log_paths,
    )

    structured_dates = {entry["date"] for entry in structured_entries}
    if structured_entries:
      structured_project_count += 1

    git_entries = read_git_entries(
      project_name=project["name"],
      project_path=project_path,
      repo_url=repo_url,
      max_commits=git_max_commits,
      since_days=git_since_days,
      skip_dates=structured_dates,
    )
    if git_entries:
      git_fallback_project_count += 1

    entries.extend(structured_entries)
    entries.extend(git_entries)

  entries.sort(
    key=lambda entry: (
      entry.get("timestamp", ""),
      entry.get("project", ""),
      entry.get("title", ""),
    ),
    reverse=True,
  )
  entries = entries[:max_entries]

  data = {
    "generatedAt": datetime.now().astimezone().isoformat(timespec="seconds"),
    "projectCount": len(config.get("projects", [])),
    "structuredProjectCount": structured_project_count,
    "gitFallbackProjectCount": git_fallback_project_count,
    "entries": entries,
  }

  OUTPUT_PATH.write_text(
    "window.WORK_LOG_DATA = " + json.dumps(data, indent=2) + ";\n",
    encoding="utf-8",
  )

  print(
    f"Wrote {len(entries)} entries from {len(config.get('projects', []))} projects to {OUTPUT_PATH.name}"
  )
  return 0


def load_config() -> Dict[str, Any]:
  if not CONFIG_PATH.exists():
    example_hint = EXAMPLE_CONFIG_PATH.name if EXAMPLE_CONFIG_PATH.exists() else "work-log.projects.json"
    raise SystemExit(
      f"Missing {CONFIG_PATH.name}. Copy {example_hint} to {CONFIG_PATH.name} and add your local project paths."
    )

  return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))


def read_structured_entries(
  *,
  project_name: str,
  project_path: Path,
  repo_url: Optional[str],
  structured_log_paths: List[str],
) -> List[Dict[str, Any]]:
  entries: List[Dict[str, Any]] = []

  for relative_path in structured_log_paths:
    log_path = project_path / relative_path
    if not log_path.exists():
      continue

    for raw_line in log_path.read_text(encoding="utf-8").splitlines():
      line = raw_line.strip()
      if not line:
        continue

      payload = json.loads(line)
      timestamp = parse_timestamp(payload.get("date") or payload.get("timestamp"))
      worked_on = ensure_string_list(payload.get("worked_on") or payload.get("workedOn"))
      goals = ensure_string_list(payload.get("goals") or payload.get("achievements"))
      issues = normalize_issues(payload)

      entries.append(
        {
          "date": timestamp.date().isoformat(),
          "timestamp": timestamp.isoformat(timespec="seconds"),
          "project": project_name,
          "title": payload.get("title") or f"Codex update in {project_name}",
          "summary": payload.get("summary") or "",
          "workedOn": worked_on,
          "issues": issues,
          "goals": goals,
          "lineStats": normalize_line_stats(payload),
          "repoUrl": repo_url,
          "sourceLabel": "Codex note",
        }
      )

    break

  return entries


def read_git_entries(
  *,
  project_name: str,
  project_path: Path,
  repo_url: Optional[str],
  max_commits: int,
  since_days: int,
  skip_dates: set[str],
) -> List[Dict[str, Any]]:
  since_date = (datetime.now() - timedelta(days=since_days)).date().isoformat()
  command = [
    "git",
    "-C",
    str(project_path),
    "log",
    "--no-merges",
    f"--max-count={max_commits}",
    f"--since={since_date}",
    "--pretty=format:%aI%x1f%cs%x1f%h%x1f%s",
  ]
  result = subprocess.run(
    command,
    check=False,
    capture_output=True,
    text=True,
  )
  if result.returncode != 0:
    return []

  entries: List[Dict[str, Any]] = []
  for line in result.stdout.splitlines():
    timestamp_text, date_text, short_hash, subject = line.split("\x1f", 3)
    if date_text in skip_dates:
      continue

    timestamp = parse_timestamp(timestamp_text)
    entries.append(
      {
        "date": date_text,
        "timestamp": timestamp.isoformat(timespec="seconds"),
        "project": project_name,
        "title": subject,
        "summary": "",
        "workedOn": [],
        "issues": [],
        "goals": [],
        "lineStats": read_commit_line_stats(project_path, short_hash),
        "repoUrl": repo_url,
        "sourceLabel": "Git history",
        "commitHash": short_hash,
      }
    )

  return entries


def normalize_issues(payload: Dict[str, Any]) -> List[Dict[str, str]]:
  raw_issues = payload.get("issues") or []
  normalized: List[Dict[str, str]] = []

  if isinstance(raw_issues, list):
    for item in raw_issues:
      if isinstance(item, dict):
        issue = str(item.get("issue") or "").strip()
        resolution = str(item.get("resolution") or "").strip()
        if issue or resolution:
          normalized.append({"issue": issue or "Issue", "resolution": resolution})
      elif isinstance(item, str) and item.strip():
        normalized.append({"issue": item.strip(), "resolution": ""})

  single_issue = str(payload.get("issue") or "").strip()
  single_resolution = str(payload.get("resolution") or "").strip()
  if single_issue or single_resolution:
    normalized.append({"issue": single_issue or "Issue", "resolution": single_resolution})

  return normalized


def ensure_string_list(value: Any) -> List[str]:
  if not value:
    return []
  if isinstance(value, str):
    return [value]
  if isinstance(value, list):
    return [str(item) for item in value if str(item).strip()]
  return [str(value)]


def normalize_line_stats(payload: Dict[str, Any]) -> Optional[Dict[str, int]]:
  raw_stats = payload.get("lineStats")
  added: Optional[int] = None
  deleted: Optional[int] = None

  if isinstance(raw_stats, dict):
    added = coerce_optional_int(raw_stats.get("added"))
    deleted = coerce_optional_int(raw_stats.get("deleted"))
  else:
    added = coerce_optional_int(payload.get("linesAdded") or payload.get("lines_added"))
    deleted = coerce_optional_int(payload.get("linesDeleted") or payload.get("lines_deleted"))

  if added is None and deleted is None:
    return None

  return {"added": added or 0, "deleted": deleted or 0}


def coerce_optional_int(value: Any) -> Optional[int]:
  if value in (None, ""):
    return None

  try:
    return int(value)
  except (TypeError, ValueError):
    return None


def read_commit_line_stats(project_path: Path, commit_hash: str) -> Optional[Dict[str, int]]:
  result = subprocess.run(
    ["git", "-C", str(project_path), "show", "--numstat", "--format=", commit_hash],
    check=False,
    capture_output=True,
    text=True,
  )
  if result.returncode != 0:
    return None

  added = 0
  deleted = 0
  has_numeric_stats = False

  for line in result.stdout.splitlines():
    parts = line.split("\t", 2)
    if len(parts) != 3:
      continue

    add_text, del_text, _path = parts
    if add_text.isdigit():
      added += int(add_text)
      has_numeric_stats = True
    if del_text.isdigit():
      deleted += int(del_text)
      has_numeric_stats = True

  if not has_numeric_stats:
    return None

  return {"added": added, "deleted": deleted}


def parse_timestamp(value: Optional[str]) -> datetime:
  if not value:
    return datetime.now().astimezone()

  normalized = value.replace("Z", "+00:00")
  try:
    timestamp = datetime.fromisoformat(normalized)
  except ValueError:
    timestamp = datetime.fromisoformat(f"{value}T12:00:00")

  if timestamp.tzinfo is None:
    return timestamp.astimezone()
  return timestamp


def read_repo_url(project_path: Path) -> Optional[str]:
  command = ["git", "-C", str(project_path), "remote", "get-url", "origin"]
  result = subprocess.run(
    command,
    check=False,
    capture_output=True,
    text=True,
  )
  if result.returncode != 0:
    return None

  return normalize_repo_url(result.stdout.strip())


def normalize_repo_url(url: str) -> Optional[str]:
  if not url:
    return None

  normalized = url
  if normalized.startswith("git@github.com:"):
    normalized = normalized.replace("git@github.com:", "https://github.com/", 1)
  if normalized.endswith(".git"):
    normalized = normalized[:-4]

  return normalized


if __name__ == "__main__":
  raise SystemExit(main())
