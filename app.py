
import streamlit as st
import gpxpy
import math
import pandas as pd
import matplotlib.pyplot as plt

# Classification rules
tolerances = {
    'plat': (-1, 1),
    'petite_montee': (1, 5),
    'forte_montee': (5, 100),
    'petite_descente': (-5, -1),
    'forte_descente': (-100, -5)
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
    segments = {k: {'dist': 0, 'd+': 0, 'd-': 0} for k in tolerances.keys()}
    prof_alt, prof_dist = [], [0]
    total_dist = 0

    for track in gpx.tracks:
        for segment in track.segments:
            points = segment.points
            for i in range(1, len(points)):
                p1, p2 = points[i-1], points[i]
                dist = haversine(p1.latitude, p1.longitude, p2.latitude, p2.longitude)
                elev_diff = (p2.elevation or 0) - (p1.elevation or 0)
                total_dist += dist

                prof_alt.append(p2.elevation)
                prof_dist.append(total_dist/1000)

                pct = (elev_diff/dist)*100 if dist>0 else 0
                cat = classify_segment(pct)
                if not cat: continue

                if 'montee' in cat:
                    segments[cat]['dist'] += dist
                    segments[cat]['d+'] += max(0, elev_diff)
                elif 'descente' in cat:
                    segments[cat]['dist'] += dist
                    segments[cat]['d-'] += min(0, elev_diff)
                else:
                    segments['plat']['dist'] += dist
    return segments, prof_dist, prof_alt

def estimate_time(segments, params):
    t = 0
    t += (segments['plat']['dist']/1000) / params['plat_speed']
    t += segments['petite_montee']['d+'] / params['petite_montee_vam']
    t += segments['forte_montee']['d+'] / params['forte_montee_vam']
    t += (segments['petite_descente']['dist']/1000) / params['petite_descente_speed']
    t += (segments['forte_descente']['dist']/1000) / params['forte_descente_speed']
    return t

st.title("Analyse GPX – Estimation du Temps")

# Editable parameters
st.sidebar.header("Paramètres vitesse / VAM")
params = {
    'petite_montee_vam': st.sidebar.number_input("VAM petite montée (m/h)", 200, 3000, 1000),
    'forte_montee_vam': st.sidebar.number_input("VAM forte montée (m/h)", 200, 3000, 800),
    'plat_speed': st.sidebar.number_input("Vitesse sur plat (km/h)", 5, 60, 27),
    'petite_descente_speed': st.sidebar.number_input("Vitesse petite descente (km/h)", 5, 80, 30),
    'forte_descente_speed': st.sidebar.number_input("Vitesse forte descente (km/h)", 5, 100, 40)
}

uploaded = st.file_uploader("Importer un GPX", type=["gpx"])

if uploaded:
    gpx = gpxpy.parse(uploaded)
    segments, d, a = analyze_gpx(gpx)

    df = pd.DataFrame([{ 'Type':k, 'Distance_km':v['dist']/1000, 'D+':v['d+'], 'D-':v['d-']} for k,v in segments.items()])
    st.subheader("Résumé des segments")
    st.dataframe(df)

    fig, ax = plt.subplots(figsize=(10,4))
    ax.plot(d,a)
    ax.set_xlabel("Distance (km)")
    ax.set_ylabel("Altitude (m)")
    st.pyplot(fig)

    t = estimate_time(segments, params)
    st.subheader("Temps estimé")
    st.write(f"{int(t)}h {int((t%1)*60)}m ({t:.2f} h)")

    st.download_button("Exporter CSV", df.to_csv(index=False).encode(), "segments.csv")
