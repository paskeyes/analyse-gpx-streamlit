import folium
from folium import PolyLine
import pandas as pd

def color_by_pct(pct):
    """
    Retourne une couleur en fonction de la pente (pour GPX & FIT)
    """
    if pct < -5:
        return "darkgreen"
    if -5 <= pct < -1:
        return "lightgreen"
    if -1 <= pct <= 1:
        return "blue"
    if 1 < pct <= 5:
        return "orange"
    return "red"


def build_map(profile_df):
    """
    Construit une carte Folium avec le tracé coloré par pente.
    profile_df doit contenir : lat, lon, alt, dist_km
    """

    # Si le profil est vide → carte par défaut
    if profile_df.empty:
        return folium.Map(location=[44.84, -0.58], zoom_start=12)

    # Assurer que profil_df soit trié par distance
    profile_df = profile_df.sort_values("dist_km")

    # Centre de la carte = premier point
    lat0 = profile_df["lat"].iloc[0]
    lon0 = profile_df["lon"].iloc[0]

    m = folium.Map(location=[lat0, lon0], zoom_start=13)

    # Construction du tracé segment par segment
    for i in range(1, len(profile_df)):
        p1 = profile_df.iloc[i-1]
        p2 = profile_df.iloc[i]

        # Gestion altitudes manquantes
        alt1 = p1["alt"]
        alt2 = p2["alt"]

        if alt1 is None or alt2 is None:
            dalt = 0
        else:
            dalt = alt2 - alt1
            # micro-bruit altitude filtré
            if abs(dalt) < 1:
                dalt = 0

        # Distance horizontale en degrés → approx distance locale pour pente
        dh = ((p2["lat"] - p1["lat"])**2 + (p2["lon"] - p1["lon"])**2)**0.5
        pct = (dalt / dh) if dh > 0 else 0
        pct *= 10000  # ajustement pour convertir approximativement en % visuel

        color = color_by_pct(pct)

        PolyLine(
            locations=[
                [p1["lat"], p1["lon"]],
                [p2["lat"], p2["lon"]],
            ],
            color=color,
            weight=4,
            opacity=0.95
        ).add_to(m)

    # Ajustement automatique du zoom (bounds)
    latitudes = profile_df["lat"].tolist()
    longitudes = profile_df["lon"].tolist()

    m.fit_bounds([
        [min(latitudes), min(longitudes)],
        [max(latitudes), max(longitudes)]
    ])

    return m
