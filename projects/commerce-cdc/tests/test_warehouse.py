import copy
import json
import random
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from pipeline import ROOT, Warehouse


class WarehouseTests(unittest.TestCase):
    def setUp(self):
        self.warehouse = Warehouse()
        self.addCleanup(self.warehouse.close)
        self.events = json.loads((ROOT / "data/changes.json").read_text())

    def test_replay_reconciles_without_duplicate_effects(self):
        self.assertEqual(
            self.warehouse.ingest(self.events), {"accepted": 9, "duplicates": 1, "quarantined": 2}
        )
        before = self.warehouse.report()
        self.assertEqual(
            before["revenue"], [{"segment": "premium", "paid_orders": 1, "revenue_cents": 15000}]
        )
        self.assertEqual(
            before["counts"],
            {"change_log": 9, "customer_history": 5, "customers": 2, "orders": 1, "quarantine": 2},
        )
        self.assertEqual(
            self.warehouse.ingest(self.events), {"accepted": 0, "duplicates": 10, "quarantined": 2}
        )
        self.assertEqual(self.warehouse.report(), before)

    def test_late_change_repairs_history_without_reverting_current(self):
        self.warehouse.ingest(self.events[:8])
        self.warehouse.ingest([self.events[8]])
        history = self.warehouse.db.execute(
            "SELECT valid_from, valid_to, segment FROM customer_history "
            "WHERE customer_id='c1' ORDER BY valid_from"
        ).fetchall()
        self.assertEqual(
            [tuple(row) for row in history],
            [(10, 50, "standard"), (50, 60, "standard"), (60, None, "premium")],
        )
        # Interval semantics: [valid_from, valid_to); only one version at a boundary.
        self.assertEqual(
            self.warehouse.db.execute(
                "SELECT segment FROM customer_history WHERE customer_id='c1' "
                "AND valid_from <= 60 AND (valid_to > 60 OR valid_to IS NULL)"
            ).fetchone()[0],
            "premium",
        )

    def test_deletes_survive_older_redelivery(self):
        self.warehouse.ingest(self.events[:8])
        old_order = {**self.events[3], "event_id": "late-old-order", "position": 45}
        self.warehouse.ingest([old_order])
        self.assertEqual(self.warehouse.report()["counts"]["orders"], 1)
        self.assertEqual(
            self.warehouse.db.execute(
                "SELECT is_deleted FROM customers WHERE customer_id='c2'"
            ).fetchone()[0],
            1,
        )

    def test_crash_rolls_back_journal_and_published_tables(self):
        self.warehouse.ingest(self.events[:4])
        before = self.warehouse.report()
        with self.assertRaisesRegex(RuntimeError, "injected"):
            self.warehouse.ingest(self.events[4:8], fail_before_publish=True)
        self.assertEqual(self.warehouse.report(), before)
        self.assertEqual(self.warehouse.ingest(self.events[4:8])["accepted"], 4)

    def test_conflicting_identity_rolls_back_the_entire_batch(self):
        self.warehouse.ingest(self.events[:4])
        before = self.warehouse.report()
        conflict = copy.deepcopy(self.events[0])
        conflict["after"]["segment"] = "premium"
        with self.assertRaisesRegex(ValueError, "identity conflict"):
            self.warehouse.ingest([self.events[4], conflict])
        self.assertEqual(self.warehouse.report(), before)

    def test_position_collision_is_not_silently_ignored(self):
        self.warehouse.ingest(self.events[:2])
        collision = {**self.events[2], "position": 20}
        with self.assertRaisesRegex(ValueError, "position conflict"):
            self.warehouse.ingest([collision])
        self.assertEqual(self.warehouse.report()["counts"]["change_log"], 2)

    def test_missing_customer_blocks_publication_and_can_be_replayed(self):
        with self.assertRaisesRegex(ValueError, "orphan"):
            self.warehouse.ingest([self.events[2]])
        self.assertEqual(self.warehouse.report()["counts"]["change_log"], 0)
        self.warehouse.ingest([self.events[2], self.events[0]])
        self.assertEqual(self.warehouse.report()["counts"]["orders"], 1)

    def test_state_survives_restart(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "warehouse.sqlite"
            first = Warehouse(path)
            first.ingest(self.events)
            expected = first.report()
            first.close()
            second = Warehouse(path)
            try:
                second.ingest(self.events)
                self.assertEqual(second.report(), expected)
            finally:
                second.close()

    def test_replay_does_not_write_derived_tables(self):
        self.warehouse.ingest(self.events)
        self.warehouse.ingest(self.events)
        self.assertEqual(
            self.warehouse.last_materialization,
            {"customers": 0, "orders": 0, "derived_rows_written": 0},
        )

    def test_customer_change_does_not_rewrite_orders_or_other_customers(self):
        self.warehouse.ingest(self.events)
        # Abort if the incremental path touches an unrelated row.
        self.warehouse.db.executescript("""
            CREATE TEMP TRIGGER protect_orders BEFORE DELETE ON orders
            BEGIN SELECT RAISE(ABORT, 'unrelated order rewritten'); END;
            CREATE TEMP TRIGGER protect_customer BEFORE DELETE ON customers
            WHEN OLD.customer_id = 'c2'
            BEGIN SELECT RAISE(ABORT, 'unrelated customer rewritten'); END;
        """)
        self.warehouse.ingest([{**self.events[0], "event_id": "new-segment", "position": 100}])
        self.assertEqual(self.warehouse.last_materialization["customers"], 1)
        self.assertEqual(self.warehouse.last_materialization["orders"], 0)
        self.assertEqual(self.warehouse.report()["revenue"][0]["segment"], "standard")
        self.assertEqual(self.warehouse.audit()["status"], "pass")

    def test_independent_audit_detects_row_changes_and_rebuild_repairs(self):
        self.warehouse.ingest(self.events)
        expected = self.warehouse.report()
        with self.warehouse.db:
            self.warehouse.db.execute("UPDATE orders SET amount_cents = 1")
            self.warehouse.db.execute("DELETE FROM customer_history WHERE valid_from = 50")
        bad = self.warehouse.audit()
        self.assertEqual(bad["status"], "fail")
        self.assertEqual(bad["tables"]["orders"]["missing_rows"], 1)
        self.assertEqual(bad["tables"]["customer_history"]["missing_rows"], 1)
        damaged = self.warehouse.report()
        with self.assertRaisesRegex(RuntimeError, "injected"):
            self.warehouse.rebuild(fail_before_publish=True)
        self.assertEqual(self.warehouse.report(), damaged)
        self.assertEqual(self.warehouse.rebuild()["status"], "pass")
        self.assertEqual(self.warehouse.report(), expected)

    def test_random_arrival_matches_independent_fold_and_full_rebuild(self):
        rng = random.Random(20260912)
        customers = [
            {**self.events[0], "entity_id": f"c{i}", "event_id": f"seed-{i}", "position": i + 1}
            for i in range(20)
        ]
        self.warehouse.ingest(customers)
        changes = []
        for position in range(100, 300):
            key = str(rng.randrange(20))
            is_customer = rng.choice([True, False])
            deleted = rng.randrange(5) == 0
            changes.append(
                {
                    "schema_version": 1,
                    "event_id": f"event-{position}",
                    "position": position,
                    "entity": "customer" if is_customer else "order",
                    "entity_id": ("c" if is_customer else "o") + key,
                    "op": "d" if deleted else "u",
                    "after": None
                    if deleted
                    else (
                        {"segment": rng.choice(["premium", "standard"])}
                        if is_customer
                        else {
                            "customer_id": "c" + key,
                            "amount_cents": position,
                            "status": rng.choice(["paid", "pending", "cancelled"]),
                        }
                    ),
                }
            )
        rng.shuffle(changes)
        for start in range(0, len(changes), 7):
            batch = changes[start : start + 7]
            self.warehouse.ingest(batch + batch[:1])
            self.assertEqual(self.warehouse.audit()["status"], "pass")
        expected = self.warehouse.report()
        self.assertEqual(self.warehouse.rebuild()["status"], "pass")
        self.assertEqual(self.warehouse.report(), expected)

    def test_malformed_records_are_durably_quarantined(self):
        bad = [
            None,
            [],
            {**self.events[0], "position": True},
            {**self.events[0], "after": {"segment": "premium", "email": "unexpected"}},
        ]
        self.assertEqual(self.warehouse.ingest(bad)["quarantined"], 4)
        self.warehouse.ingest(bad)
        self.assertEqual(self.warehouse.report()["counts"]["quarantine"], 4)


if __name__ == "__main__":
    unittest.main()
