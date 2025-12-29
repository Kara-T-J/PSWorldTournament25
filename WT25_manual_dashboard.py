from dash import Dash, html, dcc, callback, Output, Input, ctx
import dash_ag_grid as dag
import pandas as pd
import plotly.express as px

df = pd.read_excel("WT25_notes_cleaned.xlsx")

app = Dash(__name__)

def uniq_sorted(col):
    return sorted(df[col].dropna().unique().tolist())

def column_widths(frame):
    widths = {}
    total = 17
    for col in frame.columns:
        series = frame[col].dropna()
        max_val_len = series.astype(str).map(len).max() if not series.empty else 0
        max_len = max(len(str(col)), int(max_val_len))
        col_width = min(420, max(120, max_len * 8 + 32))
        widths[col] = col_width
        total += col_width
    widths["_total"] = total
    return widths

ALL_PARTICIPANTS = uniq_sorted("Participant")
ALL_JUGES = uniq_sorted("Juge")
ALL_ROUNDS = uniq_sorted("Round")
ALL_CRITERES = uniq_sorted("Critère")
COLUMN_WIDTHS = column_widths(df)

app.layout = html.Div([
    html.H1("Penspinning World Tournament 2025", style={"textAlign": "center"}),

    html.Div([
        html.Button("Tout sélectionner", id="btn-select-all", n_clicks=0),
        html.Button("Réinitialiser", id="btn-reset", n_clicks=0, style={"marginLeft": "10px"}),
    ], style={"marginBottom": "10px", "textAlign": "center"}),

    html.Div([
        html.Div([
            dcc.Dropdown(
                options=ALL_PARTICIPANTS,
                value=[],
                id="dropdown-participant",
                multi=True,
                placeholder="Participants…",
            ),
        ], style={"flex": "1 1 45%", "minWidth": "260px"}),
        html.Div([
            dcc.Dropdown(
                options=ALL_JUGES,
                value=[],
                id="dropdown-juge",
                multi=True,
                placeholder="Juges…",
            ),
        ], style={"flex": "1 1 45%", "minWidth": "260px"}),
        html.Div([
            dcc.Dropdown(
                options=ALL_ROUNDS,
                value=[],
                id="dropdown-round",
                multi=True,
                placeholder="Rounds…",
            ),
        ], style={"flex": "1 1 45%", "minWidth": "260px"}),
        html.Div([
            dcc.Dropdown(
                options=ALL_CRITERES,
                value=[],
                id="dropdown-critere",
                multi=True,
                placeholder="Critères…",
            ),
        ], style={"flex": "1 1 45%", "minWidth": "260px"}),
    ], style={"display": "flex", "flexWrap": "wrap", "gap": "10px", "marginBottom": "10px"}),

    html.Div([
        dag.AgGrid(
            id="grid-notes",
            rowData=df.to_dict("records"),
            columnDefs=[{"field": c, "width": COLUMN_WIDTHS.get(c)} for c in df.columns],
            defaultColDef={"filter": True, "sortable": True, "resizable": True},
            style={
                "height": "70vh",
                "marginTop": "10px",
                "width": f'{COLUMN_WIDTHS.get("_total", 0)}px',
            },
        ),
        dcc.Graph(
            id="violin-graph",
            style={"height": "70vh", "flex": "1 1 0%", "minWidth": "320px"},
        ),
    ], style={"display": "flex", "gap": "20px", "alignItems": "stretch"}),
])

@callback(
    Output("dropdown-participant", "value"),
    Output("dropdown-juge", "value"),
    Output("dropdown-round", "value"),
    Output("dropdown-critere", "value"),
    Input("btn-select-all", "n_clicks"),
    Input("btn-reset", "n_clicks"),
    prevent_initial_call=True,
)
def set_dropdowns(n_all, n_reset):
    if ctx.triggered_id == "btn-select-all":
        return ALL_PARTICIPANTS, ALL_JUGES, ALL_ROUNDS, ALL_CRITERES
    # reset : aucun filtre
    return [], [], [], []

@callback(
    Output("grid-notes", "rowData"),
    Output("violin-graph", "figure"),
    Input("dropdown-participant", "value"),
    Input("dropdown-juge", "value"),
    Input("dropdown-round", "value"),
    Input("dropdown-critere", "value"),
)
def update_grid(participants, juges, rounds, criteres):
    dff = df
    if participants:
        dff = dff[dff["Participant"].isin(participants)]
    if juges:
        dff = dff[dff["Juge"].isin(juges)]
    if rounds:
        dff = dff[dff["Round"].isin(rounds)]
    if criteres:
        dff = dff[dff["Critère"].isin(criteres)]
    fig = px.violin(
        dff,
        x="Critère",
        y="Note",
        box=True,
        points="all",
    )
    fig.update_layout(margin=dict(l=20, r=20, t=40, b=40))
    return dff.to_dict("records"), fig

if __name__ == "__main__":
    app.run(debug=True)
