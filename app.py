"""Kajini One Health emergency decision-and-consequence dashboard.

Run with: python app.py
The exercise data and visual definitions are intentionally kept in this file
for the prototype; they can later move to YAML/CSV/GeoJSON files unchanged.
"""
import json
import math
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
from dash import Dash, Input, Output, dcc, html, dash_table
from dash import State, ctx


CONFIG = {
    "title": "Kajini One Health Emergency",
    "subtitle": "Decision and consequence dashboard",
    "rounds": [
        "The signal",
        "Trust under pressure",
        "International escalation",
        "Scarce resources and political pressure",
    ],
    "health": [
        ("Human cases", "100 suspected", "↑", "amber"),
        ("Human deaths", "10", "↑", "amber"),
        ("Healthcare-worker safety", "Fragile", "↑", "red"),
        ("Cattle deaths / livelihoods", "200 deaths", "↑", "red"),
        ("Hospital capacity", "Stretched", "→", "amber"),
        ("Laboratory / testing", "Limited", "→", "amber"),
    ],
    "response": [("Community trust", 1), ("Coordination quality", 1), ("International confidence", 0)],
    "pressure": [("Misinformation / media", 2), ("Political pressure", 2), ("Resource pressure", 2)],
}
SIMULATION_DAYS = 16
UPDATE_FRACTIONS = [0.0, 0.3, 0.6, 0.8, 1.0]

UPDATE_DAYS = [round(SIMULATION_DAYS * fraction) for fraction in UPDATE_FRACTIONS]
# USER-EDITABLE SIMULATION SPEED: milliseconds per simulated day.
DAY_INTERVAL_MS = 1_000
# Optional facilitator pauses. Disabled for the current slider-led workflow.
ENABLE_STAGE_PAUSES = True
#PAUSE_FRACTIONS = [1/3, 2/3, 1.0]
PAUSE_FRACTIONS = UPDATE_FRACTIONS[1:]
PAUSE_DAYS = [round(SIMULATION_DAYS * fraction) for fraction in PAUSE_FRACTIONS]

HEALTH_HISTORY = {
    "days": UPDATE_DAYS,
    "daily_cases": [12, 28, 46, 38, 24],
    "human_deaths": [10, 25, 80, 105, 120],
    "mortality_rate": [10, 11, 16, 17, 17],
    "test_positivity": [8, 14, 27, 24, 19],
    "cattle_deaths": [200, 500, 1200, 1450, 1600],
    "hospital_capacity": [60, 78, 91, 88, 84],
}
REGION_CASES = {
    "northern_highlands": [0, 3, 12, 17, 20],
    "western_farms": [12, 40, 75, 84, 90],
    "central_capital": [0, 8, 35, 55, 70],
    "eastern_corridor": [0, 0, 12, 23, 32],
    "lakeside_communities": [0, 0, 5, 12, 18],
    "southern_plains": [0, 0, 0, 4, 8],
    "southern_borderlands": [0, 0, 0, 2, 4],
}
REGION_LABELS = {
    "northern_highlands": "AREA 1",
    "western_farms": "AREA 2",
    "central_capital": "DASS",
    "eastern_corridor": "AREA 4",
    "lakeside_communities": "AREA 5",
    "southern_plains": "AREA 6",
    "southern_borderlands": "AREA 7",
}
REGION_CENTROIDS = {
    "northern_highlands": (0.2, 3.7),
    "western_farms": (-3.4, 0.5),
    "central_capital": (-0.1, 1.1),
    "eastern_corridor": (3.4, 1.8),
    "lakeside_communities": (-0.2, -0.4),
    "southern_plains": (-0.2, -2.6),
    "southern_borderlands": (3.2, -2.8),
}
CLINICAL_SYMPTOMS = ["Fever", "Cough", "Fatigue", "Shortness of breath", "Vomiting", "Diarrhoea", "Confusion", "Bleeding"]
CLINICAL_HISTORY = {
    "symptoms": {name: [1, 12, 30, 40, 48] for name in CLINICAL_SYMPTOMS},
    "daily_mortality": [2, 4, 8, 10, 12],
}
CLINICAL_HISTORY["symptoms"].update({"Fever": [68, 72, 70, 71, 71], "Cough": [52, 55, 53, 54, 54], "Fatigue": [48, 50, 49, 51, 51], "Shortness of breath": [12, 18, 23, 22, 22], "Vomiting": [20, 21, 19, 20, 20], "Diarrhoea": [25, 27, 26, 27, 27], "Confusion": [4, 6, 9, 10, 10], "Bleeding": [1, 2, 2, 2, 2]})
AGE_GROUPS = ["0–5", "6–15", "16–25", "26–35", "36–45", "46–55", "56–65", "66–75", "76–85", "86+"]

MAP_PATH = Path(__file__).parent / "data" / "kajini_map.geojson"
with MAP_PATH.open(encoding="utf-8") as map_file:
    GEOJSON = json.load(map_file)


UPDATE_DATA = {
    1: {"response": [("Community trust", 0), ("Coordination quality", 1), ("International confidence", 0)], "pressure": [("Misinformation / media", 1), ("Political pressure", 1), ("Resource pressure", 2)], "note": "Early action improves coordination, but healthcare-worker safety remains fragile."},
    2: {"response": [("Community trust", -1), ("Coordination quality", 0), ("International confidence", 0)], "pressure": [("Misinformation / media", 3), ("Political pressure", 2), ("Resource pressure", 3)], "note": "Community resistance is now a major response barrier."},
    3: {"response": [("Community trust", -1), ("Coordination quality", 1), ("International confidence", -1)], "pressure": [("Misinformation / media", 3), ("Political pressure", 3), ("Resource pressure", 3)], "note": "International confidence falls as communication remains late and inconsistent."},
    4: {"response": [("Community trust", 0), ("Coordination quality", 1), ("International confidence", 1)], "pressure": [("Misinformation / media", 2), ("Political pressure", 3), ("Resource pressure", 4)], "note": "The response stabilises only if trust, hospital protection and transparent reporting are sustained."},
}

# ============================================================
# USER-EDITABLE CONSEQUENCE MODEL
# Change these weights and effects to tune a different exercise.
# Scores use the exercise rubric: -2 strongly negative to +2 strongly positive.
# ============================================================
MODEL_WEIGHTS = {"trust": 0.30, "coordination": 0.25, "healthcare_safety": 0.20, "misinformation": 0.15, "resources": 0.10}
# Starting conditions for the exercise. These values are user-editable.
INITIAL_HUMAN_CASES = 100
INITIAL_HUMAN_DEATHS = 10
INITIAL_CATTLE_CASES = 1000
CATTLE_CASE_GROWTH_FACTOR = 1.1

DECISION_EFFECTS = {
    10: {"question": "How was early surveillance and healthcare-worker protection established?", "option_a": "Scenario A — Coordinated early action", "option_b": "Scenario B — Partial or fragmented action", "positive": {"Community trust": 1, "Coordination quality": 2, "Healthcare-worker safety": 1, "Misinformation pressure": -1, "Resource pressure": 0}, "negative": {"Community trust": -1, "Coordination quality": -1, "Healthcare-worker safety": -2, "Misinformation pressure": 1, "Resource pressure": 1}},
    20: {"question": "How did the response engage communities and support farmer cooperation?", "option_a": "Scenario A — Trust-building engagement", "option_b": "Scenario B — Limited community engagement", "positive": {"Community trust": 2, "Coordination quality": 1, "Healthcare-worker safety": 0, "Misinformation pressure": -1, "Resource pressure": 0}, "negative": {"Community trust": -2, "Coordination quality": -1, "Healthcare-worker safety": 0, "Misinformation pressure": 2, "Resource pressure": 1}},
    30: {"question": "How were scarce resources prioritised to protect lives and essential services?", "option_a": "Scenario A — Transparent prioritisation", "option_b": "Scenario B — Competing priorities remain unresolved", "positive": {"Community trust": 1, "Coordination quality": 1, "Healthcare-worker safety": 2, "Misinformation pressure": -1, "Resource pressure": -1}, "negative": {"Community trust": -1, "Coordination quality": -1, "Healthcare-worker safety": -2, "Misinformation pressure": 1, "Resource pressure": 2}},
}
CURRENT_OUTCOME_FACTOR = 0.0
CURRENT_FACTORS = {"Community trust": 0, "Coordination quality": 0, "Healthcare-worker safety": 0, "Misinformation pressure": 0, "Resource pressure": 0}
CONTEXT_HISTORY = {name: [0, 0, 0, 0] for name in CURRENT_FACTORS}
SLIDER_FACTORS = ["Coordination effectiveness", "Healthcare-worker safety considered", "Clinical research initiative", "Cattle health considered", "Community trust", "Misinformation control", "Resource management", "Transparent political decision making", "International confidence"]
CURRENT_SLIDER_FACTORS = {name: 0 for name in SLIDER_FACTORS}

COLORS = {"green": "#22c55e", "amber": "#f59e0b", "red": "#ef4444", "grey": "#94a3b8"}


def health_table():
    return dash_table.DataTable(
        data=[{"indicator": a, "value": b, "trend": c, "status": d.title()} for a, b, c, d in CONFIG["health"]],
        columns=[{"name": "Indicator", "id": "indicator"}, {"name": "Current", "id": "value"}, {"name": "Trend", "id": "trend"}, {"name": "Status", "id": "status"}],
        style_as_list_view=True, style_header={"backgroundColor": "#172033", "color": "#f8fafc", "fontWeight": "bold"},
        style_cell={"backgroundColor": "#101827", "color": "#dbeafe", "border": "none", "padding": "8px", "fontSize": "12px", "textAlign": "left"},
        style_data_conditional=[{"if": {"filter_query": '{status} = "Red"'}, "color": COLORS["red"]}, {"if": {"filter_query": '{status} = "Amber"'}, "color": COLORS["amber"]}],
    )


def value_at_day(key, day):
    day = min(max(day, 0), SIMULATION_DAYS)
    context_score = sum(CURRENT_SLIDER_FACTORS.values()) / len(CURRENT_SLIDER_FACTORS)

    # USER-EDITABLE STYLISED EPIDEMIC CURVE
    # This deliberately mimics an epidemic shape without using R0,
    # incubation periods or claiming scientific epidemiological accuracy.
    def daily_epidemic_cases(target_day):
        onset = 1 / (1 + math.exp(-(target_day - 5) / 1.8))
        peak = 48 * math.exp(-0.5 * ((target_day - 18) / 8) ** 2)
        growth_adjustment = 1 - 0.45 * context_score
        return max(0, 2 + onset * peak * growth_adjustment)

    if key == "daily_cases":
        return round(daily_epidemic_cases(day), 1)
    if key == "human_deaths":
        cumulative_cases = sum(daily_epidemic_cases(d) for d in range(1, int(day) + 1))
        mortality = max(0.04, 0.12 - 0.04 * context_score)
        return round(INITIAL_HUMAN_DEATHS + cumulative_cases * mortality, 1)
    if key == "cattle_deaths":
        daily_cattle = lambda target_day: 1 + CATTLE_CASE_GROWTH_FACTOR * daily_epidemic_cases(target_day) * (1 - 0.25 * context_score)
        return round(INITIAL_CATTLE_CASES + sum(daily_cattle(d) for d in range(1, int(day) + 1)), 1)
    if key == "hospital_capacity":
        # Hospital pressure follows current severe-case pressure, not the
        # cumulative case total, so it can rise and later decline.
        current_cases = daily_epidemic_cases(day)
        capacity = 88 + current_cases * 0.25 - 8 * context_score
        return round(max(0, min(100, capacity)), 1)

    value = float(pd.Series(HEALTH_HISTORY[key], index=HEALTH_HISTORY["days"]).reindex(range(0, SIMULATION_DAYS + 1)).interpolate().loc[min(day, SIMULATION_DAYS)])
    # Transparent consequence adjustment: positive decisions reduce pressure;
    # negative decisions increase it. This is an exercise model, not a forecast.
    slider_score = sum(CURRENT_SLIDER_FACTORS.values()) / len(CURRENT_SLIDER_FACTORS)
    if key in {"daily_cases", "cattle_deaths"}:
        value *= 1 - 0.10 * slider_score
    elif key == "human_deaths":
        value *= 1 - 0.08 * slider_score
    elif key == "hospital_capacity":
        value -= 8 * slider_score
    return round(value, 1)


def daily_cases_chart(day=0):
    days = list(range(0, max(day, 1) + 1))
    cases = [cumulative_cases(d) for d in days]
    fig = go.Figure(go.Bar(name="Total cases", x=days, y=cases, marker_color="#f59e0b", hovertemplate="Day %{x}<br>Total cases: %{y:.0f}<extra></extra>"))
    fig.update_layout(title={"text": "Total human cases", "font": {"size": 13}}, height=215, margin=dict(l=10, r=10, t=38, b=35), xaxis={"title":"Simulation day", "range":[-0.5, SIMULATION_DAYS + 0.5], "dtick":5, "tickprefix":"Day ", "gridcolor":"#26344d"}, yaxis={"title":"Total cases", "gridcolor":"#26344d"}, paper_bgcolor="#101827", plot_bgcolor="#101827", font_color="#dbeafe", showlegend=False)
    return fig


def cumulative_cases(day=0):
    return round(INITIAL_HUMAN_CASES + sum(value_at_day("daily_cases", d) for d in range(1, int(day) + 1)))


def deaths_chart(day=0):
    days = list(range(1, max(day, 1) + 1))
    deaths = [value_at_day("human_deaths", d) for d in days]
    fig = go.Figure(go.Scatter(name="Cumulative deaths", x=days, y=deaths, mode="lines+markers", line={"color":"#ef4444", "width":3}, marker={"size":6}, hovertemplate="Day %{x}<br>Cumulative deaths: %{y:.0f}<extra></extra>"))
    fig.update_layout(title={"text": "Cumulative human deaths", "font": {"size": 13}}, height=190, margin=dict(l=10, r=10, t=38, b=35), xaxis={"title":"Simulation day", "range":[0.5, SIMULATION_DAYS + 0.5], "dtick":5, "tickprefix":"Day ", "gridcolor":"#26344d"}, yaxis={"title":"Deaths", "gridcolor":"#26344d"}, paper_bgcolor="#101827", plot_bgcolor="#101827", font_color="#dbeafe", showlegend=False)
    return fig


def positivity_chart(day=0):
    days = list(range(1, max(day, 1) + 1))
    positivity = [value_at_day("test_positivity", d) for d in days]
    fig = go.Figure(go.Scatter(name="Test positivity", x=days, y=positivity, mode="lines+markers", line={"color":"#a855f7", "width":3}, marker={"size":6}, hovertemplate="Day %{x}<br>Test positivity: %{y:.1f}%<extra></extra>"))
    fig.update_layout(title={"text": "Test positivity", "font": {"size": 13}}, height=190, margin=dict(l=10, r=10, t=38, b=35), xaxis={"title":"Simulation day", "range":[0.5, SIMULATION_DAYS + 0.5], "dtick":5, "tickprefix":"Day ", "gridcolor":"#26344d"}, yaxis={"title":"Positive tests", "range":[0,100], "ticksuffix":"%", "gridcolor":"#26344d"}, paper_bgcolor="#101827", plot_bgcolor="#101827", font_color="#dbeafe", showlegend=False)
    return fig


def cattle_chart(day=0):
    days = list(range(0, max(day, 1) + 1))
    cattle = [value_at_day("cattle_deaths", d) for d in days]
    fig = go.Figure(go.Bar(name="Cattle cases", x=days, y=cattle, marker_color="#a16207", hovertemplate="Day %{x}<br>Cattle cases: %{y:.0f}<extra></extra>"))
    fig.update_layout(title={"text": "Cattle cases", "font": {"size": 13}}, height=190, margin=dict(l=10, r=10, t=38, b=35), xaxis={"title":"Simulation day", "range":[-0.5, SIMULATION_DAYS + 0.5], "dtick":5, "tickprefix":"Day ", "gridcolor":"#26344d"}, yaxis={"title":"Total cattle cases", "gridcolor":"#26344d"}, paper_bgcolor="#101827", plot_bgcolor="#101827", font_color="#dbeafe", showlegend=False)
    return fig


def capacity_gauge(day=0):
    capacity = value_at_day("hospital_capacity", day)
    fig = go.Figure(go.Indicator(mode="gauge+number", value=capacity, number={"suffix":"%"}, title={"text":"Hospital capacity used"}, gauge={"axis":{"range":[0,100]}, "bar":{"color":"#f59e0b"}, "steps":[{"range":[0,70],"color":"#17351f"},{"range":[70,90],"color":"#4b3a13"},{"range":[90,100],"color":"#4b1d22"}], "threshold":{"line":{"color":"#ef4444","width":4},"thickness":.8,"value":90}}))
    fig.update_layout(height=190, margin=dict(l=15, r=15, t=35, b=5), paper_bgcolor="#101827", font_color="#dbeafe")
    return fig


def context_chart(day=0):
    labels = list(CURRENT_SLIDER_FACTORS)
    scores = [CURRENT_SLIDER_FACTORS[label] for label in labels]
    colors = ["#22c55e" if score >= 0 else "#ef4444" for score in scores]
    fig = go.Figure(go.Bar(x=scores, y=labels, orientation="h", marker_color=colors, customdata=["Improving" if s > 0 else "Deteriorating" if s < 0 else "Stable" for s in scores], hovertemplate="%{y}<br>Status: %{customdata}<extra></extra>"))
    fig.update_layout(title={"text":"Response context", "font":{"size":13}}, height=330, margin=dict(l=10, r=10, t=55, b=35), xaxis={"range":[-2,2], "tickvals":[-2,0,2], "ticktext":["Negative", "Neutral", "Positive"], "zeroline":True, "zerolinecolor":"#f8fafc", "gridcolor":"#26344d"}, yaxis={"autorange":"reversed", "tickfont":{"size":10}}, paper_bgcolor="#101827", plot_bgcolor="#101827", font_color="#dbeafe", showlegend=False)
    return fig


def clinical_pyramid(day=0):
    scale = max(value_at_day("daily_cases", day) / 12, .5)
    female = [round(x * scale) for x in [3, 5, 8, 12, 15, 13, 9, 6, 3, 1]]
    male = [round(x * scale) for x in [4, 6, 9, 13, 16, 14, 10, 5, 3, 1]]
    axis_max = max(max(female), max(male), 10)
    tick_values = [-axis_max, -axis_max / 2, 0, axis_max / 2, axis_max]
    tick_labels = [str(axis_max), str(round(axis_max / 2)), "0", str(round(axis_max / 2)), str(axis_max)]
    fig = go.Figure()
    fig.add_trace(go.Bar(name="Female", y=AGE_GROUPS, x=[-x for x in female], orientation="h", marker_color="#c084fc", hovertemplate="Female %{y}: %{customdata}<extra></extra>", customdata=female))
    fig.add_trace(go.Bar(name="Male", y=AGE_GROUPS, x=male, orientation="h", marker_color="#38bdf8", hovertemplate="Male %{y}: %{x}<extra></extra>"))
    fig.update_layout(title={"text": "Affected patients by age and sex", "font": {"size": 13}}, barmode="relative", height=330, margin=dict(l=10, r=10, t=38, b=25), xaxis={"title":"Patients", "range":[-axis_max * 1.1, axis_max * 1.1], "tickvals":tick_values, "ticktext":tick_labels, "gridcolor":"#26344d", "zeroline":True, "zerolinecolor":"#f8fafc"}, yaxis={"title":"Age group", "categoryorder":"array", "categoryarray":AGE_GROUPS}, paper_bgcolor="#101827", plot_bgcolor="#101827", font_color="#dbeafe", legend={"orientation":"h", "y":-0.16, "x":0})
    return fig


def symptom_chart(day=0):
    values = [(name, value_at_day_from_history(CLINICAL_HISTORY["symptoms"][name], day)) for name in CLINICAL_SYMPTOMS]
    labels, scores = zip(*values)
    fig = go.Figure(go.Bar(x=list(scores), y=list(labels), orientation="h", marker_color="#a855f7", hovertemplate="%{y}: %{x:.1f}%<extra></extra>"))
    fig.update_layout(title={"text": "Clinical symptom profile", "font": {"size": 13}}, height=285, margin=dict(l=10, r=10, t=38, b=25), xaxis={"title":"Patients with symptom", "range":[0,100], "ticksuffix":"%", "gridcolor":"#26344d"}, yaxis={"autorange":"reversed"}, paper_bgcolor="#101827", plot_bgcolor="#101827", font_color="#dbeafe", showlegend=False)
    return fig


def value_at_day_from_history(values, day):
    series = pd.Series(values, index=UPDATE_DAYS).reindex(range(0, SIMULATION_DAYS + 1)).interpolate()
    return round(float(series.loc[min(day, SIMULATION_DAYS)]), 1)


def clinical_mortality_chart(day=0):
    current_day = max(day, 1)
    cumulative_cases = INITIAL_HUMAN_CASES + sum(value_at_day("daily_cases", d) for d in range(1, current_day + 1))
    cumulative_deaths = value_at_day("human_deaths", current_day)
    rate = round(cumulative_deaths / cumulative_cases * 100, 1) if cumulative_cases else 0
    fig = go.Figure(go.Indicator(mode="number", value=rate, number={"suffix":"%", "font":{"size":52, "color":"#ef4444"}}, title={"text":f"Cumulative mortality rate · Day {current_day}", "font":{"size":13}}, domain={"x":[0,1], "y":[0,1]}))
    fig.update_layout(height=170, margin=dict(l=10, r=10, t=35, b=5), paper_bgcolor="#101827", font_color="#dbeafe")
    return fig


def bar_chart(items, title, minimum, maximum, colors):
    labels, values = zip(*items)
    fig = go.Figure(go.Bar(x=list(values), y=list(labels), orientation="h", marker_color=colors))
    fig.update_layout(title={"text": title, "font": {"size": 13}}, height=155, margin=dict(l=10, r=10, t=35, b=20), xaxis=dict(range=[minimum, maximum], zeroline=True, gridcolor="#26344d"), yaxis=dict(autorange="reversed"), paper_bgcolor="#101827", plot_bgcolor="#101827", font_color="#dbeafe", showlegend=False)
    return fig


def interpolate_items(start, end, fraction):
    """Linearly interpolate values while preserving indicator labels."""
    return [(label, round(a + (b - a) * fraction, 2)) for (label, a), (_, b) in zip(start, end)]


def state_at_day(day):
    """Return a linearly interpolated state for the 30-day exercise."""
    day = min(max(day, 0), SIMULATION_DAYS)
    right_index = next((i for i, update_day in enumerate(UPDATE_DAYS) if update_day >= day), len(UPDATE_DAYS) - 1)
    left_index = max(right_index - 1, 0)
    left_day, right_day = UPDATE_DAYS[left_index], UPDATE_DAYS[right_index]
    fraction = 0 if left_day == right_day else (day - left_day) / (right_day - left_day)
    # UPDATE_DATA describes the four session states, while UPDATE_DAYS has
    # five boundaries. Keep the final boundary on the final session state.
    base = UPDATE_DATA[min(left_index + 1, max(UPDATE_DATA))]
    target = UPDATE_DATA[min(right_index + 1, max(UPDATE_DATA))]
    return {
        "response": interpolate_items(base["response"], target["response"], fraction),
        "pressure": interpolate_items(base["pressure"], target["pressure"], fraction),
        "note": base["note"] if fraction < .5 else target["note"],
    }


def region_cases_at_day(day):
    position = min(max(day, 0), SIMULATION_DAYS)
    left_index = max(next((i for i, update_day in enumerate(UPDATE_DAYS) if update_day >= position), 3) - 1, 0)
    right_index = min(left_index + 1, 3)
    left_day, right_day = UPDATE_DAYS[left_index], UPDATE_DAYS[right_index]
    fraction = 0 if left_day == right_day else (position - left_day) / (right_day - left_day)
    return {region: round(start[left_index] + (start[right_index] - start[left_index]) * fraction, 1) for region, start in REGION_CASES.items()}


def map_figure(day=0):
    values = region_cases_at_day(day)
    locations = list(values)
    fig = go.Figure(go.Choroplethmap(name="Regional case burden", geojson=GEOJSON, featureidkey="properties.region_id", locations=locations, z=[values[region] for region in locations], colorscale=[[0, "#172033"], [.08, "#26344d"], [.45, "#f59e0b"], [1, "#ef4444"]], zmin=0, zmax=90, marker_line_color="#dbeafe", marker_line_width=1, marker_opacity=.72, showscale=True, colorbar={"title":"Cases", "thickness":10, "len":.45}, hovertemplate="%{location}<br>Cases: %{z:.0f}<extra></extra>"))
    label_lons = [REGION_CENTROIDS[region][0] for region in locations]
    label_lats = [REGION_CENTROIDS[region][1] for region in locations]
    fig.add_trace(go.Scattermap(name="Area labels", lon=label_lons, lat=label_lats, mode="text", text=[REGION_LABELS[region] for region in locations], textfont={"size":12, "color":"#ffffff"}, hoverinfo="skip", showlegend=False))
    response_sites = [
        ("Central Government", -0.85, 1.75, 0),
        ("NPHA", 0.55, 1.35, 0),
        ("National laboratory", -0.65, 0.55, 0),
        ("Dass General Hospital", 1.05, 1.75, 0),
    ]
    visible_sites = [(name, lon, lat) for name, lon, lat, appear_day in response_sites if day >= appear_day]
    if visible_sites:
        fig.add_trace(go.Scattermap(name="Functioning response capacity", lon=[site[1] for site in visible_sites], lat=[site[2] for site in visible_sites], mode="markers+text", text=[site[0] for site in visible_sites], textposition="top center", marker={"size": 16, "color":"#A501FF", "symbol":"circle"}, hoverinfo="text", showlegend=False))
    # white-bg deliberately removes real-world labels, country borders and
    # attribution. Kajini is a fictional schematic map, not a geographic map.
    fig.update_layout(map={"style": "white-bg", "center": {"lat": .2, "lon": .2}, "zoom": 5.8}, height=850, margin=dict(l=0, r=0, t=0, b=0), paper_bgcolor="#0b1220", plot_bgcolor="#0b1220", font_color="#dbeafe", showlegend=False, uirevision="kajini")
    return fig


def app_layout():
    return html.Div([
        html.Div([html.Div([html.H1(CONFIG["title"]), html.Div(CONFIG["subtitle"])], className="brand"), html.Div([html.Div("ROUND 1", id="round-label", className="phase")], className="header-status")], className="topbar"),
        html.Div([html.Div([dcc.Graph(id="map", figure=map_figure(), config={"displayModeBar": False})], className="map-panel"), html.Div([dcc.Tabs(id="panel-tabs", value="outbreak-tab", children=[dcc.Tab(label="Outbreak & health", value="outbreak-tab", children=[html.Div([dcc.Graph(id="daily-cases-chart", figure=daily_cases_chart(), config={"displayModeBar": False})], className="card chart-card"), html.Div([dcc.Graph(id="deaths-chart", figure=deaths_chart(), config={"displayModeBar": False})], className="card chart-card"), html.Div([dcc.Graph(id="positivity-chart", figure=positivity_chart(), config={"displayModeBar": False})], className="card chart-card"), html.Div([dcc.Graph(id="cattle-chart", figure=cattle_chart(), config={"displayModeBar": False})], className="card chart-card"), html.Div([dcc.Graph(id="capacity-gauge", figure=capacity_gauge(), config={"displayModeBar": False})], className="card chart-card")]), dcc.Tab(label="Clinical data", value="clinical-tab", children=[html.Div([dcc.Graph(id="clinical-pyramid", figure=clinical_pyramid(), config={"displayModeBar": False})], className="card chart-card"), html.Div([dcc.Graph(id="symptom-chart", figure=symptom_chart(), config={"displayModeBar": False})], className="card chart-card"), html.Div([dcc.Graph(id="clinical-mortality-chart", figure=clinical_mortality_chart(), config={"displayModeBar": False})], className="card chart-card")])])], className="right-panel")], className="content"),
        #html.Div([html.Label("Simulation clock — one day every 10 seconds"), dcc.Slider(0, 30, 1, value=0, marks={0: "Start", 10: "Update 2", 20: "Update 3", 30: "Final"}, id="update-slider"), dcc.Interval(id="simulation-clock", interval=10_000, n_intervals=0)], className="controls"),
        html.Div([html.Label("Simulation clock — one day every 10 seconds"), dcc.Slider(0, SIMULATION_DAYS, 1, value=0, marks={0: "Start", 10: "Update 2", 20: "Update 3", 30: "Final"}, id="update-slider"), dcc.Interval(id="simulation-clock", interval=10_00, n_intervals=0)], className="controls"),
    ], className="app-shell")


app = Dash(__name__, suppress_callback_exceptions=True)
app.title = CONFIG["title"]
app.layout = app_layout
server = app.server

# Replacement lower control strip. The original strip remains in app_layout
# for backward compatibility and is hidden by CSS below.
def enhanced_layout():
    base = app_layout()
    topbar = base.children[0]
    topbar.children[1].children.append(html.Button("⚙ Facilitator controls", id="facilitator-toggle", className="facilitator-toggle", n_clicks=0))
    topbar.children[1].children.append(html.Button("Continue simulation", id="simulation-toggle", className="simulation-toggle", n_clicks=0))
    content = base.children[1]
    middle_panel = content.children[1]
    middle_panel.className = "middle-panel"
    tabs = middle_panel.children[0]
    tabs.children[0].children[0].children.insert(0, html.Div(id="total-cases", children="Total cases: 0", className="headline-number"))
    context_body = html.Div([], className="context-controls")
    for index, factor in enumerate(SLIDER_FACTORS):
        mark_style = {"color":"#ffffff", "fontSize":"10px", "fontWeight":"400", "whiteSpace":"nowrap"}
        context_body.children.append(html.Div([html.Div(factor, className="factor-label"), dcc.Slider(id=f"factor-slider-{index}", min=-1, max=1, step=0.5, value=0, marks={-1: {"label":"Negative", "style":mark_style}, 0: {"label":"Neutral", "style":mark_style}, 1: {"label":"Positive", "style":mark_style}}, tooltip={"placement":"bottom", "always_visible":False})], className="factor-slider"))
    context_panel = html.Div([html.H2("Context"), context_body], id="context-panel", className="context-panel facilitator-drawer hidden")
    content.children = [content.children[0], middle_panel]
    clock_marks = {UPDATE_DAYS[0]: "Start", UPDATE_DAYS[1]: "Update 2", UPDATE_DAYS[2]: "Update 3", UPDATE_DAYS[3]: "Final"}
    base.children.append(html.Div([
        html.Div([html.Label("Simulation clock — one day every 10 seconds"), dcc.Slider(0, SIMULATION_DAYS, 1, value=0, marks=clock_marks, id="decision-slider")], className="clock-control"),
            html.Div([html.Div(id="decision-question", children="The simulation will pause at each transition for a facilitator decision."), dcc.RadioItems(id="decision-choice", options=[{"label":"Scenario A", "value":"positive"}, {"label":"Scenario B", "value":"negative"}], value="positive", inline=True), html.Button("Submit decision and continue", id="decision-submit", n_clicks=0), html.Div(id="decision-status", className="decision-status")], id="decision-control", className="decision-control hidden"),
            dcc.Interval(id="decision-clock", interval=DAY_INTERVAL_MS, n_intervals=0),
    ], className="controls decision-controls"))
    base.children[-1].children[0].children.insert(0, html.Div(f"Simulation clock: one day every {DAY_INTERVAL_MS / 1000:g} seconds", className="clock-label"))
    base.children.append(context_panel)
    base.children.append(dcc.Store(id="simulation-paused", data=True))
    return base
app.layout = enhanced_layout()


@app.callback(Output("context-panel", "className"), Input("facilitator-toggle", "n_clicks"))
def toggle_facilitator_controls(n_clicks):
    return "context-panel facilitator-drawer" if (n_clicks or 0) % 2 else "context-panel facilitator-drawer hidden"


@app.callback(Output("simulation-paused", "data"), Output("simulation-toggle", "children"), Input("simulation-toggle", "n_clicks"), Input("decision-clock", "n_intervals"), State("simulation-paused", "data"))
def toggle_simulation(n_clicks, n_intervals, currently_paused):
    triggered = ctx.triggered_id
    paused = bool(currently_paused)
    if triggered == "simulation-toggle":
        paused = not paused
    elif ENABLE_STAGE_PAUSES and n_intervals in PAUSE_DAYS:
        paused = True
    return paused, "Continue simulation" if paused else "Pause simulation"


@app.callback(Output("decision-clock", "disabled"), Output("decision-question", "children"), Output("decision-status", "children"), Output("decision-slider", "value"), Output("decision-control", "className"), Output("decision-choice", "options"), Input("decision-clock", "n_intervals"), Input("decision-submit", "n_clicks"), Input("simulation-paused", "data"), Input("simulation-toggle", "n_clicks"), State("decision-choice", "value"), State("decision-slider", "value"))
def decision_gate(n_intervals, n_clicks, simulation_paused, toggle_clicks, choice, day):
    triggered = ctx.triggered_id
    day = min(int(n_intervals), SIMULATION_DAYS)
    if simulation_paused and (triggered == "simulation-toggle" or (n_intervals == 0 and triggered == "simulation-paused")):
        return True, "", "", day, "decision-control hidden", [{"label":"Scenario A", "value":"positive"}, {"label":"Scenario B", "value":"negative"}]
    if not ENABLE_STAGE_PAUSES:
        return False, "", "", day, "decision-control hidden", [{"label":"Scenario A", "value":"positive"}, {"label":"Scenario B", "value":"negative"}]
    if triggered == "decision-submit" and day in PAUSE_DAYS:
        return False, "The stage decision has been recorded. The simulation is continuing.", f"Resumed at Day {day}.", day, "decision-control hidden", [{"label":"Scenario A", "value":"positive"}, {"label":"Scenario B", "value":"negative"}]
    if ENABLE_STAGE_PAUSES and day in PAUSE_DAYS and (triggered == "decision-clock" or triggered == "simulation-paused"):
        return True, f"Stage transition reached at Day {day}.", f"Paused at Day {day}. Select Continue simulation to resume.", day, "decision-control active", [{"label":"Scenario A", "value":"positive"}, {"label":"Scenario B", "value":"negative"}]
    if triggered == "decision-submit" and day in DECISION_EFFECTS:
        global CURRENT_OUTCOME_FACTOR, CURRENT_FACTORS
        for factor, effect in DECISION_EFFECTS[day][choice].items():
            CURRENT_FACTORS[factor] = max(-2, min(2, CURRENT_FACTORS[factor] + effect))
        CURRENT_OUTCOME_FACTOR = sum(CURRENT_FACTORS.values()) / len(CURRENT_FACTORS)
        return False, "The decision has been recorded. The simulation is continuing.", f"Recorded: Scenario {choice.upper()} at Day {day}. Model factor: {CURRENT_OUTCOME_FACTOR:+.1f}", day, "decision-control hidden", [{"label":"Scenario A", "value":"positive"}, {"label":"Scenario B", "value":"negative"}]
    if day in DECISION_EFFECTS and triggered == "decision-clock" and day in PAUSE_DAYS:
        return True, DECISION_EFFECTS[day]["question"], f"Paused at Day {day}. Select a scenario and submit to continue.", day, "decision-control active", [{"label":DECISION_EFFECTS[day]["option_a"], "value":"positive"}, {"label":DECISION_EFFECTS[day]["option_b"], "value":"negative"}]
    if day >= SIMULATION_DAYS:
        return True, "Simulation complete.", "Final decision state reached.", day, "decision-control hidden", [{"label":"Scenario A", "value":"positive"}, {"label":"Scenario B", "value":"negative"}]
    return False, "The simulation will pause at Days 10, 20 and 30 for a facilitator decision.", "Simulation running.", day, "decision-control hidden", [{"label":"Scenario A", "value":"positive"}, {"label":"Scenario B", "value":"negative"}]


@app.callback(Output("map", "figure"), Output("daily-cases-chart", "figure"), Output("deaths-chart", "figure"), Output("positivity-chart", "figure"), Output("cattle-chart", "figure"), Output("capacity-gauge", "figure"), Output("clinical-pyramid", "figure"), Output("symptom-chart", "figure"), Output("clinical-mortality-chart", "figure"), Output("round-label", "children"), Output("update-slider", "value"), Output("total-cases", "children"), Input("decision-clock", "n_intervals"), *[Input(f"factor-slider-{i}", "value") for i in range(len(SLIDER_FACTORS))])
def update_dashboard(n_intervals, *factor_values):
    for factor, value in zip(SLIDER_FACTORS, factor_values):
        CURRENT_SLIDER_FACTORS[factor] = value or 0
    day = min(int(n_intervals), SIMULATION_DAYS)
    state = state_at_day(day)
    # Derive the displayed session from the configurable stage boundaries.
    stage = min(max(sum(day >= boundary for boundary in UPDATE_DAYS), 1), len(CONFIG["rounds"]))
    return (map_figure(day), daily_cases_chart(day), deaths_chart(day), positivity_chart(day), cattle_chart(day), capacity_gauge(day), clinical_pyramid(day), symptom_chart(day), clinical_mortality_chart(day), f"DAY {day} — ROUND {stage}: {CONFIG['rounds'][stage-1].upper()}", day, f"Total human cases: {cumulative_cases(day):,}")


if __name__ == "__main__":
    app.run(debug=True)
