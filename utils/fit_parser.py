import math
import pandas as pd
from fitparse import FitFile

# Classification identique GPX
TOL = {
    "plat": (-1, 1),
    "petite_montee": (1, 5),
    "forte_montee": (5, 999),
    "petite_descente": (-5, -1),
    "forte_descente": (-999, -5),
}

def haversine(lat1, lon1, lat2, lon2):
    """
    Distance en mètres entre deux points GPS.
    """
    R = 6371000
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlam = math.radians(lon2 - lon1)
    a = math.sin(dphi/2)**2 + math.cos(phi1)*math.cos(phi2)*math.sin(dlam/2)**2
    return 2 * R * math.atan2(math.sqrt(a), math.sqrt(1 - a))

def classify(pct):
    """
    Catégorie de pente.
    """
    for k, (lo, hi) in TOL.items():
        if lo <= pct <= hi:
            return k
    return "plat"


def parse_fit_and_compute(uploaded_file):
    """
    Analyse avancée d'un fichier FIT :
    - segmentation par pente
    - D+, D-, distance, temps
    - vitesse moyenne (km/h)
    - VAM (m/h)
    - cadence, FC, puissance, équilibre D/G
    - profil complet pour carte + altimétrie
    """

    fit = FitFile(uploaded_file)

    # accumulateurs par catégorie
    stats = {
        k: {
            "dist": 0,
            "d+": 0,
            "d-": 0,
            "time": 0,
            "speed_vals": [],
            "cad_vals": [],
            "fc_vals": [],
            "pwr_vals": [],
            "bal_vals": []
        }
        for k in TOL.keys()
    }

    prev = None
    profile = []         # profil complet lat/lon/alt/dist
    total_dist = 0

    # Lecture FIT
    for record in fit.get_messages("record"):
        data = record.get_values()

        # Vérifier position GPS
        if "position_lat" not in data or "position_long" not in data:
            continue

        # Conversion FIT → degrés
        lat = data["position_lat"] * (180.0 / 2**31)
        lon = data["position_long"] * (180.0 / 2**31)

        alt = data.get("altitude", None)
        ts = data.get("timestamp", None)
        cad = data.get("cadence", None)
        fc = data.get("heart_rate", None)
        pwr = data.get("power", None)

        # left/right balance (souvent codé *100)
        bal_raw = data.get("left_right_balance_100", None)
        if bal_raw is None:
            bal_raw = data.get("left_right_balance", None)

        balance = None
        if bal_raw is not None:
            balance = bal_raw / 100.0

        if prev:

            # distance horizontale
            dist = haversine(prev["lat"], prev["lon"], lat, lon)
            if dist < 0.5:   # filtrage bruit
                prev = {"lat": lat, "lon": lon, "alt": alt, "ts": ts}
                continue

            # delta altitude
            if alt is None or prev["alt"] is None:
                dalt = 0
            else:
                dalt = alt - prev["alt"]
                if abs(dalt) < 1:
                    dalt = 0

            total_dist += dist

            # delta temps
            if ts and prev["ts"]:
                dt = (ts - prev["ts"]).total_seconds()
            else:
                dt = 0

            if dt <= 0:
                prev = {"lat": lat, "lon": lon, "alt": alt, "ts": ts}
                continue

            # pente
            pct = (dalt / dist * 100) if dist > 0 else 0
            cat = classify(pct)

            # accumulation
            stats[cat]["dist"] += dist
            stats[cat]["time"] += dt

            # D+ / D- uniquement hors PLAT
            if cat != "plat":
                if dalt > 0:
                    stats[cat]["d+"] += dalt
                else:
                    stats[cat]["d-"] += dalt

            # Vitesse instantanée (m/s → km/h)
            if "speed" in data and data["speed"] is not None:
                stats[cat]["speed_vals"].append(data["speed"] * 3.6)

            # Cadence
            if cad is not None:
                stats[cat]["cad_vals"].append(cad)

            # FC
            if fc is not None:
                stats[cat]["fc_vals"].append(fc)

            # Puissance
            if pwr is not None:
                stats[cat]["pwr_vals"].append(pwr)

            # Équilibre
            if balance is not None:
                stats[cat]["bal_vals"].append(balance)

            # Profil complet pour la carte
            profile.append({
                "dist_km": total_dist / 1000,
                "alt": alt,
                "lat": lat,
                "lon": lon
            })

        prev = {"lat": lat, "lon": lon, "alt": alt, "ts": ts}

    # ===============================
    # Construction du tableau final
    # ===============================

    rows = []

    # moyenne sûre
    def avg(lst):
        return sum(lst) / len(lst) if lst else 0

    for k, v in stats.items():

        time_h = v["time"] / 3600 if v["time"] > 0 else 0

        # vitesse moy km/h
        if time_h > 0:
            v_moy = (v["dist"] / 1000) / time_h
        else:
            v_moy = 0

        # VAM pour montées
        dplus = v["d+"]
        if k in ["petite_montee", "forte_montee"] and time_h > 0:
            vam = dplus / time_h
        else:
            vam = 0

        rows.append({
            "Type": k,
            "Distance_km": v["dist"] / 1000,
            "D+": v["d+"],
            "D-": v["d-"],
            "Temps_h": time_h,
            "Vitesse_kmh": round(v_moy, 2),
            "VAM_mh": round(vam, 1),         # m/h
            "Cadence": int(avg(v["cad_vals"])),
            "FC": int(avg(v["fc_vals"])),
            "Puissance": int(avg(v["pwr_vals"])),
            "Equilibre_DG": round(avg(v["bal_vals"]), 1)
        })

    df = pd.DataFrame(rows)
    profile_df = pd.DataFrame(profile)

    return df, profile_df
