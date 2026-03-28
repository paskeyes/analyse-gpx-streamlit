import gpxpy
import numpy as np
import pandas as pd
import math
from scipy.signal import savgol_filter

# -----------------------------------------------------------
# SEUILS DE CLASSIFICATION (pentes)
# -----------------------------------------------------------
TOL = {
    "plat": (-1, 1),
    "petite_montee": (1, 5),
    "forte_montee": (5, 999),
    "petite_descente": (-5, -1),
    "forte_descente": (-999, -5),
}

# -----------------------------------------------------------
# DISTANCE HAVERSINE (mètres)
# -----------------------------------------------------------
def haversine(lat1, lon1, lat2, lon2):
    R = 6371000
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlam = math.radians(lon2 - lon1)
    a = math.sin(dphi/2)**2 + math.cos(phi1)*math.cos(phi2)*math.sin(dlam/2)**2
    return 2 * R * math.atan2(math.sqrt(a), math.sqrt(1 - a))

# -----------------------------------------------------------
# CLASSIFICATION SELON PENTE (%)
# -----------------------------------------------------------
def classify(pct):
    for k, (lo, hi) in TOL.items():
        if lo <= pct <= hi:
            return k
    return "plat"

# -----------------------------------------------------------
# FIX ALTITUDES : interpolation + lissage + anti-outliers
# -----------------------------------------------------------
def fix_altitude_series(alts):
    alts = pd.Series(alts, dtype="float")

    # 1) Remplacer None par NaN
    alts.replace({None: np.nan}, inplace=True)

    # 2) Interpolation linéaire
    alts = alts.interpolate(method="linear", limit_direction="both")

    # 3) Anti-outliers (écarts > 25m)
    diffs = alts.diff().abs()
    mask = diffs > 25
    alts[mask] = np.nan
    alts = alts.interpolate()

    # 4) Lissage Savitzky-Golay
    if len(alts) >= 9:
        alts = savgol_filter(alts, window_length=9, polyorder=3)

    return alts.tolist()

# -----------------------------------------------------------
# PARSE GPX + CALCUL COMPLET
# -----------------------------------------------------------
def parse_gpx_and_compute(uploaded_file, params):

    gpx = gpxpy.parse(uploaded_file)

    # Récupération des points
    points = []
    if gpx.tracks:
        for track in gpx.tracks:
            for seg in track.segments:
                points.extend(seg.points)
    elif gpx.routes:
        points.extend(gpx.routes[0].points)
    elif gpx.waypoints:
        points.extend(gpx.waypoints)

    if len(points) < 2:
        return pd.DataFrame(), pd.DataFrame(), {}

    # EXTRACTION ALTITUDES POUR FIX
    raw_alts = [p.elevation for p in points]
    fixed_alts = fix_altitude_series(raw_alts)

    # RÉÉCRITURE DES ALTITUDES FIXÉES
    for i, p in enumerate(points):
        p.elevation = fixed_alts[i]

    # -----------------------------------------------------------
    # CALCUL DES SEGMENTS
    # -----------------------------------------------------------
    seg_stats = {
        k: {"dist": 0, "d+": 0, "d-": 0, "dur": 0}
        for k in TOL.keys()
    }

    profile = []
    total_dist = 0

    for i in range(1, len(points)):
        p1 = points[i-1]
        p2 = points[i]

        # Distance horizontale
        dist = haversine(p1.latitude, p1.longitude, p2.latitude, p2.longitude)
        if dist < 0.5:  # bruit GPS
            continue

        total_dist += dist

        dalt = p2.elevation - p1.elevation
        pct = (dalt / dist) * 100 if dist > 0 else 0
        cat = classify(pct)

        # Accumulation
        seg_stats[cat]["dist"] += dist
        if cat != "plat":
            if dalt > 0:
                seg_stats[cat]["d+"] += dalt
            else:
                seg_stats[cat]["d-"] += dalt

        profile.append({
            "dist_km": total_dist / 1000,
            "alt": p2.elevation,
            "lat": p2.latitude,
            "lon": p2.longitude,
            "pct": pct
        })

    # -----------------------------------------------------------
    # DURÉES (heures)
    # -----------------------------------------------------------
    for k, v in seg_stats.items():
        if k == "plat":
            v["dur"] = (v["dist"] / 1000) / params["plat_speed"]
        elif k == "petite_descente":
            v["dur"] = (v["dist"] / 1000) / params["petite_descente_speed"]
        elif k == "forte_descente":
            v["dur"] = (v["dist"] / 1000) / params["forte_descente_speed"]
        elif k == "petite_montee":
            v["dur"] = v["d+"] / params["petite_montee_vam"]
        elif k == "forte_montee":
            v["dur"] = v["d+"] / params["forte_montee_vam"]

    # -----------------------------------------------------------
    # DATAFRAME DES SEGMENTS
    # -----------------------------------------------------------
    df = pd.DataFrame([
        {
            "Type": k,
            "Distance_km": v["dist"] / 1000,
            "D+": v["d+"],
            "D-": v["d-"],
            "Durée": v["dur"],
            "Durée_raw": v["dur"]
        }
        for k, v in seg_stats.items()
    ])

    # -----------------------------------------------------------
    # RÉSUMÉ GLOBAL
    # -----------------------------------------------------------
    tot_dist = df["Distance_km"].sum()
    tot_dplus = df["D+"].sum()
    tot_dur = df["Durée"].sum()

    h = int(tot_dur)
    m = int((tot_dur - h) * 60)
    h_str = f"{h}h{m:02d}"

    profile_df = pd.DataFrame(profile)

    summary_text = (
        f"✅ Distance totale : **{tot_dist:.1f} km**  \n"
        f"✅ Dénivelé positif : **{tot_dplus:.0f} m**  \n"
        f"⏱️ Temps estimé total : **{h_str}**"
    )

    return df, profile_df, {
        "distance": tot_dist,
        "d+": tot_dplus,
        "h_str": h_str,
        "duration_h": tot_dur,
        "text": summary_text,
    }
