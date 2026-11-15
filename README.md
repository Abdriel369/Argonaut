Station Doctor · NASA Space Apps Challenge 2026 Prototype
> **Prototype using simulated data. This is not a medical diagnostic tool.**
Challenge: Create Health Monitoring Software for Astronauts on Space Missions (intermediate difficulty).
Demo tagline: 20 minutes from Earth, the station doctor already knows what to do.
An assistant that lives inside the station. With a 20-minute communication delay, the crew cannot wait for Earth, so it monitors, interprets, and provides guidance autonomously. It does not diagnose: it raises risk alerts and recommends actions.
A rules orchestrator detects a potential risk, consults four specialist models (sleep, fatigue and well-being, cardiovascular health, and solar risk), and explains the result in plain language with a step-by-step protocol and a report for the flight surgeon.

Two views share the same simulated data:

- **Crew** (main page): the commander's or medical team's dashboard. It shows the six astronauts, their level, a readiness index with its breakdown, data coverage, trend and an individual detail with alerts, specialist board, protocol and data quality.
- **Watch** (`/reloj/`): the astronaut's device. A web screen that simulates a smart watch, collects readings, receives alerts and the next protocol step, and stores readings offline to resend them later.

**All data is simulated.** The readiness index is a demo heuristic, not a calibrated probability or a medical evaluation. The watch is a web simulation, not a real device.

Laptop setup
Laptop	Runs	Folder	Port
1	Backend (API, SQLite, scenario, baseline), web interface	`laptop1-backend-frontend/`	8100
2	Gateway + 3 models (sleep, fatigue and well-being, cardiovascular)	`laptop2-modelos/`	8200 (gateway)
3	Orchestrator (rules, panel, synthesis) + solar-risk model	`laptop3-orquestador/`	8300 (orchestrator), 8310 (solar)
The three laptops are connected to a dedicated router with static IP addresses. Each one runs its own `docker compose` setup, and they communicate over HTTP using the IP addresses in their `.env` files. No IP address is hard-coded.
```text
Laptop 1 ──HTTP──▶ Laptop 3 orchestrator ──HTTP──▶ Laptop 2 gateway ──▶ sleep · fatigue · cardio
 (dashboard)        │ rules → routing table          (dispatches, 3 s per model)
                    └──local──▶ solar risk (GPU if available)

If Laptop 2 does not respond: DEGRADED MODE (rules + solar); the screen indicates this.
If Laptop 3 does not respond: Laptop 1 evaluates using its local copy of the rules.
```
Getting started
On each laptop, with Docker installed:
```bash
cd laptop2-modelos        # then laptop3-orquestador, laptop1-backend-frontend
cp .env.example .env      # set the actual IP_LAPTOP1/2/3 addresses on the router
docker compose up --build
```
Recommended order: Laptop 2, then Laptop 3, then Laptop 1. Interface: `http://IP_LAPTOP1:8100/` (it can also be opened from a phone).
Verify the network from each laptop (Docker and internet are not required):
```bash
python3 scripts/verificar_red.py --desde laptop1   # Laptop 1 → Laptop 3 and what it can reach on Laptop 2
python3 scripts/verificar_red.py --desde laptop3   # Laptop 3 → gateway and each model on Laptop 2
```
Without all three laptops (for judges): `modo-demo-sin-laptops/arrancar_demo.sh` (with Docker, or `local` without Docker). It uses model responses recorded from real executions, and the screen clearly indicates demo mode at all times.
Local development on a single machine (seven real processes, on `127.0.0.1` ports): `scripts/arrancar_local.sh` and `scripts/arrancar_local.sh parar`.
On Windows, without bash: `.\scripts\arrancar_local.ps1` and `.\scripts\arrancar_local.ps1 parar`.
If the execution policy blocks it: `powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\arrancar_local.ps1`.
Dashboard: `http://127.0.0.1:8100/`. Watch: `http://127.0.0.1:8100/reloj/`.
Tests
```bash
pip install -r laptop2-modelos/requirements.txt pytest
python -m pytest           # from the repository root (see the exact count in the output)
```
At the time of this change: **303 tests pass**. `xgboost` is pinned below 3.0 in
the model requirements: version 3.x crashed while shutting down with this
machine's CUDA driver. On Windows the tests force `USAR_GPU=no` for the same
reason; the runtime keeps `USAR_GPU=auto`. The pure watch queue
also has a Node script: `node laptop1-backend-frontend/frontend/reloj/pruebas/cola.script.mjs`.

Coverage:
Contracts: every JSON schema is valid; invalid messages are rejected.
Rules: each day in the scenario produces the expected level (green, green, yellow, orange, red, yellow, green; day 4 rises to orange starting with sleep-specialist version 1.1.0); adaptation window; persistence; missing data does not break the system.
Orchestrator: table-based routing; a specialist can raise a level by only one step (it can never lower the rule-based level); degraded mode without specialists.
Each model (4): minimum AUC, artifact integrity (hash), output contract, explanatory factors, behavior with incomplete data, determinism, API (`/salud`, `/info`, `/predecir`), and reproducibility of synthetic data.
Backend: data validation, baseline recalibration, muscle-and-bone exposure, protocols in the report, link with Earth, solar event, outages, and local fallback.
Sensor validation: impossible value, abrupt jump, frozen value, normal scenario without false positives, and ensuring a broken sensor does not trigger a red alert by itself or lower alerts from other signals.
Integration: complete 7-day scenario; Laptop 2 offline; one model offline; interface without remote resources.
Demo mode: the scenario plays back identically using saved responses.
Crew: the readiness formula with a fixed fixture, orange/red caps, `null` when coverage is low, tie-breakers, degraded mode and one astronaut failing without hiding the others.
Watch: reading isolation, idempotency by `lectura_id`, sensor validation of a suspicious reading, compact-state contract, no orchestrator call on every poll, and the linear projection (including fewer than 3 points).
Migration: an old single-astronaut SQLite file keeps AST-01's history, gets a backup and seeds the other five.
Data, assumptions, and thresholds
All data is simulated. Models are trained on synthetic data generated within public reference ranges (NASA HRP, CSA). Each generator uses a fixed seed and documents its assumptions: `laptop2-modelos/datos-sinteticos/SUPUESTOS.md` and `laptop3-orquestador/modelos/riesgo-solar/SUPUESTOS.md`.
Metrics show that the model learned the synthetic rule, not that it is clinically valid.
Thresholds and weights are stored in configuration files with comments. They are example values. They must be replaced and sourced before any serious use.
Sources: `SOURCES.md` explains where each threshold comes from and provides the full reference for each source. The team verified NASA-STD-3001 Vol. 1 [V1 4030] (career dose below 600 mSv). Nine other sources were opened and checked on 2026-11-15; they support the rationale behind 14 thresholds, not their numerical values. Three thresholds remain marked `SOURCE TO BE CITED` (heart rate, heart-rate variability, and the cardiovascular rule). The cutoffs are design decisions, not values copied from the standard.
Sensors: sensor validation runs before the rules and models (possible range, abrupt change, frozen value). A suspicious reading is not used and generates an equipment warning. Example limits and assumptions are documented in `laptop1-backend-frontend/SUPUESTOS.md`.
Threshold	Example value	Location	Suggested source (to be verified; not checked)
Sleep below baseline	1 h yellow, 2.5 h orange, 3.5 h red; 3-day persistence	`reglas/config/umbrales.toml`	NASA HRP, sleep and fatigue risk
Low mood	2 points (1–5 scale); 3-day persistence	same	NASA HRP, behavioral health
High stress	20 / 35 / 55 points above baseline (0–100)	same	Prototype's own scale
Low exercise	30% and 50% below plan; 5 days	same	ISS exercise countermeasures
High resting heart rate	+15% / +25% / +40%	same	NASA HRP reference values
Low HRV	−20% / −35% / −50%	same	NASA HRP reference values
Low SpO₂	3 / 5 / 8 points below baseline	same	Reference value (approx. 95%)
Elevated temperature	+0.8 / +1.3 / +2.0 °C	same	Reference value
Low food intake	below 75% of plan (and 60% in combination)	same	NASA HRP, nutrition
Current radiation rate	60 / 200 / 1000 µSv/h	same	NASA-STD-3001 Vol. 1
Cumulative radiation	50 / 150 / 250 mSv	same	Verified: NASA-STD-3001 Vol. 1 [V1 4030], career dose below 600 mSv. The three cutoffs are design steps toward that limit
Risk-level cutoff	0.20 / 0.50 / 0.75	`comun/especialista/nucleo.py`	Prototype's own scale
Maximum time per model	3 s	Laptop 2 and 3 `.env` files	System design
Adaptation window	2 days, thresholds ×1.5	`reglas/config/umbrales.toml`	NASA HRP, duration of initial adaptation
The source column in this table contains older leads, not citations. The verified sources and their complete references are in `SOURCES.md`. Before presenting them, open each document and confirm the figure. Suggested documents: NASA-STD-3001 (Volumes 1 and 2); NASA Human Research Program evidence reports by risk; and public space-health pages from the Canadian Space Agency (CSA).
Limitations (honest disclosure)
Not a diagnosis. It flags risk and recommends actions; it does not replace the medical team.
Simulated and synthetic data. The ranges are reference ranges; Earth-based and synthetic data do not fully represent the space environment.
Blood pressure and glucose: they are not reliable without dedicated equipment. They are optional external modules using simulated data.
Muscle and bone: this is only an estimated exposure based on mission days and completed exercise. It is not a measurement.
Immune system: planned future work. It requires blood, saliva, and urine; it is not simulated.
Radiation: the solar event is simulated. There is no space-weather forecast or real dosimeter.
Confidence: this is a heuristic, not a calibrated probability.
Sensor validation: limits are example values and the prototype has only one reading per day. A sensor stuck at a plausible value may take 4 or 5 days to detect. A very abrupt real change remains flagged as suspicious until a person manually confirms it.
Protocols: these are example text and contain no medication dosages. A real protocol must be defined by the mission medical team.
Readiness index: it is a demo heuristic built from simulated profiles and local rules. It is not a calibrated probability, a medical evaluation or a fitness-for-duty decision. The weights and caps live in `laptop1-backend-frontend/backend/config/tripulacion.toml`; see `laptop1-backend-frontend/SUPUESTOS_TRIPULACION.md`.
Crew profiles: the six astronauts are fictional and deterministic. AST-05 intentionally has no records for days 3–7, so the crew view shows **Not enough data** instead of a misleading zero.
Watch: it is a web screen, not a native app, and it does not use Bluetooth or real sensors. Its offline queue lives in `localStorage` and is limited to 20 readings per astronaut; the demo does not use service workers or background execution.
Verification status
Verified here: all 303 tests pass; the 7-day scenario produces the expected scripted levels; the local demo (`arrancar_demo.sh local`) works end to end; the `docker-compose.yml` files have valid syntax. The real server was started and `/`, `/reloj/` (plus its JS/CSS/font assets), `/api/tripulacion`, `/api/reloj/estado`, `/api/reloj/lectura` and `/api/exportar.csv` answered correctly. The crew view, the individual detail and the five watch screens were smoke-tested from Node with a minimal DOM and real backend payloads.
A visual check with headless Chrome rendered `/` and `/reloj/` at desktop size and with emulated 360/390 px viewports; the Crew table loaded its six rows, the AST-03 detail opened, and there was no horizontal overflow. The full offline → reload → online cycle in browser DevTools was not automated; the pure queue logic is covered by Node tests and the HTTP endpoints by pytest.
Not verified here: Docker image builds and startup with `docker compose`. The development environment does not have a Docker daemon. The Dockerfiles follow the same folder structure used by the tests.
To do on site: test with the three actual laptops on the router; set the IP and port in each `.env`; decide whether to use an NVIDIA GPU (see the commented section in `laptop3-orquestador/docker-compose.yml`).
Repository structure
```text
contratos/                  shared JSON schemas + examples + tests
comun/                      validation, levels, specialist core, shared verification
laptop1-backend-frontend/   backend, frontend (no CDN), profile and scenario configuration,
                            six crew profiles (tripulacion.toml), readiness index (aptitud.py),
                            sensor validation, /reloj/ watch page with offline queue
laptop2-modelos/            gateway, 3 models, synthetic data and assumptions
laptop3-orquestador/        orchestrator, rules, protocols, solar-risk model
modo-demo-sin-laptops/      single-machine demo with recorded responses
pruebas-integracion/        in-memory stack, input factory, integration tests
scripts/                    network verification and local startup (.sh and .ps1)
PLAN.md                     phases and acceptance state
DEMO_RELOJ.md               2–3 minute watch + crew demo script
SOURCES.md                  threshold origins and items still requiring verification
```


Tools used in Argonaut – Station Doctor
Tool or resource	What it contributed to the project
Git and GitHub	Git made it possible to keep a history of changes to the code. GitHub provided a shared repository so team members could pull updates and test the same version of the dashboard on their own laptops.
Visual Studio Code	Used to work with the backend and interface files in one workspace. From its integrated terminal, the team could start the application and review container messages while checking the result in the browser.
Docker Desktop and Docker Compose	Allowed the application to run with the dependencies and configuration defined by the project. During testing, the team could start the service, open the dashboard at localhost:8100, and stop it once the demo was finished.
Python, FastAPI, and Uvicorn	Python was used to write the backend logic. FastAPI organizes the endpoints through which the interface requests information, and Uvicorn runs the server that handles those requests. Together, they let the dashboard receive the data it shows to the user.
SQLite, HTTPX, and jsonschema	SQLite provides local storage for the backend. HTTPX lets one service communicate with another over HTTP requests. jsonschema checks that messages have the expected structure — for example, that required fields are present and each value has the correct type.
HTML, CSS, and JavaScript	HTML organizes elements such as the sleep, mood, and pulse cards. CSS defines their layout, typography, and colors so each indicator's status can be recognized at a glance. JavaScript handles actions such as selecting a region on the body map, replaying the mission week, or triggering a solar event.
Atkinson Hyperlegible and Barlow Semi Condensed	These typefaces are part of the dashboard's design. They help distinguish titles, labels, and numeric values on a screen that brings together several indicators. The font files are bundled with the project so the interface can display them without downloading fonts during the demo.
Claude – Anthropic	Used as support to review and explain scientific sources, discuss how to present information on the dashboard, and work through questions while running the application. It also helped organize references and draft the project description for the competition.




Font licenses (SIL OFL 1.1): `laptop1-backend-frontend/frontend/fuentes/`.
Sources and threshold documentation
The full source register, including bibliographic details, verification status, what each reference supports, and which values are design choices, is maintained in `SOURCES.md`. Read it before interpreting any threshold as an evidence-based clinical limit.
