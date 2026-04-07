import folium
import math
from folium import PolyLine
import pandas as pd

# ------------------------------
# Couleurs unifiées GPX + FIT
# ------------------------------
def color_by_pct(pct):
    """
    Palette unifiée pour GPX & FIT
    """
    if pct is None:
        return "#6ec1ff"  # plat par défaut

    if pct < -5:
        return "#2f8f2f"      # forte descente
    if -5 <= pct < -1:
        return "#4cd964"      # petite descente
    if -1 <= pct <= 1:
        return "#6ec1ff"      # plat
    if 1 < pct <= 5:
        return "#ff9f40"      # petite montée
    return "#ff3b30"          # forte montée


# ------------------------------
# Calcul du bon niveau de zoom
# ------------------------------
def compute_zoom(lat_min, lat_max, lon_min, lon_max, map_width_px=800):
    """
    Calcule un zoom Leaflet adapté à l'étendue du tracé.
    map_width_px : largeur estimée du conteneur (px)
    """

    # Étendue géographique
    lat_range = lat_max - lat_min
    lon_range = lon_max - lon_min

    # Sécurité
    if lat_range == 0 and lon_range == 0:
        return 15

    # Étendue retenue
    max_range = max(lat_range, lon_range)

    # Formule Leaflet / Mercator
    zoom = math.log2(360 / max_range)

    # Ajustement empirique (marges / UX)
    zoom -= 1.2

    # Clamp raisonnable
    return int(max(3, min(18, zoom)))



# ------------------------------
# CARTE GPX + FIT (sans recalcul de pente)
# ------------------------------
def build_map(profile_df):
    """
    Construit une carte Folium avec zoom calculé explicitement.
    """

    if profile_df.empty:
        return folium.Map(location=[44.84, -0.58], zoom_start=12)

    profile_df = profile_df.sort_values("dist_km")

    lat_min, lat_max = profile_df["lat"].min(), profile_df["lat"].max()
    lon_min, lon_max = profile_df["lon"].min(), profile_df["lon"].max()

    # Centre exact
    center_lat = (lat_min + lat_max) / 2
    center_lon = (lon_min + lon_max) / 2

    # ✅ Zoom calculé
    zoom_start = compute_zoom(lat_min, lat_max, lon_min, lon_max)

    # ✅ Carte créée DIRECTEMENT au bon zoom
    m = folium.Map(
        location=[center_lat, center_lon],
        zoom_start=zoom_start,
        tiles="OpenStreetMap",
        control_scale=True
    )

    use_pct = "pct" in profile_df.columns

    for i in range(1, len(profile_df)):
        p1 = profile_df.iloc[i - 1]
        p2 = profile_df.iloc[i]

        pct = p2["pct"] if use_pct else 0
        color = color_by_pct(pct)

        PolyLine(
            locations=[[p1["lat"], p1["lon"]], [p2["lat"], p2["lon"]]],
            color=color,
            weight=5,
            opacity=0.9
        ).add_to(m)

    return m
