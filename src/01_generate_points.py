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
import math
import csv
import json
import os
import xml.etree.ElementTree as ET
import matplotlib.pyplot as plt
from shapely.geometry import Polygon, Point
from pyproj import Proj, Transformer
import numpy as np
import sys
import rasterio
from rasterio.mask import mask
from shapely.geometry import box, mapping

BASE_DIR = os.path.dirname(
    os.path.dirname(os.path.abspath(__file__))
)

TEMP_DIR = os.path.join(BASE_DIR, "temp")
DATA_DIR = os.path.join(BASE_DIR, "data")

# Coordinate conventions:
#
# WGS84 input/output for users (Google Maps):
#     latitude, longitude
#
# Internal pyproj transforms:
#     longitude, latitude
#
# RD:
#     x, y

plt.rcParams["font.size"] = 8

# ---------------- Logging ---------------- #
OUTPUT_DIR = TEMP_DIR
os.makedirs(OUTPUT_DIR, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(message)s"
)

logger = logging.getLogger(__name__)



# ---------- Figure settings ----------
FIG_WIDTH_CM = 8
FIG_HEIGHT_CM = 8
DPI = 220
FONT_SIZE = 10
FONT_FAMILY = "Arial"

plt.rcParams.update({
    "font.size": FONT_SIZE,
    "font.family": FONT_FAMILY,
})
# ---------------- Read input ---------------- #

INPUT_JSON = os.path.join(BASE_DIR,"invoer_parameters.json")

def read_invoer_parameters(filename=INPUT_JSON):
    with open(filename, "r") as f:
        return json.load(f)
        

# ---------------- LGN colors ---------------- #
def get_lgn_debug_colors():

    colors = {}

    # Landbouw
    for cls in [
        1, 2, 3, 4, 5, 6,
        8, 9, 10,
        23, 27, 28, 45, 46, 47,
        61, 62
    ]:
        colors[cls] = (210, 230, 80)

    # Bos
    for cls in [
        11, 12, 20, 22, 40, 43
    ]:
        colors[cls] = (0, 140, 0)

    # Water
    for cls in [
        16, 17
    ]:
        colors[cls] = (70, 140, 255)

    # Bebouwing
    for cls in [
        18, 19, 26
    ]:
        colors[cls] = (220, 30, 30)

    # Infrastructuur
    for cls in [
        25, 251, 252, 253
    ]:
        colors[cls] = (120, 120, 120)

    # Heide / duinen / open zand
    for cls in [
        30, 31, 32, 33, 34,
        35, 36, 37, 38
    ]:
        colors[cls] = (170, 120, 170)

    # Veen / moeras / riet
    for cls in [
        39, 41, 42
    ]:
        colors[cls] = (60, 180, 180)

    # Struweel
    for cls in [
        321, 322, 323,
        331, 332, 333
    ]:
        colors[cls] = (100, 180, 80)

    # Zonneparken
    colors[29] = (0, 0, 0)

    return colors

# ---------------- Wind statistics domain ------------ #
# Wind statistics domain
IX_MIN, IX_MAX = 1, 217
IY_MIN, IY_MAX = 1, 234

def validate_wind_statistics_domain(ix_f, iy_f, angle):
    if not (
        IX_MIN <= ix_f <= IX_MAX and
        IY_MIN <= iy_f <= IY_MAX
    ):
        raise ValueError(
            f"Richtingspunt bij hoek {angle:.1f}° valt buiten het "
            f"windstatistiekdomein "
            f"(ix={ix_f:.2f}, iy={iy_f:.2f}). "
            f"Geldig bereik: ix001-ix217, iy001-iy234."
        )

# ---------------- Coordinate systems ---------------- #
rd_to_wgs84 = Transformer.from_crs("EPSG:28992", "EPSG:4326", always_xy=True)
wgs84_to_rd = Transformer.from_crs("EPSG:4326", "EPSG:28992", always_xy=True)

proj_lcc = Proj(
    "+proj=lcc +lat_1=52.5 +lat_2=52.5 +lat_0=52.5 +lon_0=0 "
    "+k_0=1 +x_0=-92963.487426 +y_0=230383.739533 "
    "+a=6371220 +b=6371220"
)

# ---------------- Conversions ---------------- #
def to_rd(a, b, coord_sys):
    if coord_sys in ["EPSG:28992", "RD"]:
        return a, b

    elif coord_sys in ["WGS84", "GCS"]:
        # Google Maps input: (lat, lon)
        lat, lon = a, b

        return wgs84_to_rd.transform(lon, lat)

    else:
        raise ValueError(
            "FOUT: Niet-ondersteund coördinatenstelsel."
        )

def rd_to_lonlat(x, y):
    return rd_to_wgs84.transform(x, y)

def lonlat_to_xy(lon, lat):
    return proj_lcc(lon, lat)

def xy_to_lonlat(x, y):
    return proj_lcc(x, y, inverse=True)

def xy_to_float_indices(x, y):
    return 0.0004 * x + 1, 0.0004 * y + 1

def surrounding_indices(ix_f, iy_f):
    ix0, ix1 = math.floor(ix_f), math.ceil(ix_f)
    iy0, iy1 = math.floor(iy_f), math.ceil(iy_f)
    return [(ix0, iy0), (ix0, iy1), (ix1, iy0), (ix1, iy1)]

# ---------------- Geometry: cirkel ---------------- #
def cirkel_points_from_plan_angles(cx,cy,px,py,radius,angles):
    pts = []

    for a in angles:

        theta = math.pi/2 - math.radians(a)
        dx, dy = math.cos(theta), math.sin(theta)

        A = dx*dx + dy*dy
        B = 2*(dx*(px-cx) + dy*(py-cy))
        C = (px-cx)**2 + (py-cy)**2 - radius**2

        D = B*B - 4*A*C

        if D < 0:
            continue

        t = max(
            (-B + math.sqrt(D))/(2*A),
            (-B - math.sqrt(D))/(2*A)
        )

        x = px + t*dx
        y = py + t*dy

        pts.append((x, y, a))

    return pts

def cirkel_points_from_plan(cx, cy, px, py, radius, aantal_richtingen):


    pts = []
    angles = np.linspace(0, 360, aantal_richtingen, endpoint=False)

    for a in angles:
        theta = math.pi/2 - math.radians(a)
        dx, dy = math.cos(theta), math.sin(theta)

        A = dx*dx + dy*dy
        B = 2*(dx*(px-cx) + dy*(py-cy))
        C = (px-cx)**2 + (py-cy)**2 - radius**2

        D = B*B - 4*A*C
        if D < 0:
            continue

        t = max(
            (-B + math.sqrt(D))/(2*A),
            (-B - math.sqrt(D))/(2*A)
        )

        x = px + t*dx
        y = py + t*dy

        pts.append((x, y, a))

    return pts

# ---------------- intermediate angles for ruwheid sectores ---------------- #

def intermediate_angles(aantal_richtingen):
    step = 360.0 / aantal_richtingen
    return np.linspace(
        step / 2,
        360 - step / 2,
        aantal_richtingen
    )

# ---------------- Geometry: rechthoek ---------------- #
def get_rechthoek_frame(
    cx,
    cy,
    width,
    height,
    rotatie_graden
):

    theta = math.radians(-rotatie_graden)

    ux = math.cos(theta)
    uy = math.sin(theta)

    vx = -uy
    vy = ux

    xmin = -width / 2.0
    xmax = width / 2.0
    ymin = -height / 2.0
    ymax = height / 2.0

    local_corners = [
        (xmin, ymin),
        (xmax, ymin),
        (xmax, ymax),
        (xmin, ymax)
    ]

    rect_coords = []

    for xl, yl in local_corners:
        x = cx + xl * ux + yl * vx
        y = cy + xl * uy + yl * vy
        rect_coords.append((x, y))

    return (
        cx, cy,
        ux, uy,
        vx, vy,
        xmin, xmax,
        ymin, ymax,
        rect_coords
    )

def rechthoek_points_from_plan_angles(frame,px,py,angles):
    cx, cy, ux, uy, vx, vy, xmin, xmax, ymin, ymax, rect_coords = frame

    xt, yt = px - cx, py - cy
    px_l = xt*ux + yt*uy
    py_l = xt*vx + yt*vy

    pts = []

    for a in angles:

        theta = math.pi/2 - math.radians(a)
        dx, dy = math.cos(theta), math.sin(theta)

        dx_l = dx*ux + dy*uy
        dy_l = dx*vx + dy*vy

        candidates = []

        if abs(dx_l) > 1e-12:
            for xe in (xmin, xmax):
                t = (xe - px_l)/dx_l
                if t > 0:
                    y = py_l + t*dy_l
                    if ymin <= y <= ymax:
                        candidates.append((t, xe, y))

        if abs(dy_l) > 1e-12:
            for ye in (ymin, ymax):
                t = (ye - py_l)/dy_l
                if t > 0:
                    x = px_l + t*dx_l
                    if xmin <= x <= xmax:
                        candidates.append((t, x, ye))

        if not candidates:
            continue

        best = None
        best_dist = 1e99

        for t, xl, yl in candidates:
            xr = cx + xl*ux + yl*vx
            yr = cy + xl*uy + yl*vy

            d = math.hypot(xr - px, yr - py)

            if d < best_dist:
                best = (xr, yr)
                best_dist = d

        xr, yr = best

        pts.append((xr, yr, a))

    return pts

def rechthoek_points_from_plan(frame, px, py, aantal_richtingen):

    cx, cy, ux, uy, vx, vy, xmin, xmax, ymin, ymax, rect_coords = frame

    xt, yt = px - cx, py - cy
    px_l = xt*ux + yt*uy
    py_l = xt*vx + yt*vy


    pts = []
    angles = np.linspace(0, 360, aantal_richtingen, endpoint=False)

    for a in angles:

        theta = math.pi/2 - math.radians(a)
        dx, dy = math.cos(theta), math.sin(theta)

        dx_l = dx*ux + dy*uy
        dy_l = dx*vx + dy*vy

        candidates = []

        if abs(dx_l) > 1e-12:
            for xe in (xmin, xmax):
                t = (xe - px_l)/dx_l
                if t > 0:
                    y = py_l + t*dy_l
                    if ymin <= y <= ymax:
                        candidates.append((t, xe, y))

        if abs(dy_l) > 1e-12:
            for ye in (ymin, ymax):
                t = (ye - py_l)/dy_l
                if t > 0:
                    x = px_l + t*dx_l
                    if xmin <= x <= xmax:
                        candidates.append((t, x, ye))

        if not candidates:
            continue

        best = None
        best_dist = 1e99

        for t, xl, yl in candidates:
            xr = cx + xl*ux + yl*vx
            yr = cy + xl*uy + yl*vy
            d = math.hypot(xr - px, yr - py)

            if d < best_dist:
                best = (xr, yr)
                best_dist = d

        xr, yr = best

        pts.append((xr, yr, a))

    return pts

# ---------------- File path ---------------- #
def get_nc_path(ix,iy,base_folder=os.path.join(DATA_DIR, "NC")):
    return os.path.join(
        base_folder,
        f"ix{ix:03d}",
        f"ix{ix:03d}_iy{iy:03d}.nc"
    )

# ---------------- Plot ---------------- #
def plot_debug(
    plan_xy,
    pts,
    coord_sys,
    rect_coords=None,
    input_points=None,
    grid_cells=None,
    cirkel=None,
    toon_richtingspunten=True):

    # ---------- Figure style ----------
    FIG_SIZE_CM = 8
    DPI = 220

    plt.rcParams.update({
        "font.size": 6,
        "font.family": "sans-serif"
    })

    fig, ax = plt.subplots(figsize=(8/2.54, 8/2.54))

    # ---------------- LGN background (safe + cropped) ---------------- #
    lgn_tif = os.path.join(DATA_DIR, "LGN", "LGN2023.tif")

    if os.path.exists(lgn_tif):
        try:
            # determine extent from your data
            all_x = [plan_xy[0]] + [p[0] for p in pts]
            all_y = [plan_xy[1]] + [p[1] for p in pts]

            if rect_coords:
                all_x += [p[0] for p in rect_coords]
                all_y += [p[1] for p in rect_coords]

            xmin, xmax, ymin, ymax = get_square_extent(all_x,all_y)
            
            bbox = box(xmin, ymin, xmax, ymax)


            with rasterio.open(lgn_tif) as src:
                out_img, out_transform = mask(src, [mapping(bbox)], crop=True)

            # ✅ correct extent from raster transform
            height, width = out_img.shape[1], out_img.shape[2]

            left = out_transform.c
            top = out_transform.f
            right = left + width * out_transform.a
            bottom = top + height * out_transform.e

            lgn = out_img[0]

            style = get_lgn_debug_colors()

            rgb = np.full(
                (lgn.shape[0], lgn.shape[1], 3),
                (81,0,81),
                dtype=np.uint8
            )

            for cls, color in style.items():
                rgb[lgn == cls] = color

            ax.imshow(
                rgb,
                extent=(left, right, bottom, top),
                origin="upper"
            )

        except Exception as e:
            logger.warning(f"Plotten van LGN-achtergrond mislukt: {e}")

    # ---------------- ORIGINAL plotting (unchanged) ---------------- #

    ax.scatter(*plan_xy, c="white", edgecolors= "black", linewidth=1.5,s=30, label="Plan location")

    if toon_richtingspunten:

        xs = [p[0] for p in pts]
        ys = [p[1] for p in pts]

        ax.scatter(
            xs,
            ys,
            c="black",
            s=5,
            label="Directional wind statistics points"
        )

#    for x, y, _ in pts: ax.plot([plan_xy[0], x], [plan_xy[1], y], alpha=0.2)

    if rect_coords:
        xs = [p[0] for p in rect_coords] + [rect_coords[0][0]]
        ys = [p[1] for p in rect_coords] + [rect_coords[0][1]]
        ax.plot(xs, ys, "k-", lw=1, label="Fitted domain")

    if input_points:
        xs = [p[0] for p in input_points] + [input_points[0][0]]
        ys = [p[1] for p in input_points] + [input_points[0][1]]
        ax.plot(xs, ys, ":", color="black", label="Explicitly modeled domain")

    if grid_cells:
        gx, gy = [], []
        for (_, _, x_lcc, y_lcc) in grid_cells:
            lon, lat = xy_to_lonlat(x_lcc, y_lcc)
            xr, yr = wgs84_to_rd.transform(lon, lat)
            gx.append(xr)
            gy.append(yr)

#        ax.scatter(gx, gy, c="green", marker="x", label="nearest_dowa_point")

    if cirkel:
        cx, cy, radius = cirkel
        angles = np.linspace(0, 2*np.pi, 200)
        xs = cx + radius * np.cos(angles)
        ys = cy + radius * np.sin(angles)
        ax.plot(xs, ys, color="black", linewidth=0.5, label="Explicitly modeled domain")

    ax.set_box_aspect(1)

    
    # Show axis labels in the same coordinate system as the input JSON

    ax.set_xlim(xmin, xmax)
    ax.set_ylim(ymin, ymax)
    ax.tick_params(axis="x", labelrotation=90)
    ax.set_xlabel("RD X (m)")
    ax.set_ylabel("RD Y (m)")               
    plt.tight_layout()
    plot_path = os.path.join(TEMP_DIR, "debug_plot.png")
    plt.savefig(
    plot_path,
    dpi=DPI)

    logger.info(f"Afbeelding opgeslagen in: {plot_path}")

# --------------- Create squared buffer --------------
def get_square_extent(all_x, all_y, buffer_m=1000):

    xmin = min(all_x)
    xmax = max(all_x)
    ymin = min(all_y)
    ymax = max(all_y)

    largest_dimension = max(
        xmax - xmin,
        ymax - ymin
    )

    span = largest_dimension + 2 * buffer_m

    xmiddelpunt = (xmin + xmax) / 2
    ymiddelpunt = (ymin + ymax) / 2

    return (
        xmiddelpunt - span / 2,
        xmiddelpunt + span / 2,
        ymiddelpunt - span / 2,
        ymiddelpunt + span / 2
    )

# --------------- Check coordinates --------------

def validate_plan_inside_domain(
    px,
    py,
    domain,
    coord_sys
):
    """
    Verify that the plan location lies within the modeled domain.
    Raises ValueError if not.
    """

    plan_point = Point(px, py)

    if domain["type"] == "rechthoek":

        middelpunt_lat, middelpunt_lon = domain["middelpunt"]

        cx, cy = to_rd(
            middelpunt_lat,
            middelpunt_lon,
            coord_sys
        )

        width = domain["breedte_m"]
        height = domain["hoogte_m"]
        rotation = domain["rotatie_graden"]

        frame = get_rechthoek_frame(
            cx,
            cy,
            width,
            height,
            rotation
        )

        polygon = Polygon(frame[-1])

        inside = (
            polygon.contains(plan_point)
            or polygon.touches(plan_point)
        )

    elif domain["type"] == "cirkel":

        middelpunt_lat, middelpunt_lon = domain.get(
            "middelpunt",
            None
        )

        cx, cy = to_rd(
            middelpunt_lat,
            middelpunt_lon,
            coord_sys
        )

        radius = domain["straal_m"]

        inside = (
            math.hypot(px - cx, py - cy)
            <= radius
        )

    else:
        raise ValueError(
            f"FOUT: Onbekend domeintype: {domain['type']}"
        )

    if not inside:

        raise ValueError(
            "FOUT: Plangebied ligt buiten het gemodelleerde domein."
        )

    logger.info(
        "Plangebied ligt binnen het gemodelleerde domein."
    )

# ---------------- Main ---------------- #
def main():

    params = read_invoer_parameters()

    coord_sys = params["coordinatenstelsel"]
    plan = params["planlocatie"]
    domain = params["domein"]
    aantal_richtingen = params.get("aantal_richtingen", 12)
    
    plot_opties = params.get("plot_opties", {})
    domain_plot_opties = plot_opties.get("domain",{})
    toon_richtingspunten = domain_plot_opties.get("toon_richtingspunten",True)

    if not isinstance(aantal_richtingen, int):
        raise ValueError(
            f"FOUT: aantal_richtingen moet een geheel getal zijn, ontvangen waarde:{aantal_richtingen}."
        )

    if aantal_richtingen < 2 or aantal_richtingen > 360:
        raise ValueError(
            f"FOUT: aantal_richtingen={aantal_richtingen} is ongeldig. "
            "Toegestane waarde ligt tussen 2 en 360."
        )

    coord1, coord2 = plan

    px, py = to_rd(
        coord1,
        coord2,
        coord_sys
    )

    validate_plan_inside_domain(
        px,
        py,
        domain,
        coord_sys
    )

    grid_cells = []
    cirkel_info = None

    csv_path = os.path.join(OUTPUT_DIR, "dowa_points.csv")
    mid_csv_path = os.path.join(OUTPUT_DIR, "dowa_points_mid_angles.csv")
    with open(csv_path, "w", newline="") as f:

        writer = csv.writer(f)
        writer.writerow([
            "Type","Angle_deg","RD_X","RD_Y",
            "Lon","Lat","X_proj","Y_proj",
            "Index_X","Index_Y","FilePath"
        ])
        
        mid_angles = intermediate_angles(aantal_richtingen)

        if domain["type"] == "rechthoek":

            middelpunt_lat, middelpunt_lon = domain["middelpunt"]

            cx, cy = to_rd(
                middelpunt_lat,
                middelpunt_lon,
                coord_sys
            )

            width = domain["breedte_m"]
            height = domain["hoogte_m"]
            rotation = domain["rotatie_graden"]

            frame = get_rechthoek_frame(
                cx,
                cy,
                width,
                height,
                rotation
            )

            pts = rechthoek_points_from_plan(
                frame,
                px,
                py,
                aantal_richtingen
            )
            
            mid_pts = rechthoek_points_from_plan_angles(
                frame,
                px,
                py,
                mid_angles
            )

            rect_coords = frame[-1]
            pts_rd = None

        elif domain["type"] == "cirkel":

            middelpunt_lat, middelpunt_lon = domain.get("middelpunt", plan)
            cx, cy = to_rd(middelpunt_lat, middelpunt_lon, coord_sys)
            radius = domain["straal_m"]
            pts = cirkel_points_from_plan(cx, cy, px, py, radius, aantal_richtingen)
            mid_pts = cirkel_points_from_plan_angles(cx,cy,px,py,radius,mid_angles)
            rect_coords = None
            pts_rd = None
            cirkel_info = (cx, cy, radius)

        else:
            raise ValueError("FOUT: Onbekend domeintype")

        # ---------------- CSV + GRID ---------------- #
        for x, y, angle in pts:

            lon, lat = rd_to_lonlat(x, y)
            xp, yp = lonlat_to_xy(lon, lat)
            ix_f, iy_f = xy_to_float_indices(xp, yp)
            
            validate_wind_statistics_domain(
                ix_f,
                iy_f,
                angle
            )

            writer.writerow([
                "domain_edge_point", int(angle),
                x, y,
                lon, lat,
                xp, yp,
                ix_f, iy_f,
                None
            ])

            for ix, iy in surrounding_indices(ix_f, iy_f):

                x_lcc = (ix - 1) / 0.0004
                y_lcc = (iy - 1) / 0.0004

                grid_cells.append((ix, iy, x_lcc, y_lcc))

                writer.writerow([
                    "nearest_dowa_point", int(angle),
                    None, None,
                    None, None,
                    None, None,
                    ix, iy,
                    get_nc_path(ix, iy)
                ])

    logger.info(
        f"DOWA-punten opgeslagen naar: {csv_path}"
    )
    
    with open(mid_csv_path, "w", newline="") as f:

        writer = csv.writer(f)

        writer.writerow([
            "Angle_deg",
            "RD_X",
            "RD_Y",
            "Lon",
            "Lat",
            "X_proj",
            "Y_proj",
            "Index_X",
            "Index_Y"
        ])

        for x, y, angle in mid_pts:

            lon, lat = rd_to_lonlat(x, y)
            xp, yp = lonlat_to_xy(lon, lat)

            ix_f, iy_f = xy_to_float_indices(
                xp,
                yp
            )

            writer.writerow([
                angle,
                x,
                y,
                lon,
                lat,
                xp,
                yp,
                ix_f,
                iy_f
            ])

    logger.info(
        f"DOWA-punten voor tussenliggende hoeken opgeslagen naar: {mid_csv_path}"
    )

    plot_debug(
        (px, py),
        pts,
        coord_sys,
        rect_coords=rect_coords,
        input_points=pts_rd,
        grid_cells=grid_cells,
        cirkel=cirkel_info,
        toon_richtingspunten=toon_richtingspunten
    )

if __name__ == "__main__":
    main()