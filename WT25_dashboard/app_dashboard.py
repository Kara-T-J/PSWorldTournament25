from dash import Dash, html, dcc, callback, Output, Input, ctx
import pandas as pd
import dash_ag_grid as dag
import plotly.express as px
import plotly.graph_objects as go
import numpy as np

DATA_PATH = "WT25_notes_cleaned.xlsx"

app = Dash(__name__)

def get_col(df, candidates):
    for name in candidates:
        if name in df.columns:
            return name
    raise KeyError(f"Missing expected column. Tried: {candidates}")


def load_data():
    # Load the cleaned Excel file from the project root.
    frame = pd.read_excel(DATA_PATH)
    return frame


def uniq_sorted(frame, col):
    return sorted(frame[col].dropna().unique().tolist())


def empty_fig(message):
    fig = go.Figure()
    fig.add_annotation(
        text=message,
        xref="paper",
        yref="paper",
        x=0.5,
        y=0.5,
        showarrow=False,
    )
    fig.update_xaxes(visible=False)
    fig.update_yaxes(visible=False)
    fig.update_layout(margin=dict(l=20, r=20, t=40, b=40))
    return finalize_fig(fig)


def finalize_fig(fig):
    fig.update_layout(title=None, showlegend=False, xaxis_title=None, yaxis_title=None)
    return fig


def make_tabs(lang):
    t = TRANSLATIONS[lang]
    return [
        dcc.Tab(label=t["tab_overview"], value="overview"),
        dcc.Tab(label=t["tab_judges"], value="judges"),
        dcc.Tab(label=t["tab_criteria"], value="criteria"),
        dcc.Tab(label=t["tab_rounds"], value="rounds"),
        dcc.Tab(label=t["tab_spinners"], value="spinners"),
    ]


def find_total_label(frame, col):
    for value in frame[col].dropna().unique().tolist():
        if str(value).strip().lower() == "total":
            return value
    return None


def split_total(frame, criteria_col, total_label):
    # Split out the "Total" criterion to avoid mixing it with base criteria.
    if total_label is None:
        return frame, frame.iloc[0:0]
    criteria_series = frame[criteria_col].astype(str).str.strip().str.lower()
    total_value = str(total_label).strip().lower()
    is_total = criteria_series == total_value
    return frame[~is_total], frame[is_total]

def heatmap_or_empty(pivot, title, empty_message, colorscale="RdBu", zmin=None, zmax=None):
    # Render heatmaps with in-cell values; fallback to a placeholder when empty.
    if pivot.empty:
        return empty_fig(empty_message)
    fig = px.imshow(
        pivot,
        aspect="auto",
        title=title,
        text_auto=".2f",
        color_continuous_scale=colorscale,
        zmin=zmin,
        zmax=zmax,
    )
    return finalize_fig(fig)

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

TRANSLATIONS = {
    "fr": {
        "title": "Penspinning World Tournament 2025",
        "language": "Langue",
        "select_all": "Tout sélectionner",
        "reset": "Réinitialiser",
        "participants": "Participants...",
        "judges": "Juges...",
        "rounds": "Rounds...",
        "criteria": "Critères...",
        "kpi_notes": "Nombre de notes",
        "kpi_participants": "Participants",
        "hide_controls": "Masquer les filtres",
        "show_controls": "Afficher les filtres",
        "tab_overview": "Vue d'ensemble",
        "tab_judges": "Juges",
        "tab_criteria": "Critères",
        "tab_rounds": "Rounds",
        "tab_spinners": "Spinners",
        "dist_notes": "Distribution des notes",
        "violin_criteria": "Notes par critère",
        "violin_judges": "Notes par juge",
        "violin_rounds_total": "Total par round",
        "box_rounds": "Notes par round",
        "judge_mean": "Moyenne par juge",
        "judge_bias": "Biais par juge (moyenne - globale)",
        "judge_heatmap": "Moyenne par critère",
        "judge_std_heatmap": "Dispersion par critère",
        "judge_range_heatmap": "Amplitude par critère",
        "judge_severity_heatmap": "Sévérité par critère",
        "judge_total_corr_heatmap": "Corrélation au Total",
        "judge_total_wo_corr_heatmap": "Corrélation critère au total du reste",
        "judge_crit_bias_heatmap": "Biais relatif juge x critère (contrôle sévérité)",
        "judge_part_bias_heatmap": "Biais relatif juge x participant (contrôle sévérité)",
        "criteria_mean": "Moyenne par critère",
        "criteria_heatmap": "Round x critère (moyennes)",
        "criteria_corr": "Corrélation entre critères",
        "criteria_total_wo_corr": "Corrélation critère vs total sans critère (par juge)",
        "rounds_trend": "Évolution des moyennes par round",
        "total_dist": "Distribution du Total",
        "data_table": "Données brutes",
        "no_data": "Aucune donnée pour la sélection",
    },
    "en": {
        "title": "Analytics Dashboard - Penspinning World Tournament 2025",
        "language": "Language",
        "select_all": "Select all",
        "reset": "Reset",
        "participants": "Participants...",
        "judges": "Judges...",
        "rounds": "Rounds...",
        "criteria": "Criteria...",
        "kpi_notes": "Number of scores",
        "kpi_participants": "Participants",
        "hide_controls": "Hide filters",
        "show_controls": "Show filters",
        "tab_overview": "Overview",
        "tab_judges": "Judges",
        "tab_criteria": "Criteria",
        "tab_rounds": "Rounds",
        "tab_spinners": "Spinners",
        "dist_notes": "Score distribution",
        "violin_criteria": "Scores by criteria",
        "violin_judges": "Scores by judge",
        "violin_rounds_total": "Total by round",
        "box_rounds": "Scores by round",
        "judge_mean": "Average by judge",
        "judge_bias": "Judge bias (mean - overall)",
        "judge_heatmap": "Heatmap judge x criteria (mean)",
        "judge_std_heatmap": "Heatmap judge x criteria (spread)",
        "judge_range_heatmap": "Heatmap judge x criteria (range)",
        "judge_severity_heatmap": "Severity by judge and criteria (mean delta)",
        "judge_total_corr_heatmap": "Correlation with Total by judge and criteria",
        "judge_total_wo_corr_heatmap": "Correlation criterion vs total without criterion (by judge)",
        "judge_crit_bias_heatmap": "Relative bias judge x criteria (severity-adjusted)",
        "judge_part_bias_heatmap": "Relative bias judge x participant (severity-adjusted)",
        "criteria_mean": "Average by criteria",
        "criteria_heatmap": "Round x criteria (means)",
        "criteria_corr": "Criteria correlation",
        "criteria_total_wo_corr": "Criterion vs total-without-criterion (by judge)",
        "rounds_trend": "Round-by-round mean trends",
        "total_dist": "Total distribution",
        "data_table": "Raw data",
        "no_data": "No data for selection",
    },
}


df = load_data()

COL_PARTICIPANT = get_col(df, ["Participant", "Participant(s)"])
COL_ROUND = get_col(df, ["Round", "Tour"])
COL_JUDGE = get_col(df, ["Juge", "Judge"])
COL_CRITERIA = get_col(df, ["Critere", "Critère", "Criteria"])
COL_SCORE = get_col(df, ["Note", "Score"])
TOTAL_LABEL = find_total_label(df, COL_CRITERIA)

ALL_PARTICIPANTS = uniq_sorted(df, COL_PARTICIPANT)
ALL_JUDGES = uniq_sorted(df, COL_JUDGE)
ALL_ROUNDS = uniq_sorted(df, COL_ROUND)
ALL_CRITERIA = uniq_sorted(df, COL_CRITERIA)
COLUMN_WIDTHS = column_widths(df)
COLUMN_WIDTHS = column_widths(df)

app.layout = html.Div([
    html.Div([
        html.H1(id="title", style={"margin": "0"}),
        html.Button(id="btn-toggle-header", n_clicks=0),
    ], style={"display": "flex", "justifyContent": "space-between", "alignItems": "center", "marginBottom": "16px"}),
    html.Div([
        html.Div([
            html.Span(id="lang-label", style={"marginRight": "10px"}),
            dcc.RadioItems(
                id="lang",
                options=[
                    {"label": "FR", "value": "fr"},
                    {"label": "EN", "value": "en"},
                ],
                value="fr",
                inline=True,
            ),
        ], style={"display": "flex", "alignItems": "center", "marginBottom": "10px"}),
        html.Div([
            html.Button(id="btn-select-all", n_clicks=0),
            html.Button(id="btn-reset", n_clicks=0, style={"marginLeft": "10px"}),
        ], style={"marginBottom": "10px"}),
        html.Div([
            html.Div([
                dcc.Dropdown(
                    options=ALL_PARTICIPANTS,
                    value=[],
                    id="dropdown-participant",
                    multi=True,
                ),
            ], style={"flex": "1 1 45%", "minWidth": "260px"}),
            html.Div([
                dcc.Dropdown(
                    options=ALL_JUDGES,
                    value=[],
                    id="dropdown-judge",
                    multi=True,
                ),
            ], style={"flex": "1 1 45%", "minWidth": "260px"}),
            html.Div([
                dcc.Dropdown(
                    options=ALL_ROUNDS,
                    value=[],
                    id="dropdown-round",
                    multi=True,
                ),
            ], style={"flex": "1 1 45%", "minWidth": "260px"}),
            html.Div([
                dcc.Dropdown(
                    options=ALL_CRITERIA,
                    value=[],
                    id="dropdown-criteria",
                    multi=True,
                ),
            ], style={"flex": "1 1 45%", "minWidth": "260px"}),
        ], style={"display": "flex", "flexWrap": "wrap", "gap": "10px", "marginBottom": "10px"}),
        html.Div([
            html.Div([
                html.Div(id="kpi-notes", className="kpi"),
                html.Div(id="kpi-participants", className="kpi"),
            ], style={"display": "grid", "gridTemplateColumns": "repeat(auto-fit, minmax(160px, 1fr))", "gap": "10px"}),
        ], style={"marginBottom": "10px"}),
    ], id="header-panel"),
    dcc.Tabs(id="tabs", value="overview"),
    html.Div(id="tab-content"),
])


@callback(
    Output("tabs", "children"),
    Output("title", "children"),
    Output("lang-label", "children"),
    Output("btn-select-all", "children"),
    Output("btn-reset", "children"),
    Output("dropdown-participant", "placeholder"),
    Output("dropdown-judge", "placeholder"),
    Output("dropdown-round", "placeholder"),
    Output("dropdown-criteria", "placeholder"),
    Input("lang", "value"),
)
def update_labels(lang):
    t = TRANSLATIONS[lang]
    return (
        make_tabs(lang),
        t["title"],
        t["language"],
        t["select_all"],
        t["reset"],
        t["participants"],
        t["judges"],
        t["rounds"],
        t["criteria"],
    )


@callback(
    Output("header-panel", "style"),
    Output("btn-toggle-header", "children"),
    Input("btn-toggle-header", "n_clicks"),
    Input("lang", "value"),
)
def toggle_header(n_clicks, lang):
    t = TRANSLATIONS[lang]
    if n_clicks and n_clicks % 2 == 1:
        return {"display": "none"}, t["show_controls"]
    return {"display": "block"}, t["hide_controls"]


@callback(
    Output("dropdown-participant", "value"),
    Output("dropdown-judge", "value"),
    Output("dropdown-round", "value"),
    Output("dropdown-criteria", "value"),
    Input("btn-select-all", "n_clicks"),
    Input("btn-reset", "n_clicks"),
    prevent_initial_call=True,
)
def set_dropdowns(n_all, n_reset):
    if ctx.triggered_id == "btn-select-all":
        return ALL_PARTICIPANTS, ALL_JUDGES, ALL_ROUNDS, ALL_CRITERIA
    return [], [], [], []


@callback(
    Output("tab-content", "children"),
    Output("kpi-notes", "children"),
    Output("kpi-participants", "children"),
    Input("dropdown-participant", "value"),
    Input("dropdown-judge", "value"),
    Input("dropdown-round", "value"),
    Input("dropdown-criteria", "value"),
    Input("tabs", "value"),
    Input("lang", "value"),
)
def update_dashboard(participants, judges, rounds, criteria, tab, lang):
    t = TRANSLATIONS[lang]
    dff = df
    if participants:
        dff = dff[dff[COL_PARTICIPANT].isin(participants)]
    if judges:
        dff = dff[dff[COL_JUDGE].isin(judges)]
    if rounds:
        dff = dff[dff[COL_ROUND].isin(rounds)]
    if criteria:
        dff = dff[dff[COL_CRITERIA].isin(criteria)]

    # Keep "Total" out of criteria-only analysis; use base for most stats.
    dff_base, dff_total = split_total(dff, COL_CRITERIA, TOTAL_LABEL)
    kpi_frame = dff_base if not dff_base.empty else dff

    if dff.empty:
        empty = empty_fig(t["no_data"])
        content = html.Div([dcc.Graph(figure=empty)])
        return (content, f"{t['kpi_notes']}: 0", f"{t['kpi_participants']}: 0")

    kpi_notes = f"{t['kpi_notes']}: {len(kpi_frame)}"
    kpi_participants = f"{t['kpi_participants']}: {kpi_frame[COL_PARTICIPANT].nunique()}"

    if tab == "overview":
        row_data = dff.where(pd.notna(dff), None).to_dict("records")
        column_defs = [{"field": c, "width": COLUMN_WIDTHS.get(c)} for c in dff.columns]
        grid = dag.AgGrid(
            id="overview-grid",
            rowData=row_data,
            columnDefs=column_defs,
            defaultColDef={"filter": True, "sortable": True, "resizable": True},
            style={
                "height": "70vh",
                "marginTop": "10px",
                "width": f'{COLUMN_WIDTHS.get("_total", 0)}px',
            },
        )

        if dff_base.empty:
            fig_criteria = empty_fig(t["no_data"])
            fig_judges = empty_fig(t["no_data"])
        else:
            fig_criteria = finalize_fig(px.violin(
                dff_base,
                x=COL_CRITERIA,
                y=COL_SCORE,
                box=True,
                points="all",
            ))
            fig_judges = finalize_fig(px.violin(
                dff_base,
                x=COL_JUDGE,
                y=COL_SCORE,
                box=True,
                points="all",
            ))

        content = html.Div([
            html.Div(grid, style={"flex": "0 0 auto", "overflowX": "auto"}),
            html.Div([
                dcc.Graph(figure=fig_criteria, style={"height": "34vh"}),
                dcc.Graph(figure=fig_judges, style={"height": "34vh"}),
            ], style={"flex": "1 1 0%   ", "minWidth": "320px", "display": "flex", "flexDirection": "column", "gap": "20px"}),
        ], style={"display": "flex", "gap": "20px", "alignItems": "stretch", "flexWrap": "nowrap"})
    elif tab == "judges":
        if dff_base.empty:
            fig_violin = empty_fig(t["no_data"])
            fig_mean = empty_fig(t["no_data"])
            fig_std = empty_fig(t["no_data"])
            fig_severity = empty_fig(t["no_data"])
        else:
            fig_violin = finalize_fig(px.violin(
                dff_base,
                x=COL_JUDGE,
                y=COL_SCORE,
                box=True,
                points="all",
            ))
            mean_pivot = dff_base.pivot_table(index=COL_JUDGE, columns=COL_CRITERIA, values=COL_SCORE, aggfunc="mean")
            std_pivot = dff_base.pivot_table(index=COL_JUDGE, columns=COL_CRITERIA, values=COL_SCORE, aggfunc="std")
            crit_means = dff_base.groupby(COL_CRITERIA)[COL_SCORE].mean()
            judge_means = dff_base.groupby(COL_JUDGE)[COL_SCORE].mean()
            overall_mean_base = dff_base[COL_SCORE].mean()
            crit_shift = crit_means - overall_mean_base
            crit_bias = mean_pivot.subtract(judge_means, axis="rows").subtract(crit_shift, axis="columns")

            fig_mean = heatmap_or_empty(
                mean_pivot,
                t["judge_heatmap"],
                t["no_data"],
                zmin=mean_pivot.min().min() if not mean_pivot.empty else None,
                zmax=mean_pivot.max().max() if not mean_pivot.empty else None,
            )
            fig_std = heatmap_or_empty(
                std_pivot,
                t["judge_std_heatmap"],
                t["no_data"],
                zmin=0,
                zmax=std_pivot.max().max() if not std_pivot.empty else None,
            )
            fig_severity = heatmap_or_empty(
                crit_bias,
                t["judge_crit_bias_heatmap"],
                t["no_data"],
                zmin=crit_bias.min().min() if not crit_bias.empty else None,
                zmax=crit_bias.max().max() if not crit_bias.empty else None,
            )

        content = html.Div([
            dcc.Graph(figure=fig_violin, className="full-row"),
            html.Div([
                dcc.Graph(figure=fig_mean),
                dcc.Graph(figure=fig_std),
                dcc.Graph(figure=fig_severity),
            ], className="graph-grid-3"),
        ], className="stacked")
    elif tab == "criteria":
        if dff_base.empty:
            fig_violin = empty_fig(t["no_data"])
            fig_corr_total_wo = empty_fig(t["no_data"])
            fig_corr = empty_fig(t["no_data"])
        else:
            fig_violin = finalize_fig(px.violin(
                dff_base,
                x=COL_CRITERIA,
                y=COL_SCORE,
                box=True,
                points="all",
            ))

            corr_total_wo_pivot = pd.DataFrame()
            if TOTAL_LABEL is not None and not dff.empty:
                pivot = dff.pivot_table(
                    index=[COL_PARTICIPANT, COL_ROUND, COL_JUDGE],
                    columns=COL_CRITERIA,
                    values=COL_SCORE,
                    aggfunc="mean",
                )
                if TOTAL_LABEL in pivot.columns:
                    rows = []
                    for judge in pivot.index.get_level_values(COL_JUDGE).unique():
                        sub = pivot.xs(judge, level=COL_JUDGE)
                        for crit in sub.columns:
                            if crit == TOTAL_LABEL:
                                continue
                            series = sub[[crit, TOTAL_LABEL]].dropna()
                            if series.shape[0] < 2:
                                continue
                            total_wo = series[TOTAL_LABEL] - series[crit]
                            corr = series[crit].corr(total_wo)
                            rows.append({"judge": judge, "criteria": crit, "corr_total_wo": corr})
                    if rows:
                        corr_df = pd.DataFrame(rows)
                        corr_total_wo_pivot = corr_df.pivot_table(
                            index="judge",
                            columns="criteria",
                            values="corr_total_wo",
                            aggfunc="mean",
                        )

            fig_corr_total_wo = heatmap_or_empty(
                corr_total_wo_pivot,
                t["criteria_total_wo_corr"],
                t["no_data"],
                zmin=-1,
                zmax=1,
            )

            pivot = dff_base.pivot_table(
                index=[COL_PARTICIPANT, COL_ROUND, COL_JUDGE],
                columns=COL_CRITERIA,
                values=COL_SCORE,
                aggfunc="mean",
            )
            if pivot.shape[1] < 2:
                fig_corr = empty_fig(t["no_data"])
            else:
                corr = pivot.corr().mask(np.eye(len(pivot.columns), dtype=bool))
                fig_corr = finalize_fig(px.imshow(
                    corr,
                    aspect="auto",
                    title=t["criteria_corr"],
                    text_auto=".2f",
                    color_continuous_scale="RdBu",
                    zmin=-1,
                    zmax=1,
                ))

        content = html.Div([
            html.Div([
                dcc.Graph(figure=fig_violin),
            ], style={"flex": "1 1 55%"}),
            html.Div([
                dcc.Graph(figure=fig_corr_total_wo),
                dcc.Graph(figure=fig_corr),
            ], style={"flex": "1 1 45%", "display": "flex", "flexDirection": "column", "gap": "20px"}),
        ], style={"display": "flex", "gap": "20px", "alignItems": "stretch", "flexWrap": "nowrap"})
    elif tab == "rounds":
        if dff_total.empty:
            fig_total_rounds = empty_fig(t["no_data"])
        else:
            fig_total_rounds = finalize_fig(px.violin(
                dff_total,
                x=COL_ROUND,
                y=COL_SCORE,
                box=True,
                points="all",
            ))

        if dff_base.empty:
            fig_trend = empty_fig(t["no_data"])
        else:
            trend = dff_base.groupby([COL_ROUND, COL_CRITERIA])[COL_SCORE].mean().reset_index()
            fig_trend = finalize_fig(px.line(
                trend,
                x=COL_ROUND,
                y=COL_SCORE,
                color=COL_CRITERIA,
                markers=True,
            ))

        content = html.Div([
            dcc.Graph(figure=fig_total_rounds, className="rounds-graph"),
            dcc.Graph(figure=fig_trend, className="rounds-graph"),
        ], className="graph-grid")
    else:
        content = html.Div([
            html.P("Section à définir."),
        ])

    return (content, kpi_notes, kpi_participants)


if __name__ == "__main__":
    app.run(debug=True)
