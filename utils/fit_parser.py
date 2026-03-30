import math
import numpy as np
import pandas as pd
from fitparse import FitFile
from scipy.signal import savgol_filter


# ---------------------------------------------------------
# Classification pente
# ---------------------------------------------------------
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


# ---------------------------------------------------------
# Distance haversine
# ---------------------------------------------------------
def haversine(lat1, lon1, lat2, lon2):
    R = 6371000
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlam = math.radians(lon2 - lon1)
    a = math.sin(dphi/2)**2 + math.cos(phi1)*math.cos(phi2)*math.sin(dlam/2)**2
    return 2 * R * math.atan2(math.sqrt(a), math.sqrt(1 - a))


# ---------------------------------------------------------
# Lissage altitude FIT (optimisé pour D+ juste)
# ---------------------------------------------------------
def fix_altitudes(raw_alts):
    alts = pd.Series(raw_alts, dtype=float)
    alts.replace({None: np.nan}, inplace=True)

    alts = alts.interpolate(method="linear", limit_direction="both")

    diffs = alts.diff().abs()
    alts[diffs > 12] = np.nan
    alts = alts.interpolate(method="linear", limit_direction="both")

    # ✅ SG léger (n’écrase pas les montées)
    if len(alts) >= 5:
        alts = savgol_filter(alts, window_length=5, polyorder=2)

    return alts.tolist()


# ---------------------------------------------------------
# PARSER FIT FINAL (Option B : moving = speed>1.5 OR cadence>0)
# ---------------------------------------------------------
def parse_fit_and_compute(uploaded_file):

    fit = FitFile(uploaded_file)
    raw = []

    # Extraction brute
    for rec in fit.get_messages("record"):
        d = rec.get_values()
        if "position_lat" not in d or "position_long" not in d:
            continue

        raw.append({
            "lat": d["position_lat"]*(180/2**31),
            "lon": d["position_long"]*(180/2**31),
            "alt": d.get("enhanced_altitude", d.get("altitude", None)),
            "ts": d.get("timestamp", None),
            "speed": (d.get("speed", 0))*3.6,  # km/h
            "cad": d.get("cadence", None),
            "fc": d.get("heart_rate", None),
            "pwr": d.get("power", None),
            "bal": d.get("left_right_balance_100", None)
        })

    if len(raw) < 2:
        return pd.DataFrame(), pd.DataFrame()

    # Fix altitude
    alts = fix_altitudes([p["alt"] for p in raw])
    for i, p in enumerate(raw):
        p["alt"] = alts[i]

    # ✅ Option B : moving = speed>1.5 OR cadence>0
    for p in raw:
        p["moving"] = (p["speed"] > 1.5) or (p["cad"] and p["cad"] > 0)

    # Accumulateurs
    stats = {
        k: {"dist":0, "d+":0, "d-":0,
            "time":0, "moving_time":0,
            "cad_vals":[], "cad_dt":[],
            "fc_vals":[],  "fc_dt":[],
            "pwr_vals":[], "pwr_dt":[],
            "bal_vals":[]}
        for k in ["plat","petite_montee","forte_montee",
                  "petite_descente","forte_descente"]
    }

    profile = []
    prev = raw[0]
    total_dist = 0

    # Boucle point-à-point
    for pt in raw[1:]:

        dist = haversine(prev["lat"], prev["lon"], pt["lat"], pt["lon"])
        if dist < 0.05:
            prev = pt
            continue

        # ✅ seuil altitude optimisé : 0.10 m
        dalt = pt["alt"] - prev["alt"]
        if abs(dalt) < 0.10:
            dalt = 0

        dt = (pt["ts"] - prev["ts"]).total_seconds() if pt["ts"] and prev["ts"] else 0
        if dt <= 0:
            prev = pt
            continue

        total_dist += dist

        pct = (dalt/dist*100) if dist>0 else 0
        cat = classify(pct)

        stats[cat]["dist"] += dist
        stats[cat]["time"] += dt

        if pt["moving"]:
            stats[cat]["moving_time"] += dt

            if pt["cad"] and pt["cad"] > 0:
                stats[cat]["cad_vals"].append(pt["cad"])
                stats[cat]["cad_dt"].append(dt)

            if pt["fc"]:
                stats[cat]["fc_vals"].append(pt["fc"])
                stats[cat]["fc_dt"].append(dt)

            if pt["pwr"]:
                stats[cat]["pwr_vals"].append(pt["pwr"])
                stats[cat]["pwr_dt"].append(dt)

        if dalt > 0:
            stats[cat]["d+"] += dalt
        elif dalt < 0:
            stats[cat]["d-"] += dalt

        if pt["bal"]:
            stats[cat]["bal_vals"].append(pt["bal"]/100)

        profile.append({
            "dist_km": total_dist/1000,
            "alt": pt["alt"],
            "lat": pt["lat"],
            "lon": pt["lon"],
            "pct": pct
        })

        prev = pt

    # Construction DF final
