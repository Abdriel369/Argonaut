# Station Doctor · NASA Space Apps Challenge 2026 Prototype

> **Prototype using simulated data. This is not a medical diagnostic tool.**

## 🚀 Live demo (no login, no installation)

- **Crew dashboard:** https://argonaut-demo.onrender.com/
- **Astronaut watch:** https://argonaut-demo.onrender.com/reloj/

The demo runs on Render's free plan, so if nobody has used it for a while the first load can take up to about a minute while the service wakes up. Please wait for the page to finish connecting. It uses recorded model responses and simulated data only.

---

## The problem

On a long space mission, the crew is minutes away from Earth, not seconds. With a communication delay of about 20 minutes, an astronaut whose sleep, heart rate or stress is slowly drifting cannot wait for a doctor on the ground to notice and answer. Small changes that look harmless on their own can add up to a real risk.

## What Station Doctor does about it

- **Learns each astronaut's own baseline** and compares every new reading against it, instead of using one fixed number for everyone.
- **Detects combinations of signals** (for example, poor sleep plus low mood plus a high resting heart rate) and raises a preventive alert before it becomes an emergency.
- **Consults four specialist models** (sleep, fatigue and well-being, cardiovascular health, solar radiation risk) when the rules find a potential risk.
- **Explains the result in plain language** with a step-by-step protocol, and prepares a report for the flight surgeon on Earth.
- **Keeps working when things fail:** a faulty sensor does not trigger a false red alert, and if the models are unavailable it switches to a clearly labeled degraded mode.
- **Never diagnoses.** It flags risk and recommends actions to support the medical team, not replace it.

## Try it in 60 seconds

1. Open the [live dashboard](https://argonaut-demo.onrender.com/) and wait for it to finish connecting. You will see the six crew members with their status and readiness index.
2. In the **Demo panel** (presenter controls), press **Play week** to watch the 7-day scenario go from green to yellow, orange and red, then recover.
3. Select an astronaut to see the alerts, the **Medical board** (rules plus specialist models), the **What to do now** protocol and the **Flight surgeon report**.
4. Press **Solar event** or **Simulate faulty sensor** to see how the system reacts to a radiation spike or to a broken sensor without raising a false alarm.
5. Open the [astronaut's watch](https://argonaut-demo.onrender.com/reloj/) to see the wearable view: readings, alerts, the next protocol step, and offline storage.

Everything in the demo uses simulated data and recorded model responses.

---

**Challenge:** Create Health Monitoring Software for Astronauts on Space Missions (intermediate difficulty).

**Demo tagline:** *20 minutes from Earth, the station doctor already knows what to do.*

Station Doctor is an assistant that lives inside the station. With a 20-minute communication delay, the crew cannot wait for Earth, so it monitors, interprets, and provides guidance autonomously. It does not diagnose: it raises risk alerts and recommends actions.

A rules orchestrator detects a potential risk, consults four specialist models (sleep, fatigue and well-being, cardiovascular health, and solar risk), and explains the result in plain language with a step-by-step protocol and a report for the flight surgeon.

## Two views, one dataset

- **Crew** (main page): the commander's or medical team's dashboard. It shows the six astronauts, their level, a readiness index with its breakdown, data coverage, trend, and an individual detail with alerts, specialist board, protocol and data quality.
- **Watch** (`/reloj/`): the astronaut's device. A web screen that simulates a smart watch, collects readings, receives alerts and the next protocol step, and stores readings offline to resend them later.

**All data is simulated.** The readiness index is a demo heuristic, not a calibrated probability or a medical evaluation. The watch is a web simulation, not a real device.

## Repository branches

| Branch | What it contains | Use it for |
|---|---|---|
| [`main`](https://github.com/Abdriel369/Argonaut) | The full system: the three-laptop setup, the four models with their training code and synthetic-data generators, the demo mode, all 304 tests, and the documentation. | Studying the project, running it on three laptops or on one machine, and running the tests. |
| [`Modo-Demo`](https://github.com/Abdriel369/Argonaut/tree/Modo-Demo) | A trimmed copy for the public demo: backend, frontend, orchestrator and recorded responses, plus [`deploy/render/`](https://github.com/Abdriel369/Argonaut/tree/Modo-Demo/deploy/render) and [`render.yaml`](https://github.com/Abdriel369/Argonaut/blob/Modo-Demo/render.yaml). It does not include the models, the gateway or the tests. | Building and deploying the single-service demo on Render. |

## Full architecture: the three-laptop setup

The full prototype was designed as a small distributed system and **tested on three laptops**: three laptops connected to a dedicated router with static IP addresses, each running its own `docker compose` setup and communicating over HTTP. The team ran the complete system this way and it worked as designed. The idea is to mimic a station where the dashboard, the specialist models and the decision logic live on separate computers, so that one of them can fail without taking the rest down.

| Laptop | What it runs | Folder | Port |
|---|---|---|---|
| 1 | Backend (API, SQLite, scenario, personal baselines) and the web interface (Crew dashboard and Watch) | `laptop1-backend-frontend/` | 8100 |
| 2 | Gateway + three specialist models: sleep, fatigue and well-being, cardiovascular | `laptop2-modelos/` | 8200 (gateway) |
| 3 | Orchestrator (rules, medical board, synthesis, protocols, report) + solar-risk model | `laptop3-orquestador/` | 8300 (orchestrator), 8310 (solar) |

No IP address is hard-coded: each laptop reads the addresses of the others from its `.env` file (`IP_LAPTOP1`, `IP_LAPTOP2`, `IP_LAPTOP3`).

**How a reading travels through the system**

```text
Laptop 1 ──HTTP──▶ Laptop 3 orchestrator ──HTTP──▶ Laptop 2 gateway ──▶ sleep · fatigue · cardio
 (dashboard)        │ rules → routing table          (dispatches, 3 s per model)
                    └──local──▶ solar risk (GPU if available)
```

1. **Laptop 1** receives the astronaut's readings, validates the sensors and sends the data to the orchestrator.
2. **Laptop 3** applies the rules against each astronaut's baseline. If it detects a potential risk, its routing table decides which specialist models to consult.
3. **Laptop 2** receives the request through its gateway and dispatches it to the sleep, fatigue and well-being, and cardiovascular models, with a maximum of 3 seconds per model. The solar-risk model runs locally on Laptop 3.
4. **Laptop 3** combines the answers (a specialist can raise the level by only one step and can never lower the rule-based level) and returns the level, the plain-language explanation, the step-by-step protocol and the flight surgeon report.
5. **Laptop 1** shows the result on the Crew dashboard and sends the next protocol step to the Watch.

**What happens when something fails**

- If Laptop 2 does not respond: **degraded mode** (rules + solar risk). The screen says so clearly.
- If one model does not respond: the others still answer and the missing one is reported.
- If Laptop 3 does not respond: Laptop 1 evaluates using its local copy of the rules.
- A broken sensor never triggers a red alert by itself and never lowers the alerts coming from other signals.

**Getting started (on each laptop, with Docker installed, `main` branch)**

```bash
cd laptop2-modelos        # then laptop3-orquestador, laptop1-backend-frontend
cp .env.example .env      # set the actual IP_LAPTOP1/2/3 addresses on the router
docker compose up --build
```

Recommended start order: Laptop 2, then Laptop 3, then Laptop 1. The interface is at `http://IP_LAPTOP1:8100/` and can also be opened from a phone.

To verify the network (Docker and internet are not required):

```bash
python3 scripts/verificar_red.py --desde laptop1   # Laptop 1 → Laptop 3 and what it can reach on Laptop 2
python3 scripts/verificar_red.py --desde laptop3   # Laptop 3 → gateway and each model on Laptop 2
```

## Run it on one machine

### Option A · Demo mode (`main` branch)

Uses model responses recorded from real runs; the screen indicates demo mode at all times.

```bash
pip install -r laptop1-backend-frontend/requirements.txt
./modo-demo-sin-laptops/arrancar_demo.sh local     # without Docker
./modo-demo-sin-laptops/arrancar_demo.sh           # with Docker (docker compose)
```

On Windows: `.\modo-demo-sin-laptops\arrancar_demo.ps1`. Dashboard: `http://localhost:8100/`, Watch: `http://localhost:8100/reloj/`.

### Option B · Full system on one machine (`main` branch)

Seven real processes on `127.0.0.1` ports, including the models:

```bash
pip install -r laptop2-modelos/requirements.txt
./scripts/arrancar_local.sh          # start
./scripts/arrancar_local.sh parar    # stop
```

On Windows: `.\scripts\arrancar_local.ps1` and `.\scripts\arrancar_local.ps1 parar` (if the execution policy blocks it: `powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\arrancar_local.ps1`). Dashboard: `http://127.0.0.1:8100/`, Watch: `http://127.0.0.1:8100/reloj/`.

### Option C · The single-service Render build (`Modo-Demo` branch)

This is exactly what the public demo runs. The files are on the `Modo-Demo` branch:

```bash
git clone -b Modo-Demo https://github.com/Abdriel369/Argonaut.git argonaut-demo
cd argonaut-demo
```

With Docker (same command Render uses):

```bash
docker build -f deploy/render/Dockerfile -t argonaut-render:local .
docker run --rm -p 8100:8100 argonaut-render:local
```

Without Docker (Python 3.12, from the repository root, PowerShell):

```powershell
$env:PYTHONPATH = "$PWD;$PWD\laptop1-backend-frontend;$PWD\laptop3-orquestador"
$env:RUTA_BD = "$PWD\.tmp\astro_medico.db"
$env:RESPUESTAS_GUARDADAS = "$PWD\modo-demo-sin-laptops\respuestas-guardadas.json"
.\.venv\Scripts\python.exe -m uvicorn app:app --app-dir deploy/render --port 8100
```

Smoke tests (13 checks):

```powershell
powershell -ExecutionPolicy Bypass -File deploy/render/smoke.ps1 -Base http://127.0.0.1:8100
```

Full deployment guide: [`deploy/render/README.md`](https://github.com/Abdriel369/Argonaut/blob/Modo-Demo/deploy/render/README.md) on the `Modo-Demo` branch.

## Public deployment (single service)

The published demo runs as **one Render Web Service, one Docker container and one process**:

```text
Browser (HTTPS) ──▶ FastAPI backend (API + frontend)
                          │  httpx.ASGITransport (in-process, no network)
                          ▼
                     Orchestrator (rules, panel, protocols, report)
                          │
                          ▼
                     respuestas-guardadas.json (88 recorded model responses)
```

- The backend serves the web interface and the API on the same port.
- The orchestrator and its rules are embedded in the same process: no second service, no IP addresses.
- The specialist models are **not executed**: the orchestrator answers from responses recorded from real runs.
- SQLite lives in `/tmp/astro_medico.db` and is rebuilt on every start (schema + six astronauts + 7-day script).

Resources measured with the free-plan limit (`--memory=512m --cpus=0.1`): **~41 MiB of RAM**, under 1 % CPU, 211 MB image, one process, ~10 s cold start.

## Tests

From the repository root on the `main` branch:

```bash
pip install -r laptop2-modelos/requirements.txt pytest
python -m pytest           # see the exact count in the output
```

Result on 2026-11-15: **304 tests pass**. `xgboost` is pinned below 3.0 in the model requirements: version 3.x crashed while shutting down with one team machine's CUDA driver. On Windows the tests force `USAR_GPU=no` for the same reason; the runtime keeps `USAR_GPU=auto`. The pure watch queue also has a Node script: `node laptop1-backend-frontend/frontend/reloj/pruebas/cola.script.mjs`.

**Coverage**

- **Contracts:** every JSON schema is valid; invalid messages are rejected.
- **Rules:** each day in the scenario produces the expected level (green, green, yellow, orange, red, yellow, green; day 4 rises to orange starting with sleep-specialist version 1.1.0); adaptation window; persistence; missing data does not break the system.
- **Orchestrator:** table-based routing; a specialist can raise a level by only one step (it can never lower the rule-based level); degraded mode without specialists.
- **Each model (4):** minimum AUC, artifact integrity (hash), output contract, explanatory factors, behavior with incomplete data, determinism, API (`/salud`, `/info`, `/predecir`), and reproducibility of synthetic data.
- **Backend:** data validation, baseline recalibration, muscle-and-bone exposure, protocols in the report, link with Earth, solar event, outages, and local fallback.
- **Sensor validation:** impossible value, abrupt jump, frozen value, normal scenario without false positives, and ensuring a broken sensor does not trigger a red alert by itself or lower alerts from other signals.
- **Integration:** complete 7-day scenario; Laptop 2 offline; one model offline; interface without remote resources.
- **Demo mode:** the scenario plays back identically using saved responses.
- **Crew:** the readiness formula with a fixed fixture, orange/red caps, `null` when coverage is low, tie-breakers, degraded mode, and one astronaut failing without hiding the others.
- **Watch:** reading isolation, idempotency by `lectura_id`, sensor validation of a suspicious reading, compact-state contract, no orchestrator call on every poll, and the linear projection (including fewer than 3 points).
- **Migration:** an old single-astronaut SQLite file keeps AST-01's history, gets a backup and seeds the other five.

## Data, assumptions, and thresholds

All data is simulated. Models are trained on synthetic data generated within public reference ranges (NASA HRP, CSA). Each generator uses a fixed seed and documents its assumptions: `laptop2-modelos/datos-sinteticos/SUPUESTOS.md` and `laptop3-orquestador/modelos/riesgo-solar/SUPUESTOS.md`.

Metrics show that the model learned the synthetic rule, not that it is clinically valid.

Thresholds and weights are stored in configuration files with comments. **They are example values and must be replaced and sourced before any serious use.**

**Sources:** [`SOURCES.md`](SOURCES.md) (English) and [`FUENTES.md`](FUENTES.md) (Spanish) explain where each threshold comes from and provide the full reference for each source. The team verified NASA-STD-3001 Vol. 1 [V1 4030] (career dose below 600 mSv). Nine other sources were opened and checked on 2026-11-15; they support the rationale behind 14 thresholds, not their numerical values. Three thresholds remain marked `SOURCE TO BE CITED` (heart rate, heart-rate variability, and the cardiovascular rule). The cutoffs are design decisions, not values copied from the standard.

**Sensors:** sensor validation runs before the rules and models (possible range, abrupt change, frozen value). A suspicious reading is not used and generates an equipment warning. Example limits and assumptions are documented in `laptop1-backend-frontend/SUPUESTOS.md`.

| Threshold | Example value | Location | Basis |
|---|---|---|---|
| Sleep below baseline | 1 h yellow, 2.5 h orange, 3.5 h red; 3-day persistence | `laptop3-orquestador/reglas/config/umbrales.toml` | Rationale: NASA HRP, sleep and fatigue risk |
| Low mood | 2 points (1–5 scale); 3-day persistence | same | Rationale: NASA HRP, behavioral health |
| High stress | 20 / 35 / 55 points above baseline (0–100) | same | Prototype's own scale |
| Low exercise | 30% and 50% below plan; 5 days | same | Rationale: ISS exercise countermeasures |
| High resting heart rate | +15% / +25% / +40% | same | Source to be cited |
| Low HRV | −20% / −35% / −50% | same | Source to be cited |
| Low SpO₂ | 3 / 5 / 8 points below baseline | same | Reference value (approx. 95%) |
| Elevated temperature | +0.8 / +1.3 / +2.0 °C | same | Reference value |
| Low food intake | below 75% of plan (and 60% in combination) | same | Rationale: NASA HRP, nutrition |
| Current radiation rate | 60 / 200 / 1000 µSv/h | same | Rationale: NASA-STD-3001 Vol. 1 |
| Cumulative radiation | 50 / 150 / 250 mSv | same | **Verified:** NASA-STD-3001 Vol. 1 [V1 4030], career dose below 600 mSv. The three cutoffs are design steps toward that limit |
| Risk-level cutoff | 0.20 / 0.50 / 0.75 | `comun/especialista/nucleo.py` | Prototype's own scale |
| Maximum time per model | 3 s | `laptop3-orquestador/orquestador/clientes.py` (real models only; not used in the demo) | System design |
| Adaptation window | 2 days, thresholds ×1.5 | `laptop3-orquestador/reglas/config/umbrales.toml` | Rationale: NASA HRP, duration of initial adaptation |

The "Basis" column gives the rationale for each threshold, not a citation of its numerical value. Complete references and verification status are in [`SOURCES.md`](SOURCES.md).

## Limitations (honest disclosure)

- **Not a diagnosis.** It flags risk and recommends actions; it does not replace the medical team.
- **Simulated and synthetic data.** The ranges are reference ranges; Earth-based and synthetic data do not fully represent the space environment.
- **Blood pressure and glucose:** not reliable without dedicated equipment. They are optional external modules using simulated data.
- **Muscle and bone:** only an estimated exposure based on mission days and completed exercise. It is not a measurement.
- **Immune system:** planned future work. It requires blood, saliva, and urine; it is not simulated.
- **Radiation:** the solar event is simulated. There is no space-weather forecast or real dosimeter.
- **Confidence:** this is a heuristic, not a calibrated probability.
- **Sensor validation:** limits are example values and the prototype has only one reading per day. A sensor stuck at a plausible value may take 4 or 5 days to detect. A very abrupt real change remains flagged as suspicious until a person manually confirms it.
- **Protocols:** example text with no medication dosages. A real protocol must be defined by the mission medical team.
- **Readiness index:** a demo heuristic built from simulated profiles and local rules. It is not a calibrated probability, a medical evaluation or a fitness-for-duty decision. The weights and caps live in `laptop1-backend-frontend/backend/config/tripulacion.toml`; see `laptop1-backend-frontend/SUPUESTOS_TRIPULACION.md`.
- **Crew profiles:** the six astronauts are fictional and deterministic. AST-05 intentionally has no records for days 3–7, so the crew view shows **Not enough data** instead of a misleading zero.
- **Watch:** a web screen, not a native app. It does not use Bluetooth or real sensors. Its offline queue lives in `localStorage` and is limited to 20 readings per astronaut; the demo does not use service workers or background execution.

## Known issues

- **Watch "Today" screen language:** when an alert is active, the next protocol step on the watch's **Today** tab is shown in Spanish, while the rest of the interface is in English. The **Alert** tab shows the same steps correctly in English. Cause: `laptop1-backend-frontend/frontend/reloj/reloj.js` renders `paso.texto` directly instead of passing it through `pasoProtocolo(...)`, which the Alert tab already uses.

## Verification status

**Verified:**

- All 304 tests pass on the `main` branch (re-run on 2026-11-15); the 7-day scenario produces the expected scripted levels.
- **Three-laptop setup:** the full system was run on three laptops connected through a dedicated router, each with its own `docker compose` stack, and it worked as designed.
- The single-service demo (`Modo-Demo` branch) was built with Docker and run under the free-plan limit (`--memory=512m --cpus=0.1`) on a dynamic `PORT`. The 13 smoke checks passed inside the container (`deploy/render/smoke.ps1`): `/`, `/reloj/` and their local assets, `/salud`, six astronauts, day change, solar event, recorded specialist responses, alerts, protocols, suspicious sensor, degraded mode and recovery, watch state and idempotent reading, reset, and CSV export. Memory stayed at ~41 MiB, CPU under 1 %, and SIGTERM shut the server down in ~1.1 s with exit code 0.
- The public deployment on Render is reachable without login at https://argonaut-demo.onrender.com/ (checked on 2026-11-15).
- A visual check with headless Chrome rendered `/` and `/reloj/` at desktop size and with emulated 360/390 px viewports; the Crew table loaded its six rows, the AST-03 detail opened, and there was no horizontal overflow.

**Not verified:**

- The full offline → reload → online cycle in browser DevTools was not automated; the pure queue logic is covered by Node tests and the HTTP endpoints by pytest.

## Repository structure

`main` branch:

```text
contratos/                  shared JSON schemas + examples + tests
comun/                      validation, levels, shared logging, base for the 4 specialist models
laptop1-backend-frontend/   backend, frontend (no CDN), profile and scenario configuration,
                            six crew profiles (tripulacion.toml), readiness index (aptitud.py),
                            sensor validation, /reloj/ watch page with offline queue
laptop2-modelos/            gateway, 3 models, synthetic-data generators (training only)
laptop3-orquestador/        orchestrator, rules, protocols, solar-risk model
modo-demo-sin-laptops/      recorded specialist responses (88), the script that captured them,
                            and the one-machine demo launcher
pruebas-integracion/        in-memory stack, input factory, integration tests
scripts/                    one-machine launcher (7 processes) and network checker
PLAN.md                     phases and acceptance state
DEMO_RELOJ.md               2–3 minute watch + crew demo script
PROMPT_RELOJ_Y_TRIPULACION.md  brief used for the AI-assisted watch and crew work
SOURCES.md / FUENTES.md     threshold origins and items still requiring verification (EN / ES)
```

`Modo-Demo` branch (public demo only):

```text
deploy/render/              Dockerfile, entrypoint (backend + orchestrator in-process via
                            httpx.ASGITransport), requirements, smoke tests and deployment guide
render.yaml                 optional Render Blueprint for the Web Service
```

## Tools and Resources

| Tool or resource | What it contributed to the project |
|---|---|
| Git and GitHub | Git kept a history of changes to the code. GitHub provided a shared repository so team members could pull updates and test the same version of the dashboard on their own laptops. |
| Visual Studio Code | Used to work with the backend and interface files in one workspace. From its integrated terminal, the team could start the application and review container messages while checking the result in the browser. |
| Docker Desktop and Docker Compose | Allowed the application to run with the dependencies and configuration defined by the project. During testing, the team could start the service, open the dashboard at `localhost:8100`, and stop it once the demo was finished. |
| Render | Hosts the public demo as a single Docker web service so anyone can try the dashboard and the watch without installing anything. |
| Python, FastAPI, and Uvicorn | Python was used to write the backend logic. FastAPI organizes the endpoints through which the interface requests information, and Uvicorn runs the server that handles those requests. |
| SQLite, HTTPX, and jsonschema | SQLite provides local storage for the backend. HTTPX lets services communicate over HTTP (and in-process in the public demo). jsonschema checks that messages have the expected structure, for example that required fields are present and each value has the correct type. |
| NumPy, scikit-learn, and XGBoost | Used to train and run the four specialist models (logistic regression and small gradient-boosting models) on synthetic data. |
| HTML, CSS, and JavaScript | HTML organizes elements such as the sleep, mood, and pulse cards. CSS defines their layout, typography, and colors so each indicator's status can be recognized at a glance. JavaScript handles actions such as selecting a region on the body map, replaying the mission week, or triggering a solar event. |
| Atkinson Hyperlegible and Barlow Semi Condensed | Typefaces used in the dashboard design to distinguish titles, labels, and numeric values. The font files are bundled with the project so the interface works without downloading fonts during the demo. |
| Gemini (Google) | Used as research support to search for data and background information on the topics behind the project. The team checked the findings against the original sources before using them. |
| Claude (Anthropic) | Handled most of the programming and the design of the system, including the backend, the dashboard interface, and how its components connect. It also helped review scientific sources, organize references, and draft the project description and presentation for the competition. The team tested and validated the result. |
| ChatGPT Pro (OpenAI) | Used to review and correct the project's flowchart as the system evolved. It also helped proofread texts and supported the writing of the project documentation. The team reviewed and edited the final content. |
| DeepSeek (with an agent harness) | Used as a coding assistant to merge the backend and the orchestrator into a single container for Render. It replaced the heavy models with saved responses and verified that the full demo runs within 512 MB of memory and 0.1 CPU. The team reviewed and validated the result. |

Font licenses (SIL OFL 1.1): `laptop1-backend-frontend/frontend/fuentes/`.

## Sources and threshold documentation

The full source register, including bibliographic details, verification status, what each reference supports, and which values are design choices, is maintained in [`SOURCES.md`](SOURCES.md). Read it before interpreting any threshold as an evidence-based clinical limit.
