from dash import Dash, html, dcc, callback, Output, Input, ctx
import pandas as pd
import dash_ag_grid as dag
import plotly.express as px
import plotly.graph_objects as go
import numpy as np

DATA_PATH = "data/intermediate/WT25_notes_cleaned.xlsx"
ZSCORE_PATH = "data/intermediate/WT25_zscore.xlsx"
CLUSTER_PATH = "data/output/WT25_participant_clusters.csv"
CLUSTER_SUMMARY_PATH = "data/output/WT25_cluster_summary.csv"
PCA_LOADINGS_PATH = "data/output/WT25_pca_loadings.csv"
PCA_EXPLAINED_PATH = "data/output/WT25_pca_explained_variance.csv"

HEATMAP_COLORSCALE = [
    [0.0, "#e67c73"],
    [0.5, "#f4ede9"],
    [1.0, "#57bb8a"],
]

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


def load_optional_csv(path):
    try:
        return pd.read_csv(path)
    except FileNotFoundError:
        return None


def load_optional_excel(path):
    try:
        return pd.read_excel(path)
    except FileNotFoundError:
        return None


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


def finalize_fig(fig, keep_title=False):
    title = fig.layout.title if keep_title else None
    fig.update_layout(title=title, showlegend=False, xaxis_title=None, yaxis_title=None)
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

def heatmap_or_empty(pivot, title, empty_message, colorscale=HEATMAP_COLORSCALE, zmin=None, zmax=None):
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
    return finalize_fig(fig, keep_title=True)

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


def build_network_fig(z_df, clusters_df, threshold=0.4):
    criteria_cols = [
        c for c in z_df.columns
        if str(c).strip().lower() not in {"participant", "round", "rank"}
    ]
    features = z_df[criteria_cols].apply(pd.to_numeric, errors="coerce").fillna(0).values
    norms = np.linalg.norm(features, axis=1, keepdims=True)
    norms[norms == 0] = 1
    feats_norm = features / norms
    sim = feats_norm @ feats_norm.T

    participants = z_df["Participant"].tolist()
    index_map = {p: i for i, p in enumerate(participants)}

    coords = None
    if clusters_df is not None and {"Participant", "PC1", "PC2"}.issubset(clusters_df.columns):
        coords = (
            clusters_df.set_index("Participant")[["PC1", "PC2"]]
            .reindex(participants)
            .fillna(0)
            .values
        )
    else:
        angles = np.linspace(0, 2 * np.pi, len(participants), endpoint=False)
        coords = np.c_[np.cos(angles), np.sin(angles)]

    cluster_map = {}
    if clusters_df is not None and "Cluster" in clusters_df.columns:
        cluster_map = clusters_df.set_index("Participant")["Cluster"].to_dict()

    edges_x = []
    edges_y = []
    for i in range(len(participants)):
        sim_row = sim[i]
        top_idx = np.argsort(sim_row)[::-1][1:6]
        for j in top_idx:
            if sim_row[j] < threshold:
                continue
            if cluster_map and cluster_map.get(participants[i]) != cluster_map.get(participants[j]):
                continue
            edges_x += [coords[i, 0], coords[j, 0], None]
            edges_y += [coords[i, 1], coords[j, 1], None]

    edge_trace = go.Scatter(
        x=edges_x,
        y=edges_y,
        mode="lines",
        line=dict(width=1, color="rgba(60, 60, 60, 0.25)"),
        hoverinfo="skip",
    )

    node_text = []
    node_color = []
    if cluster_map:
        for p in participants:
            node_text.append(f"{p} | Cluster {cluster_map.get(p, 'N/A')}")
            node_color.append(cluster_map.get(p, -1))
    else:
        node_text = participants
        node_color = "#444"

    node_trace = go.Scatter(
        x=coords[:, 0],
        y=coords[:, 1],
        mode="markers",
        marker=dict(
            size=8,
            color=node_color,
            colorscale="Viridis",
            showscale=False,
            line=dict(width=0.5, color="rgba(255, 255, 255, 0.7)"),
        ),
        text=node_text,
        hoverinfo="text",
    )

    fig = go.Figure(data=[edge_trace, node_trace])
    fig.update_layout(
        xaxis=dict(visible=False),
        yaxis=dict(visible=False),
        margin=dict(l=20, r=20, t=20, b=20),
    )
    return finalize_fig(fig)

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
        "spinners_pca": "Projection PCA (clusters)",
        "spinners_cluster_rank": "Cluster vs classement",
        "spinners_network": "Réseau de similarité des spinners",
        "spinners_cluster_ranking": "Classement interne par cluster",
        "spinners_loadings": "Chargements PCA (PC1/PC2)",
        "no_cluster_data": "Données de clustering manquantes",
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
        "judge_crit_bias_heatmap": "Biais / sévérité par critère",
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
        "spinners_pca": "PCA projection (clusters)",
        "spinners_cluster_rank": "Cluster vs rank",
        "spinners_network": "Spinner similarity network",
        "spinners_cluster_ranking": "Cluster internal ranking",
        "spinners_loadings": "PCA loadings (PC1/PC2)",
        "no_cluster_data": "Missing clustering data",
        "dist_notes": "Score distribution",
        "violin_criteria": "Scores by criteria",
        "violin_judges": "Scores by judge",
        "violin_rounds_total": "Total by round",
        "box_rounds": "Scores by round",
        "judge_mean": "Average by judge",
        "judge_bias": "Judge bias (mean - overall)",
        "judge_heatmap": "Average by criteria",
        "judge_std_heatmap": "Spread by criteria",
        "judge_range_heatmap": "Range by criteria",
        "judge_severity_heatmap": "Severity by judge and criteria (mean delta)",
        "judge_total_corr_heatmap": "Correlation with Total by judge and criteria",
        "judge_total_wo_corr_heatmap": "Correlation criterion vs total without criterion (by judge)",
        "judge_crit_bias_heatmap": "Severity / bias by criteria",
        "judge_part_bias_heatmap": "Severity / bias by spinner",
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
            html.Div(grid, className="viz-aggrid", style={"flex": "0 0 auto", "overflowX": "auto"}),
            html.Div([
                dcc.Graph(figure=fig_criteria, className="viz-graph viz-violin", style={"height": "34vh"}),
                dcc.Graph(figure=fig_judges, className="viz-graph viz-violin", style={"height": "34vh"}),
            ], style={"flex": "1 1 0%   ", "minWidth": "320px", "display": "flex", "flexDirection": "column", "gap": "20px"}),
        ], className="tab-view tab-overview", style={"display": "flex", "gap": "20px", "alignItems": "stretch", "flexWrap": "nowrap"})
    elif tab == "judges":
        if dff_base.empty:
            fig_violin = empty_fig(t["no_data"])
            fig_mean = empty_fig(t["no_data"])
            fig_std = empty_fig(t["no_data"])
            fig_severity = empty_fig(t["no_data"])
            fig_total_violin = empty_fig(t["no_data"])
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
            if dff_total.empty:
                fig_total_violin = empty_fig(t["no_data"])
            else:
                fig_total_violin = finalize_fig(px.violin(
                    dff_total,
                    x=COL_JUDGE,
                    y=COL_SCORE,
                    box=True,
                    points="all",
                ))

        content = html.Div([
            dcc.Graph(figure=fig_violin, className="viz-graph viz-violin full-row"),
            html.Div([
                dcc.Graph(figure=fig_mean, className="viz-graph viz-heatmap"),
                dcc.Graph(figure=fig_std, className="viz-graph viz-heatmap"),
                dcc.Graph(figure=fig_severity, className="viz-graph viz-heatmap"),
            ], className="graph-grid-3"),
            dcc.Graph(figure=fig_total_violin, className="viz-graph viz-violin full-row"),
        ], className="tab-view tab-judges stacked")
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
                    color_continuous_scale=HEATMAP_COLORSCALE,
                    zmin=-1,
                    zmax=1,
                ))

        content = html.Div([
            html.Div([
                dcc.Graph(figure=fig_violin, className="viz-graph viz-violin"),
            ], style={"flex": "1 1 55%"}),
            html.Div([
                dcc.Graph(figure=fig_corr_total_wo, className="viz-graph viz-heatmap"),
                dcc.Graph(figure=fig_corr, className="viz-graph viz-heatmap"),
            ], style={"flex": "1 1 45%", "display": "flex", "flexDirection": "column", "gap": "20px"}),
        ], className="tab-view tab-criteria", style={"display": "flex", "gap": "20px", "alignItems": "stretch", "flexWrap": "nowrap"})
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

        crit_graphs = []
        if dff_base.empty:
            crit_graphs.append(dcc.Graph(figure=empty_fig(t["no_data"])))
        else:
            for crit in sorted(dff_base[COL_CRITERIA].dropna().unique().tolist()):
                sub = dff_base[dff_base[COL_CRITERIA] == crit]
                fig = finalize_fig(px.violin(
                    sub,
                    x=COL_ROUND,
                    y=COL_SCORE,
                    box=True,
                    points="all",
                    title=str(crit),
                ), keep_title=True)
                graph_class = "viz-graph viz-violin rounds-crit-violin"
                if str(crit).strip().lower() in {"créativité", "creativite", "construction"}:
                    graph_class = f"{graph_class} rounds-crit-violin-large"
                crit_graphs.append(dcc.Graph(figure=fig, className=graph_class))

        content = html.Div([
            html.Div([
                dcc.Graph(figure=fig_total_rounds, className="viz-graph viz-violin rounds-graph"),
                dcc.Graph(figure=fig_trend, className="viz-graph viz-line rounds-graph"),
            ], className="graph-grid"),
            html.Div(crit_graphs, className="graph-grid"),
        ], className="tab-view tab-rounds stacked")
    else:
        clusters_df = load_optional_csv(CLUSTER_PATH)
        loadings_df = load_optional_csv(PCA_LOADINGS_PATH)

        if clusters_df is None or "PC1" not in clusters_df.columns or "PC2" not in clusters_df.columns:
            fig_pca = empty_fig(t["no_cluster_data"])
        else:
            fig_pca = px.scatter(
                clusters_df,
                x="PC1",
                y="PC2",
                color="Cluster",
                hover_data=[c for c in ["Participant", "Round", "Rank"] if c in clusters_df.columns],
                color_discrete_sequence=px.colors.qualitative.Dark24,
            )
            fig_pca = finalize_fig(fig_pca)

        if clusters_df is None or "Cluster" not in clusters_df.columns or "Rank" not in clusters_df.columns:
            fig_rank = empty_fig(t["no_cluster_data"])
        else:
            fig_rank = px.violin(
                clusters_df,
                x="Cluster",
                y="Rank",
                box=True,
                points="all",
                color="Cluster",
                hover_data=["Participant"],
                color_discrete_sequence=px.colors.qualitative.Dark24,
            )
            fig_rank = finalize_fig(fig_rank)

        rank_table = html.Div(t["no_cluster_data"])
        if clusters_df is not None and {"Cluster", "Rank", "Participant"}.issubset(clusters_df.columns):
            mean_ranks = (
                clusters_df.groupby("Cluster")["Rank"]
                .mean()
                .sort_values()
            )
            clusters = mean_ranks.index.tolist()
            clusters = clusters[:8]
            max_rank = 17
            rows = []
            for rank in range(1, max_rank + 1):
                row = {"Classement": rank}
                for cluster_id in clusters:
                    sub = clusters_df[clusters_df["Cluster"] == cluster_id].sort_values("Rank")
                    name = ""
                    if len(sub) >= rank:
                        participant = sub.iloc[rank - 1]["Participant"]
                        pr = sub.iloc[rank - 1]["Rank"]
                        name = f"{participant} ({int(pr)})"
                    row[f"cluster_{cluster_id}"] = name
                rows.append(row)

            column_defs = [{"field": "Classement", "headerName": "Classement"}]
            for cluster_id in clusters:
                sub = clusters_df[clusters_df["Cluster"] == cluster_id]
                mean_rank = sub["Rank"].mean()
                column_defs.append(
                    {
                        "field": f"cluster_{cluster_id}",
                        "headerName": f"Cluster {cluster_id} | μ {mean_rank:.2f}",
                    }
                )
            rank_table = dag.AgGrid(
                rowData=rows,
                columnDefs=column_defs,
                defaultColDef={"filter": False, "sortable": False, "resizable": True},
                className="viz-aggrid",
                style={"height": "60vh", "width": "100%"},
            )

        loadings_kpis = html.Div(t["no_cluster_data"])
        if loadings_df is not None and {"PC1", "PC2"}.issubset(loadings_df.columns):
            crit_col = None
            for col in loadings_df.columns:
                if col not in {"PC1", "PC2"}:
                    crit_col = col
                    break
            loadings_work = loadings_df.copy()
            if crit_col is not None:
                loadings_work = loadings_work.set_index(crit_col)

            top_pc1 = loadings_work["PC1"].abs().sort_values(ascending=False).head(4)
            top_pc2 = loadings_work["PC2"].abs().sort_values(ascending=False).head(4)
            top_pc1_str = ", ".join([f"{idx} ({loadings_work.loc[idx, 'PC1']:.2f})" for idx in top_pc1.index])
            top_pc2_str = ", ".join([f"{idx} ({loadings_work.loc[idx, 'PC2']:.2f})" for idx in top_pc2.index])
            loadings_kpis = html.Div([
                html.Div(f"PC1: {top_pc1_str}", className="kpi"),
                html.Div(f"PC2: {top_pc2_str}", className="kpi"),
            ], style={"display": "grid", "gridTemplateColumns": "repeat(auto-fit, minmax(160px, 1fr))", "gap": "10px", "marginTop": "20px"})

        content = html.Div([
            loadings_kpis,
            html.Div([
                dcc.Graph(figure=fig_pca, className="viz-graph viz-scatter", style={"height": "90vh"}),
            ], style={"marginTop": "20px"}),
            html.Div([
                dcc.Graph(figure=fig_rank, className="viz-graph viz-violin", style={"height": "90vh"}),
            ], style={"marginTop": "20px"}),
            html.Div([
                html.H3(t["spinners_cluster_ranking"]),
                rank_table,
            ], style={"marginTop": "20px"}),
        ], className="tab-view tab-spinners")

    return (content, kpi_notes, kpi_participants)


if __name__ == "__main__":
    app.run(debug=True)
