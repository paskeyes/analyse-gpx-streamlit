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
def compute_zoom_precise(
    lat_min, lat_max, lon_min, lon_max,
    map_width_px=900,
    padding_px=40
):
    """
    Calcul précis du zoom Leaflet adapté au tracé.
    Approche équivalente à fitBounds mais déterministe.
    """

    # Sécurité
    if lat_min == lat_max and lon_min == lon_max:
        return 15

    # Largeur réellement exploitable
    effective_width = map_width_px - 2 * padding_px
    effective_width = max(effective_width, 200)

    # Étendue géographique
    lon_range = lon_max - lon_min
    lat_range = lat_max - lat_min

    # Conversion latitude → Mercator
    def lat_to_mercator(lat):
        rad = math.radians(lat)
        return math.log(math.tan(rad / 2 + math.pi / 4))

    merc_min = lat_to_mercator(lat_min)
    merc_max = lat_to_mercator(lat_max)
    merc_range = abs(merc_max - merc_min)

    # Résolution requise (en degrés Mercator)
    max_range = max(lon_range, merc_range)

    # Zoom théorique Leaflet
    zoom = math.log2((effective_width * 360) / (max_range * 256))

    # ✅ Ajustement FIN : UX (le point clé)
    zoom -= 0.3   # ← corrige exactement le “manque de 1–2 niveaux”

    # Clamp standard Leaflet
    return int(max(3, min(18, round(zoom))))


# ------------------------------
# CARTE GPX + FIT (sans recalcul de pente)
# ------------------------------
def build_map(profile_df):
    if profile_df.empty:
        return folium.Map(location=[44.84, -0.58], zoom_start=12)

    profile_df = profile_df.sort_values("dist_km")

    lat_min, lat_max = profile_df["lat"].min(), profile_df["lat"].max()
    lon_min, lon_max = profile_df["lon"].min(), profile_df["lon"].max()

    center_lat = (lat_min + lat_max) / 2
    center_lon = (lon_min + lon_max) / 2

    zoom_start = compute_zoom_precise(
        lat_min, lat_max,
        lon_min, lon_max,
        map_width_px=900  # ← ajustable si tu connais le container
    )

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
