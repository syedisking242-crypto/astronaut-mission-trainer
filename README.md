# Junior Astronaut Mission Trainer

## Browser application

The repository also includes a responsive React/Vite web edition. It ports the five-mission campaign, scoring, astronaut profiles, simulated telemetry and health readings, emergency response, EVA, delayed communications, orbital navigation, flight history, and certificate download. The Python desktop edition below remains intact.

Requirements: Node.js 18 or newer (npm is included).

```powershell
npm install
npm run dev
```

Create a production build and preview it locally:

```powershell
npm run build
npm run preview
```

### Deploy to Vercel

Push the repository to GitHub and import it as a new Vercel project. Vercel detects Vite; use `npm run build` for the build command and `dist` for the output directory. The included `vercel.json` supports app-route fallback. No backend, paid service, or secret is required.

The web edition stores profiles, mission results, health readings, and radio messages in browser `localStorage`. Records stay in the current browser and do not sync across devices; the browser app does not read or migrate the desktop SQLite database. All spacecraft and health values are simulated for training, not connected to physical devices, and not medical advice.

A local, software-only astronaut training simulator for students. All spacecraft and health values are simulated; no physical devices or live medical measurements are used. Student records stay in a local SQLite database.

## Architecture

```text
main.py                         Desktop application entry point
astronaut_trainer/
  database.py                    SQLite schema, connections, migrations
  models.py                      Immutable domain records and mission catalog
  services.py                    Registration, telemetry, progress, scoring
  simulations.py                 Launch, emergency, EVA, and communications rules
  navigation.py                  Pygame space-navigation activity
  ui/
    app.py                       CustomTkinter shell and navigation
    screens.py                   Registration, dashboard, mission, and analytics views
  assets/                        Optional local visual assets
  data/                           Local database (created on first run)
tests/
  test_services.py               Database and scoring behavior tests
```

### Responsibility boundaries

- **UI:** CustomTkinter presents workflows and calls application services; it does not issue SQL.
- **Domain/services:** Mission catalog, validation, simulated system values, mission outcomes, and scoring are plain Python and testable without a window.
- **Persistence:** SQLite is accessed through a repository/service boundary with parameterized statements and transactions. The database is created under the user's local application data directory, not beside the source files.
- **Interactive navigation:** Pygame owns its activity window and emits a result when the objective is completed or the trainee exits. The Tk application remains responsive.
- **Analytics:** Matplotlib graphs saved mission and health-history data; Pillow is used for optional image assets.

## Database schema

All tables use SQLite foreign keys and UTC ISO-8601 timestamps.

- `astronauts(id TEXT PRIMARY KEY, name TEXT NOT NULL, age INTEGER NOT NULL CHECK(age BETWEEN 6 AND 45), profile TEXT NOT NULL, training_level TEXT NOT NULL, selected_mission_id TEXT REFERENCES missions(id), created_at TEXT NOT NULL)`
- `missions(id TEXT PRIMARY KEY, name TEXT NOT NULL UNIQUE, category TEXT NOT NULL, description TEXT NOT NULL, base_score INTEGER NOT NULL)`
- `mission_records(id INTEGER PRIMARY KEY AUTOINCREMENT, astronaut_id TEXT NOT NULL REFERENCES astronauts(id), mission_id TEXT NOT NULL REFERENCES missions(id), status TEXT NOT NULL CHECK(status IN ('completed','failed')), score INTEGER NOT NULL, completion_percent INTEGER NOT NULL, response_seconds REAL NOT NULL, mistakes INTEGER NOT NULL, details_json TEXT NOT NULL, completed_at TEXT NOT NULL)`
- `telemetry(id INTEGER PRIMARY KEY AUTOINCREMENT, astronaut_id TEXT NOT NULL REFERENCES astronauts(id), mission_record_id INTEGER REFERENCES mission_records(id), recorded_at TEXT NOT NULL, oxygen REAL NOT NULL, battery REAL NOT NULL, fuel REAL NOT NULL, cabin_temperature REAL NOT NULL, cabin_pressure REAL NOT NULL, heart_rate REAL NOT NULL, body_temperature REAL NOT NULL, oxygen_saturation REAL NOT NULL)`
- `messages(id INTEGER PRIMARY KEY AUTOINCREMENT, astronaut_id TEXT NOT NULL REFERENCES astronauts(id), direction TEXT NOT NULL CHECK(direction IN ('earth_to_astronaut','astronaut_to_earth')), body TEXT NOT NULL, signal_strength INTEGER NOT NULL, delay_seconds REAL NOT NULL, sent_at TEXT NOT NULL)`

Mission records are append-only results, preserving training history. Mission progress and achievements are derived from those records so they cannot drift from the underlying scores. `missions` is seeded from the built-in catalog during database initialization.

## UI design plan

A focused desktop layout uses a persistent left navigation rail and a single main work area. The visual system uses deep navy surfaces, restrained cyan and mission-amber accents, clear status colors, compact data panels, and readable system-style typography. Dashboard summaries lead to registration, mission launch, systems, health, emergency response, EVA, communications, and assessment workflows. Status is never conveyed by color alone: each indicator also has a label/value. Mission feedback includes the score and the reason for success or failure.

## Run on Windows

1. Install Python 3.10 or newer.
2. From this folder, create and activate a virtual environment:

   ```powershell
   py -3 -m venv .venv
   .\.venv\Scripts\Activate.ps1
   python -m pip install -r requirements.txt
   ```

3. Start the application with `python main.py`.
4. Run checks with `python -m unittest discover -s tests -v`.

The first run creates the database in `%LOCALAPPDATA%\JuniorAstronautMissionTrainer\trainer.sqlite3` (or the platform's user-data directory). No account or network connection is required.

## Development phases

1. Registration, local database, mission catalog, and dashboard persistence.
2. Simulated spacecraft/health telemetry, launch checklist, and chart history.
3. Emergency decisions, communications, EVA objectives, and assessment/certificate output.
4. Pygame navigation, end-to-end mission record verification, and Windows packaging/setup polish.
