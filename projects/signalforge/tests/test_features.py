import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from pipeline import ROOT, FeatureStore, QualityGateError

AT = "2026-09-01T10:00:00Z"


class FeatureTests(unittest.TestCase):
    def setUp(self):
        self.store = FeatureStore()
        self.addCleanup(self.store.close)
        self.fixture = json.loads((ROOT / "data/fixture.json").read_text())
        self.store.ingest(self.fixture["readings"])

    def test_excludes_future_and_not_yet_available_readings(self):
        rows = self.store.features(self.fixture["requests"])
        self.assertEqual(rows[0]["reading_id"], "a-known")
        self.assertEqual(rows[0]["temperature_milli_c"], 68000)
        self.assertIsNone(rows[1]["reading_id"])
        self.assertIsNone(rows[2]["reading_id"])
        naive = self.store.db.execute(
            "SELECT reading_id FROM readings WHERE machine_id='machine-a' "
            "AND event_time <= ? ORDER BY event_time DESC LIMIT 1",
            (rows[0]["prediction_time"],),
        ).fetchone()[0]
        self.assertEqual(naive, "a-delayed")  # An event-time-only join demonstrably leaks.

    def test_same_machine_at_multiple_prediction_times(self):
        first = self.fixture["requests"][0]
        rows = self.store.features(
            [
                first,
                {
                    **first,
                    "request_id": "prediction-later",
                    "prediction_time": "2026-09-01T10:10:00Z",
                },
            ]
        )
        self.assertEqual([row["reading_id"] for row in rows], ["a-known", "a-future"])

    def test_snapshots_are_reproducible_and_preserve_old_results(self):
        original = self.store.training_snapshot(self.fixture["requests"])
        self.assertEqual(
            original, self.store.training_snapshot(list(reversed(self.fixture["requests"])))
        )
        revision = copy.deepcopy(self.fixture["readings"][0])
        revision.update(
            reading_id="a-correction",
            available_at="2026-09-01T09:45:00Z",
            temperature_milli_c=69000,
        )
        self.store.ingest([revision])
        revised = self.store.training_snapshot(self.fixture["requests"])
        self.assertNotEqual(original["snapshot_id"], revised["snapshot_id"])
        saved = json.loads(
            self.store.db.execute(
                "SELECT manifest FROM training_snapshots WHERE snapshot_id=?",
                (original["snapshot_id"],),
            ).fetchone()[0]
        )
        self.assertEqual(saved["rows"][0]["temperature_milli_c"], 68000)

    def test_serving_and_training_use_identical_features(self):
        offline = self.store.features([{**self.fixture["requests"][0], "request_id": "machine-a"}])[
            0
        ]
        self.store.materialize(AT)
        online = self.store.online("machine-a", AT)
        self.assertEqual(online, {"status": "ready", "features": offline})
        self.assertEqual(self.store.online("machine-b", AT)["status"], "missing")

    def test_freshness_is_checked_again_at_read_time(self):
        self.store.materialize(AT)
        self.assertEqual(self.store.online("machine-a", "2026-09-01T10:40:00Z")["status"], "ready")
        self.assertEqual(self.store.online("machine-a", "2026-09-01T10:40:01Z")["status"], "stale")

    def test_failed_materialization_retains_last_good_generation(self):
        self.store.materialize(AT)
        before = self.store.online("machine-a", AT)
        with self.assertRaisesRegex(RuntimeError, "injected"):
            self.store.materialize("2026-09-01T10:10:00Z", fail_before_publish=True)
        self.assertEqual(self.store.online("machine-a", AT), before)

    def test_backward_materialization_and_time_travel_online_reads_are_rejected(self):
        self.store.materialize(AT)
        with self.assertRaisesRegex(ValueError, "backwards"):
            self.store.materialize("2026-09-01T09:00:00Z")
        with self.assertRaisesRegex(ValueError, "precede"):
            self.store.online("machine-a", "2026-09-01T09:00:00Z")

    def test_duplicate_replay_and_conflicting_identity(self):
        result = self.store.ingest(self.fixture["readings"])
        self.assertEqual(result, {"accepted": 0, "duplicates": 5, "quarantined": 1})
        conflict = {**self.fixture["readings"][0], "temperature_milli_c": 1}
        with self.assertRaisesRegex(ValueError, "identity conflict"):
            self.store.ingest([conflict])
        self.assertEqual(self.store.db.execute("SELECT COUNT(*) FROM readings").fetchone()[0], 4)
        self.assertEqual(self.store.db.execute("SELECT COUNT(*) FROM quarantine").fetchone()[0], 1)

    def test_quality_explains_missing_without_counting_future_knowledge(self):
        report = self.store.quality(self.fixture["requests"], min_coverage=100)
        self.assertEqual(report["status"], "fail")
        self.assertEqual(report["counts"], {"ready": 1, "expired": 1, "no_known_reading": 1})
        self.assertEqual(report["expected"], 3)
        self.assertEqual(report["coverage_percent"], 33.33)
        # A future-only machine must not be described as known historically.
        future = {
            **self.fixture["readings"][2],
            "reading_id": "new-future",
            "machine_id": "unseen",
            "event_time": "2026-09-01T11:00:00Z",
            "available_at": "2026-09-01T11:01:00Z",
        }
        self.store.ingest([future])
        request = {**self.fixture["requests"][0], "machine_id": "unseen"}
        self.assertEqual(self.store.quality([request])["missing"][0]["reason"], "no_known_reading")

    def test_rejected_serving_generation_preserves_rows_cutoff_and_quality(self):
        self.store.materialize(AT, machines=["machine-a"], min_coverage=100)
        before = self.store.generation_report()
        served = self.store.online("machine-a", AT)
        with self.assertRaises(QualityGateError) as caught:
            self.store.materialize(
                "2026-09-01T10:10:00Z",
                machines=["machine-a", "machine-b", "never-seen"],
                min_coverage=100,
            )
        self.assertEqual(caught.exception.report["expected"], 3)
        self.assertEqual(self.store.generation_report(), before)
        self.assertEqual(self.store.online("machine-a", AT), served)

    def test_training_gate_does_not_save_rejected_snapshot(self):
        original = self.store.training_snapshot(self.fixture["requests"])
        with self.assertRaises(QualityGateError):
            self.store.training_snapshot(self.fixture["requests"], min_coverage=100)
        self.assertEqual(
            self.store.db.execute("SELECT COUNT(*) FROM training_snapshots").fetchone()[0], 1
        )
        self.assertEqual(original["quality"]["ready"], 1)

    def test_coverage_policy_roster_and_empty_populations(self):
        for value in (-1, 101, True, 33.3):
            with self.assertRaisesRegex(ValueError, "integer"):
                self.store.materialize(AT, machines=["machine-a"], min_coverage=value)
        with self.assertRaisesRegex(ValueError, "explicit"):
            self.store.materialize(AT, min_coverage=100)
        for machines in (["machine-a", "machine-a"], [""], "machine-a", [None]):
            with self.assertRaisesRegex(ValueError, "unique"):
                self.store.materialize(AT, machines=machines)
        with self.assertRaises(QualityGateError):
            self.store.materialize(AT, machines=[], min_coverage=1)
        self.assertIsNone(self.store.quality([])["coverage_percent"])
        self.assertEqual(
            self.store.quality(self.fixture["requests"], min_coverage=33)["status"], "pass"
        )
        self.assertEqual(
            self.store.quality(self.fixture["requests"], min_coverage=34)["status"], "fail"
        )

    def test_coverage_boundary_and_recovery_after_missing_reading_arrives(self):
        roster = ["machine-a", "machine-b"]
        self.store.materialize(AT, machines=roster, min_coverage=50)
        with self.assertRaises(QualityGateError):
            self.store.materialize(AT, machines=roster, min_coverage=51)
        self.store.ingest(
            [
                {
                    **self.fixture["readings"][0],
                    "reading_id": "b-recovered",
                    "machine_id": "machine-b",
                    "event_time": "2026-09-01T09:59:00Z",
                    "available_at": "2026-09-01T10:01:00Z",
                }
            ]
        )
        self.store.materialize("2026-09-01T10:01:00Z", machines=roster, min_coverage=100)
        self.assertEqual(self.store.generation_report()["quality"]["ready"], 2)
        self.assertEqual(self.store.online("machine-b", "2026-09-01T10:01:00Z")["status"], "ready")

    def test_coverage_report_survives_restart(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "coverage.sqlite"
            first = FeatureStore(path)
            first.ingest(self.fixture["readings"])
            first.materialize(AT, machines=["machine-a"], min_coverage=100)
            expected = first.generation_report()
            first.close()
            second = FeatureStore(path)
            try:
                self.assertEqual(second.generation_report(), expected)
            finally:
                second.close()

    def test_bad_timestamps_and_sensor_values_go_to_quarantine(self):
        first = self.fixture["readings"][0]
        records = [
            None,
            {**first, "event_time": "2026-09-01T09:40:00"},
            {**first, "available_at": "2026-09-01T08:00:00Z"},
            {**first, "vibration_milli_mm_s": True},
        ]
        self.assertEqual(self.store.ingest(records)["quarantined"], 4)

    def test_duplicate_request_keys_are_rejected(self):
        request = self.fixture["requests"][0]
        with self.assertRaisesRegex(ValueError, "unique"):
            self.store.features([request, request])

    def test_serving_state_survives_restart_and_definition_change(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "features.sqlite"
            first = FeatureStore(path)
            first.ingest(self.fixture["readings"])
            first.materialize(AT)
            first.close()
            second = FeatureStore(path)
            try:
                self.assertEqual(second.online("machine-a", AT)["status"], "ready")
                second.definition_hash = "new-feature-definition"
                self.assertEqual(second.online("machine-a", AT)["status"], "definition_changed")
            finally:
                second.close()


if __name__ == "__main__":
    unittest.main()
