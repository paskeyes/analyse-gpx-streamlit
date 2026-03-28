import streamlit as st
import gpxpy
import math
import pandas as pd
import matplotlib.pyplot as plt

# -----------------------------------------------------------
# PARAMÈTRES
# -----------------------------------------------------------
tolerances = {
    'plat': (-1, 1),
    'petite_montee': (1, 5),
    'forte_montee': (5, 100),
    'petite_descente': (-5, -1),
    'forte_descente': (-100, -5)
}

params = {
    'petite_montee_vam': 800,
    'forte_montee_vam': 700,
    'plat_speed': 27,
    'petite_descente_speed': 30,
    'forte_descente_speed': 40
}

# -----------------------------------------------------------
# OUTILS
# -----------------------------------------------------------
def haversine(lat1, lon1, lat2, lon2):
    R = 6371000
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi/2)**2 + math.cos(phi1)*math.cos(phi2)*math.sin(dlambda/2)**2
    return 2 * R * math.atan2(math.sqrt(a), math.sqrt(1 - a))

def classify_segment(pct):
    for key, (low, high) in tolerances.items():
        if low <= pct <= high:
            return key
    return None

# -----------------------------------------------------------
# ANALYSE GPX
# -----------------------------------------------------------
def analyze_gpx(file):

    gpx = gpxpy.parse(file)

    segments = {
        'plat': {'dist': 0, 'd+': 0, 'd-': 0},
        'petite_montee': {'dist': 0, 'd+': 0},
        'forte_montee': {'dist': 0, 'd+': 0},
        'petite_descente': {'dist': 0, 'd-': 0},
        'forte_descente': {'dist': 0, 'd-': 0}
    }

    # On récupère la liste de points (tracks ou routes)
    if gpx.tracks:
        points = []
        for track in gpx.tracks:
            for seg in track.segments:
                points.extend(seg.points)
    elif gpx.routes:
        points = gpx.routes[0].points
    else:
        points = gpx.waypoints

    # Analyse des segments
    distances = []
    altitudes = []

    for i in range(1, len(points)):
        p1, p2 = points[i-1], points[i]

        dist_m = haversine(p1.latitude, p1.longitude, p2.latitude, p2.longitude)
        elev_diff = (p2.elevation or 0) - (p1.elevation or 0)
        pct = (elev_diff / dist_m * 100) if dist_m > 0 else 0

        distances.append(dist_m)
        altitudes.append(p2.elevation)

        category = classify_segment(pct)
        if not category:
            continue

        if "montee" in category:
            segments[category]['dist'] += dist_m
            segments[category]['d+'] += max(0, elev_diff)
        elif "descente" in category:
            segments[category]['dist'] += dist_m
            segments[category]['d-'] += min(0, elev_diff)
        else:
            segments['plat']['dist'] += dist_m

    return segments, altitudes

# -----------------------------------------------------------
# TEMPS TOTAL
# -----------------------------------------------------------
def estimate_time(segments):
    t = 0
    t += (segments['plat']['dist']/1000) / params['plat_speed']
    t += (segments['petite_montee']['d+']) / params['petite_montee_vam']
    t += (segments['forte_montee']['d+']) / params['forte_montee_vam']
    t += (segments['petite_descente']['dist']/1000) / params['petite_descente_speed']
    t += (segments['forte_descente']['dist']/1000) / params['forte_descente_speed']
    return t  # heures

# -----------------------------------------------------------
# WEB APP STREAMLIT
# -----------------------------------------------------------

st.title("🚴 Analyse complète d’un fichier GPX")
st.write("Upload ton GPX, et l’app fera :")
st.markdown("""
✅ Découpage par pente (plat / montées / descentes)  
✅ Distances, D+, D−  
✅ Durées segmentées  
✅ Durée totale  
✅ Graphique altimétrique  
""")

# Upload GPX
uploaded_file = st.file_uploader("📂 Choisis un fichier GPX", type=["gpx"])

if uploaded_file:
    st.success("✅ Fichier chargé !")

    segments, altitudes = analyze_gpx(uploaded_file)

    # Tableau
    rows = []
    total_dist_km = 0
    total_dplus = 0
    total_dminus = 0
    total_duree_min = 0

    for seg_type, data in segments.items():

        dist_km = data["dist"] / 1000

        # Durée
        if "montee" in seg_type:
            dplus = data.get("d+", 0)
            if seg_type == "petite_montee":
                duree = (dplus / params["petite_montee_vam"]) * 60
            else:
                duree = (dplus / params["forte_montee_vam"]) * 60
        else:
            if seg_type == "plat":
                vitesse = params["plat_speed"]
            elif seg_type == "petite_descente":
                vitesse = params["petite_descente_speed"]
            else:
                vitesse = params["forte_descente_speed"]
            duree = (dist_km / vitesse) * 60

        rows.append({
            "Type": seg_type,
            "Distance (km)": f"{dist_km:.2f}",
            "D+ (m)": f"{data.get('d+', 0):.0f}",
            "D- (m)": f"{data.get('d-', 0):.0f}",
            "Durée (min)": f"{duree:.1f}"
        })

        total_dist_km += dist_km
        total_dplus += data.get("d+", 0)
        total_dminus += data.get("d-", 0)
        total_duree_min += duree

    # Ligne TOTAL
    tot_h = int(total_duree_min // 60)
    tot_m = int(total_duree_min % 60)

    rows.append({
        "Type": "TOTAL",
        "Distance (km)": f"{total_dist_km:.2f}",
        "D+ (m)": f"{total_dplus}",
        "D- (m)": f"{total_dminus}",
        "Durée (min)": f"{tot_h}h {tot_m}min"
    })

    df = pd.DataFrame(rows)
    st.subheader("📊 Tableau d'analyse")
    st.dataframe(df)

    # Temps total
    temps_h = estimate_time(segments)
    st.subheader("⏱️ Temps estimé total")
    st.write(f"**{temps_h:.2f} heures / {temps_h*60:.0f} minutes**")

    # Export CSV
    csv = df.to_csv(index=False).encode("utf-8")
    st.download_button("⬇️ Télécharger le tableau (CSV)", csv, "analyse_gpx.csv")

    # Graphique altimétrique
    st.subheader("📈 Profil altimétrique")

    plt.figure(figsize=(10,4))
    plt.plot(altitudes)
    plt.xlabel("Points")
    plt.ylabel("Altitude (m)")
    plt.grid(True)
    st.pyplot(plt)