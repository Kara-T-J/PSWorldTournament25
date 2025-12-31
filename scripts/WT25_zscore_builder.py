import argparse

import pandas as pd


def load_cleaned(path):
    return pd.read_excel(path)


def compute_zscore(frame, judge_col, criteria_col, score_col):
    mean = frame.groupby([judge_col, criteria_col])[score_col].transform("mean")
    std = frame.groupby([judge_col, criteria_col])[score_col].transform("std").replace(0, pd.NA)
    return (frame[score_col] - mean) / std


def compute_rank_from_cleaned(frame):
    participants = frame["Participant"].unique().tolist()
    round_max = frame.groupby("Participant")["Round"].max().to_dict()
    has_total = (frame["Critère"].astype(str).str.strip().str.lower() == "total").any()

    total_scores = None
    if has_total:
        total_only = frame[frame["Critère"].astype(str).str.strip().str.lower() == "total"]
        total_scores = total_only[["Participant", "Round", "Juge", "Note"]].rename(columns={"Note": "Total"})
    else:
        crit_only = frame[frame["Critère"].astype(str).str.strip().str.lower() != "total"]
        total_scores = (
            crit_only.groupby(["Participant", "Round", "Juge"])["Note"]
            .sum()
            .reset_index()
            .rename(columns={"Note": "Total"})
        )

    ranks = {}
    current_rank = 1
    rounds = sorted(set(round_max.values()), reverse=True)

    for rnd in rounds:
        group_participants = [p for p in participants if round_max[p] == rnd]
        if not group_participants:
            continue
        sub = total_scores[
            (total_scores["Round"] == rnd) & (total_scores["Participant"].isin(group_participants))
        ]
        if sub.empty:
            continue

        # Rank within each judge: higher total => higher rank number.
        sub = sub.copy()
        sub["JudgeRank"] = sub.groupby("Juge")["Total"].rank(ascending=True, method="average")
        avg_rank = sub.groupby("Participant")["JudgeRank"].mean().sort_values(ascending=False)

        for p in avg_rank.index.tolist():
            ranks[p] = current_rank
            current_rank += 1

    return pd.DataFrame({"Participant": list(ranks.keys()), "Rank": list(ranks.values())})


def main():
    parser = argparse.ArgumentParser(description="Build participant z-score matrix from cleaned notes.")
    parser.add_argument("--input", default="data/intermediate/WT25_notes_cleaned.xlsx", help="Cleaned notes file.")
    parser.add_argument("--output", default="data/intermediate/WT25_zscore.xlsx", help="Output z-score file.")
    parser.add_argument("--exclude-total", action="store_true", help="Exclude Total criterion.")
    parser.add_argument("--rank-file", default=None, help="Optional CSV/XLSX with Participant and Rank.")
    parser.add_argument("--rank-column", default="Rank", help="Rank column name in rank file.")
    parser.add_argument("--derive-rank", action="store_true", default=True, help="Derive Rank from cleaned notes.")
    args = parser.parse_args()

    df = load_cleaned(args.input)
    expected = {"Participant", "Round", "Juge", "Critère", "Note"}
    missing = expected.difference(df.columns)
    if missing:
        raise ValueError(f"Missing columns in cleaned data: {sorted(missing)}")

    work = df.copy()
    if args.exclude_total:
        work = work[work["Critère"].astype(str).str.strip().str.lower() != "total"]

    work["zscore"] = compute_zscore(work, "Juge", "Critère", "Note")

    z_matrix = (
        work.pivot_table(
            index="Participant",
            columns="Critère",
            values="zscore",
            aggfunc="mean",
        )
        .reset_index()
    )

    round_max = work.groupby("Participant")["Round"].max().reset_index()
    z_matrix = z_matrix.merge(round_max, on="Participant", how="left")

    if args.rank_file:
        if args.rank_file.lower().endswith(".csv"):
            rank_df = pd.read_csv(args.rank_file)
        else:
            rank_df = pd.read_excel(args.rank_file)
        if "Participant" in rank_df.columns and args.rank_column in rank_df.columns:
            z_matrix = z_matrix.merge(
                rank_df[["Participant", args.rank_column]],
                on="Participant",
                how="left",
            )
        else:
            raise ValueError("Rank file must contain Participant and Rank columns.")
    elif args.derive_rank:
        rank_df = compute_rank_from_cleaned(df)
        z_matrix = z_matrix.merge(rank_df, on="Participant", how="left")

    z_matrix.to_excel(args.output, index=False)


if __name__ == "__main__":
    main()
