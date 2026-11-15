import sqlite3
import tempfile
import unittest
from pathlib import Path

from astronaut_trainer.database import Database
from astronaut_trainer.services import TrainerService
from astronaut_trainer.simulations import (
    advance_telemetry, evaluate_emergency, evaluate_eva, launch_checklist, telemetry_status,
)


class TrainerServiceTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.service = TrainerService(Database(Path(self.temp_dir.name) / "test.sqlite3"))
        self.astronaut = self.service.register_astronaut("Ari Orbit", 12, "Curious pilot", "Cadet", "navigation")

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_registration_persists_profile_and_mission_catalog(self):
        self.assertEqual(self.service.astronaut(self.astronaut["id"])["name"], "Ari Orbit")
        self.assertEqual(self.astronaut["selected_mission_id"], "navigation")
        self.assertEqual(len(self.service.missions()), 5)

    def test_registration_rejects_invalid_age(self):
        with self.assertRaises(ValueError):
            self.service.register_astronaut("Ari Orbit", 5, "", "Cadet")
        with self.assertRaises(ValueError):
            self.service.register_astronaut("Ari Orbit", 46, "", "Cadet")
        astronaut = self.service.register_astronaut("Senior Cadet", 45, "", "Explorer")
        self.assertEqual(astronaut["age"], 45)

    def test_existing_database_migrates_age_limit_and_preserves_history(self):
        legacy_path = Path(self.temp_dir.name) / "legacy.sqlite3"
        connection = sqlite3.connect(legacy_path)
        try:
            connection.execute(
                """CREATE TABLE missions(id TEXT PRIMARY KEY, name TEXT NOT NULL UNIQUE,
                   category TEXT NOT NULL, description TEXT NOT NULL, base_score INTEGER NOT NULL)"""
            )
            connection.execute("INSERT INTO missions VALUES('launch','Launch Readiness','Flight Operations','Launch',100)")
            connection.execute(
                """CREATE TABLE astronauts(id TEXT PRIMARY KEY, name TEXT NOT NULL,
                   age INTEGER NOT NULL CHECK(age BETWEEN 6 AND 18), profile TEXT NOT NULL,
                   training_level TEXT NOT NULL, selected_mission_id TEXT REFERENCES missions(id),
                   created_at TEXT NOT NULL)"""
            )
            connection.execute(
                "INSERT INTO astronauts VALUES('JAT-OLD','Legacy Cadet',18,'Profile','Cadet','launch','2026-01-01T00:00:00+00:00')"
            )
            connection.execute(
                """CREATE TABLE mission_records(id INTEGER PRIMARY KEY AUTOINCREMENT,
                   astronaut_id TEXT NOT NULL REFERENCES astronauts(id), mission_id TEXT NOT NULL REFERENCES missions(id),
                   status TEXT NOT NULL, score INTEGER NOT NULL, completion_percent INTEGER NOT NULL,
                   response_seconds REAL NOT NULL, mistakes INTEGER NOT NULL, details_json TEXT NOT NULL,
                   completed_at TEXT NOT NULL)"""
            )
            connection.execute(
                """INSERT INTO mission_records(astronaut_id,mission_id,status,score,completion_percent,
                   response_seconds,mistakes,details_json,completed_at)
                   VALUES('JAT-OLD','launch','completed',100,100,10,0,'{}','2026-01-01T00:00:00+00:00')"""
            )
            connection.commit()
        finally:
            connection.close()
        migrated = Database(legacy_path)
        with migrated.connect() as connection:
            astronaut = connection.execute("SELECT * FROM astronauts WHERE id='JAT-OLD'").fetchone()
            history_count = connection.execute("SELECT COUNT(*) FROM mission_records WHERE astronaut_id='JAT-OLD'").fetchone()[0]
            schema = connection.execute("SELECT sql FROM sqlite_master WHERE name='astronauts'").fetchone()[0]
        self.assertEqual(astronaut["age"], 18)
        self.assertEqual(astronaut["selected_mission_id"], "launch")
        self.assertEqual(history_count, 1)
        self.assertIn("BETWEEN 6 AND 45", schema)
        migrated_service = TrainerService(migrated)
        senior = migrated_service.register_astronaut("Older Cadet", 45, "", "Explorer")
        self.assertEqual(senior["age"], 45)

    def test_mission_score_and_dashboard_are_persisted(self):
        result = self.service.record_mission(self.astronaut["id"], "emergency", True, 100, 8.4, 0)
        dashboard = self.service.dashboard(self.astronaut["id"])
        self.assertEqual(result["score"], 100)
        self.assertEqual(dashboard["completed"], 1)
        self.assertIn("emergency", dashboard["completed_missions"])

    def test_campaign_unlocks_one_mission_after_success_only(self):
        status = self.service.campaign_status(self.astronaut["id"])
        self.assertEqual(status["unlocked_missions"], {"launch"})
        self.service.record_mission(self.astronaut["id"], "launch", False, 40, 4, 1)
        self.assertEqual(self.service.campaign_status(self.astronaut["id"])["unlocked_missions"], {"launch"})
        self.service.record_mission(self.astronaut["id"], "launch", True, 100, 8, 0)
        self.assertEqual(self.service.campaign_status(self.astronaut["id"])["unlocked_missions"], {"launch", "navigation"})
        self.service.record_mission(self.astronaut["id"], "navigation", True, 100, 20, 0)
        self.assertEqual(self.service.campaign_status(self.astronaut["id"])["unlocked_missions"],
                         {"launch", "navigation", "emergency"})

    def test_simulation_decisions_enforce_success_conditions(self):
        self.assertTrue(evaluate_emergency("Low battery", "Switch to power-saving mode")[0])
        self.assertFalse(evaluate_eva(True, True, False, 80)[0])
        self.assertFalse(launch_checklist(20, {"Flight plan": True})[0])

    def test_telemetry_changes_and_alert_bands_are_distinct(self):
        reading = {"oxygen": 90, "battery": 90, "fuel": 90, "cabin_temperature": 22,
                   "cabin_pressure": 100, "heart_rate": 80, "body_temperature": 36.8,
                   "oxygen_saturation": 98}
        after = advance_telemetry(reading)
        self.assertLess(after["oxygen"], 90)
        self.assertEqual(telemetry_status("oxygen", 80), "NORMAL")
        self.assertEqual(telemetry_status("oxygen", 60), "WARNING")
        self.assertEqual(telemetry_status("oxygen", 30), "CRITICAL")


if __name__ == "__main__":
    unittest.main()