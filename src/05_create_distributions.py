# =============================================================================
#      _       ___     _____ ______ _____        _   _ _
#     | |     / (_)   / ____|  ____|  __ \      | \ | | |
#     | | /| / / _   | (___ | |__  | |__) | ___ |  \| | |
#     | |/ |/ / | |   \___ \|  __| |  _  / |___|| . ` | |
#    _|__/|__/__|_|_______) | |____| | \ \      | |\  | |__
#   |______________________/|______|_|  \_\     |_| \_|____|
#
# Copyright (c) 2026 Eindhoven University of Technology
#
# Auteur: Thijs van Druenen
# Versie: 1.0
#
# Voor informatie over licentie, aansprakelijkheid, disclaimer en
# gebruiksvoorwaarden wordt verwezen naar:
# LICENSE
# DISCLAIMER.md
# =============================================================================

import pandas as pd
import numpy as np
import os
import json
import logging
import sys

BASE_DIR = os.path.dirname(
    os.path.dirname(os.path.abspath(__file__))
)

TEMP_DIR = os.path.join(BASE_DIR, "temp")

INPUT_JSON = os.path.join(
    BASE_DIR,
    "invoer_parameters.json"
)

# ---------------- Logging ---------------- #

logging.basicConfig(
    level=logging.INFO,
    format="%(message)s"
)

logger = logging.getLogger(__name__)

# ---------------- Output folder ---------------- #

OUTPUT_DIR = TEMP_DIR
os.makedirs(OUTPUT_DIR, exist_ok=True)

# ---------------- Read parameters ---------------- #
def read_invoer_parameters(filename=INPUT_JSON):
    if not os.path.exists(filename):
        raise FileNotFoundError(
            f"Invoerbestand niet gevonden: {filename}"
        )
    with open(filename, "r") as f:
        return json.load(f)

params = read_invoer_parameters()

# parameters still read (not used in filenames anymore)
plan = params["planlocatie"]
x_rd, y_rd = plan
domain = params["domein"]
straal_m = domain.get("straal_m", "rect")

# Optional fields
max_ws = params.get("max_wind_speed", 40)
bin_width = params.get("bin_width", 1)

# ---------------- File names ---------------- #
input_file = os.path.join(OUTPUT_DIR, "merged_edge_points.csv")

if not os.path.exists(input_file):
    raise FileNotFoundError(
        f"Invoerbestand niet gevonden: {input_file}"
    )

# ---------------- Load Data ---------------- #
df = pd.read_csv(input_file)
df.columns = df.columns.str.strip()

required_cols = ["ws", "Parent_Angle", "time"]
missing = [c for c in required_cols if c not in df.columns]
if missing:
    raise KeyError(
        f"Invoerbestand mist vereiste kolommen: {missing}"
    )

# ---------------- Time Handling ---------------- #
df["time"] = pd.to_datetime(df["time"])
df["month"] = df["time"].dt.month

# Season definition
df["Season"] = np.where(df["month"].between(5, 10), "summer", "winter")

# ---------------- Analysis Function ---------------- #
def process_subset(df_subset, label):

    if len(df_subset) == 0:
        logger.info(
            f"Analyse '{label}' overgeslagen (geen gegevens beschikbaar)"
        )
        return

    bins = np.arange(0, max_ws + bin_width, bin_width)

    df_subset = df_subset.copy()
    df_subset["ws_bin"] = pd.cut(df_subset["ws"], bins=bins, right=False)

    # -------- Counts table -------- #
    table_counts = df_subset.pivot_table(
        index="ws_bin",
        columns="Parent_Angle",
        values="ws",
        aggfunc="count",
        fill_value=0,
        observed=False
    )

    table_counts["ws_min"] = table_counts.index.map(lambda x: x.left)
    table_counts["ws_max"] = table_counts.index.map(lambda x: x.right)

    angle_cols = sorted([
        c for c in table_counts.columns if isinstance(c, (int, float))
    ])

    ordered_cols = ["ws_min", "ws_max"] + angle_cols
    table_counts = table_counts[ordered_cols]

    table_counts["Total"] = table_counts[angle_cols].sum(axis=1)

    # ✅ Save counts CSV
    counts_file = os.path.join(
        OUTPUT_DIR,
        f"wind_speed_bin_counts_{label}.csv"
    )

    table_counts_reset = table_counts.reset_index(drop=True)
    table_counts_reset.to_csv(counts_file, index=False)

    logger.info(f"Tabel met aantallen opgeslagen: {counts_file}")

# -------- Percent exceedance -------- #

    grand_total = len(df_subset)

    # Percentage contribution of each bin/direction to total hours
    percent_df = (table_counts[angle_cols].divide(grand_total).multiply(100))

    # Exceedance:
    # % of time WS >= ws_max
    percent_inverse = (percent_df.iloc[::-1].cumsum().iloc[::-1])

    # Add threshold column
    percent_inverse["Drempelsnelheid [m/s]"] = table_counts["ws_min"]

    percent_inverse = percent_inverse[["Drempelsnelheid [m/s]"] + angle_cols]

    # Total exceedance probability
    som = (table_counts["Total"].divide(grand_total).multiply(100))

    percent_inverse["Totale overschrijdingskans [%]"] = (som.iloc[::-1].cumsum().iloc[::-1])

    # Output table
    percent_out = (percent_inverse.reset_index(drop=True).round(6))


    # ✅ Save percentage CSV
    percent_csv_file = os.path.join(
        OUTPUT_DIR,
        f"wind_speed_bin_percentages_exceedance_{label}.csv"
    )
# Hernoem kolommen voor uitvoer
    output_columns = {
        "drempelsnelheid": "Drempelsnelheid [m/s]",
        "som": "Totale overschrijdingskans [%]"
    }

    for angle in angle_cols:
        output_columns[angle] = (
            f"Overschrijdingskans uit {int(angle)} [%]"
        )

    percent_out = percent_out.rename(columns=output_columns)
    percent_out.to_csv(percent_csv_file, index=False)

    logger.info(
        f"CSV met cumulatieve percentages opgeslagen: "
        f"{percent_csv_file}"
    )


    # ✅ Save percentage JSON
    percent_json_file = os.path.join(
        OUTPUT_DIR,
        f"wind_speed_bin_percentages_exceedance_{label}.json"
    )

    # convert to records (list of dicts)
    percent_out.to_json(
        percent_json_file,
        orient="records",
        indent=2
    )

    logger.info(
        f"JSON met cumulatieve percentages opgeslagen: "
        f"{percent_json_file}"
    )

# ---------------- Run Analyses ---------------- #

# All data
process_subset(df, "all")

# Summer
process_subset(df[df["Season"] == "summer"], "summer")

# Winter
process_subset(df[df["Season"] == "winter"], "winter")