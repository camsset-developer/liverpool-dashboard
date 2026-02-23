
import requests
import pandas as pd
import os
from dash import Dash, dcc, html, Input, Output
import plotly.graph_objects as go
import plotly.express as px

API_KEY = os.environ.get("API_KEY")
headers = {"X-Auth-Token": API_KEY}
BASE_URL = "https://api.football-data.org/v4"
LIVERPOOL_ID = 64
PL_ID = 2021
seasons = [2023, 2024]

# Cargar datos desde CSV
df_matches = pd.read_csv("matches.csv")
df_standings = pd.read_csv("standings.csv")
df_scorers = pd.read_csv("scorers.csv")

# Preparar matches
pl_matches = df_matches[df_matches["competition"] == "Premier League"].copy()
pl_matches["date"] = pd.to_datetime(pl_matches["date"])
pl_matches = pl_matches.sort_values("date")

def calcular_puntos(row):
    if row["winner"] == "HOME_TEAM" and row["home_team"] == "Liverpool FC":
        return 3
    elif row["winner"] == "AWAY_TEAM" and row["away_team"] == "Liverpool FC":
        return 3
    elif row["winner"] == "DRAW":
        return 1
    return 0

def resultado_liverpool(row):
    if row["home_team"] == "Liverpool FC":
        ubicacion = "Local"
        if row["winner"] == "HOME_TEAM": resultado = "Victoria"
        elif row["winner"] == "DRAW": resultado = "Empate"
        else: resultado = "Derrota"
    else:
        ubicacion = "Visitante"
        if row["winner"] == "AWAY_TEAM": resultado = "Victoria"
        elif row["winner"] == "DRAW": resultado = "Empate"
        else: resultado = "Derrota"
    return ubicacion, resultado

def goles_liverpool(row):
    if row["home_team"] == "Liverpool FC":
        return row["home_goals"], row["away_goals"]
    else:
        return row["away_goals"], row["home_goals"]

pl_matches["points"] = pl_matches.apply(calcular_puntos, axis=1)
pl_matches["matchday"] = pl_matches.groupby("season").cumcount() + 1
pl_matches["cumulative_points"] = pl_matches.groupby("season")["points"].cumsum()
pl_matches[["ubicacion", "resultado"]] = pl_matches.apply(lambda row: pd.Series(resultado_liverpool(row)), axis=1)
pl_matches[["goles_favor", "goles_contra"]] = pl_matches.apply(lambda row: pd.Series(goles_liverpool(row)), axis=1)
pl_matches["month"] = pd.to_datetime(pl_matches["date"]).dt.strftime("%b")
pl_matches["month_num"] = pd.to_datetime(pl_matches["date"]).dt.month

ROJO = "#C8102E"
VERDE = "#00B2A9"
AMARI = "#F6EB61"
NEGRO = "#1a1a1a"

app = Dash(__name__)
server = app.server

app.layout = html.Div(style={"backgroundColor": NEGRO, "fontFamily": "Arial", "padding": "20px"}, children=[
    html.Div(style={"textAlign": "center", "marginBottom": "30px"}, children=[
        html.H1("🔴 Liverpool FC — Analytics Dashboard",
                style={"color": "white", "fontSize": "2.2em", "marginBottom": "5px"}),
        html.P("Temporadas 2023/24 · 2024/25 | Premier League",
               style={"color": "#aaaaaa", "fontSize": "1em"})
    ]),
    html.Div(style={"textAlign": "center", "marginBottom": "25px"}, children=[
        html.Label("Selecciona temporada:", style={"color": "white", "marginRight": "10px"}),
        dcc.Dropdown(
            id="season-dropdown",
            options=[
                {"label": "Ambas temporadas", "value": "all"},
                {"label": "2023/24", "value": "2023/24"},
                {"label": "2024/25", "value": "2024/25"}
            ],
            value="all",
            clearable=False,
            style={"width": "250px", "display": "inline-block", "verticalAlign": "middle"}
        )
    ]),
    html.Div(id="kpi-cards", style={"display": "flex", "justifyContent": "center",
                                     "gap": "20px", "marginBottom": "30px", "flexWrap": "wrap"}),
    html.Div(style={"display": "flex", "gap": "20px", "marginBottom": "20px", "flexWrap": "wrap"}, children=[
        html.Div(dcc.Graph(id="graph-points"), style={"flex": "1", "minWidth": "400px",
            "backgroundColor": "white", "borderRadius": "10px", "padding": "10px"}),
        html.Div(dcc.Graph(id="graph-scorers"), style={"flex": "1", "minWidth": "400px",
            "backgroundColor": "white", "borderRadius": "10px", "padding": "10px"}),
    ]),
    html.Div(style={"display": "flex", "gap": "20px", "marginBottom": "20px", "flexWrap": "wrap"}, children=[
        html.Div(dcc.Graph(id="graph-home-away"), style={"flex": "1", "minWidth": "400px",
            "backgroundColor": "white", "borderRadius": "10px", "padding": "10px"}),
        html.Div(dcc.Graph(id="graph-goals-month"), style={"flex": "1", "minWidth": "400px",
            "backgroundColor": "white", "borderRadius": "10px", "padding": "10px"}),
    ]),
    html.Div(dcc.Graph(id="graph-top5"),
             style={"backgroundColor": "white", "borderRadius": "10px", "padding": "10px"})
])

@app.callback(
    Output("kpi-cards", "children"),
    Output("graph-points", "figure"),
    Output("graph-scorers", "figure"),
    Output("graph-home-away", "figure"),
    Output("graph-goals-month", "figure"),
    Output("graph-top5", "figure"),
    Input("season-dropdown", "value")
)
def update_dashboard(selected_season):
    if selected_season == "all":
        matches = pl_matches.copy()
        scorers = df_scorers.copy()
        standings = df_standings.copy()
        seasons_shown = ["2023/24", "2024/25"]
    else:
        matches = pl_matches[pl_matches["season"] == selected_season].copy()
        scorers = df_scorers[df_scorers["season"] == selected_season].copy()
        standings = df_standings[df_standings["season"] == selected_season].copy()
        seasons_shown = [selected_season]

    color_map = {"2023/24": ROJO, "2024/25": VERDE}

    liv_standings = standings[standings["team"] == "Liverpool FC"]
    kpi_list = []
    for _, row in liv_standings.iterrows():
        win_rate = round(row["won"] / row["played"] * 100, 1)
        for label, value, color in [
            (f"{row['season']} — Posición", f"#{int(row['position'])}", ROJO),
            ("Puntos", str(int(row["points"])), VERDE),
            ("Victorias", str(int(row["won"])), ROJO),
            ("% Victorias", f"{win_rate}%", VERDE),
            ("Goles anotados", str(int(row["goals_for"])), ROJO),
        ]:
            kpi_list.append(html.Div(style={
                "backgroundColor": color, "borderRadius": "10px",
                "padding": "15px 25px", "textAlign": "center", "minWidth": "110px"
            }, children=[
                html.P(label, style={"color": "white", "fontSize": "0.75em", "margin": "0"}),
                html.H3(value, style={"color": "white", "margin": "5px 0 0 0", "fontSize": "1.8em"})
            ]))

    matches["cumulative_points"] = matches.groupby("season")["points"].cumsum()
    matches["matchday"] = matches.groupby("season").cumcount() + 1
    fig1 = go.Figure()
    for s in seasons_shown:
        g = matches[matches["season"] == s]
        fig1.add_trace(go.Scatter(x=g["matchday"], y=g["cumulative_points"],
            mode="lines+markers", name=s,
            line=dict(color=color_map[s], width=3), marker=dict(size=5),
            hovertemplate=f"<b>{s}</b><br>Jornada: %{{x}}<br>Puntos: %{{y}}<extra></extra>"))
    fig1.update_layout(title="Puntos Acumulados por Jornada", plot_bgcolor="white",
                       paper_bgcolor="white", xaxis_title="Jornada", yaxis_title="Puntos",
                       xaxis=dict(gridcolor="#f0f0f0"), yaxis=dict(gridcolor="#f0f0f0"))

    fig2 = px.bar(scorers, x="player", y="goals", color="season", barmode="group",
                  color_discrete_map=color_map, text="goals", title="Goleadores de Liverpool")
    fig2.update_traces(textposition="outside")
    fig2.update_layout(plot_bgcolor="white", paper_bgcolor="white")

    resumen = matches.groupby(["season", "ubicacion", "resultado"]).size().reset_index(name="partidos")
    fig3 = px.bar(resumen, x="ubicacion", y="partidos", color="resultado", facet_col="season",
                  barmode="group",
                  color_discrete_map={"Victoria": ROJO, "Empate": AMARI, "Derrota": "#333"},
                  text="partidos", title="Rendimiento Local vs Visitante")
    fig3.update_traces(textposition="outside")
    fig3.update_layout(plot_bgcolor="white", paper_bgcolor="white")

    goles = matches.groupby(["season", "month", "month_num"]).agg(
        favor=("goles_favor", "sum"), contra=("goles_contra", "sum")
    ).reset_index().sort_values(["season", "month_num"])
    fig4 = px.line(goles, x="month", y=["favor", "contra"], facet_col="season",
                   markers=True, color_discrete_map={"favor": ROJO, "contra": NEGRO},
                   title="Goles Anotados vs Recibidos por Mes",
                   labels={"value": "Goles", "month": "Mes"})
    fig4.update_layout(plot_bgcolor="white", paper_bgcolor="white")

    top5 = standings.groupby("season").apply(lambda x: x.nsmallest(5, "position")).reset_index(drop=True)
    fig5 = px.bar(top5, x="team", y="points", color="season", barmode="group",
                  color_discrete_map=color_map, text="points",
                  title="Top 5 Premier League — Comparativa de Puntos")
    fig5.update_traces(textposition="outside")
    fig5.update_layout(plot_bgcolor="white", paper_bgcolor="white", xaxis_tickangle=-20)

    return kpi_list, fig1, fig2, fig3, fig4, fig5

if __name__ == "__main__":
    app.run(debug=False, port=8050)
