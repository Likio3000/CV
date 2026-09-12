"""Reproducible maintenance features with event-time AND knowledge-time cutoffs."""

from __future__ import annotations

import argparse
import hashlib
import json
import sqlite3
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent
TTL_SECONDS = 3600


def canonical(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)


def fingerprint(value: object) -> str:
    return hashlib.sha256(canonical(value).encode()).hexdigest()


def timestamp(value: object) -> int:
    if not isinstance(value, str):
        raise ValueError("timestamp must be an ISO 8601 string with timezone")
    try:
        instant = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as error:
        raise ValueError("invalid timestamp") from error
    if instant.tzinfo is None or instant.microsecond:
        raise ValueError("timestamps require a timezone and whole-second precision")
    return int(instant.timestamp())


def identifier(value: object) -> bool:
    return isinstance(value, str) and bool(value.strip())


class QualityGateError(ValueError):
    def __init__(self, report: dict):
        self.report = report
        super().__init__("feature coverage below publication threshold")


def coverage(rows: list[dict], min_coverage: int = 0) -> dict:
    if type(min_coverage) is not int or not 0 <= min_coverage <= 100:
        raise ValueError("min_coverage must be an integer from 0 to 100")
    counts = {
        status: sum(row["status"] == status for row in rows)
        for status in ("ready", "expired", "no_known_reading")
    }
    ready, expected = counts["ready"], len(rows)
    # Evaluate with integers, never a rounded percentage. An empty population
    # cannot satisfy a nonzero coverage requirement.
    passed = min_coverage == 0 or (expected > 0 and ready * 100 >= min_coverage * expected)
    return {
        "status": "pass" if passed else "fail",
        "expected": expected,
        "ready": ready,
        "coverage_percent": round(100 * ready / expected, 2) if expected else None,
        "min_coverage_percent": min_coverage,
        "counts": counts,
        "missing": [
            {
                "request_id": row["request_id"],
                "machine_id": row["machine_id"],
                "reason": row["status"],
            }
            for row in rows
            if row["status"] != "ready"
        ],
    }


class FeatureStore:
    def __init__(self, database: str | Path = ":memory:"):
        self.db = sqlite3.connect(database)
        self.db.row_factory = sqlite3.Row
        self.db.executescript((ROOT / "sql/schema.sql").read_text())
        self.sql = (ROOT / "sql/point_in_time.sql").read_text()
        self.definition_hash = fingerprint({"sql": self.sql, "ttl_seconds": TTL_SECONDS})

    def close(self) -> None:
        self.db.close()

    def ingest(self, readings: list) -> dict:
        result = {"accepted": 0, "duplicates": 0, "quarantined": 0}
        with self.db:
            for raw in readings:
                digest = fingerprint(raw)
                try:
                    if not isinstance(raw, dict) or set(raw) != {
                        "reading_id",
                        "machine_id",
                        "event_time",
                        "available_at",
                        "temperature_milli_c",
                        "vibration_milli_mm_s",
                    }:
                        raise ValueError("reading fields must match the contract")
                    if not identifier(raw["reading_id"]) or not identifier(raw["machine_id"]):
                        raise ValueError("reading and machine identifiers must be nonempty strings")
                    event_time, available_at = (
                        timestamp(raw["event_time"]),
                        timestamp(raw["available_at"]),
                    )
                    if available_at < event_time:
                        raise ValueError("a reading cannot be available before it occurs")
                    for field, lower, upper in (
                        ("temperature_milli_c", -50000, 150000),
                        ("vibration_milli_mm_s", 0, 100000),
                    ):
                        if type(raw[field]) is not int or not lower <= raw[field] <= upper:
                            raise ValueError(f"{field} outside its integer contract")
                except ValueError as error:
                    self.db.execute(
                        "INSERT OR IGNORE INTO quarantine VALUES (?, ?, ?)",
                        (digest, canonical(raw), str(error)),
                    )
                    result["quarantined"] += 1
                    continue
                prior = self.db.execute(
                    "SELECT digest FROM readings WHERE reading_id = ?", (raw["reading_id"],)
                ).fetchone()
                if prior:
                    if prior["digest"] != digest:
                        raise ValueError(f"reading identity conflict: {raw['reading_id']}")
                    result["duplicates"] += 1
                    continue
                self.db.execute(
                    "INSERT INTO readings VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (
                        raw["reading_id"],
                        raw["machine_id"],
                        event_time,
                        available_at,
                        raw["temperature_milli_c"],
                        raw["vibration_milli_mm_s"],
                        digest,
                    ),
                )
                result["accepted"] += 1
        return result

    def features(self, requests: list) -> list[dict]:
        normalized, seen = [], set()
        for request in requests:
            if not isinstance(request, dict) or set(request) != {
                "request_id",
                "machine_id",
                "prediction_time",
            }:
                raise ValueError("request fields must match the contract")
            if not identifier(request["request_id"]) or not identifier(request["machine_id"]):
                raise ValueError("request and machine identifiers must be nonempty strings")
            if request["request_id"] in seen:
                raise ValueError("request_id must be unique; machine_id may repeat")
            seen.add(request["request_id"])
            normalized.append({**request, "prediction_time": timestamp(request["prediction_time"])})
        return [
            dict(row)
            for row in self.db.execute(
                self.sql, {"requests": canonical(normalized), "ttl": TTL_SECONDS}
            )
        ]

    def quality(self, requests: list, *, min_coverage: int = 0) -> dict:
        return coverage(self.features(requests), min_coverage)

    def training_snapshot(self, requests: list, *, min_coverage: int = 0) -> dict:
        # A transaction gives the manifest and result one consistent database snapshot.
        self.db.execute("BEGIN IMMEDIATE")
        try:
            rows = self.features(requests)
            quality = coverage(rows, min_coverage)
            if quality["status"] == "fail":
                raise QualityGateError(quality)
            source = [
                row[0] for row in self.db.execute("SELECT digest FROM readings ORDER BY reading_id")
            ]
            manifest = {
                "definition_hash": self.definition_hash,
                "source_hash": fingerprint(source),
                "ttl_seconds": TTL_SECONDS,
                "quality": quality,
                "rows": rows,
            }
            snapshot_id = fingerprint(manifest)
            self.db.execute(
                "INSERT OR IGNORE INTO training_snapshots VALUES (?, ?)",
                (snapshot_id, canonical(manifest)),
            )
            self.db.commit()
            return {"snapshot_id": snapshot_id, **manifest}
        except Exception:
            self.db.rollback()
            raise

    def materialize(
        self,
        as_of: str,
        *,
        machines: list[str] | None = None,
        min_coverage: int = 0,
        fail_before_publish: bool = False,
    ) -> list[dict]:
        cutoff = timestamp(as_of)
        coverage([], min_coverage)  # Validate the policy before opening a transaction.
        if machines is None and min_coverage:
            raise ValueError("a coverage gate requires an explicit machine roster")
        if machines is not None and (
            not isinstance(machines, list)
            or not all(identifier(machine) for machine in machines)
            or len(set(machines)) != len(machines)
        ):
            raise ValueError("machines must be a list of unique nonempty machine identifiers")
        self.db.execute("BEGIN IMMEDIATE")
        try:
            prior = self.db.execute("SELECT as_of FROM online_generation").fetchone()
            if prior and cutoff < prior["as_of"]:
                raise ValueError("online materialization cannot move backwards")
            population = "explicit_roster" if machines is not None else "observed_machines"
            if machines is None:
                machines = [
                    row[0] for row in self.db.execute("SELECT DISTINCT machine_id FROM readings")
                ]
            rows = self.features(
                [
                    {"request_id": machine, "machine_id": machine, "prediction_time": as_of}
                    for machine in machines
                ]
            )
            quality = {**coverage(rows, min_coverage), "population": population}
            if quality["status"] == "fail":
                raise QualityGateError(quality)
            self.db.execute("DELETE FROM online_features")
            self.db.executemany(
                "INSERT INTO online_features VALUES (?, ?)",
                [(row["machine_id"], canonical(row)) for row in rows],
            )
            if fail_before_publish:
                raise RuntimeError("injected failure before online publication")
            self.db.execute(
                "INSERT OR REPLACE INTO online_generation VALUES (1, ?, ?)",
                (cutoff, self.definition_hash),
            )
            self.db.execute(
                "INSERT OR REPLACE INTO online_quality VALUES (1, ?)", (canonical(quality),)
            )
            self.db.commit()
            return rows
        except Exception:
            self.db.rollback()
            raise

    def generation_report(self) -> dict | None:
        row = self.db.execute(
            "SELECT g.as_of, g.definition_hash, q.report_json FROM online_generation g "
            "LEFT JOIN online_quality q USING(singleton)"
        ).fetchone()
        if row is None:
            return None
        return {
            "as_of": row["as_of"],
            "definition_hash": row["definition_hash"],
            "quality": json.loads(row["report_json"]) if row["report_json"] else None,
        }

    def online(self, machine_id: str, now: str) -> dict:
        cutoff = timestamp(now)
        generation = self.db.execute(
            "SELECT g.as_of, g.definition_hash, f.feature_json FROM online_generation g "
            "LEFT JOIN online_features f ON f.machine_id = ?",
            (machine_id,),
        ).fetchone()
        if not generation:
            return {"status": "not_materialized", "features": None}
        if cutoff < generation["as_of"]:
            raise ValueError("online reads cannot precede materialization")
        if generation["definition_hash"] != self.definition_hash:
            return {"status": "definition_changed", "features": None}
        # Read generation metadata and its feature in one consistent SQL snapshot.
        feature = json.loads(generation["feature_json"]) if generation["feature_json"] else None
        if not feature or feature["reading_id"] is None:
            return {"status": "missing", "features": None}
        if feature["event_time"] < cutoff - TTL_SECONDS:
            return {"status": "stale", "features": None}
        return {"status": "ready", "features": feature}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "command", choices=("demo", "ingest", "training", "materialize", "online", "quality")
    )
    parser.add_argument("--database", default=":memory:")
    parser.add_argument("--input", type=Path)
    parser.add_argument("--at")
    parser.add_argument("--machine")
    parser.add_argument("--machines", type=Path, help="JSON array of expected machine IDs")
    parser.add_argument(
        "--min-coverage", type=int, default=0, help="minimum ready percentage, 0 disables gate"
    )
    args = parser.parse_args()
    if args.command in ("ingest", "training", "quality") and not args.input:
        parser.error(f"{args.command} requires --input")
    if args.command in ("materialize", "online") and not args.at:
        parser.error(f"{args.command} requires --at")
    if args.command == "online" and not args.machine:
        parser.error("online requires --machine")
    store = FeatureStore(args.database)
    try:
        if args.command == "demo":
            fixture = json.loads((ROOT / "data/fixture.json").read_text())
            ingestion = store.ingest(fixture["readings"])
            snapshot = store.training_snapshot(fixture["requests"])
            store.materialize("2026-09-01T10:00:00Z")
            before = store.generation_report()
            try:
                store.materialize(
                    "2026-09-01T10:10:00Z",
                    machines=["machine-a", "machine-b", "machine-unseen"],
                    min_coverage=100,
                )
            except QualityGateError as error:
                blocked = error.report
            else:
                raise AssertionError("demo fixture must fail the 100% coverage gate")
            output = {
                "coverage_gate": {
                    "rejected": blocked,
                    "prior_generation_preserved": store.generation_report() == before,
                },
                "ingestion": ingestion,
                "training": snapshot,
                "online": store.online("machine-a", "2026-09-01T10:00:00Z"),
                "expired": store.online("machine-a", "2026-09-01T12:00:00Z"),
            }
        elif args.command == "ingest":
            output = store.ingest(json.loads(args.input.read_text()))
        elif args.command == "training":
            output = store.training_snapshot(
                json.loads(args.input.read_text()), min_coverage=args.min_coverage
            )
        elif args.command == "quality":
            output = store.quality(
                json.loads(args.input.read_text()), min_coverage=args.min_coverage
            )
            print(json.dumps(output, indent=2))
            if output["status"] == "fail":
                raise SystemExit(1)
            return
        elif args.command == "materialize":
            machines = json.loads(args.machines.read_text()) if args.machines else None
            rows = store.materialize(args.at, machines=machines, min_coverage=args.min_coverage)
            output = {"rows": rows, "generation": store.generation_report()}
        else:
            output = store.online(args.machine, args.at)
        print(json.dumps(output, indent=2))
    except QualityGateError as error:
        print(json.dumps({"error": str(error), "quality": error.report}, indent=2))
        raise SystemExit(1) from None
    finally:
        store.close()


if __name__ == "__main__":
    main()
