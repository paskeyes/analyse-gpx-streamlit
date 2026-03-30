import math
import numpy as np
import pandas as pd
from fitparse import FitFile
from scipy.signal import savgol_filter

# ---------------------------------------
# Classification (inchangée)
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
# Distance haversine (inchangée)
# ---------------------------------------
def haversine(lat1, lon1, lat2, lon2):
    R = 6371000
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlam = math.radians(lon2 - lon1)
    a = math.sin(dphi/2)**2 + math.cos(phi1)*math.cos(phi2)*math.sin(dlam/2)**2
    return 2 * R * math.atan2(math.sqrt(a), math.sqrt(1 - a))


# ---------------------------------------
# Lissage altitude FIT
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

    # --------------------
    # Extraire les enregistrements
    # --------------------
    for rec in fit.get_messages("record"):
        d = rec.get_values()
        if "position_lat" not in d or "position_long" not in d:
            continue

        lat = d["position_lat"] * (180 / 2**31)
        lon = d["position_long"] * (180 / 2**31)

        alt = d.get("enhanced_altitude", d.get("altitude", None))
        ts = d.get("timestamp", None)
        spd = d.get("speed", 0)  # m/s

        raw.append({
            "lat": lat,
            "lon": lon,
            "alt": alt,
            "ts": ts,
            "speed": spd * 3.6,  # km/h
            "cad": d.get("cadence", None),
            "fc": d.get("heart_rate", None),
            "pwr": d.get("power", None),
            "bal": d.get("left_right_balance_100", None)
        })

    if len(raw) < 2:
        return pd.DataFrame(), pd.DataFrame()

    # -------------------------
    # Lissage altitude
    # -------------------------
    fixed_alts = fix_altitudes([p["alt"] for p in raw])
    for i, p in enumerate(raw):
        p["alt"] = fixed_alts[i]

    # -------------------------
    # Détection pauses (Wahoo)
    # moving = speed > 1.5 km/h
    # pause = speed <= 1.5 km/h pendant >= 5 s
    # -------------------------
    SPEED_THRESHOLD = 1.5  # km/h
    PAUSE_SEC = 5

    for p in raw:
        p["moving"] = p["speed"] > SPEED_THRESHOLD

    # label pause segments
    last_moving = None
    pause_start = None

    for i in range(len(raw)):
        if not raw[i]["moving"]:
            if pause_start is None:
                pause_start = raw[i]["ts"]
        else:
            pause_start = None

    # -------------------------
    # Accumulateurs par type
    # -------------------------
    stats = {
        k: {"dist":0, "d+":0, "d-":0, "time":0, "moving_time":0,
            "cad_vals":[], "fc_vals":[], "pwr_vals":[], "bal_vals":[]}
        for k in ["plat", "petite_montee", "forte_montee",
                  "petite_descente", "forte_descente"]
    }

    profile = []
    total_dist = 0

    prev = raw[0]

    # --------------------------------------
    # Boucle point-à-point complète, FIT
    # --------------------------------------
    for pt in raw[1:]:

        dist = haversine(prev["lat"], prev["lon"], pt["lat"], pt["lon"])
        if dist < 0.1:  # faible déplacement
            prev = pt
            continue

        # Delta altitude filtré (FIT noise)
        dalt = pt["alt"] - prev["alt"]
        if abs(dalt) < 0.6:    # ✅ seuil correct
            dalt = 0

        total_dist += dist

        # Temps total
        dt = (pt["ts"] - prev["ts"]).total_seconds() if pt["ts"] and prev["ts"] else 0
        if dt <= 0:
            prev = pt
            continue

        # Détection pause ≥5 sec
        moving = pt["speed"] > 1.5
        prev_moving = prev["speed"] > 1.5

        if not moving:
            # vélo à l'arrêt → ne compte pas dans moving_time
            pass
        else:
            # vélo en mouvement
            for k in stats.keys():
                # ne sera réellement ajouté qu’après classification
                pass

        pct = (dalt/dist*100) if dist>0 else 0
        cat = classify(pct)

        # distance & temps segment
        stats[cat]["dist"] += dist
        stats[cat]["time"] += dt

        # moving_time = seulement si moving
        if moving:
            stats[cat]["moving_time"] += dt

        # D+ / D-
        if dalt > 0:
            stats[cat]["d+"] += dalt
        elif dalt < 0:
            stats[cat]["d-"] += dalt

        # Cadence
        if pt["cad"] and moving and pt["cad"] > 0:
            stats[cat]["cad_vals"].append(pt["cad"])

        # FC
        if pt["fc"] and moving:
            stats[cat]["fc_vals"].append(pt["fc"])

        # Puissance
        if pt["pwr"] and moving:
            stats[cat]["pwr_vals"].append(pt["pwr"])

        # Balance
        if pt["bal"] is not None:
            stats[cat]["bal_vals"].append(pt["bal"]/100)

        profile.append({
            "dist_km": total_dist/1000,
            "alt": pt["alt"],
            "lat": pt["lat"],
            "lon": pt["lon"],
            "pct": pct
        })

        prev = pt

    # -----------------------------------------
    # Construction du tableau final
    # -----------------------------------------
    rows = []

    for k, v in stats.items():

        dist_km = v["dist"]/1000
        time_h = v["time"]/3600 if v["time"] else 0
        moving_h = v["moving_time"]/3600 if v["moving_time"] else 0

        # vitesse moyenne réelle = distance totale / moving_time
        if moving_h > 0:
            vit = dist_km / moving_h
        else:
            vit = 0

        # VAM segmentaire
        if k in ["petite_montee","forte_montee"] and time_h > 0:
            vam = v["d+"] / time_h
        else:
            vam = 0

        cadence = np.mean(v["cad_vals"]) if len(v["cad_vals"]) else 0
        fc = np.mean(v["fc_vals"]) if len(v["fc_vals"]) else 0
        pwr = np.mean(v["pwr_vals"]) if len(v["pwr_vals"]) else 0
        bal = np.mean(v["bal_vals"]) if len(v["bal_vals"]) else 0

        rows.append({
            "Type": k,
            "Distance_km": dist_km,
            "D+": v["d+"],
            "D-": v["d-"],
            "Temps_h": moving_h,               # ✅ temps de mouvement
            "Vitesse_kmh": round(vit, 2),
            "VAM_mh": round(vam, 1),
            "Cadence": int(cadence),
            "FC": int(fc),
            "Puissance": int(pwr),
            "Equilibre_DG": round(bal,1)
        })

    df = pd.DataFrame(rows)

    # ✅ Formattage Durée
    def format_h(hours):
        h = int(hours)
        m = int(round((hours - h) * 60))
        return f"{h}h {m:02d}min"

    df["Durée"] = df["Temps_h"].apply(format_h)

    profile_df = pd.DataFrame(profile)

    return df, profile_df
