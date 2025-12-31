import argparse
import sys

import numpy as np
import pandas as pd

try:
    from sklearn.cluster import KMeans
    from sklearn.metrics import silhouette_score
    from sklearn.decomposition import PCA
except ImportError:  # pragma: no cover - runtime guard
    KMeans = None
    silhouette_score = None
    PCA = None


def load_data(path):
    return pd.read_excel(path)


def pick_k(X, k_min=4, k_max=8, random_state=42):
    best_k = None
    best_score = -1
    for k in range(k_min, k_max + 1):
        kmeans = fit_kmeans(X, k, random_state)
        labels = kmeans.labels_
        if len(set(labels)) < 2:
            continue
        score = silhouette_score(X, labels)
        if score > best_score:
            best_score = score
            best_k = k
    return best_k, best_score


def fit_kmeans(X, k, random_state=42):
    try:
        return KMeans(n_clusters=k, n_init="auto", random_state=random_state).fit(X)
    except TypeError:
        return KMeans(n_clusters=k, n_init=10, random_state=random_state).fit(X)


def ensure_sklearn():
    if KMeans is None or silhouette_score is None:
        print("Missing dependency: scikit-learn. Install with `pip install scikit-learn`.")
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(description="Cluster participants from z-score matrix.")
    parser.add_argument("--input", default="data/intermediate/WT25_zscore.xlsx", help="Path to z-score file.")
    parser.add_argument("--output", default="data/output/WT25_participant_clusters.csv", help="Clustered output CSV.")
    parser.add_argument("--summary", default="data/output/WT25_cluster_summary.csv", help="Cluster summary CSV.")
    parser.add_argument("--k", type=int, default=None, help="Number of clusters. Auto if omitted.")
    parser.add_argument("--max-k", type=int, default=8, help="Max k for auto selection.")
    parser.add_argument("--plot", default="data/output/WT25_cluster_pca.html", help="PCA plot HTML output.")
    parser.add_argument("--no-plot", action="store_true", help="Skip PCA plot.")
    args = parser.parse_args()

    ensure_sklearn()
    df = load_data(args.input)

    if "Participant" not in df.columns:
        print("Missing 'Participant' column.")
        sys.exit(1)

    round_col = None
    rank_col = None
    for col in df.columns:
        if str(col).strip().lower() in {"round", "rounds", "tour"}:
            round_col = col
            break
    for col in df.columns:
        if str(col).strip().lower() in {"rank", "ranking", "classement"}:
            rank_col = col
            break

    criteria_cols = [
        c for c in df.columns
        if c not in ("Participant",) and c not in {round_col, rank_col}
    ]
    X = df[criteria_cols].apply(pd.to_numeric, errors="coerce").values

    k = args.k
    if k is None:
        max_k = min(args.max_k, max(4, len(df) - 1))
        k, score = pick_k(X, k_min=4, k_max=max_k)
        if k is None:
            print("Unable to determine k (insufficient data).")
            sys.exit(1)
        print(f"Auto-selected k={k} (silhouette={score:.3f})")

    kmeans = fit_kmeans(X, k)
    df["Cluster"] = kmeans.labels_

    summary_aggs = {"Participants": ("Participant", "count")}
    if round_col is not None:
        summary_aggs["Round_Mean"] = (round_col, "mean")
    if rank_col is not None:
        summary_aggs["Rank_Mean"] = (rank_col, "mean")
    summary_aggs.update({f"{c}_Mean": (c, "mean") for c in criteria_cols})
    summary = df.groupby("Cluster").agg(**summary_aggs).reset_index()

    pca = PCA(n_components=2, random_state=42)
    coords = pca.fit_transform(X)
    df["PC1"] = coords[:, 0]
    df["PC2"] = coords[:, 1]
    plot_df = df.copy()

    loadings = pd.DataFrame(
        pca.components_.T,
        index=criteria_cols,
        columns=["PC1", "PC2"],
    )
    loadings.to_csv("data/output/WT25_pca_loadings.csv")
    explained = pd.DataFrame(
        {
            "PC": ["PC1", "PC2"],
            "ExplainedVariance": pca.explained_variance_ratio_,
        }
    )
    explained.to_csv("data/output/WT25_pca_explained_variance.csv", index=False)

    df.to_csv(args.output, index=False)
    summary.to_csv(args.summary, index=False)
    print(f"Wrote clusters to {args.output}")
    print(f"Wrote summary to {args.summary}")
    print("Wrote PCA loadings to data/output/WT25_pca_loadings.csv")
    print("Wrote PCA explained variance to data/output/WT25_pca_explained_variance.csv")

    if args.no_plot:
        return

    try:
        import plotly.express as px
    except ImportError:
        print("Plotly not installed; skipping PCA plot.")
        return
    hover = ["Participant"]
    if round_col is not None:
        hover.append(round_col)
    fig = px.scatter(
        plot_df,
        x="PC1",
        y="PC2",
        color="Cluster",
        hover_data=hover,
        title="Participant clustering (PCA projection)",
        color_discrete_sequence=px.colors.qualitative.Dark24,
    )
    fig.write_html(args.plot)
    print(f"Wrote PCA plot to {args.plot}")


if __name__ == "__main__":
    main()
