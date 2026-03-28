import folium
from folium import PolyLine

def color_by_pct(pct):
    if pct < -5: return "darkgreen"
    if -5 <= pct < -1: return "lightgreen"
    if -1 <= pct <= 1: return "blue"
    if 1 < pct <= 5: return "orange"
    return "red"

def build_map(profile_df):

    # Si pas de coordonnées, retourne carte vide
    if profile_df.empty:
        return folium.Map(location=[44.84, -0.58], zoom_start=12)

    # Centre de la carte = premier point
    lat0 = profile_df["lat"].iloc[0]
    lon0 = profile_df["lon"].iloc[0]

    m = folium.Map(location=[lat0, lon0], zoom_start=13)

    # Tracé segment par segment, coloré selon la pente
    for i in range(1, len(profile_df)):
        p1 = profile_df.iloc[i-1]
        p2 = profile_df.iloc[i]

        dalt = p2["alt"] - p1["alt"]
        # distance horizontale en mètres
        d = ((p2["lat"] - p1["lat"])**2 + (p2["lon"] - p1["lon"])**2)**0.5
        pct = (dalt / d)*100 if d != 0 else 0

        PolyLine(
            locations=[
                [p1["lat"], p1["lon"]],
                [p2["lat"], p2["lon"]]
            ],
            color=color_by_pct(pct),
            weight=4,
            opacity=0.9
        ).add_to(m)

    return m
