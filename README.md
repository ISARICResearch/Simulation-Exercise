# Kajini Simulation Exercise Dashboard

A facilitator-facing Plotly Dash dashboard for the Kajini One Health simulation exercise.

The dashboard is an illustrative consequence tool. It is not a validated epidemiological forecast.

## How the simulation works

The simulation runs across a configurable number of simulated days. The map and charts update automatically as the simulation clock advances.

The main control is the **Context** panel. Facilitators adjust nine response factors using sliders from `-1` to `+1`, in steps of `0.5`:

- Coordination effectiveness
- Healthcare-worker safety considered
- Clinical research initiative
- Cattle health considered
- Community trust
- Misinformation control
- Resource management
- Transparent political decision making
- International confidence

Changing a slider immediately updates the illustrative outbreak and health outputs. More favourable context generally reduces cases, deaths and cattle losses, and reduces pressure on hospital capacity.

There are currently no facilitator questions, scenario choices or decision-flow pauses in the active dashboard. Optional pause settings remain in `app.py` if a future version needs them.

## Dashboard structure

### Map

The central map is a fictional schematic map of Kajini with seven regions, including DASS, the central capital. Regions are coloured according to illustrative case burden.

DASS includes functioning response capacity: Central Government, NPHA, the national laboratory and Dass General Hospital.

### Outbreak & health tab

- Daily human cases and total human cases
- Cumulative human deaths
- Test positivity
- Cattle deaths
- Hospital capacity

### Clinical data tab

- Patient age/sex pyramid
- Clinical symptom profile
- Cumulative mortality rate

### Context panel

The Context panel is always visible and contains the nine sliders. It is the main mechanism for exploring how response conditions affect the simulated outcomes.

## Simulation timing

The default simulation length is controlled in `app.py`:

    SIMULATION_DAYS = 30

The speed is controlled in milliseconds per simulated day:

    DAY_INTERVAL_MS = 1_000

The simulation clock display is hidden in the current interface, but the interval continues to drive daily updates.

## Consequence model

The editable outcome logic is marked in `app.py` with:

    # USER-EDITABLE CONSEQUENCE MODEL

The model uses simple assumptions to translate the context sliders into changes in daily cases, cumulative deaths, mortality, cattle deaths, hospital capacity and regional case burden.

The epidemic curve is intentionally stylised rather than scientifically calibrated. It includes an onset, growth phase and peak-like pattern so that the exercise can show cases increasing and then stabilising or declining. The context factors modify the trajectory; this is not a formal `R0`, incubation-period or transmission model.

The coefficients are exercise assumptions and can be changed by the user. They should not be interpreted as real-world estimates.

## Running the app

    .\.venv\Scripts\Activate.ps1
    pip install -r requirements.txt
    python app.py

Open `http://127.0.0.1:8050/`.

## Files

    app.py                         Main Dash application and editable model
    assets/dashboard.css           Dashboard styling
    data/kajini_map.geojson        Fictional Kajini map
    requirements.txt               Python dependencies
    Reference/                     Exercise notes and reference materials

## Facilitator workflow

1. Start the dashboard.
2. Confirm the simulation duration and speed in `app.py`.
3. Start the simulation clock.
4. Use the Context sliders to represent the response conditions being discussed.
5. Observe the immediate changes in the map, outbreak charts and clinical indicators.
6. Use the Outbreak & health and Clinical data tabs during discussion and debrief.
7. Adjust the editable model or add plots if the exercise design changes.

## Interpretation

All values are illustrative scenario values. The dashboard supports discussion of how coordination, trust, safety, information, resources and other response factors may influence outcomes. It is not an AI system, clinical decision-support system or validated outbreak forecast.
