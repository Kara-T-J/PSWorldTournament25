# Penspinning World Tournament 2025 score analysis

Dashboard and tooling to explore PSWT 2025 scoring data with Dash.

## Overview

This project provides a multi-tab dashboard to inspect scores, judge behavior,
criteria relationships, and round evolution. It is geared toward detecting
biases and understanding how criteria affect outcomes.

## Data

- Source file: `WT25_notes_cleaned.xlsx`
- Expected columns: Participant, Round, Juge/Judge, Critere/Critère/Criteria, Note/Score
- The "Total" criterion is treated separately when needed (it is the sum of other criteria).

## Features

- Multi-tab analytics dashboard (Vue d'ensemble, Juges, Critères, Rounds, Spinners)
- AgGrid table with filters and sorting in the overview
- Violin plots for criteria, judges, and total by round
- Judge x criteria heatmaps (mean, spread, severity-controlled bias)
- Correlations: criteria vs total-without-criterion (per judge) + inter-criteria
- FR/EN labels

## Project structure

- `WT25_dashboard/` main analytics dashboard
- `dash_test.py` simple Dash app for quick checks
- `WT25_data_cleaning.py` data prep helpers
- `WT25_notes_cleaned.xlsx` cleaned dataset

## Requirements

- Python 3.9+

## Quick start

```bash
cd WT25_dashboard
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python app_dashboard.py
```

Open the URL printed in the terminal (default: `http://127.0.0.1:8050`).

## Notes on methodology

- "Total" is excluded from criteria-only analyses unless explicitly used.
- Severity-adjusted bias:
  (judge-criterion mean - judge mean) - (criterion mean - global mean).
- Correlations to Total are computed against Total-without-criterion to reduce
  tautology.

## Contributing

Issues and PRs are welcome. Keep changes focused and document methodology impacts.

## License

TBD. Add a license file if you plan to open-source distribution.
