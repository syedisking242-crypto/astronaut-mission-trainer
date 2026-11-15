import json
import secrets
from datetime import datetime, timezone

from astronaut_trainer.database import Database


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class TrainerService:
    def __init__(self, database: Database | None = None):
        self.database = database or Database()

    def missions(self) -> list[dict]:
        with self.database.connect() as connection:
            return [dict(row) for row in connection.execute("SELECT * FROM missions ORDER BY rowid")]

    def register_astronaut(self, name: str, age: int | str, profile: str, training_level: str,
                            selected_mission_id: str | None = None) -> dict:
        clean_name = " ".join(name.split())
        clean_profile = profile.strip()
        levels = {"Cadet", "Explorer", "Commander"}
        try:
            parsed_age = int(age)
        except (TypeError, ValueError) as error:
            raise ValueError("Enter an age from 6 to 45.") from error
        if not 2 <= len(clean_name) <= 60:
            raise ValueError("Name must be between 2 and 60 characters.")
        if not 6 <= parsed_age <= 45:
            raise ValueError("Astronauts must be between 6 and 45 years old.")
        if len(clean_profile) > 500:
            raise ValueError("Profile must be 500 characters or fewer.")
        if training_level not in levels:
            raise ValueError("Select Cadet, Explorer, or Commander training.")
        astronaut_id = f"JAT-{secrets.token_hex(3).upper()}"
        record = {
            "id": astronaut_id,
            "name": clean_name,
            "age": parsed_age,
            "profile": clean_profile or "Ready for mission training.",
            "training_level": training_level,
            "created_at": utc_now(),
        }
        with self.database.connect() as connection:
            if selected_mission_id and not connection.execute("SELECT 1 FROM missions WHERE id=?", (selected_mission_id,)).fetchone():
                raise ValueError("Select a mission from the training manifest.")
            if not selected_mission_id:
                selected_mission_id = "launch"
            connection.execute(
                """INSERT INTO astronauts(id,name,age,profile,training_level,selected_mission_id,created_at)
                   VALUES(:id,:name,:age,:profile,:training_level,:selected_mission_id,:created_at)""",
                {**record, "selected_mission_id": selected_mission_id},
            )
        record["selected_mission_id"] = selected_mission_id
        return record

    def astronaut(self, astronaut_id: str) -> dict | None:
        with self.database.connect() as connection:
            row = connection.execute("SELECT * FROM astronauts WHERE id=?", (astronaut_id,)).fetchone()
            return dict(row) if row else None

    def astronauts(self) -> list[dict]:
        with self.database.connect() as connection:
            return [dict(row) for row in connection.execute("SELECT * FROM astronauts ORDER BY created_at DESC")]

    def record_mission(self, astronaut_id: str, mission_id: str, success: bool, completion_percent: int,
                       response_seconds: float, mistakes: int, details: dict | None = None) -> dict:
        with self.database.connect() as connection:
            mission = connection.execute("SELECT base_score FROM missions WHERE id=?", (mission_id,)).fetchone()
            if not connection.execute("SELECT 1 FROM astronauts WHERE id=?", (astronaut_id,)).fetchone():
                raise ValueError("Register or select an astronaut before starting a mission.")
            if mission is None:
                raise ValueError("Unknown mission.")
            completion = max(0, min(100, int(completion_percent)))
            score = int(mission["base_score"] * completion / 100) if success else int(mission["base_score"] * completion / 200)
            score = max(0, score - max(0, int(mistakes)) * 5)
            cursor = connection.execute(
                """INSERT INTO mission_records(astronaut_id,mission_id,status,score,completion_percent,
                   response_seconds,mistakes,details_json,completed_at) VALUES(?,?,?,?,?,?,?,?,?)""",
                (astronaut_id, mission_id, "completed" if success else "failed", score, completion,
                 max(0.0, float(response_seconds)), max(0, int(mistakes)), json.dumps(details or {}), utc_now()),
            )
            return {"id": cursor.lastrowid, "success": success, "score": score, "completion_percent": completion}

    def dashboard(self, astronaut_id: str) -> dict:
        with self.database.connect() as connection:
            astronaut = connection.execute("SELECT * FROM astronauts WHERE id=?", (astronaut_id,)).fetchone()
            if astronaut is None:
                raise ValueError("Select an astronaut to open the dashboard.")
            summary = connection.execute(
                """SELECT COUNT(*) AS attempts, SUM(status='completed') AS completed,
                   COALESCE(SUM(score),0) AS score, COALESCE(AVG(completion_percent),0) AS progress
                   FROM mission_records WHERE astronaut_id=?""", (astronaut_id,),
            ).fetchone()
            done_ids = {row[0] for row in connection.execute(
                "SELECT DISTINCT mission_id FROM mission_records WHERE astronaut_id=? AND status='completed'", (astronaut_id,)
            )}
            return {"astronaut": dict(astronaut), "attempts": summary["attempts"], "completed": summary["completed"] or 0,
                    "score": summary["score"], "progress": round(summary["progress"]), "completed_missions": done_ids}

    def campaign_status(self, astronaut_id: str) -> dict[str, set[str]]:
        missions = self.missions()
        with self.database.connect() as connection:
            completed = {row[0] for row in connection.execute(
                "SELECT DISTINCT mission_id FROM mission_records WHERE astronaut_id=? AND status='completed'",
                (astronaut_id,),
            )}
        unlocked = set()
        for index, mission in enumerate(missions):
            if index == 0 or missions[index - 1]["id"] in completed:
                unlocked.add(mission["id"])
        return {"completed_missions": completed, "unlocked_missions": unlocked}

    def history(self, astronaut_id: str) -> list[dict]:
        with self.database.connect() as connection:
            return [dict(row) for row in connection.execute(
                """SELECT r.*, m.name AS mission_name FROM mission_records r JOIN missions m ON m.id=r.mission_id
                   WHERE astronaut_id=? ORDER BY completed_at DESC""", (astronaut_id,)
            )]

    def save_telemetry(self, astronaut_id: str, values: dict, mission_record_id: int | None = None) -> None:
        fields = ("oxygen", "battery", "fuel", "cabin_temperature", "cabin_pressure", "heart_rate",
                  "body_temperature", "oxygen_saturation")
        with self.database.connect() as connection:
            connection.execute(
                """INSERT INTO telemetry(astronaut_id,mission_record_id,recorded_at,oxygen,battery,fuel,
                   cabin_temperature,cabin_pressure,heart_rate,body_temperature,oxygen_saturation)
                   VALUES(?,?,?,?,?,?,?,?,?,?,?)""",
                (astronaut_id, mission_record_id, utc_now(), *(float(values[key]) for key in fields)),
            )

    def telemetry_history(self, astronaut_id: str, limit: int = 30) -> list[dict]:
        with self.database.connect() as connection:
            return [dict(row) for row in connection.execute(
                "SELECT * FROM telemetry WHERE astronaut_id=? ORDER BY recorded_at DESC LIMIT ?", (astronaut_id, limit)
            )][::-1]

    def send_message(self, astronaut_id: str, body: str, signal: int, delay: float, direction: str = "astronaut_to_earth") -> None:
        if direction not in {"earth_to_astronaut", "astronaut_to_earth"}:
            raise ValueError("Invalid message direction.")
        if not body.strip() or len(body) > 500:
            raise ValueError("Message must contain 1 to 500 characters.")
        with self.database.connect() as connection:
            connection.execute(
                "INSERT INTO messages(astronaut_id,direction,body,signal_strength,delay_seconds,sent_at) VALUES(?,?,?,?,?,?)",
                (astronaut_id, direction, body.strip(), max(0, min(100, int(signal))), max(0, float(delay)), utc_now()),
            )

    def messages(self, astronaut_id: str, limit: int = 30) -> list[dict]:
        with self.database.connect() as connection:
            return [dict(row) for row in connection.execute(
                "SELECT * FROM messages WHERE astronaut_id=? ORDER BY sent_at DESC LIMIT ?", (astronaut_id, limit)
            )][::-1]