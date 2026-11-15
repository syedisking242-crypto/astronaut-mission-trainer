import os
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Generator

from astronaut_trainer.models import MISSIONS


def default_database_path() -> Path:
    root = Path(os.environ.get("LOCALAPPDATA", Path.home() / ".local" / "share"))
    return root / "JuniorAstronautMissionTrainer" / "trainer.sqlite3"


class Database:
    def __init__(self, path: str | Path | None = None):
        self.path = Path(path) if path else default_database_path()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.initialize()

    @contextmanager
    def connect(self) -> Generator[sqlite3.Connection, None, None]:
        connection = sqlite3.connect(self.path, timeout=10)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        try:
            yield connection
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def initialize(self) -> None:
        schema = """
        CREATE TABLE IF NOT EXISTS astronauts (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            age INTEGER NOT NULL CHECK(age BETWEEN 6 AND 45),
            profile TEXT NOT NULL,
            training_level TEXT NOT NULL,
            selected_mission_id TEXT REFERENCES missions(id),
            created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS missions (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL UNIQUE,
            category TEXT NOT NULL,
            description TEXT NOT NULL,
            base_score INTEGER NOT NULL
        );
        CREATE TABLE IF NOT EXISTS mission_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            astronaut_id TEXT NOT NULL REFERENCES astronauts(id),
            mission_id TEXT NOT NULL REFERENCES missions(id),
            status TEXT NOT NULL CHECK(status IN ('completed','failed')),
            score INTEGER NOT NULL,
            completion_percent INTEGER NOT NULL,
            response_seconds REAL NOT NULL,
            mistakes INTEGER NOT NULL,
            details_json TEXT NOT NULL,
            completed_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS telemetry (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            astronaut_id TEXT NOT NULL REFERENCES astronauts(id),
            mission_record_id INTEGER REFERENCES mission_records(id),
            recorded_at TEXT NOT NULL,
            oxygen REAL NOT NULL,
            battery REAL NOT NULL,
            fuel REAL NOT NULL,
            cabin_temperature REAL NOT NULL,
            cabin_pressure REAL NOT NULL,
            heart_rate REAL NOT NULL,
            body_temperature REAL NOT NULL,
            oxygen_saturation REAL NOT NULL
        );
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            astronaut_id TEXT NOT NULL REFERENCES astronauts(id),
            direction TEXT NOT NULL CHECK(direction IN ('earth_to_astronaut','astronaut_to_earth')),
            body TEXT NOT NULL,
            signal_strength INTEGER NOT NULL,
            delay_seconds REAL NOT NULL,
            sent_at TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_records_astronaut ON mission_records(astronaut_id, completed_at);
        CREATE INDEX IF NOT EXISTS idx_telemetry_astronaut ON telemetry(astronaut_id, recorded_at);
        """
        connection = sqlite3.connect(self.path, timeout=10)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = OFF")
        try:
            connection.executescript(schema)
            connection.execute("BEGIN IMMEDIATE")
            astronaut_columns = {row["name"] for row in connection.execute("PRAGMA table_info(astronauts)")}
            if "selected_mission_id" not in astronaut_columns:
                connection.execute("ALTER TABLE astronauts ADD COLUMN selected_mission_id TEXT REFERENCES missions(id)")
            astronaut_schema = connection.execute(
                "SELECT sql FROM sqlite_master WHERE type='table' AND name='astronauts'"
            ).fetchone()["sql"].lower()
            if "between 6 and 18" in astronaut_schema:
                connection.execute(
                    """CREATE TABLE astronauts_migrated (
                       id TEXT PRIMARY KEY,
                       name TEXT NOT NULL,
                       age INTEGER NOT NULL CHECK(age BETWEEN 6 AND 45),
                       profile TEXT NOT NULL,
                       training_level TEXT NOT NULL,
                       selected_mission_id TEXT REFERENCES missions(id),
                       created_at TEXT NOT NULL
                    )"""
                )
                connection.execute(
                    """INSERT INTO astronauts_migrated
                       (id,name,age,profile,training_level,selected_mission_id,created_at)
                       SELECT id,name,age,profile,training_level,selected_mission_id,created_at FROM astronauts"""
                )
                connection.execute("DROP TABLE astronauts")
                connection.execute("ALTER TABLE astronauts_migrated RENAME TO astronauts")
            connection.executemany(
                "INSERT OR IGNORE INTO missions(id,name,category,description,base_score) VALUES(?,?,?,?,?)",
                [(m.id, m.name, m.category, m.description, m.base_score) for m in MISSIONS],
            )
            connection.commit()
            connection.execute("PRAGMA foreign_keys = ON")
            violations = connection.execute("PRAGMA foreign_key_check").fetchall()
            if violations:
                raise sqlite3.IntegrityError("Database migration found invalid foreign-key references.")
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()
