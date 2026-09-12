"""Normalized CDC log -> replayable warehouse. Python standard library only."""

from __future__ import annotations

import argparse
import hashlib
import json
import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def canonical(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)


def validate(event: object) -> dict:
    if not isinstance(event, dict):
        raise ValueError("event must be an object")
    required = {"schema_version", "event_id", "position", "entity", "entity_id", "op", "after"}
    if set(event) != required:
        raise ValueError("v1 envelope fields must match the contract")
    if type(event["schema_version"]) is not int or event["schema_version"] != 1:
        raise ValueError("unsupported schema_version")
    for field in ("event_id", "entity_id"):
        if not isinstance(event[field], str) or not event[field].strip():
            raise ValueError(f"{field} must be a nonempty string")
    if type(event["position"]) is not int or not 0 < event["position"] <= 9223372036854775807:
        raise ValueError("position must be a positive signed 64-bit integer")
    if event["entity"] not in ("customer", "order") or event["op"] not in ("r", "c", "u", "d"):
        raise ValueError("unsupported entity or operation")
    row = event["after"]
    if event["op"] == "d":
        if row is not None:
            raise ValueError("delete must have a null after image")
        return event
    if not isinstance(row, dict):
        raise ValueError("non-delete events need a complete after image")
    if event["entity"] == "customer":
        if set(row) != {"segment"} or row["segment"] not in ("standard", "premium"):
            raise ValueError("customer needs a supported segment")
    else:
        if set(row) != {"customer_id", "amount_cents", "status"}:
            raise ValueError("order after image fields must match the contract")
        if not isinstance(row["customer_id"], str) or not row["customer_id"].strip():
            raise ValueError("customer_id must be a nonempty string")
        if (
            type(row["amount_cents"]) is not int
            or not 0 <= row["amount_cents"] <= 9223372036854775807
        ):
            raise ValueError("amount_cents must be a nonnegative signed 64-bit integer")
        if row["status"] not in ("pending", "paid", "cancelled"):
            raise ValueError("unsupported order status")
    return event


class Warehouse:
    def __init__(self, database: str | Path = ":memory:"):
        self.db = sqlite3.connect(database)
        self.db.row_factory = sqlite3.Row
        self.db.executescript((ROOT / "sql/schema.sql").read_text())
        self.db.execute(
            "CREATE TEMP TABLE touched (entity TEXT, entity_id TEXT, PRIMARY KEY(entity, entity_id))"
        )
        self.last_materialization = {"customers": 0, "orders": 0, "derived_rows_written": 0}

    def close(self) -> None:
        self.db.close()

    def ingest(self, events: list, *, fail_before_publish: bool = False) -> dict:
        result = {"accepted": 0, "duplicates": 0, "quarantined": 0}
        # Do not use executescript here: it commits an active transaction implicitly.
        with self.db:
            self.db.execute("BEGIN IMMEDIATE")
            self.db.execute("DELETE FROM touched")
            for raw in events:
                payload = canonical(raw)
                digest = hashlib.sha256(payload.encode()).hexdigest()
                try:
                    event = validate(raw)
                except ValueError as error:
                    self.db.execute(
                        "INSERT OR IGNORE INTO quarantine VALUES (?, ?, ?)",
                        (digest, payload, str(error)),
                    )
                    result["quarantined"] += 1
                    continue
                prior = self.db.execute(
                    "SELECT digest FROM change_log WHERE event_id = ?", (event["event_id"],)
                ).fetchone()
                if prior:
                    if prior["digest"] != digest:
                        raise ValueError(f"event identity conflict: {event['event_id']}")
                    result["duplicates"] += 1
                    continue
                try:
                    self.db.execute(
                        "INSERT INTO change_log VALUES (?, ?, ?, ?, ?, ?, ?)",
                        (
                            event["event_id"],
                            event["position"],
                            event["entity"],
                            event["entity_id"],
                            event["op"],
                            payload,
                            digest,
                        ),
                    )
                except sqlite3.IntegrityError as error:
                    raise ValueError(
                        "source position conflict; repair the normalized log"
                    ) from error
                self.db.execute(
                    "INSERT OR IGNORE INTO touched VALUES (?, ?)",
                    (event["entity"], event["entity_id"]),
                )
                result["accepted"] += 1
            if fail_before_publish:
                raise RuntimeError("injected failure before publication")
            work = {
                key + "s": self.db.execute(
                    "SELECT COUNT(*) FROM touched WHERE entity = ?", (key,)
                ).fetchone()[0]
                for key in ("customer", "order")
            }
            before = self.db.total_changes
            if result["accepted"]:
                self._materialize("incremental.sql")
            work["derived_rows_written"] = self.db.total_changes - before
            self._check_references()
        self.last_materialization = work
        return result

    def _materialize(self, filename: str) -> None:
        for statement in (ROOT / "sql" / filename).read_text().split(";"):
            if statement.strip():
                self.db.execute(statement)

    def _check_references(self) -> None:
        orphans = self.db.execute(
            "SELECT COUNT(*) FROM orders o LEFT JOIN customers c USING(customer_id) "
            "WHERE c.customer_id IS NULL"
        ).fetchone()[0]
        if orphans:
            raise ValueError("orphan orders; replay with missing customer changes")

    def rebuild(self, *, fail_before_publish: bool = False) -> dict:
        """Explicit repair from the journal, preserving the accepted source log."""
        with self.db:
            self.db.execute("BEGIN IMMEDIATE")
            self._materialize("materialize.sql")
            self._check_references()
            if fail_before_publish:
                raise RuntimeError("injected failure before rebuild publication")
        return self.audit()

    def audit(self) -> dict:
        """Compare published rows to an independent Python fold of the source log."""
        with self.db:
            self.db.execute("BEGIN")
            expected = {"customer_history": [], "customers": [], "orders": []}
            histories, current_orders = {}, {}
            for record in self.db.execute("SELECT payload FROM change_log ORDER BY position"):
                event = json.loads(record[0])
                key, position, row = event["entity_id"], event["position"], event["after"]
                if event["entity"] == "customer":
                    versions = histories.setdefault(key, [])
                    if versions:
                        versions[-1]["valid_to"] = position
                    versions.append(
                        {
                            "customer_id": key,
                            "segment": row["segment"] if row else None,
                            "valid_from": position,
                            "valid_to": None,
                            "is_deleted": int(event["op"] == "d"),
                        }
                    )
                elif event["op"] == "d":
                    current_orders.pop(key, None)
                else:
                    current_orders[key] = {"order_id": key, **row, "position": position}
            for key, versions in histories.items():
                expected["customer_history"].extend(versions)
                latest = versions[-1]
                expected["customers"].append(
                    {
                        "customer_id": key,
                        "segment": latest["segment"],
                        "position": latest["valid_from"],
                        "is_deleted": latest["is_deleted"],
                    }
                )
            expected["orders"] = list(current_orders.values())
            tables = {}
            for table, rows in expected.items():
                wanted = {canonical(row) for row in rows}
                actual = {canonical(dict(row)) for row in self.db.execute(f"SELECT * FROM {table}")}
                tables[table] = {
                    "expected_rows": len(wanted),
                    "actual_rows": len(actual),
                    "missing_rows": len(wanted - actual),
                    "unexpected_rows": len(actual - wanted),
                }
            return {
                "status": "pass"
                if all(v["missing_rows"] == v["unexpected_rows"] == 0 for v in tables.values())
                else "fail",
                "tables": tables,
            }

    def report(self) -> dict:
        counts = {
            table: self.db.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
            for table in ("change_log", "customer_history", "customers", "orders", "quarantine")
        }
        return {
            "counts": counts,
            "revenue": [
                dict(row)
                for row in self.db.execute("SELECT * FROM revenue_by_segment ORDER BY segment")
            ],
        }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("demo", "ingest", "report", "audit", "rebuild"))
    parser.add_argument("--database", default=":memory:")
    parser.add_argument("--input", type=Path)
    args = parser.parse_args()
    if args.command == "ingest" and args.input is None:
        parser.error("ingest requires --input")
    warehouse = Warehouse(args.database)
    try:
        output = {}
        if args.command in ("audit", "rebuild"):
            output = getattr(warehouse, args.command)()
            print(json.dumps(output, indent=2))
            if output["status"] != "pass":
                raise SystemExit(1)
            return
        if args.command != "report":
            source = args.input or ROOT / "data/changes.json"
            events = json.loads(source.read_text())
            if not isinstance(events, list):
                parser.error("input must be a JSON array of normalized change events")
            output["ingestion"] = warehouse.ingest(events)
            output["materialization"] = warehouse.last_materialization
            if args.command == "demo":
                output["replay"] = warehouse.ingest(events)
                output["replay_materialization"] = warehouse.last_materialization
                output["audit"] = warehouse.audit()
        output["warehouse"] = warehouse.report()
        print(json.dumps(output, indent=2))
    finally:
        warehouse.close()


if __name__ == "__main__":
    main()
