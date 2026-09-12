"""Deterministic write-work comparison; not a wall-clock or throughput benchmark."""

import argparse
import json

from pipeline import Warehouse


def run(customers: int = 2000) -> dict:
    if type(customers) is not int or not 1 <= customers <= 100000:
        raise ValueError("customers must be between 1 and 100000")
    warehouse = Warehouse()
    try:
        events = []
        for index in range(customers):
            customer_id = f"customer-{index}"
            for entity, after in (
                ("customer", {"segment": "standard"}),
                ("order", {"customer_id": customer_id, "amount_cents": 1000, "status": "paid"}),
            ):
                events.append(
                    {
                        "schema_version": 1,
                        "event_id": f"{entity}-{index}",
                        "entity": entity,
                        "entity_id": f"{entity}-{index}",
                        "position": len(events) + 1,
                        "op": "c",
                        "after": after,
                    }
                )
        warehouse.ingest(events)
        warehouse.ingest(
            [
                {
                    **events[0],
                    "event_id": "segment-update",
                    "position": len(events) + 1,
                    "op": "u",
                    "after": {"segment": "premium"},
                }
            ]
        )
        incremental = warehouse.last_materialization
        before = warehouse.db.total_changes
        audit = warehouse.rebuild()
        rebuilt_rows = warehouse.db.total_changes - before
        assert audit["status"] == "pass"
        return {
            "fixture": "synthetic",
            "customers": customers,
            "orders": customers,
            "accepted_changes": len(events) + 1,
            "updated_customers": 1,
            "incremental": incremental,
            "full_rebuild_derived_rows_written": rebuilt_rows,
            "audit": audit["status"],
            "interpretation": "SQLite derived-row inserts and deletes for one customer update versus a subsequent full rebuild of the same state; excludes journal, temporary tables, reads and elapsed time.",
        }
    finally:
        warehouse.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--customers", type=int, default=2000)
    args = parser.parse_args()
    print(json.dumps(run(args.customers), indent=2))
