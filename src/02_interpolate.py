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

import logging
import os
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import xarray as xr

# ---------------- Logging ---------------- #

logging.basicConfig(
    level=logging.INFO,
    format="%(message)s"
)

# ---------------- Paths ---------------- #

BASE_DIR = os.path.dirname(
    os.path.dirname(os.path.abspath(__file__))
)

TEMP_DIR = os.path.join(BASE_DIR, "temp")
DATA_DIR = os.path.join(BASE_DIR, "data")


csv_file = os.path.join(
    TEMP_DIR,
    "dowa_points.csv"
)

output_dir = os.path.join(
    TEMP_DIR,
    "edge_point_outputs"
)

os.makedirs(
    output_dir,
    exist_ok=True
)

time_file = os.path.join(
    DATA_DIR,
    "NC",
    "time_series.nc"
)

# ---------------- Time series ---------------- #

if not os.path.exists(time_file):
    raise FileNotFoundError(
        f"Tijdseries niet gevonden: {time_file}"
    )

ds_time = xr.open_dataset(time_file)

if "time" not in ds_time:
    raise ValueError(
        "FOUT: Variabele 'time' ontbreekt in time_series.nc."
    )

time_vals = pd.to_datetime(
    ds_time["time"].values
)

logging.info(
    f"Tijdreeks geladen: {len(time_vals)} tijdstappen"
)

# ---------------- Read CSV ---------------- #

if not os.path.exists(csv_file):
    raise FileNotFoundError(
        f"CSV-bestand niet gevonden: {csv_file}"
    )

logging.info(
    f"CSV-bestand ingelezen: {Path(csv_file).as_posix()}"
)

df = pd.read_csv(csv_file)

# ---------------- Bilinear interpolation ---------------- #

def bilinear_interp(
    u_vals,
    v_vals,
    ix_pts,
    iy_pts,
    ix_target,
    iy_target
):

    ix_unique = np.unique(ix_pts)
    iy_unique = np.unique(iy_pts)

    if len(ix_unique) != 2 or len(iy_unique) != 2:
        raise ValueError(
            f"FOUT: Een 2x2-grid is vereist, ontvangen ix={ix_unique}, iy={iy_unique}."
        )

    ix0, ix1 = sorted(ix_unique)
    iy0, iy1 = sorted(iy_unique)

    def get_corner(vals, ix_c, iy_c):

        idx = np.where(
            (ix_pts == ix_c)
            & (iy_pts == iy_c)
        )[0]

        if len(idx) != 1:
            raise ValueError(
                f"FOUT: Hoekpunt ({ix_c},{iy_c}) is niet uniek."
            )

        return vals[:, idx[0]]

    # corners

    u00 = get_corner(u_vals, ix0, iy0)
    u10 = get_corner(u_vals, ix1, iy0)
    u01 = get_corner(u_vals, ix0, iy1)
    u11 = get_corner(u_vals, ix1, iy1)

    v00 = get_corner(v_vals, ix0, iy0)
    v10 = get_corner(v_vals, ix1, iy0)
    v01 = get_corner(v_vals, ix0, iy1)
    v11 = get_corner(v_vals, ix1, iy1)

    # fractional position

    tx = (
        (ix_target - ix0)
        / (ix1 - ix0)
    )

    ty = (
        (iy_target - iy0)
        / (iy1 - iy0)
    )

    # bilinear interpolation

    u_interp = (
        (1 - tx) * (1 - ty) * u00
        + tx * (1 - ty) * u10
        + (1 - tx) * ty * u01
        + tx * ty * u11
    )

    v_interp = (
        (1 - tx) * (1 - ty) * v00
        + tx * (1 - ty) * v10
        + (1 - tx) * ty * v01
        + tx * ty * v11
    )

    return u_interp, v_interp


# ---------------- Processing ---------------- #

domain_points = df[
    df["Type"] == "domain_edge_point"
]

surround_points = df[
    df["Type"] == "nearest_dowa_point"
]

if len(domain_points) == 0:
    raise ValueError(
        "FOUT: Geen domeinrandpunten gevonden in het CSV-bestand."
    )

if len(surround_points) == 0:
    raise ValueError(
        "FOUT: Geen nearest_dowa_point-records gevonden in het CSV-bestand."
    )

for _, domain_row in domain_points.iterrows():

    angle = domain_row["Angle_deg"]

    ix_target = domain_row["Index_X"]
    iy_target = domain_row["Index_Y"]

    surrounds = surround_points[
        surround_points["Angle_deg"] == angle
    ]

    try:

        u_list = []
        v_list = []

        ix_list = []
        iy_list = []

        for _, s in surrounds.iterrows():

            file_path = s["FilePath"]

            if (
                not isinstance(file_path, str)
                or not file_path.strip()
            ):
                raise ValueError(
                    f"FOUT: Ongeldig bestandspad voor hoek {angle}."
                )

            if not os.path.exists(file_path):
                raise FileNotFoundError(file_path)

            ds = xr.open_dataset(file_path)

            if (
                "wspeed" not in ds
                or "wdir" not in ds
            ):
                raise ValueError(
                    f"FOUT: Vereiste variabelen ontbreken in {file_path}."
                )

            ws = ds["wspeed"].values
            wd = ds["wdir"].values

            theta = np.deg2rad(wd)

            u = ws * np.sin(theta)
            v = ws * np.cos(theta)

            if len(u) != len(time_vals):
                raise ValueError(
                    "FOUT: Tijdreeks komt niet overeen met time_series.nc."
                )

            u_list.append(u)
            v_list.append(v)

            ix_list.append(
                int(s["Index_X"])
            )

            iy_list.append(
                int(s["Index_Y"])
            )

            ds.close()

        ix_array = np.array(ix_list)
        iy_array = np.array(iy_list)

        if len(
            set(zip(ix_array, iy_array))
        ) != 4:
            raise ValueError(
                f"FOUT: Ongeldige gridpunten: "
                f"{list(zip(ix_array, iy_array))}"
            )

        u_array = np.stack(
            u_list,
            axis=1
        )

        v_array = np.stack(
            v_list,
            axis=1
        )

        u_i, v_i = bilinear_interp(
            u_array,
            v_array,
            ix_array,
            iy_array,
            ix_target,
            iy_target
        )

        ws_i = np.sqrt(
            u_i**2 + v_i**2
        )

        wd_i = (
            np.rad2deg(
                np.arctan2(u_i, v_i)
            )
            % 360
        )

        out_df = pd.DataFrame({
            "time": time_vals,
            "ws": ws_i,
            "wd": wd_i
        })

        output_file = os.path.join(
            output_dir,
            f"point_{int(angle)}.csv"
        )

        out_df.to_csv(
            output_file,
            index=False
        )

        logging.info(
            f"Geïnterpoleerde tijdreeks opgeslagen: "
            f"{Path(output_file).as_posix()}"
        )

    except Exception as e:

        logging.error(
            f"Verwerking van hoek {angle} mislukt: {e}"
        )
