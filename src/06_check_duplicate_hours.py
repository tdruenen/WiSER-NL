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
import os
import json
import logging
import sys

BASE_DIR = os.path.dirname(
    os.path.dirname(os.path.abspath(__file__))
)

TEMP_DIR = os.path.join(BASE_DIR, "temp")

logging.basicConfig(
    level=logging.INFO,
    format="%(message)s"
)

logger = logging.getLogger(__name__)
# ---------------- Parameters ---------------- #
INPUT_DIR = TEMP_DIR

input_file = os.path.join(INPUT_DIR, "merged_edge_points.csv")
json_output = os.path.join(INPUT_DIR, "hour_check_summary.json")

start_date = "2008-01-01 00:00"
end_date = "2018-01-01 00:00"

# ---------------- Load Data ---------------- #
if not os.path.exists(input_file):
    raise FileNotFoundError(
        f"Invoerbestand niet gevonden: {input_file}"
    )

df = pd.read_csv(input_file)
df.columns = df.columns.str.strip()

df["time"] = pd.to_datetime(df["time"])

# ---------------- Expected timeline ---------------- #
all_hours = pd.date_range(start=start_date, end=end_date, freq="h")
n_expected_hours = len(all_hours)

# ---------------- Counts ---------------- #
time_counts = df["time"].value_counts()

# 1️⃣ Hours with no data
missing_hours = all_hours.difference(time_counts.index)
n_missing = len(missing_hours)

# 2️⃣ Hours with >1 data
duplicate_hours = time_counts[time_counts > 1]
n_duplicate_hours = len(duplicate_hours)

# 3️⃣ Total rows (includes duplicates)
n_total_rows = len(df)


# ---------------- Percentages ---------------- #
pct_missing = n_missing / n_expected_hours * 100
pct_duplicate_hours = n_duplicate_hours / n_expected_hours * 100

# ---------------- Console output ---------------- #
logger.info("===== SAMENVATTING =====")

logger.info(f"Verwacht aantal uren: {n_expected_hours}")
logger.info(f"Totaal aantal regels in bestand: {n_total_rows}")

logger.info("--- Ontbrekende gegevens ---")
logger.info(f"Uren zonder gegevens: {n_missing}")
logger.info(f"Percentage ontbrekend: {pct_missing:.2f}%")

logger.info("--- Duplicaten ---")
logger.info(f"Uren met meer dan één gegevenspunt: {n_duplicate_hours}")
logger.info(f"Percentage dubbele uren: {pct_duplicate_hours:.2f}%")

logger.info("==========================")

# ---------------- JSON summary ---------------- #
summary = {
    "verwachte_uren": int(n_expected_hours),
    "totaal_aantal_regels": int(n_total_rows),

    "ontbrekend": {
        "aantal": int(n_missing),
        "percentage": round(pct_missing, 2)
    },

    "duplicaten": {
        "uren_met_meer_dan_een_gegeven": int(n_duplicate_hours),
        "percentage": round(pct_duplicate_hours, 2)
    },

}

# Save JSON
with open(json_output, "w", encoding="utf-8") as f:
    json.dump(summary, f, indent=2)

logger.info(f"Samenvatting opgeslagen als JSON-bestand: {json_output}")
logger.info(
    "Controle van ontbrekende en dubbele uren voltooid"
)