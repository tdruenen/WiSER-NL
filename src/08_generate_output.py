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

import os
import json
import pandas as pd
import logging
from datetime import datetime
from zipfile import ZipFile
from pyproj import Transformer

BASE_DIR = os.path.dirname(
    os.path.dirname(os.path.abspath(__file__))
)

TEMP_DIR = os.path.join(BASE_DIR, "temp")
OUTPUT_DIR = os.path.join(BASE_DIR, "output")

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

# ---------------- Paths ---------------- #


os.makedirs(
    OUTPUT_DIR,
    exist_ok=True
)

# ---------------- Read input ---------------- #

def read_invoer_parameters(
    filename=INPUT_JSON
):
    if not os.path.exists(filename):
        raise FileNotFoundError(
            f"Invoerbestand ontbreekt: {filename}"
        )

    with open(filename, "r") as f:
        return json.load(f)

params = read_invoer_parameters()

projectnaam = params.get(
    "projectnaam",
    "Project"
)

plan = params["planlocatie"]
coord_sys = params["coordinatenstelsel"]
domain = params["domein"]

uitvoerniveau = params.get(
    "uitvoerniveau",
    1
)

aantal_richtingen = params.get(
    "aantal_richtingen",
    None
)

# ---------------- Zip naming ---------------- #

def get_next_index(base_name):

    existing = [
        f for f in os.listdir(OUTPUT_DIR)
        if f.startswith(base_name)
        and f.endswith(".zip")
    ]

    indices = []

    for name in existing:

        parts = (
            name
            .replace(".zip", "")
            .split("_")
        )

        if (
            len(parts) >= 2 and
            parts[-1].isdigit()
        ):
            indices.append(
                int(parts[-1])
            )

    next_idx = (
        1
        if not indices
        else max(indices) + 1
    )

    return (
        f"{base_name}_{next_idx:03d}.zip"
    )

zip_filename = get_next_index(
    projectnaam
)

zip_path = os.path.join(
    OUTPUT_DIR,
    zip_filename
)

logger.info(
    f"ZIP-archief wordt aangemaakt: {zip_path}"
)

# ---------------- Coordinate conversion ---------------- #

rd_to_wgs = Transformer.from_crs(
    "EPSG:28992",
    "EPSG:4326",
    always_xy=True
)

wgs_to_rd = Transformer.from_crs(
    "EPSG:4326",
    "EPSG:28992",
    always_xy=True
)

if coord_sys in ["EPSG:28992", "RD"]:

    # Input is RD (x, y)
    rd_x, rd_y = plan

    # Convert to WGS84 (lon, lat)
    lon, lat = rd_to_wgs.transform(
        rd_x,
        rd_y
    )

else:

    # Input is geographic (lat, lon)
    lat, lon = plan

    # Convert to RD (x, y)
    rd_x, rd_y = wgs_to_rd.transform(
        lon,
        lat
    )

    # Optional rounding
    rd_x = round(rd_x)
    rd_y = round(rd_y)

# ---------------- Domain ---------------- #

domain_type = domain["type"]

if domain_type == "cirkel":

    domain_definition = {
        "middelpunt":
            domain.get(
                "middelpunt",
                plan
            ),
        "straal [m]":
            domain["straal_m"]
    }

elif domain_type == "rechthoek":

    domain_definition = {
        "middelpunt":
            domain["middelpunt"],
        "breedte [m]":
            domain["breedte_m"],
        "hoogte [m]":
            domain["hoogte_m"],
        "rotatie [graden]":
            domain["rotatie_graden"]
    }

else:

    domain_definition = domain

# ---------------- Load hour summary ---------------- #

hour_summary_path = os.path.join(
    TEMP_DIR,
    "hour_check_summary.json"
)

if not os.path.exists(
    hour_summary_path
):
    raise FileNotFoundError(
        "Bestand hour_check_summary.json ontbreekt"
    )

with open(
    hour_summary_path,
    "r"
) as f:

    hour_summary = json.load(f)

# ---------------- Load ruwheid summary ---------------- #

effective_z0_path = os.path.join(
    TEMP_DIR,
    "ruwheidslengte_eff_debug.csv"
)

if not os.path.exists(
    effective_z0_path
):
    raise FileNotFoundError(
        "ruwheidslengte_eff_debug.csv ontbreekt"
    )

effective_z0_df = pd.read_csv(
    effective_z0_path
)

effective_z0_summary = (
    effective_z0_df[
        [
            "angle_middelpunt",
            "z0_effective",
            "pct_masked"
        ]
    ]
    .assign(
        z0_effective=lambda df: df["z0_effective"].round(2),
        pct_masked=lambda df: df["pct_masked"].round(2)
    )
    .rename(
        columns={
            "angle_middelpunt": "windrichting [graden]",
            "z0_effective": "effectieve ruwheidslengte [m]",
            "pct_masked": "gemaskeerd [%]"
        }
    )
    .to_dict(
        orient="records"
    )
)

# ---------------- Build summary ---------------- #

summary = {

    "software": {
        "naam": "WiSER-NL",
        "versie": "1.0"
    },

    "project": {
        "projectnaam": projectnaam,
        "archief": zip_filename
    },

    "locatie": {

        "rijksdriehoek": {

            "coordinatenstelsel":
                "EPSG:28992",

            "naam":
                "Rijksdriehoeksstelsel",

            "eenheid":
                "m",

            "x":
                rd_x,

            "y":
                rd_y
        },

        "geografisch": {

            "coordinatenstelsel":
                "EPSG:4326",

            "referentiesysteem":
                "WGS84",

            "eenheid":
                "graden",

            "breedtegraad":
                lat,

            "lengtegraad":
                lon
        }
    },

    "domein": {

        "type":
            domain_type,

        "definitie":
            domain_definition
    },

    "analyse": {

        "uitvoerdatum":
            datetime.now()
            .astimezone()
            .isoformat(),
            
        "uitvoerniveau":
            uitvoerniveau,

        "aantal_richtingen":
            aantal_richtingen,

        "datakwaliteit": {

            "uurcontrole":
                hour_summary
        },

        "ruwheid": {

            "bron":
                "ruwheidslengte_eff.csv",

            "richtingsafhankelijk":

                effective_z0_summary
        }
    }
}

# ---------------- Required files ---------------- #

required_files = [

    # Niveau 1
    "wind_speed_bin_percentages_exceedance_all.csv",
    "wind_speed_bin_percentages_exceedance_summer.csv",
    "wind_speed_bin_percentages_exceedance_winter.csv",

    "debug_plot.png",
    "run_log.txt",

    "ruwheidslengte_eff.csv",
    "ruwheid_sectors.png"
]

# Niveau 2
if uitvoerniveau >= 2:

    required_files.extend([
        "wind_speed_bin_percentages_exceedance_all.json",
        "wind_speed_bin_percentages_exceedance_summer.json",
        "wind_speed_bin_percentages_exceedance_winter.json"
    ])

# Niveau 3
if uitvoerniveau >= 3:

    required_files.extend([
        "richtingspunten_windstatistiek.csv",
        "richtingspunten_windstatistiek_sectorgrenzen.csv",
        "ruwheidslengte_eff_sectorgegevens.csv"
    ])

# ---------------- Rename mapping ---------------- #

rename_map = {

    "wind_speed_bin_percentages_exceedance_all":
        "freq_inv_cum_rel",

    "wind_speed_bin_percentages_exceedance_summer":
        "freq_inv_cum_rel_zomer",

    "wind_speed_bin_percentages_exceedance_winter":
        "freq_inv_cum_rel_winter",
        

    "debug_plot":
        "grondgebruikskaart",

    "run_log":
        "log",

    "ruwheidslengte_eff":
        "ruwheidslengte_eff",

    "ruwheid_sectors":
        "ruwheidskaart"
}

# ---------------- Nederlandstalige technische exports ---------------- #

if uitvoerniveau >= 3:

    # Richtingspunten windstatistiek

    pd.read_csv(
        os.path.join(TEMP_DIR, "dowa_points.csv")
    ).replace({
        "Type": {
            "domain_edge_point": "richtingspunt",
            "nearest_dowa_point": "dichtstbijzijnde_dowa_punt"
        }
    }).rename(
        columns={
            "Type": "type",
            "Angle_deg": "windrichting",
            "RD_X": "rd_x",
            "RD_Y": "rd_y",
            "Lon": "lengtegraad",
            "Lat": "breedtegraad",
            "X_proj": "projectie_x",
            "Y_proj": "projectie_y",
            "Index_X": "index_x",
            "Index_Y": "index_y",
            "FilePath": "bestandspad"
        }
    ).to_csv(
        os.path.join(
            TEMP_DIR,
            "richtingspunten_windstatistiek.csv"
        ),
        index=False
    )

    # Sectorgrenzen

    pd.read_csv(
        os.path.join(TEMP_DIR, "dowa_points_mid_angles.csv")
    ).rename(
        columns={
            "Angle_deg": "windrichting",
            "RD_X": "rd_x",
            "RD_Y": "rd_y",
            "Lon": "lengtegraad",
            "Lat": "breedtegraad",
            "X_proj": "projectie_x",
            "Y_proj": "projectie_y",
            "Index_X": "index_x",
            "Index_Y": "index_y"
        }
    ).to_csv(
        os.path.join(
            TEMP_DIR,
            "richtingspunten_windstatistiek_sectorgrenzen.csv"
        ),
        index=False
    )
    
    # Ruwheid

    df = pd.read_csv(
        os.path.join(TEMP_DIR, "ruwheidslengte_eff_debug.csv")
    )

    ruwheid_rename_map = {
        "angle_middelpunt": "Windrichting [graden]",
        "angle_start": "Windrichtingssector start [graden]",
        "angle_end": "Windrichtingssector einde [graden]",
        "z0_effective": "Effectieve ruwheidslengte [m]",
        "pct_masked": "Gemaskeerd [%]"
    }

    for i in range(1, 11):
        ruwheid_rename_map[f"z0_ring_{i:02d}"] = f"Ruwheidslengte_ring_{i:02d} [m]"
        ruwheid_rename_map[f"n_ring_{i:02d}"] = f"Equivalente_cellen_ring_{i:02d} [-]"
        ruwheid_rename_map[f"weight_ring_{i:02d}"] = f"Weegfactor_ring_{i:02d} [-]"
        ruwheid_rename_map[f"cd_ring_{i:02d}"] = f"Cd_ring_{i:02d} [-]"

    df.rename(columns=ruwheid_rename_map).to_csv(
        os.path.join(
            TEMP_DIR,
            "ruwheidslengte_eff_sectorgegevens.csv"
        ),
        index=False
    )

# ---------------- Create ZIP ---------------- #

with ZipFile(
    zip_path,
    "w"
) as zipf:

    for filename in required_files:

        src_path = os.path.join(
            TEMP_DIR,
            filename
        )

        if not os.path.exists(
            src_path
        ):
            raise FileNotFoundError(
                f"Vereist bestand ontbreekt: {filename}"
            )

        name, ext = os.path.splitext(
            filename
        )

        for key in rename_map:

            if name == key:

                dest_name = (
                    rename_map[key]
                    + ext
                )

                break

        else:

            dest_name = filename

        zipf.write(
            src_path,
            dest_name
        )

        logger.info(
            f"[OK] Toegevoegd: {dest_name}"
        )

    # input.json

    if not os.path.exists(
        INPUT_JSON
    ):
        raise FileNotFoundError(
            "Bestand invoer_parameters.json ontbreekt"
        )

    zipf.write(
        INPUT_JSON,
        "invoer_parameters.json"
    )

    logger.info(
        "[OK] Toegevoegd: invoer_parameters.json"
    )

    # summary.json

    zipf.writestr(
        "samenvatting.json",
        json.dumps(
            summary,
            indent=2
        )
    )

    logger.info(
        "[OK] Toegevoegd: samenvatting.json"
    )

logger.info(
    f"SUCCES: ZIP-archief aangemaakt: {zip_path}"
)
