# This script is used to clean raw ratings data by removing null values.

# Import
import argparse
import pandas as pd

parser = argparse.ArgumentParser(description="Clean raw WT25 notes.")
parser.add_argument("--input", default="data/source/WT25_notes_raw.xlsx", help="Raw notes file.")
parser.add_argument("--output", default="data/intermediate/WT25_notes_cleaned.xlsx", help="Cleaned output file.")
parser.add_argument("--sheet", default="Notes2", help="Sheet name in the raw file.")
args = parser.parse_args()

data = pd.read_excel(args.input, sheet_name=args.sheet)

# Database preparation

def clean_data(df):
    
    # Vérifier colonnes attendues
    required = ['Participant', 'Round', 'Juge', 'Critère', 'Note']
    for col in required:
        if col not in df.columns:
            raise ValueError(f"Colonne manquante: {col}")

    df = df.copy()

    df['Note'] = pd.to_numeric(df['Note'], errors='coerce')

    df = df.dropna(subset=required)

    group_cols = ['Participant', 'Round', 'Juge']

    grouped = df.groupby(group_cols)['Note'].apply(lambda s: s.eq(0).all())
    groups_all_zero = set(grouped[grouped].index)

    to_drop = []
    for idx, row in df.iterrows():
        key = (row['Participant'], row['Round'], row['Juge'])
        if key in groups_all_zero:
            to_drop.append(idx)

    cleaned_df = df.drop(index=to_drop).reset_index(drop=True)
    return cleaned_df

cleaned_df = clean_data(data)
cleaned_df.to_excel(args.output, index=False)
