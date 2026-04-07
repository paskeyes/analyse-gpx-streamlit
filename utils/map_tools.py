import folium
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
# CARTE GPX + FIT (sans recalcul de pente)
# ------------------------------
def build_map(profile_df):
    """
    Construit une carte Folium centrée automatiquement sur le tracé GPX/FIT.
    profile_df DOIT contenir :
      - lat
      - lon
      - dist_km
      - pct (optionnel pour la coloration)
    """

    # Cas vide → fallback propre
    if profile_df.empty:
        return folium.Map(location=[44.84, -0.58], zoom_start=12)

    # Tri par distance
    profile_df = profile_df.sort_values("dist_km")

    # ✅ Créer la carte sans zoom ni centre forcés
    m = folium.Map(
        tiles="OpenStreetMap",
        control_scale=True
    )

    use_pct = "pct" in profile_df.columns

    # Tracé segment par segment
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

    # ✅ Zoom automatique EXACT sur le tracé
    lat_min, lat_max = profile_df["lat"].min(), profile_df["lat"].max()
    lon_min, lon_max = profile_df["lon"].min(), profile_df["lon"].max()

    # Cas 1 seul point → zoom local
    if lat_min == lat_max and lon_min == lon_max:
        m.location = [lat_min, lon_min]
        m.zoom_start = 15
    else:
        m.fit_bounds(
            [[lat_min, lon_min], [lat_max, lon_max]],
            padding=(30, 30)  # marges confort visuelles
        )

    return m
