#!/usr/bin/env python3
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List

ROOT = Path(__file__).resolve().parents[1]
DATA_PATH = ROOT / "work-log-data.js"
GENERATOR_PATH = ROOT / "scripts" / "generate_work_log.py"


def main() -> int:
  previous = load_current_data()

  result = subprocess.run(
    ["/usr/bin/python3", str(GENERATOR_PATH)],
    cwd=str(ROOT),
    check=False,
    capture_output=True,
    text=True,
  )
  if result.returncode != 0:
    sys.stderr.write(result.stderr)
    return result.returncode

  current = load_current_data()
  added = diff_entries(previous.get("entries", []), current.get("entries", []))

  print(result.stdout.strip())
  if not added:
    print("No new work log entries were added.")
    return 0

  print(f"Added {len(added)} new work log entr{'y' if len(added) == 1 else 'ies'}:")
  for entry in added:
    print(f"- {entry['date']} | {entry['project']} | {entry['title']}")

  return 0


def load_current_data() -> Dict[str, Any]:
  if not DATA_PATH.exists():
    return {"entries": []}

  content = DATA_PATH.read_text(encoding="utf-8").strip()
  prefix = "window.WORK_LOG_DATA = "
  suffix = ";"
  if not content.startswith(prefix) or not content.endswith(suffix):
    raise SystemExit(f"Unexpected format in {DATA_PATH.name}")

  payload = content[len(prefix):-len(suffix)]
  return json.loads(payload)


def diff_entries(previous_entries: List[Dict[str, Any]], current_entries: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
  previous_keys = {entry_key(entry) for entry in previous_entries}
  added = [entry for entry in current_entries if entry_key(entry) not in previous_keys]
  return added


def entry_key(entry: Dict[str, Any]) -> str:
  return json.dumps(entry, sort_keys=True)


if __name__ == "__main__":
  raise SystemExit(main())
