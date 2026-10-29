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
import os
from pathlib import Path
import logging
import pandas as pd

BASE_DIR = os.path.dirname(
    os.path.dirname(os.path.abspath(__file__))
)

TEMP_DIR = os.path.join(BASE_DIR, "temp")

# ---------------- Logging ---------------- #

logging.basicConfig(
    level=logging.INFO,
    format="%(message)s"
)

logger = logging.getLogger(__name__)
# ---------------- Parameters ---------------- #

input_folder = os.path.join(
    TEMP_DIR,
    "edge_point_outputs"
)

output_folder = os.path.join(
    TEMP_DIR,
    "filtered"
)

os.makedirs(
    output_folder,
    exist_ok=True
)

# ---------------- Find input files ---------------- #

csv_files = sorted(
    glob.glob(
        os.path.join(
            input_folder,
            "point_*.csv"
        )
    )
)

if not csv_files:
    raise FileNotFoundError(
        f"FOUT: Geen bestanden gevonden in {input_folder} "
        f"die voldoen aan 'point_*.csv'"
    )

# ---------------- Determine sector width ---------------- #

n_bins = len(csv_files)
bin_width = 360 / n_bins

logger.info(
    f"{n_bins} bestanden gevonden "
    f"-> sectorbreedte = {bin_width:.2f}"
)

# ---------------- Filtering ---------------- #

for csv_file in csv_files:

    basename = os.path.basename(csv_file)

    parent_angle = int(
        basename
        .split("_")[1]
        .replace(".csv", "")
    )

    half_bin = bin_width / 2

    lower = (
        parent_angle - half_bin
    ) % 360

    upper = (
        parent_angle + half_bin
    ) % 360

    # Load CSV

    df = pd.read_csv(csv_file)

    df.columns = (
        df.columns
        .str.strip()
    )

    if "wd" not in df.columns:
        raise KeyError(
            f"FOUT: Kolom 'wd' niet gevonden in {csv_file}. "
            f"Gevonden kolommen: {df.columns.tolist()}"
        )

    # Filter based on wind direction

    if lower < upper:

        df_filtered = df[
            (df["wd"] >= lower)
            & (df["wd"] < upper)
        ]

    else:

        # Wrap-around case
        df_filtered = df[
            (df["wd"] >= lower)
            | (df["wd"] < upper)
        ]

    # Save filtered CSV

    out_file = os.path.join(
        output_folder,
        basename
    )

    df_filtered.to_csv(
        out_file,
        index=False
    )

    logger.info(
        f"{basename}: "
        f"{len(df_filtered)} rijen behouden "
        f"-> opgeslagen als "
        f"{Path(out_file).as_posix()}"
    )