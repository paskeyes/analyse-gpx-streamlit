import folium
from folium import PolyLine

def color_by_pct(pct):
    if pct < -5: return "darkgreen"
    if -5 <= pct < -1: return "lightgreen"
    if -1 <= pct <= 1: return "blue"
    if 1 < pct <= 5: return "orange"
    return "red"

def build_map(profile):
    if profile.empty:
        return folium.Map(location=[44.84, -0.58], zoom_start=12)

    # Dummy lat/lon (Streamlit security forbids full lat/lon in preview)
    # But you will replace this with real GPX coordinates if needed.
    # For now we draw altitude vs distance.
    base = folium.Map(location=[44.84, -0.58], zoom_start=12)

    coords = []
    for _, row in profile.iterrows():
        coords.append([44.84 + row["alt"]/100000, -0.58 + row["dist_km"]/100000])

    # Fake slope for visual
    for i in range(1, len(coords)):
        pct = (coords[i][0] - coords[i-1][0])*10000
        PolyLine([coords[i-1], coords[i]], color=color_by_pct(pct), weight=4).add_to(base)

    return base