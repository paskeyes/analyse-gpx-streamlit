import streamlit as st
import gpxpy
import math
import pandas as pd
import matplotlib.pyplot as plt
from tabulate import tabulate
import io

# --- Classification rules ---
tolerances = {
    'plat': (-1, 1),
    'petite_montee': (1, 5),
    'forte_montee': (5, 100),
    'petite_descente': (-5, -1),
    'forte_descente': (-100, -5)
}

# --- Speeds and VAMs ---
params = {
    'petite_montee_vam': 1000,
    'forte_montee_vam': 800,
    'plat_speed': 27,
    'petite_descente_speed': 30,
    'forte_descente_speed': 40
}

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

def analyze_gpx(gpx):
    segments = {
        'plat': {'dist': 0, 'd+': 0, 'd-': 0},
        'petite_montee': {'dist': 0, 'd+': 0},
        'forte_montee': {'dist': 0, 'd+': 0},
        'petite_descente': {'dist': 0, 'd-': 0},
        'forte_descente': {'dist': 0, 'd-': 0}
    }

    profile_alt = []
    profile_dist = [0]
    total_dist = 0

    for track in gpx.tracks:
        for segment in track.segments:
            points = segment.points
            for i in range(1, len(points)):
                p1, p2 = points[i-1], points[i]
                dist = haversine(p1.latitude, p1.longitude, p2.latitude, p2.longitude)
                elev_diff = (p2.elevation or 0) - (p1.elevation or 0)

                total_dist += dist
                profile_alt.append(p2.elevation)
                profile_dist.append(total_dist/1000)

                pct = (elev_diff / dist) * 100 if dist > 0 else 0
                category = classify_segment(pct)

                if category:
                    if 'montee' in category:
                        segments[category]['dist'] += dist
                        segments[category]['d+'] += max(0, elev_diff)
                    elif 'descente' in category:
                        segments[category]['dist'] += dist
                        segments[category]['d-'] += min(0, elev_diff)
                    else:
                        segments['plat']['dist'] += dist

    return segments, profile_dist, profile_alt

def estimate_time(segments):
    h = 0
    h += (segments['plat']['dist']/1000)/params['plat_speed']
    h += (segments['petite_montee']['d+']/params['petite_montee_vam'])
    h += (segments['forte_montee']['d+']/params['forte_montee_vam'])
    h += (segments['petite_descente']['dist']/1000)/params['petite_descente_speed']
    h += (segments['forte_descente']['dist']/1000)/params['forte_descente_speed']
    return h

# ----- Streamlit UI -----
st.title("Analyse GPX et Estimation du Temps")

uploaded = st.file_uploader("Importer un fichier GPX", type=["gpx"])

if uploaded:
    gpx = gpxpy.parse(uploaded)
    segments, prof_dist, prof_alt = analyze_gpx(gpx)

    df = []
    for k,v in segments.items():
        df.append([k, v['dist']/1000, v.get('d+',0), v.get('d-',0)])
    df = pd.DataFrame(df, columns=["Type", "Distance_km", "D+", "D-"])

    st.subheader("Tableau récapitulatif")
    st.dataframe(df)

    # Profile plot
    fig, ax = plt.subplots(figsize=(10,4))
    ax.plot(prof_dist, prof_alt)
    ax.set_xlabel("Distance (km)")
    ax.set_ylabel("Altitude (m)")
    st.pyplot(fig)

    # Estimated time
    h = estimate_time(segments)
    st.subheader("Temps estimé")
    st.write(f"**{h:.2f} h** soit {int(h)}h {int((h-int(h))*60)}m")

    # Export CSV
    csv = df.to_csv(index=False).encode()
    st.download_button("Télécharger résultats (CSV)", csv, "segments.csv")
