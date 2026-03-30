import math
import numpy as np
import pandas as pd
from fitparse import FitFile
from scipy.signal import savgol_filter

# ---------------------------------------
# Classification
# ---------------------------------------
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

# ---------------------------------------
# Haversine
# ---------------------------------------
def haversine(lat1, lon1, lat2, lon2):
    R = 6371000
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlam = math.radians(lon2 - lon1)
    a = math.sin(dphi/2)**2 + math.cos(phi1)*math.cos(phi2)*math.sin(dlam/2)**2
    return 2 * R * math.atan2(math.sqrt(a), math.sqrt(1 - a))

# ---------------------------------------
# Lissage altitude
# ---------------------------------------
def fix_altitudes(raw_alts):
    alts = pd.Series(raw_alts, dtype=float)
    alts.replace({None: np.nan}, inplace=True)
    alts = alts.interpolate(method="linear", limit_direction="both")
    diffs = alts.diff().abs()
    alts[diffs > 8] = np.nan
    alts = alts.interpolate(method="linear", limit_direction="both")
    if len(alts) >= 9:
        alts = savgol_filter(alts, window_length=9, polyorder=2)
    return alts.tolist()

# ---------------------------------------
# FIT PARSER FINAL
# ---------------------------------------
def parse_fit_and_compute(uploaded_file):

    fit = FitFile(uploaded_file)
    raw = []

    # Extraction
    for rec in fit.get_messages("record"):
        d = rec.get_values()
        if "position_lat" not in d or "position_long" not in d:
            continue

        lat = d["position_lat"] * (180 / 2**31)
        lon = d["position_long"] * (180 / 2**31)

        alt = d.get("enhanced_altitude", d.get("altitude", None))
        ts = d.get("timestamp", None)
        spd = d.get("speed", 0)  # m/s -> km/h

        raw.append({
            "lat": lat,
            "lon": lon,
            "alt": alt,
            "ts": ts,
            "speed": spd * 3.6,
            "cad": d.get("cadence", None),
            "fc": d.get("heart_rate", None),
            "pwr": d.get("power", None),
            "bal": d.get("left_right_balance_100", None)
        })

    if len(raw) < 2:
        return pd.DataFrame(), pd.DataFrame()

    # Altitude lissée
    fixed_alts = fix_altitudes([p["alt"] for p in raw])
    for i, p in enumerate(raw):
        p["alt"] = fixed_alts[i]

    # Détection mouvement Wahoo
    SPEED_THRESHOLD = 1.5
    for p in raw:
        p["moving"] = p["speed"] > SPEED_THRESHOLD

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
    total_dist = 0
    prev = raw[0]

    # Boucle
    for pt in raw[1:]:

        dist = haversine(prev["lat"], prev["lon"], pt["lat"], pt["lon"])
        if dist < 0.1:
            prev = pt
            continue

        # Altitude → seuil corrigé = 0.25 m
        dalt = pt["alt"] - prev["alt"]
        if abs(dalt) < 0.25:
            dalt = 0

        total_dist += dist

        dt = (pt["ts"] - prev["ts"]).total_seconds() if prev["ts"] and pt["ts"] else 0
        if dt <= 0:
            prev = pt
            continue

        pct = (dalt/dist*100) if dist>0 else 0
        cat = classify(pct)

        # Segment values
        stats[cat]["dist"] += dist
        stats[cat]["time"] += dt

        # moving_time (pour moyennes globales)
        if pt["moving"]:
            stats[cat]["moving_time"] += dt

            # Cadence pondérée
            if pt["cad"] and pt["cad"] > 0:
                stats[cat]["cad_vals"].append(pt["cad"])
                stats[cat]["cad_dt"].append(dt)

            # FC pondérée
            if pt["fc"]:
                stats[cat]["fc_vals"].append(pt["fc"])
                stats[cat]["fc_dt"].append(dt)

            # Puissance pondérée
            if pt["pwr"]:
                stats[cat]["pwr_vals"].append(pt["pwr"])
                stats[cat]["pwr_dt"].append(dt)

        # D+ où D-
        if dalt > 0:
            stats[cat]["d+"] += dalt
        elif dalt < 0:
            stats[cat]["d-"] += dalt

        # balance (non pondérée)
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

    # Construire tableau final
    rows = []

    for k, v in stats.items():

        dist_km = v["dist"]/1000
        time_h = v["time"]/3600 if v["time"] else 0
        moving_h = v["moving_time"]/3600 if v["moving_time"] else 0

        # vitesse moyenne = dist / moving_time
        vit = dist_km / moving_h if moving_h>0 else 0

        # VAM segment = d+ / time réel
        vam = v["d+"] / time_h if (time_h>0 and k in ["petite_montee","forte_montee"]) else 0

        # Moyennes pondérées
        def wmean(vals, dts):
            return (np.sum(np.array(vals)*np.array(dts))/np.sum(dts)) if dts else 0

        cad = wmean(v["cad_vals"], v["cad_dt"])
        fc  = wmean(v["fc_vals"], v["fc_dt"])
        pwr = wmean(v["pwr_vals"], v["pwr_dt"])
        bal = np.mean(v["bal_vals"]) if v["bal_vals"] else 0

        rows.append({
            "Type": k,
            "Distance_km": dist_km,
            "D+": v["d+"],
            "D-": v["d-"],
            "Temps_h": time_h,        # ✅ segment = temps réel
            "Vitesse_kmh": round(vit,2),
            "VAM_mh": round(vam,1),
            "Cadence": round(cad),
            "FC": round(fc),
            "Puissance": round(pwr),
            "Equilibre_DG": round(bal,1)
        })

    df = pd.DataFrame(rows)

    # Durée formatée
    def format_h(hours):
        h = int(hours)
        m = int(round((hours-h)*60))
        return f"{h}h {m:02d}min"

    df["Durée"] = df["Temps_h"].apply(format_h)

    profile_df = pd.DataFrame(profile)

    return df, profile_df
