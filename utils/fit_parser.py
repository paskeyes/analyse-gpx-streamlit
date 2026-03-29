import math
import numpy as np
import pandas as pd
from fitparse import FitFile
from scipy.signal import savgol_filter

# ----------------------------------------------------------
# Classification identique au GPX (bornes non ambiguës)
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
# Distance haversine en mètres
# ----------------------------------------------------------
def haversine(lat1, lon1, lat2, lon2):
    R = 6371000
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlam = math.radians(lon2 - lon1)
    a = math.sin(dphi/2)**2 + math.cos(phi1)*math.cos(phi2)*math.sin(dlam/2)**2
    return 2 * R * math.atan2(math.sqrt(a), math.sqrt(1 - a))

# ----------------------------------------------------------
# Correction altimétrique : interpolation + lissage + anti‐outliers
# ----------------------------------------------------------
def fix_altitudes(raw_alts):

    alts = pd.Series(raw_alts, dtype="float")

    # Remplacer None par NaN
    alts.replace({None: np.nan}, inplace=True)

    # Interpolation des trous
    alts = alts.interpolate(method="linear", limit_direction="both")

    # Suppression des outliers (> 20 m entre deux points)
    diffs = alts.diff().abs()
    outliers = diffs > 20
    alts[outliers] = np.nan
    alts = alts.interpolate(method="linear", limit_direction="both")

    # Lisser (FIT = très précis → fenêtre petite)
    if len(alts) >= 9:
        alts = savgol_filter(alts, window_length=9, polyorder=2)

    return alts.tolist()

# ----------------------------------------------------------
# PARSER FIT — VERSION FINALE
# ----------------------------------------------------------
def parse_fit_and_compute(uploaded_file):

    fit = FitFile(uploaded_file)

    # ------------------------------------------------------
    # Extraction brute des points (lat/lon/alt/time)
    # ------------------------------------------------------
    raw_points = []

    for record in fit.get_messages("record"):
        data = record.get_values()

        if "position_lat" not in data or "position_long" not in data:
            continue

        lat = data["position_lat"] * (180.0 / 2**31)
        lon = data["position_long"] * (180.0 / 2**31)
        
        alt = data.get("enhanced_altitude", None)
        if alt is None:
            alt = data.get("altitude", None)
        
        ts = data.get("timestamp", None)

        cad = data.get("cadence", None)
        fc = data.get("heart_rate", None)
        pwr = data.get("power", None)

        bal_raw = data.get("left_right_balance_100", None)
        if bal_raw is None:
            bal_raw = data.get("left_right_balance", None)

        balance = None
        if bal_raw is not None:
            try:
                balance = float(bal_raw) / 100.0
            except:
                balance = None

        raw_points.append({
            "lat": lat,
            "lon": lon,
            "alt": alt,
            "ts": ts,
            "cad": cad,
            "fc": fc,
            "pwr": pwr,
            "balance": balance
        })

    if len(raw_points) < 2:
        return pd.DataFrame(), pd.DataFrame()

    # ------------------------------------------------------
    # Fix altitudes (lissage identique GPX)
    # ------------------------------------------------------
    fixed_alts = fix_altitudes([p["alt"] for p in raw_points])
    for i in range(len(raw_points)):
        raw_points[i]["alt"] = fixed_alts[i]

    # ------------------------------------------------------
    # Accumulateurs
    # ------------------------------------------------------
    stats = {
        "plat": {"dist":0,"d+":0,"d-":0,"time":0,"cad":[],"fc":[],"pwr":[],"bal":[]},
        "petite_montee": {"dist":0,"d+":0,"d-":0,"time":0,"cad":[],"fc":[],"pwr":[],"bal":[]},
        "forte_montee": {"dist":0,"d+":0,"d-":0,"time":0,"cad":[],"fc":[],"pwr":[],"bal":[]},
        "petite_descente": {"dist":0,"d+":0,"d-":0,"time":0,"cad":[],"fc":[],"pwr":[],"bal":[]},
        "forte_descente": {"dist":0,"d+":0,"d-":0,"time":0,"cad":[],"fc":[],"pwr":[],"bal":[]}
    }

    profile = []
    total_dist = 0

    # ------------------------------------------------------
    # Parcours point-à-point
    # ------------------------------------------------------
    prev = raw_points[0]

    for pt in raw_points[1:]:

        dist = haversine(prev["lat"], prev["lon"], pt["lat"], pt["lon"])

        # Filtrage micro‐distance
        if dist < 0.05:
            prev = pt
            continue

        # Variation altitude
        dalt = pt["alt"] - prev["alt"]
        if abs(dalt) < 0.1:   # FIT = pas de bruit >0.3 m → seuil idéal 0.5
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

        # Pente %
        pct = (dalt / dist * 100) if dist > 0 else 0
        cat = classify(pct)

        # Accumulation
        stats[cat]["dist"] += dist
        stats[cat]["time"] += dt

        if cat != "plat":
            if dalt > 0:
                stats[cat]["d+"] += dalt
            else:
                stats[cat]["d-"] += dalt

        # Physio
        if pt["cad"] is not None:
            stats[cat]["cad"].append(pt["cad"])
        if pt["fc"] is not None:
            stats[cat]["fc"].append(pt["fc"])
        if pt["pwr"] is not None:
            stats[cat]["pwr"].append(pt["pwr"])
        if pt["balance"] is not None:
            stats[cat]["bal"].append(pt["balance"])

        # Profil pour carte / altimétrie
        profile.append({
            "dist_km": total_dist / 1000,
            "alt": pt["alt"],
            "lat": pt["lat"],
            "lon": pt["lon"]
        })

        prev = pt

    # ------------------------------------------------------
    # Construction DataFrame final
    # ------------------------------------------------------
    rows = []
    for k, v in stats.items():

        time_h = v["time"]/3600 if v["time"] > 0 else 0

        # vitesse
        if time_h > 0:
            v_kmh = (v["dist"]/1000) / time_h
        else:
            v_kmh = 0

        # VAM
        if k in ("petite_montee","forte_montee") and time_h > 0:
            vam = v["d+"] / time_h
        else:
            vam = 0

        mean = lambda L: sum(L)/len(L) if L else 0

        rows.append({
            "Type": k,
            "Distance_km": v["dist"]/1000,
            "D+": v["d+"],
            "D-": v["d-"],
            "Temps_h": time_h,
            "Vitesse_kmh": round(v_kmh, 2),
            "VAM_mh": round(vam, 1),
            "Cadence": int(mean(v["cad"])),
            "FC": int(mean(v["fc"])),
            "Puissance": int(mean(v["pwr"])),
            "Equilibre_DG": round(mean(v["bal"]),1)
        })

    df = pd.DataFrame(rows)
    profile_df = pd.DataFrame(profile)

    return df, profile_df
