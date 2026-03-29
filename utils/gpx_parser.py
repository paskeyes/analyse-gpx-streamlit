import gpxpy
import pandas as pd
import math

# Classification thresholds (identiques FIT)
TOL = {
    "plat": (-1, 1),
    "petite_montee": (1, 5),
    "forte_montee": (5, 999),
    "petite_descente": (-5, -1),
    "forte_descente": (-999, -5),
}

def haversine(lat1, lon1, lat2, lon2):
    R = 6371000
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlam = math.radians(lon2 - lon1)
    a = math.sin(dphi/2)**2 + math.cos(phi1)*math.cos(phi2)*math.sin(dlam/2)**2
    return 2 * R * math.atan2(math.sqrt(a), math.sqrt(1 - a))

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


def parse_gpx_and_compute(uploaded_file, params):

    gpx = gpxpy.parse(uploaded_file)

    # accumulateurs
    stats = {
        k: {"dist": 0, "d+": 0, "d-": 0}
        for k in TOL.keys()
    }

    profile = []
    prev = None
    total_dist = 0

    # Parcours du GPX
    for track in gpx.tracks:
        for seg in track.segments:
            for pt in seg.points:

                if prev:

                    dist = haversine(prev.latitude, prev.longitude,
                                     pt.latitude, pt.longitude)

                    if dist < 2:  # filtrage GPS
                        prev = pt
                        continue

                    # delta altitude
                    if pt.elevation is None or prev.elevation is None:
                        dalt = 0
                    else:
                        dalt = pt.elevation - prev.elevation
                        if abs(dalt) < 1.8:
                            dalt = 0

                    total_dist += dist

                    # pente
                    pct = (dalt / dist * 100) if dist > 0 else 0
                    cat = classify(pct)

                    # accumulations
                    stats[cat]["dist"] += dist
                    if cat != "plat":
                        if dalt > 0:
                            stats[cat]["d+"] += dalt
                        else:
                            stats[cat]["d-"] += dalt

                    # profil alt/lat/lon pour la carte
                    profile.append({
                        "dist_km": total_dist / 1000,
                        "alt": pt.elevation,
                        "lat": pt.latitude,
                        "lon": pt.longitude,
                        "pct": pct
                    })

                prev = pt

    # --------------------------
    # Construction du tableau
    # --------------------------
    rows = []
    for k, v in stats.items():

        dist_km = v["dist"] / 1000
        dplus = v["d+"]

        # ✅ Calcul du temps estimé basé sur paramètres utilisateur
        if k == "plat":
            time_h = dist_km / params["plat_speed"]
        elif k == "petite_descente":
            time_h = dist_km / params["petite_descente_speed"]
        elif k == "forte_descente":
            time_h = dist_km / params["forte_descente_speed"]
        elif k == "petite_montee":
            time_h = dplus / params["petite_montee_vam"]
        elif k == "forte_montee":
            time_h = dplus / params["forte_montee_vam"]
        else:
            time_h = 0

        rows.append({
            "Type": k,
            "Distance_km": dist_km,
            "D+": dplus,
            "D-": v["d-"],
            "Temps_h": time_h
        })

    df = pd.DataFrame(rows)

    # ✅ Durée formatée Hh MMmin
    def format_hm(hours):
        h = int(hours)
        m = int(round((hours - h) * 60))
        return f"{h}h {m:02d}min"

    df["Durée"] = df["Temps_h"].apply(format_hm)

    profile_df = pd.DataFrame(profile)

    # Résumé Global
    tot_dist = df["Distance_km"].sum()
    tot_dplus = df["D+"].sum()
    tot_time_h = df["Temps_h"].sum()

    # Format résumé
    h = int(tot_time_h)
    m = int((tot_time_h - h) * 60)
    h_str = f"{h}h{m:02d}"

    summary_text = (
        f"✅ Votre parcours fait **{tot_dist:.1f} km**  \n"
        f"✅ Dénivelé positif **{tot_dplus:.0f} m**  \n"
        f"⏱️ Temps estimé : **{h_str}**"
    )

    return df, profile_df, {
        "distance": tot_dist,
        "d+": tot_dplus,
        "h_str": h_str,
        "duration_h": tot_time_h,
        "text": summary_text,
    }
