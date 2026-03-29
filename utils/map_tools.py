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
    Construit une carte Folium.
    profile_df DOIT contenir :
      - lat
      - lon
      - dist_km
      - pct (obligatoire pour la coloration)
    """

    # Si pas de points → carte vide
    if profile_df.empty:
        return folium.Map(location=[44.84, -0.58], zoom_start=12)

    # Tri distance
    profile_df = profile_df.sort_values("dist_km")

    # Centre carte
    lat0 = profile_df["lat"].iloc[0]
    lon0 = profile_df["lon"].iloc[0]
    m = folium.Map(location=[lat0, lon0], zoom_start=13)

    # Vérifier si la pente est fournie
    use_pct = "pct" in profile_df.columns

    # Tracé segment par segment
    for i in range(1, len(profile_df)):
        p1 = profile_df.iloc[i - 1]
        p2 = profile_df.iloc[i]

        # ✅ NE PAS recalculer la pente ici !
        pct = p2["pct"] if use_pct else 0

        color = color_by_pct(pct)

        PolyLine(
            locations=[[p1["lat"], p1["lon"]], [p2["lat"], p2["lon"]]],
            color=color,
            weight=5,
            opacity=0.9
        ).add_to(m)

    # Ajuster zoom automatiquement
    m.fit_bounds([
        [profile_df["lat"].min(), profile_df["lon"].min()],
        [profile_df["lat"].max(), profile_df["lon"].max()]
    ])

    return m
