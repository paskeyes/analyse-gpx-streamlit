import math
import numpy as np
import pandas as pd
from fitparse import FitFile
from scipy.signal import savgol_filter


# ----------------------------------------------------------
# Classification unifiée GPX/FIT (bornes non ambiguës)
# ----------------------------------------------------------
def classify(pct: float):
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
# Fix altitude FIT → interpolation + filtrage + lissage léger
# ----------------------------------------------------------
def fix_altitudes(raw_alts):
    alts = pd.Series(raw_alts, dtype=float)

    # None → NaN
    alts.replace({None: np.nan}, inplace=True)

    # Interpolation trous
    alts = alts.interpolate(method="linear", limit_direction="both")

    # Anti-outliers (FIT ne fait jamais >10 m par point)
    diffs = alts.diff().abs()
    alts[diffs > 10] = np.nan
    alts = alts.interpolate(method="linear", limit_direction="both")

    # Lissage léger (pas trop fort)
    if len(alts) >= 11:
        alts = savgol_filter(alts, window_length=11, polyorder=3)

    return alts.tolist()


# ----------------------------------------------------------
# PARSER FIT — VERSION FINALE STABLE
# ----------------------------------------------------------
def parse_fit_and_compute(uploaded_file):

    fit = FitFile(uploaded_file)

    raw_points = []

    # ------------------------------------------------------
    # Extraction brute FIT
    # ------------------------------------------------------
    for record in fit.get_messages("record"):
        data = record.get_values()

        if "position_lat" not in data or "position_long" not in data:
            continue

        lat = data["position_lat"] * (180 / 2**31)
        lon = data["position_long"] * (180 / 2**31)

        # Altitude FIT fiable = enhanced_altitude
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
    # ALTITUDE FIX (très important !)
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

        # FIT sampling = 1 Hz → ignorer seulement < 0.15 m//modifié à 0.1
        if dist < 0.15:
            prev = pt
            continue

        dalt = pt["alt"] - prev["alt"]

        # seuil altitude FIT idéal
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

        # ✅ Pente FIT correcte
        pct = (dalt / dist * 100) if dist > 0 else 0

        cat = classify(pct)

        # Accumulation
        stats[cat]["dist"] += dist
        stats[cat]["time"] += dt

        if dalt > 0:
            stats[cat]["d+"] += dalt
        elif dalt < 0:
            stats[cat]["d-"] += dalt

        if pt["cad"] is not None:
            stats[cat]["cad"].append(pt["cad"])
        if pt["fc"] is not None:
            stats[cat]["fc"].append(pt["fc"])
        if pt["pwr"] is not None:
            stats[cat]["pwr"].append(pt["pwr"])
        if pt["balance"] is not None:
            stats[cat]["bal"].append(pt["balance"])

        # Profil carte
        profile.append({
            "dist_km": total_dist / 1000,
            "alt": pt["alt"],
            "lat": pt["lat"],
            "lon": pt["lon"],
            "pct": pct
        })

        prev = pt

    # ------------------------------------------------------
    # Construction DF final
    # ------------------------------------------------------
    rows = []

    def avg(L):
        return sum(L)/len(L) if L else 0

    for k, v in stats.items():

        time_h = v["time"]/3600 if v["time"] else 0

        vit = (v["dist"]/1000)/time_h if time_h > 0 else 0

        if k in ("petite_montee","forte_montee") and time_h > 0:
            vam = v["d+"] / time_h
        else:
            vam = 0

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
