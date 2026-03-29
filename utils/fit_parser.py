import math
import numpy as np
import pandas as pd
from fitparse import FitFile
from scipy.signal import savgol_filter


# ----------------------------------------------------------
# Classification unifiée GPX/FIT
# ----------------------------------------------------------
def classify(pct):
    if -1 <= pct <= 1:
        return "plat"
    if 1 < pct <= 5:
        return "petite_montee"
    if pct > 5:
        return "forte_montee"
    if -5 <= pct < -1:
        return "petite_descente"
    if pct < -5:
        return "forte_descente"
    return "plat"


# ----------------------------------------------------------
# Distance haversine
# ----------------------------------------------------------
def haversine(lat1, lon1, lat2, lon2):
    R = 6371000
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlam = math.radians(lon2 - lon1)
    a = math.sin(dphi/2)**2 + math.cos(phi1)*math.cos(phi2)*math.sin(dlam/2)**2
    return 2 * R * math.atan2(math.sqrt(a), math.sqrt(1 - a))


# ----------------------------------------------------------
# Fix altitude : interpolation + léger SG (UNIQUEMENT 9 pts)
# ----------------------------------------------------------
def fix_altitudes(raw_alts):

    alts = pd.Series(raw_alts, dtype=float)
    alts.replace({None: np.nan}, inplace=True)
    alts = alts.interpolate(method="linear", limit_direction="both")

    # Anti-outlier léger
    diffs = alts.diff().abs()
    alts[diffs > 8] = np.nan
    alts = alts.interpolate(method="linear", limit_direction="both")

    # Lissage FIT : fenêtre minimale (9)
    if len(alts) >= 9:
        alts = savgol_filter(alts, window_length=9, polyorder=2)

    return alts.tolist()


# ----------------------------------------------------------
# PARSER FIT — Version finale stable
# ----------------------------------------------------------
def parse_fit_and_compute(uploaded_file):

    fit = FitFile(uploaded_file)

    raw_points = []

    # Extraction brute FIT
    for record in fit.get_messages("record"):
        data = record.get_values()

        if "position_lat" not in data or "position_long" not in data:
            continue

        lat = data["position_lat"] * (180 / 2**31)
        lon = data["position_long"] * (180 / 2**31)

        alt = data.get("enhanced_altitude", data.get("altitude", None))
        ts = data.get("timestamp", None)

        raw_points.append({
            "lat": lat,
            "lon": lon,
            "alt": alt,
            "ts": ts,
            "cad": data.get("cadence", None),
            "fc": data.get("heart_rate", None),
            "pwr": data.get("power", None),
            "bal": data.get("left_right_balance_100", None)
        })

    if len(raw_points) < 2:
        return pd.DataFrame(), pd.DataFrame()

    # -----------------------------
    # Fix altitude
    # -----------------------------
    fixed_alts = fix_altitudes([p["alt"] for p in raw_points])
    for i, p in enumerate(raw_points):
        p["alt"] = fixed_alts[i]

    # accumulateurs
    stats = {k: {"dist":0,"d+":0,"d-":0,"time":0,
                 "cad":[],"fc":[],"pwr":[],"bal":[]} 
             for k in ["plat","petite_montee","forte_montee",
                       "petite_descente","forte_descente"]}

    profile = []
    total_dist = 0
    prev = raw_points[0]

    # -----------------------------
    # Boucle point-à-point
    # -----------------------------
    for pt in raw_points[1:]:

        # Distance FIT 1 Hz → très petite
        dist = haversine(prev["lat"], prev["lon"], pt["lat"], pt["lon"])
        if dist < 0.1:
            prev = pt
            continue

        dalt = pt["alt"] - prev["alt"]

        # Seuil idéal FIT
        if abs(dalt) < 0.05:
            dalt = 0

        total_dist += dist

        # Temps
        if pt["ts"] and prev["ts"]:
            dt = (pt["ts"] - prev["ts"]).total_seconds()
        else:
            dt = 0

        if dt <= 0:
            prev = pt
            continue

        # Pente % FIT
        pct = (dalt / dist * 100) if dist > 0 else 0
        cat = classify(pct)

        # Accumulation
        stats[cat]["dist"] += dist
        stats[cat]["time"] += dt

        if dalt > 0:
            stats[cat]["d+"] += dalt
        elif dalt < 0:
            stats[cat]["d-"] += dalt

        if pt["cad"] is not None: stats[cat]["cad"].append(pt["cad"])
        if pt["fc"] is not None:  stats[cat]["fc"].append(pt["fc"])
        if pt["pwr"] is not None: stats[cat]["pwr"].append(pt["pwr"])
        if pt["bal"] is not None: stats[cat]["bal"].append(pt["bal"]/100)

        # Profil carte
        profile.append({
            "dist_km": total_dist / 1000,
            "alt": pt["alt"],
            "lat": pt["lat"],
            "lon": pt["lon"],
            "pct": pct
        })

        prev = pt

    # -----------------------------
    # Construction DF final
    # -----------------------------
    rows = []
    def avg(v): return sum(v)/len(v) if v else 0

    for k, v in stats.items():

        time_h = v["time"]/3600 if v["time"] else 0
        vit = (v["dist"]/1000)/time_h if time_h > 0 else 0

        vam = v["d+"] / time_h if k in ("petite_montee","forte_montee") and time_h > 0 else 0

        rows.append({
            "Type": k,
            "Distance_km": v["dist"]/1000,
            "D+": v["d+"],
            "D-": v["d-"],
            "Temps_h": time_h,
            "Vitesse_kmh": round(vit, 2),
            "VAM_mh": round(vam, 1),
            "Cadence": int(avg(v["cad"])),
            "FC": int(avg(v["fc"])),
            "Puissance": int(avg(v["pwr"])),
            "Equilibre_DG": round(avg(v["bal"]),1)
        })

    df = pd.DataFrame(rows)
    profile_df = pd.DataFrame(profile)

    return df, profile_df
