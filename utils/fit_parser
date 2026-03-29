import math
import pandas as pd
from fitparse import FitFile

# Classification thresholds (identiques au GPX)
TOL = {
    "plat": (-1, 1),
    "petite_montee": (1, 5),
    "forte_montee": (5, 999),
    "petite_descente": (-5, -1),
    "forte_descente": (-999, -5),
}

def haversine(lat1, lon1, lat2, lon2):
    """
    Distance entre deux points GPS en mètres.
    """
    R = 6371000
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlam = math.radians(lon2 - lon1)

    a = math.sin(dphi/2)**2 + math.cos(phi1)*math.cos(phi2)*math.sin(dlam/2)**2
    return 2 * R * math.atan2(math.sqrt(a), math.sqrt(1 - a))

def classify(pct):
    """
    Classification de la pente selon les 5 catégories.
    """
    for k, (lo, hi) in TOL.items():
        if lo <= pct <= hi:
            return k
    return "plat"

def parse_fit_and_compute(uploaded_file):
    """
    Analyse complète d’un fichier FIT :
    - segmentation selon la pente
    - calcul distances, D+/D-, temps
    - vitesse moyenne par type
    - VAM (uniquement en montée)
    - cadence, FC, puissance, équilibre D/G
    """

    fit = FitFile(uploaded_file)

    # Accumulateurs par catégorie
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

    # Lecture de tous les records
    for record in fit.get_messages("record"):
        data = record.get_values()

        # Vérifier présence GPS
        if "position_lat" not in data or "position_long" not in data:
            continue

        # Conversion FIT -> degrés
        lat = data["position_lat"] * (180.0 / 2**31)
        lon = data["position_long"] * (180.0 / 2**31)

        alt = data.get("altitude", None)
        ts = data.get("timestamp", None)

        cad = data.get("cadence", None)
        fc = data.get("heart_rate", None)
        pwr = data.get("power", None)

        # left/right balance
        bal_raw = data.get("left_right_balance_100", None)
        if bal_raw is None:
            bal_raw = data.get("left_right_balance", None)

        balance = None
        if bal_raw is not None:
            # les valeurs FIT LR balance sont souvent codées *2
            if isinstance(bal_raw, int):
                balance = bal_raw / 100.0

        if prev:
            # Distance horizontale
            dist = haversine(prev["lat"], prev["lon"], lat, lon)

            # Filtrage micro-déplacements
            if dist < 0.5:
                prev = {"lat": lat, "lon": lon, "alt": alt, "ts": ts}
                continue

            # Delta altitude (avec gestion alt manquante)
            if alt is None or prev["alt"] is None:
                dalt = 0
            else:
                dalt = alt - prev["alt"]
                # Filtrage micro variations
                if abs(dalt) < 1:
                    dalt = 0

            # Temps écoulé
            if ts and prev["ts"]:
                dt = (ts - prev["ts"]).total_seconds()
            else:
                dt = 0

            if dt <= 0:
                prev = {"lat": lat, "lon": lon, "alt": alt, "ts": ts}
                continue

            # Pente
            pct = (dalt / dist * 100) if dist > 0 else 0
            cat = classify(pct)

            # Accumulations
            stats[cat]["dist"] += dist
            stats[cat]["time"] += dt

            # D+ / D- uniquement hors plat
            if cat != "plat":
                if dalt > 0:
                    stats[cat]["d+"] += dalt
                else:
                    stats[cat]["d-"] += dalt

            # Vitesse instantanée FIT (m/s → km/h)
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

            # Équilibre D/G
            if balance is not None:
                stats[cat]["bal_vals"].append(balance)

        prev = {"lat": lat, "lon": lon, "alt": alt, "ts": ts}

    # Construction du tableau final
    rows = []
    for k, v in stats.items():

        time_h = v["time"] / 3600 if v["time"] > 0 else 0

        # Vitesse moyenne en km/h (2 déc.)
        if time_h > 0:
            v_moy = (v["dist"] / 1000) / time_h
        else:
            v_moy = 0

        # VAM (uniquement si montée)
        dplus = v["d+"]
        if k in ["petite_montee", "forte_montee"] and time_h > 0:
            vam = dplus / time_h    # m / h
        else:
            vam = 0

        # Moyennes cardio / cadence / puissance
        def avg(lst):
            return sum(lst) / len(lst) if lst else 0

        rows.append({
            "Type": k,
            "Distance_km": v["dist"]/1000,
            "D+": v["d+"],
            "D-": v["d-"],
            "Temps_h": time_h,
            "Vitesse_kmh": round(v_moy, 2),
            "VAM_mh": round(vam, 1),
            "Cadence": int(avg(v["cad_vals"])),
            "FC": int(avg(v["fc_vals"])),
            "Puissance": int(avg(v["pwr_vals"])),
            "Equilibre_DG": round(avg(v["bal_vals"]), 1)
        })

    df = pd.DataFrame(rows)
    return df
