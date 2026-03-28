import folium
from folium import PolyLine
import numpy as np

# -----------------------------------------------------------
# COULEURS PAR PENTE (utilisées aussi dans styling.py)
# -----------------------------------------------------------
def color_by_pct(pct):
    """
    Retourne une couleur en fonction de la pente (%).
    """
    if pct < -5:
        return "#2f8f2f"      # Forte descente
    if -5 <= pct < -1:
        return "#4cd964"      # Petite descente
    if -1 <= pct <= 1:
        return "#6ec1ff"      # Plat
    if 1 < pct <= 5:
        return "#ff9f40"      # Petite montée
    return "#ff3b30"          # Forte montée

# -----------------------------------------------------------
# LÉGENDE (ajoutée manuellement au HTML du folium Map)
# -----------------------------------------------------------
def add_legend(m):
    legend_html = """
    <div style="
        position: fixed; 
        bottom: 50px; 
        left: 50px; 
        z-index: 9999; 
        background-color: white; 
        padding: 10px; 
        border: 2px solid grey; 
        border-radius: 5px;
        box-shadow: 2px 2px 5px rgba(0,0,0,0.3);
        font-size: 14px;
    ">
        <b>Légende pente (%)</b><br>
        <span style="color:#2f8f2f;">▬</span> Forte descente &lt; -5%<br>
        <span style="color:#4cd964;">▬</span> Petite descente (-5% à -1%)<br>
        <span style="color:#6ec1ff;">▬</span> Plat (-1% à +1%)<br>
        <span style="color:#ff9f40;">▬</span> Petite montée (+1% à +5%)<br>
        <span style="color:#ff3b30;">▬</span> Forte montée &gt; 5%<br>
    </div>
    """
    m.get_root().html.add_child(folium.Element(legend_html))


# -----------------------------------------------------------
# CRÉATION CARTE INTERACTIVE
# -----------------------------------------------------------
def build_map(profile_df):
    """
    Construit une carte Folium avec :
    - segments colorés selon la pente
    - zoom automatique
    - légende
    """

    if profile_df.empty:
        return folium.Map(location=[44.84, -0.58], zoom_start=12)

    # Coordonnées centrales (premier point)
    lat0 = profile_df["lat"].iloc[0]
    lon0 = profile_df["lon"].iloc[0]

    m = folium.Map(
        location=[lat0, lon0],
        zoom_start=13,
        tiles="cartodbpositron"  # Style clair et lisible
    )

    # Ensemble des points pour zoom automatique
    bounds = []

    # Tracé segment par segment
    for i in range(1, len(profile_df)):
        p1 = profile_df.iloc[i-1]
        p2 = profile_df.iloc[i]

        pct = p2["pct"]  # pente déjà calculée dans gpx_parser

        color = color_by_pct(pct)

        lat1, lon1 = p1["lat"], p1["lon"]
        lat2, lon2 = p2["lat"], p2["lon"]

        # Ajout du segment
        PolyLine(
            locations=[[lat1, lon1], [lat2, lon2]],
            color=color,
            weight=5,
            opacity=0.85
        ).add_to(m)

        bounds.append((lat1, lon1))
        bounds.append((lat2, lon2))

    # Zoom automatique sur toute la trace
    m.fit_bounds(bounds)

    # Ajout de la légende
    add_legend(m)

    return m
