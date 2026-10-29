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

import json
import math
import os

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from pyproj import Transformer

from shapely.geometry import Polygon, box, Point
from shapely.affinity import rotate, translate

from matplotlib.colors import LogNorm
import logging
import sys

logging.basicConfig(
    level=logging.INFO,
    format="%(message)s"
)

logger = logging.getLogger(__name__)

# ============================================================
# SETTINGS
# ============================================================

BASE_DIR = os.path.dirname(
    os.path.dirname(os.path.abspath(__file__))
)

TEMP_DIR = os.path.join(BASE_DIR, "temp")
DATA_DIR = os.path.join(BASE_DIR, "data")

CELL_SIZE = 250.0
HALF_CELL = CELL_SIZE / 2
CELL_AREA = CELL_SIZE * CELL_SIZE
RING_breedte_m = 1000
OUTPUT_DIR = TEMP_DIR
KAPPA = 0.42
BLENDING_HEIGHT = 60 

os.makedirs(
    OUTPUT_DIR,
    exist_ok=True
)

DOWA_CSV = os.path.join(
    OUTPUT_DIR,
    "dowa_points.csv"
)

MID_DOWA_CSV = os.path.join(
    OUTPUT_DIR,
    "dowa_points_mid_angles.csv"
)

INPUT_JSON = os.path.join(
    BASE_DIR,
    "invoer_parameters.json"
)

LGN_PARQUET = os.path.join(
    DATA_DIR,
    "LGN",
    "lgn2023_z0_250m_cellcentre_masked_m.parquet"
)



FETCH_DISTANCE_M = 10000
N_RINGS = 10
MASK_VALUE = -999

wgs84_to_rd = Transformer.from_crs(
    "EPSG:4326",
    "EPSG:28992",
    always_xy=True
)

rd_to_wgs84 = Transformer.from_crs(
    "EPSG:28992",
    "EPSG:4326",
    always_xy=True
)

def to_rd(a, b, coord_sys):

    if coord_sys in ["EPSG:28992", "RD"]:
        return a, b

    elif coord_sys in ["WGS84", "GCS"]:

        # Google Maps convention:
        # input = [lat, lon]

        lat, lon = a, b

        return wgs84_to_rd.transform(
            lon,
            lat
        )

    else:
        raise ValueError(
            f"Niet-ondersteund coördinatensysteem: {coord_sys}"
        )

# ============================================================
# READ INPUT
# ============================================================

with open(INPUT_JSON, "r") as f:
    params = json.load(f)

plot_opties = params.get("plot_opties",{})
ruwheid_plot = plot_opties.get("ruwheid",{})
toon_sectorlabels = ruwheid_plot.get("toon_sectorlabels",True)
toon_sectoren = ruwheid_plot.get("toon_sectoren",True)

coord_sys = params["coordinatenstelsel"].upper()

PLOT_COORD_SYS = "RD"

lat_or_x, lon_or_y = params["planlocatie"]

plan_x, plan_y = to_rd(
    lat_or_x,
    lon_or_y,
    coord_sys
)
# ============================================================
# READ DOMAIN POLYGON
# ============================================================

domain = params["domein"]

domain_type = domain["type"].lower()

middelpunt_a, middelpunt_b = domain["middelpunt"]

domain_x, domain_y = to_rd(
    middelpunt_a,
    middelpunt_b,
    coord_sys
)

if domain_type == "cirkel":

    radius = domain["straal_m"]

    domain_poly = Point(
        domain_x,
        domain_y
    ).buffer(radius)

elif domain_type == "rechthoek":

    width = domain["breedte_m"]
    height = domain["hoogte_m"]
    rotatie_graden = domain.get(
        "rotatie_graden",
        0
    )

    dx = width / 2
    dy = height / 2

    domain_poly = Polygon([
        (-dx, -dy),
        ( dx, -dy),
        ( dx,  dy),
        (-dx,  dy)
    ])

    domain_poly = rotate(
        domain_poly,
        -rotatie_graden,
        origin=(0, 0),
        use_radians=False
    )

    domain_poly = translate(
        domain_poly,
        xoff=domain_x,
        yoff=domain_y
    )

else:

    raise ValueError(
        f"FOUT: Onbekend domeintype: {domain_type}"
    )


# ============================================================
# READ DOMAIN EDGE POINTS
# ============================================================

edge_df = (
    pd.read_csv(DOWA_CSV)
    .query("Type == 'domain_edge_point'")
    .sort_values("Angle_deg")
    .reset_index(drop=True)
)


domain_minx, domain_miny, domain_maxx, domain_maxy = domain_poly.bounds

EDGE_BUFFER_M = 3200

span_x = (
    domain_maxx -
    domain_minx +
    2 * EDGE_BUFFER_M
)

span_y = (
    domain_maxy -
    domain_miny +
    2 * EDGE_BUFFER_M
)

span = max(span_x, span_y)

middelpunt_x = 0.5 * (domain_minx + domain_maxx)
middelpunt_y = 0.5 * (domain_miny + domain_maxy)

plot_minx = middelpunt_x - span / 2
plot_maxx = middelpunt_x + span / 2

plot_miny = middelpunt_y - span / 2
plot_maxy = middelpunt_y + span / 2

boundary_df = (
    pd.read_csv(MID_DOWA_CSV)
    .sort_values("Angle_deg")
    .reset_index(drop=True)
)

# ============================================================
# HELPERS
# ============================================================

def extend_point(plan_x, plan_y, x, y, distance):

    dx = x - plan_x
    dy = y - plan_y

    L = math.hypot(dx, dy)

    ux = dx / L
    uy = dy / L

    return (
        x + distance * ux,
        y + distance * uy
    )

def format_z0(x):

    if not np.isfinite(x) or x <= 0:
        return x

    if x >= 1:
        return round(x, 1)

    exponent = np.floor(np.log10(abs(x)))

    decimals = int(-exponent)

    return round(x, decimals)


def create_default_results(sectors):

    results = []

    for sector in sectors:

        row = {
            "angle_middelpunt": sector["angle_middelpunt"],
            "angle_start": sector["angle_start"],
            "angle_end": sector["angle_end"],
            "pct_masked": 100.0,
            "z0_effective": 0.0
        }

        for i_ring in range(N_RINGS):

            row[f"z0_ring_{i_ring+1:02d}"] = 0.0
            row[f"n_ring_{i_ring+1:02d}"] = 0
            row[f"weight_ring_{i_ring+1:02d}"] = np.nan

        results.append(row)

    return pd.DataFrame(results)

# ============================================================
# BUILD FETCH SECTORS
# ============================================================

logger.info("Sectoren opbouwen...")

sectors = []

n = len(edge_df)

for i in range(n):

    curr_row = edge_df.iloc[i]

    left_boundary  = boundary_df.iloc[(i - 1) % n]
    right_boundary = boundary_df.iloc[i]

    angle_middelpunt = curr_row["Angle_deg"]

    x_left = left_boundary["RD_X"]
    y_left = left_boundary["RD_Y"]

    x_right = right_boundary["RD_X"]
    y_right = right_boundary["RD_Y"]

    ox_left, oy_left = extend_point(
        plan_x,
        plan_y,
        x_left,
        y_left,
        FETCH_DISTANCE_M
    )

    ox_right, oy_right = extend_point(
        plan_x,
        plan_y,
        x_right,
        y_right,
        FETCH_DISTANCE_M
    )

    poly = Polygon([
        (x_left, y_left),
        (x_right, y_right),
        (ox_right, oy_right),
        (ox_left, oy_left)
    ])

    sectors.append({

        "angle_middelpunt": angle_middelpunt,

        "angle_start": left_boundary["Angle_deg"],

        "angle_end": right_boundary["Angle_deg"],

        "polygon": poly,

        "x_left": x_left,
        "y_left": y_left,

        "x_right": x_right,
        "y_right": y_right,

        "ox_left": ox_left,
        "oy_left": oy_left,

        "ox_right": ox_right,
        "oy_right": oy_right
    })

logger.info(f"{len(sectors)} sectoren aangemaakt")

# ============================================================
# TOTAL BOUNDS
# ============================================================

all_polys = [s["polygon"] for s in sectors]

minx = min(p.bounds[0] for p in all_polys)
miny = min(p.bounds[1] for p in all_polys)
maxx = max(p.bounds[2] for p in all_polys)
maxy = max(p.bounds[3] for p in all_polys)

logger.info("Totale begrenzing:")

logger.info(
    f"Totale begrenzing: "
    f"x=[{minx:.1f}, {maxx:.1f}], "
    f"y=[{miny:.1f}, {maxy:.1f}]"
)

# ============================================================
# LOAD LGN PARQUET
# ============================================================

logger.info("LGN-parquetbestand wordt ingelezen...")

lgn_df = pd.read_parquet(
    LGN_PARQUET
)


buffer = 10000

lgn_df = lgn_df[
    (lgn_df["X"] >= minx - buffer) &
    (lgn_df["X"] <= maxx + buffer) &
    (lgn_df["Y"] >= miny - buffer) &
    (lgn_df["Y"] <= maxy + buffer)
]

if "Z0" not in lgn_df.columns:
    raise ValueError(
        "Kolom 'Z0' niet gevonden in LGN-bestand."
    )

xs = lgn_df["X"].to_numpy()
ys = lgn_df["Y"].to_numpy()
values = lgn_df["Z0"].to_numpy()

logger.info(
    f"{len(values)} LGN-cellen geladen"
)

logger.info(
    f"Aantal ontbrekende Z0-waarden: "
    f"{lgn_df['Z0'].isna().sum()}"
)

valid_mask = (
    np.isfinite(values) &
    (values != MASK_VALUE)
)

n_total = len(values)
n_valid = np.sum(valid_mask)

coverage_pct = (
    100 * n_valid / n_total
    if n_total > 0
    else 0
)

logger.info(
    f"Dekking met geldige LGN-cellen: "
    f"{coverage_pct:.1f}%"
)

if coverage_pct < 50:

    logger.warning(
        "Minder dan 50% van de beschikbare "
        "LGN-cellen bevat geldige ruwheidsgegevens."
    )

del lgn_df

# ------------------------------------------------------------
# CHECK COVERAGE
# ------------------------------------------------------------

if len(values) == 0:

    logger.warning(
        "Geen LGN-cellen gevonden voor deze locatie."
    )

    logger.warning(
        "Voor alle sectoren wordt de standaardwaarde "
        "z0 = 0,0 toegepast."
    )

    results_df = create_default_results(
        sectors
    )

    results_csv = os.path.join(
        OUTPUT_DIR,
        "effective_z0.csv"
    )

    results_df.to_csv(
        results_csv,
        index=False
    )

    logger.info(
        f"Resultaten opgeslagen: {results_csv}"
    )

    logger.info("Resultaten:")
    logger.info(results_df)

    raise SystemExit(0)


if n_valid == 0:

    logger.warning(
        "Alle LGN-ruwheidswaarden zijn ongeldig."
    )

    logger.warning(
        "Voor alle sectoren wordt de standaardwaarde "
        "z0 = 0,0 toegepast."
    )

    results_df = create_default_results(
        sectors
    )

    results_csv = os.path.join(
        OUTPUT_DIR,
        "effective_z0.csv"
    )

    results_df.to_csv(
        results_csv,
        index=False
    )

    logger.info(
        f"Resultaten opgeslagen: {results_csv}"
    )

    logger.info("Resultaten:")
    logger.info(results_df)

    raise SystemExit(0)

# ============================================================
# PROCESS SECTORS
# ============================================================

results = []


plt.rcParams.update({
    "font.size": 6,
    "font.family": "sans-serif"
    })

fig, ax = plt.subplots(figsize=(8/2.54, 8/2.54))


# ============================================================
# RECONSTRUCT GRID FOR PLOTTING
# ============================================================

plot_df = pd.DataFrame({
    "X": xs,
    "Y": ys,
    "Z0": values
})

z_grid = (
    plot_df.pivot(
        index="Y",
        columns="X",
        values="Z0"
    )
    .sort_index(
        ascending=False
    )
)

x_grid = z_grid.columns.values
y_grid = z_grid.index.values

# ------------------------------------------------------------
# MASK INVALID VALUES
# ------------------------------------------------------------

z_values = z_grid.values.copy()

z_values[
    z_values == MASK_VALUE
] = np.nan

z_plot = np.ma.masked_invalid(
    z_values
)

# ------------------------------------------------------------
# COLORMAP
# ------------------------------------------------------------

cmap = plt.cm.terrain.copy()

cmap.set_bad(
    color=(81/255, 0/255, 81/255)
)

# ------------------------------------------------------------
# COLOR LIMITS
# ------------------------------------------------------------

valid_values = z_values[
    np.isfinite(z_values)
]

vmin = 0.01
vmax = 1.6


# ------------------------------------------------------------
# PLOT
# ------------------------------------------------------------

if PLOT_COORD_SYS == "RD":

    im = ax.imshow(
        z_plot,
        extent=[
            x_grid.min(),
            x_grid.max(),
            y_grid.min(),
            y_grid.max()
        ],
        cmap=cmap,
        norm=LogNorm(vmin=vmin, vmax=vmax),
        interpolation="nearest",
        origin="upper"
    )



# ============================================================
# PROCESS EACH SECTOR
# ============================================================

for sector in sectors:

    poly = sector["polygon"]

    minx_p, miny_p, maxx_p, maxy_p = poly.bounds

    mask = (
        (xs >= minx_p) &
        (xs <= maxx_p) &
        (ys >= miny_p) &
        (ys <= maxy_p)
    )

    candidate_idx = np.where(mask)[0]

    inside_idx = []
    

    for idx in candidate_idx:

        cell_poly = box(
            xs[idx] - HALF_CELL,
            ys[idx] - HALF_CELL,
            xs[idx] + HALF_CELL,
            ys[idx] + HALF_CELL
        )

        overlap_area = (
            poly.intersection(cell_poly).area
        )

        sector_fraction = (
            overlap_area /
            CELL_AREA
        )

        if sector_fraction > 0:

            inside_idx.append(idx)

    inside_idx = np.array(
        inside_idx,
        dtype=int
    )

    if len(inside_idx) == 0:

        logger.warning(
            f"Geen cellen gevonden in sector "
            f"{sector['angle_start']} - "
            f"{sector['angle_end']}"
        )

        continue

    x_inside = xs[inside_idx]
    y_inside = ys[inside_idx]

    z0_vals_all = values[inside_idx]

    mask_valid = (
        np.isfinite(z0_vals_all) &
        (z0_vals_all != MASK_VALUE)
    )
    

    n_total = len(z0_vals_all)

    n_masked = np.sum(
        ~mask_valid
    )

    pct_masked = (
        100 * n_masked / n_total
    )

    z0_vals = z0_vals_all[
        mask_valid
    ]

    x_inside = x_inside[
        mask_valid
    ]

    y_inside = y_inside[
        mask_valid
    ]

    if len(z0_vals) == 0:
        continue


    # ------------------------------------------------------------
    # AREA AVERAGING USING SUBPOLYGONS
    # ------------------------------------------------------------

    
    ring_weights = []
    ring_cd = []
    ring_results = {}
    
    sector_has_masked_in_first3 = False
    
    L = 1000

    for i_ring in range(N_RINGS):

        inner_distance = i_ring * RING_breedte_m

        outer_distance = (
            (i_ring + 1)
            * RING_breedte_m
        )

        inner_buffer = domain_poly.buffer(
            inner_distance
        )

        outer_buffer = domain_poly.buffer(
            outer_distance
        )

        ring_poly = (
            outer_buffer
            .difference(inner_buffer)
        )

        ring_poly = (
            ring_poly
            .intersection(poly)
        )

        if ring_poly.is_empty:
            continue
        # ------------------------------------------------------------
        # CHECK FOR MASKED PIXELS IN FIRST 3 RINGS
        # ------------------------------------------------------------

        if i_ring < 3:

            for idx in inside_idx:

                cell_value = values[idx]

                if (
                    not np.isfinite(cell_value)
                    or cell_value == MASK_VALUE
                ):

                    cell_poly = box(
                        xs[idx] - HALF_CELL,
                        ys[idx] - HALF_CELL,
                        xs[idx] + HALF_CELL,
                        ys[idx] + HALF_CELL
                    )

                    if (
                        ring_poly
                        .intersection(cell_poly)
                        .area > 0
                    ):

                        sector_has_masked_in_first3 = True
                        break

        fractions = []
        z0_ring_vals = []

        for i_pt in range(len(z0_vals)):

            cell_poly = box(
                x_inside[i_pt] - HALF_CELL,
                y_inside[i_pt] - HALF_CELL,
                x_inside[i_pt] + HALF_CELL,
                y_inside[i_pt] + HALF_CELL
            )

            overlap_area = (
                ring_poly
                .intersection(cell_poly)
                .area
            )

            if overlap_area <= 0:
                continue

            ring_fraction = (
                overlap_area /
                CELL_AREA
            )

            if z0_vals[i_pt] > 0:

                fractions.append(
                    ring_fraction
                )

                z0_ring_vals.append(
                    z0_vals[i_pt]
                )

        equivalent_cells = np.sum(fractions)

        if len(fractions) == 0:
            continue

        fractions = np.asarray(fractions)
        z0_ring_vals = np.asarray(z0_ring_vals)

        cd_vals = (
            KAPPA /
            np.log(
                BLENDING_HEIGHT /
                z0_ring_vals
            )
        ) ** 2

        cd_ring = np.average(
            cd_vals,
            weights=fractions
        )

        z0_ring = (
            BLENDING_HEIGHT *
            np.exp(
                -KAPPA /
                np.sqrt(cd_ring)
            )
        )

        ring_cd.append(cd_ring)
        
        ring_middelpunt = (
            inner_distance
            +
            0.5 * RING_breedte_m
        )

        weight = np.exp(
            -ring_middelpunt / L
        )

        ring_weights.append(
            weight
        )

        ring_results[
            f"z0_ring_{i_ring+1:02d}"
        ] = z0_ring

        ring_results[
            f"cd_ring_{i_ring+1:02d}"
        ] = cd_ring

        ring_results[
            f"n_ring_{i_ring+1:02d}"
        ] = equivalent_cells
        
        ring_results[
            f"weight_ring_{i_ring+1:02d}"
        ] = weight

    total_ring_cells = 0

    for i_ring in range(N_RINGS):

        total_ring_cells += ring_results.get(
            f"n_ring_{i_ring+1:02d}",
            0
        )

    logger.info(
        f"Sector {sector['angle_middelpunt']:.0f}°: "
        f"{total_ring_cells} equivalente cellen, "
        f"{len(z0_vals)} geldige LGN-cellen"
    )

    if len(ring_cd) > 0:

        cd_eff = np.average(
            ring_cd,
            weights=ring_weights
        )

        z0_mason = (
            BLENDING_HEIGHT *
            np.exp(
                -KAPPA /
                np.sqrt(cd_eff)
            )
        )

    else:

        z0_mason = np.nan
        
    for i_ring in range(N_RINGS):

        ring_results.setdefault(
            f"z0_ring_{i_ring+1:02d}",
            np.nan
        )

        ring_results.setdefault(
            f"cd_ring_{i_ring+1:02d}",
            np.nan
        )

        ring_results.setdefault(
            f"n_ring_{i_ring+1:02d}",
            0.0
        )

        ring_results.setdefault(
            f"weight_ring_{i_ring+1:02d}",
            np.nan
        )

        

    logger.info(
        f"Sector "
        f"{sector['angle_start']:>4.0f} -> "
        f"{sector['angle_end']:>4.0f} : "
        f"{n_total:>7} cellen | "
        f"gemaskeerd={pct_masked:>5.1f}% | "
        f"z0_eff={z0_mason:.3f}"
    )

    row = {

        "angle_middelpunt":
            sector["angle_middelpunt"],

        "angle_start": sector["angle_start"],

        "angle_end": sector["angle_end"],

#        "n_cells_total": n_total,

#        "n_cells_masked": n_masked,

        "pct_masked":
            pct_masked,

#        "n_cells_valid": len(z0_vals),

        "z0_effective":
            z0_mason
    }

    row.update(
        ring_results
    )

    results.append(
        row
    )

    xp, yp = poly.exterior.xy

    highlight_label = sector_has_masked_in_first3

    if toon_sectoren:

        ax.plot(
            [sector["x_left"], sector["ox_left"]],
            [sector["y_left"], sector["oy_left"]],
            color="black",
            linewidth=0.5
        )

        ax.plot(
            [sector["x_right"], sector["ox_right"]],
            [sector["y_right"], sector["oy_right"]],
            color="black",
            linewidth=0.5
        )
    label_ring = 1  # tweede ring

    inner_buffer = domain_poly.buffer(
        label_ring * RING_breedte_m
    )

    outer_buffer = domain_poly.buffer(
        (label_ring + 1) * RING_breedte_m
    )

    label_poly = (
        outer_buffer
        .difference(inner_buffer)
    )

    label_poly = (
        label_poly
        .intersection(poly)
    )

    if label_poly.is_empty:
        continue

    label_point = label_poly.centroid

    if not label_poly.contains(label_point):
        label_point = label_poly.representative_point()

    x_label = label_point.x
    y_label = label_point.y


    if toon_sectorlabels:

        ax.text(
            x_label,
            y_label,
            f"{format_z0(z0_mason)}",
            fontsize=6,
            ha="center",
            va="center",
            bbox=dict(
                facecolor=(
                    "red"
                    if highlight_label
                    else "white"
                ),
                alpha=0.7,
                edgecolor="black",
                linewidth=0,
                pad=0.1
            )
        )
# ------------------------------------------------------------
# DRAW FETCH SUBDIVISIONS
# ------------------------------------------------------------
if toon_sectoren:

    for i in range(1, N_RINGS):

        boundary = domain_poly.buffer(
            i * RING_breedte_m
        )

        xp, yp = boundary.exterior.xy

        ax.plot(
            xp,
            yp,
            color="black",
            linewidth=0.5,
            alpha=0.2
        )

# ============================================================
# DOMAIN
# ============================================================
xp, yp = domain_poly.exterior.xy
ax.plot(
    xp,
    yp,
    color="black",
    linewidth=1,
    zorder=20,
    label="Domain"
)

# ============================================================
# PLAN LOCATION
# ============================================================

px, py = plan_x, plan_y

ax.scatter(
    px,
    py,
    color="white",
    linewidth=0.8,
    edgecolors= "black",
    s=15,
#    label="Plan location"
)
ax.set_aspect("equal")
ax.set_xlabel("RD X (m)")
ax.set_ylabel("RD Y (m)")

#ax.legend(
#    loc="middelpunt left",
#    bbox_to_anchor=(1.1, 0.5),
#    frameon=False,
#    fontsize=10
#)

ax.set_aspect("equal")
ax.set_xlim(
    plot_minx,
    plot_maxx
)

ax.set_ylim(
    plot_miny,
    plot_maxy
)



# ============================================================
# SAVE FIGURE
# ============================================================

plot_path = os.path.join(
    OUTPUT_DIR,
    "ruwheid_sectors.png"
)

plt.setp(
    ax.get_xticklabels(),
    rotation=90
)
plt.tight_layout()

plt.savefig(
    plot_path,
    dpi=220
)

logger.info(
    f"Afbeelding opgeslagen: {plot_path}"
)

#plt.show()

# ============================================================
# SAVE RESULTS
# ============================================================

if len(results) == 0:

    logger.warning(
        "Er zijn geen geldige "
        "ruwheidsresultaten berekend."
    )

    logger.warning(
        "Voor alle sectoren wordt de standaardwaarde "
        "z0 = 0,0 toegepast."
    )

    results_df = create_default_results(
        sectors
    )

else:

    results_df = pd.DataFrame(results)

results_csv = os.path.join(
    OUTPUT_DIR,
    "ruwheidslengte_eff_debug.csv"
)

results_df.to_csv(
    results_csv,
    index=False
)

# ============================================================
# EXPORT VEREENVOUDIGDE RUWHEIDSTABEL
# ============================================================

ruwheid_csv = os.path.join(
    OUTPUT_DIR,
    "ruwheidslengte_eff.csv"
)
(
    results_df[
        [
            "angle_middelpunt",
            "z0_effective",
            "pct_masked"
        ]
    ]
    .rename(columns={
        "angle_middelpunt": "Windrichting [graden]",
        "z0_effective": "Effectieve ruwheidslengte [m]",
        "pct_masked": "Ontbrekende gegevens [%]"
    })
    .assign(
        **{
            "Effectieve ruwheidslengte [m]":
                lambda df: df["Effectieve ruwheidslengte [m]"].apply(
                    format_z0
                ),
            "Ontbrekende gegevens [%]":
                lambda df: df["Ontbrekende gegevens [%]"].round(2)
        }
    )
    .to_csv(
        ruwheid_csv,
        index=False
    )
)

logger.info(
    f"Vereenvoudigde ruwheidstabel opgeslagen: {ruwheid_csv}"
)

logger.info(
    f"Resultaten opgeslagen: {results_csv}"
)

logger.info("Resultaten:")

logger.info(results_df)