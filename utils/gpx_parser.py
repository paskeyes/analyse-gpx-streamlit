import gpxpy
import pandas as pd
import math


# ---------------------------------------------------------
# Utilitaires
# ---------------------------------------------------------
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


def format_hm(hours):
    h = int(hours)
    m = int((hours - h) * 60)
    return f"{h}h {m:02d}min"


def climb_category(dplus):
    if dplus >= 300: return "HC"
    if dplus >= 200: return "1"
    if dplus >= 120: return "2"
    if dplus >= 60:  return "3"
    if dplus >= 30:  return "4"
    return "NC"


# ---------------------------------------------------------
# PARSER GPX ENRICHI
# ---------------------------------------------------------
def parse_gpx_and_compute(uploaded_file, params):

    gpx = gpxpy.parse(uploaded_file)

    # -----------------------------------------------------
    # ✅ 1) PROFIL POINT‑PAR‑POINT (INCHANGÉ)
    # -----------------------------------------------------
    profile = []
    stats = {k: {"dist": 0, "d+": 0, "d-": 0} for k in [
        "plat", "petite_montee", "forte_montee",
        "petite_descente", "forte_descente"
    ]}

    prev = None
    total_dist = 0

    for track in gpx.tracks:
        for seg in track.segments:
            for pt in seg.points:

                if prev:
                    dist = haversine(prev.latitude, prev.longitude,
                                     pt.latitude, pt.longitude)

                    if dist < 2:
                        prev = pt
                        continue

                    if pt.elevation is None or prev.elevation is None:
                        dalt = 0
                    else:
                        dalt = pt.elevation - prev.elevation
                        if abs(dalt) < 1.8:
                            dalt = 0

                    total_dist += dist
                    pct = (dalt / dist * 100) if dist > 0 else 0
                    cat = classify(pct)

                    stats[cat]["dist"] += dist
                    if dalt > 0:
                        stats[cat]["d+"] += dalt
                    elif dalt < 0:
                        stats[cat]["d-"] += dalt

                    profile.append({
                        "dist_km": total_dist / 1000,
                        "alt": pt.elevation,
                        "lat": pt.latitude,
                        "lon": pt.longitude,
                        "pct": pct
                    })

                prev = pt

    profile_df = pd.DataFrame(profile)

    # -----------------------------------------------------
    # ✅ 2) TABLEAU GPX CLASSIQUE (INCHANGÉ)
    # -----------------------------------------------------
    rows = []
    for k, v in stats.items():

        dist_km = v["dist"] / 1000
        dplus = v["d+"]

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
            "Temps_h": time_h,
            "Durée": format_hm(time_h)
        })

    df_segments = pd.DataFrame(rows)

    # -----------------------------------------------------
    # ✅ 3) NOUVEAU — TABLEAU DES MONTÉES GPX (TRAININGPEAKS)
    # -----------------------------------------------------
    ### NEW : gradient cumulé sur le profil
    prof = profile_df.copy()
    prof["dist"] = prof["dist_km"] * 1000

    WINDOW = 200.0
    grad = []
    i0 = 0

    for i in range(len(prof)):
        while prof.loc[i, "dist"] - prof.loc[i0, "dist"] > WINDOW:
            i0 += 1
        dwin = prof.loc[i, "dist"] - prof.loc[i0, "dist"]
        if dwin > 1:
            dp = prof.loc[i, "alt"] - prof.loc[i0, "alt"]
            grad.append((dp / dwin) * 100)
        else:
            grad.append(0)

    prof["gradient"] = grad

    # segmentation
    segments = []
    def seg_type(g):
        if g > 1.2: return "montee"
        if g < -1: return "descente"
        return "plat"

    cur = seg_type(prof.loc[0, "gradient"])
    start = 0
    for i in range(1, len(prof)):
        t = seg_type(prof.loc[i, "gradient"])
        if t != cur:
            segments.append({"type": cur, "i0": start, "i1": i-1})
            cur = t
            start = i
    segments.append({"type": cur, "i0": start, "i1": len(prof)-1})

    # fusion des montées
    merged = []
    current = None
    for s in segments:
        if s["type"] == "montee":
            if current is None:
                current = dict(s)
            else:
                current["i1"] = s["i1"]
        else:
            if current is not None:
                gap = prof.loc[s["i1"], "dist"] - prof.loc[current["i1"], "dist"]
                drop = prof.loc[s["i1"], "alt"] - prof.loc[current["i1"], "alt"]
                if gap <= 300 and drop >= -7:
                    current["i1"] = s["i1"]
                else:
                    merged.append(current)
                    current = None
    if current:
        merged.append(current)

    # build tableau montées GPX
    rows_montees = []
    idx = 1

    for seg in merged:
        p0 = prof.iloc[seg["i0"]]
        p1 = prof.iloc[seg["i1"]]

        dist_km = (p1["dist"] - p0["dist"]) / 1000
        dplus = max(0, p1["alt"] - p0["alt"])
        pente = (dplus / (dist_km * 1000)) * 100 if dist_km > 0 else 0

        if dist_km >= 1.0 and dplus >= 30 and pente >= 2.0:
            time_h = dplus / params["petite_montee_vam"]

            rows_montees.append({
                "Montée": f"Montée {idx}",
                "Catégorie": climb_category(dplus),
                "Début_km": f"{p0['dist']/1000:.2f}",
                "Distance_km": f"{dist_km:.2f}",
                "D+": int(round(dplus)),
                "Pente_moy%": f"{pente:.1f}",
                "VAM_mh": "",
                "Vitesse_kmh": "",
                "Cadence": "",
                "FC": "",
                "Puissance": "",
                "Durée": format_hm(time_h),
                "Type": f"Montée {idx}"
            })
            idx += 1

    df_montees = pd.DataFrame(rows_montees)

    # -----------------------------------------------------
    # ✅ 4) RÉSUMÉ GLOBAL (INCHANGÉ)
    # -----------------------------------------------------
    tot_dist = df_segments["Distance_km"].sum()
    tot_dplus = df_segments["D+"].sum()
    tot_time_h = df_segments["Temps_h"].sum()

    h = int(tot_time_h)
    m = int((tot_time_h - h) * 60)
    h_str = f"{h}h{m:02d}"

    summary = {
        "distance": tot_dist,
        "d+": tot_dplus,
        "h_str": h_str,
        "duration_h": tot_time_h,
        "text": (
            f"✅ Votre parcours fait **{tot_dist:.1f} km**  \n"
            f"✅ Dénivelé positif **{tot_dplus:.0f} m**  \n"
            f"⏱️ Temps estimé : **{h_str}**"
        )
    }

    return df_segments, df_montees, profile_df, summary
