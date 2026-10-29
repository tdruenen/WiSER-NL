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

import glob
import pandas as pd
import os
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
filtered_folder = os.path.join(TEMP_DIR,"filtered")                 # ✅ updated folder
merged_file = os.path.join(TEMP_DIR,"merged_edge_points.csv")      # ✅ updated name

# ---------------- Collect files ---------------- #
csv_files = sorted(glob.glob(os.path.join(filtered_folder, "point_*.csv")))

if not csv_files:
    raise FileNotFoundError(
        f"Geen gefilterde bestanden gevonden in: {filtered_folder}"
    )
logger.info(
    f"{len(csv_files)} gefilterde bestanden gevonden."
)

# ---------------- Merge Files ---------------- #
merged_dfs = []

for csv_file in csv_files:
    basename = os.path.basename(csv_file)

    # ✅ robust angle extraction
    try:
        parent_angle = int(os.path.splitext(basename)[0].split("_")[1])
    except Exception:
        raise ValueError(
            f"Kan geen hoek bepalen uit bestandsnaam: {basename}"
        )

    # read csv
    df = pd.read_csv(csv_file)
    df.columns = df.columns.str.strip()

    # sanity check
    if "wd" not in df.columns or "ws" not in df.columns:
        raise KeyError(
            f"Verplichte kolommen ontbreken in {basename}. "
            f"Gevonden kolommen: {df.columns.tolist()}"
        )

    # add metadata column
    df["Parent_Angle"] = parent_angle

    # optional traceability (useful for debugging)
    df["Source_File"] = basename

    merged_dfs.append(df)

# ---------------- Final merge ---------------- #
df_merged = pd.concat(merged_dfs, ignore_index=True)

# save result
df_merged.to_csv(merged_file, index=False)

logger.info(
    f"Samengevoegd CSV-bestand opgeslagen: {merged_file}"
)
logger.info(
    f"Totaal aantal regels: {len(df_merged)}"
)