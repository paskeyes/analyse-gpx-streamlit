import math
import numpy as np
import pandas as pd
from fitparse import FitFile
from scipy.signal import savgol_filter


# ---------------------------------------------------------
# Distance haversine
# ---------------------------------------------------------
def haversine(lat1, lon1, lat2, lon2):
    R = 6371000
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlam = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlam / 2) ** 2
    return 2 * R * math.atan2(math.sqrt(a), math.sqrt(1 - a))


# ---------------------------------------------------------
# Classification des pentes
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
# LISSAGE ALTITUDE (inchangé)
# ---------------------------------------------------------
def fix_altitudes(raw_alts):
    alts = pd.Series(raw_alts, dtype=float)
    alts.replace({None: np.nan}, inplace=True)

    alts = alts.interpolate("linear", limit_direction="both")

    diffs = alts.diff().abs()
    alts[diffs > 12] = np.nan
    alts = alts.interpolate("linear", limit_direction="both")

    if len(alts) >= 5:
        alts = savgol_filter(alts, 5, 2)

    return alts.tolist()


# ---------------------------------------------------------
# PARSER FIT AVEC SEGMENTATION "GRADIENT CUMULATIF"
# ---------------------------------------------------------
def parse_fit_and_compute(uploaded_file):

    fit = FitFile(uploaded_file)
    raw = []

    # --------------------------
    # EXTRACTION FIT
    # --------------------------
    for rec in fit.get_messages("record"):
        d = rec.get_values()

        if "position_lat" not in d or "position_long" not in d:
            continue

        raw.append({
            "lat": d["position_lat"] * (180 / 2 ** 31),
            "lon": d["position_long"] * (180 / 2 ** 31),
            "alt": d.get("enhanced_altitude", d.get("altitude", None)),
            "ts": d.get("timestamp", None),
            "speed": d.get("speed", 0) * 3.6,  # km/h
            "cad": d.get("cadence", None),
            "fc": d.get("heart_rate", None),
            "pwr": d.get("power", None),
            "bal": d.get("left_right_balance_100", None)
        })

    if len(raw) < 2:
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()

    # --------------------------
    # FIX ALTITUDE
    # --------------------------
    alts = fix_altitudes([p["alt"] for p in raw])
    for i, p in enumerate(raw):
        p["alt"] = alts[i]

    # --------------------------
    # DÉTECTION MOUVEMENT
    # (Strava-like stable)
    # --------------------------
    for p in raw:
        p["moving"] = p["speed"] > 1.0

    # ---------------------------------------------------------
    # 1) CONSTRUCTION DU PROFIL (distance cumulée + dalt)
    # ---------------------------------------------------------
    profile = []
    total_dist = 0
    prev = raw[0]

    for pt in raw[1:]:
        dist = haversine(prev["lat"], prev["lon"], pt["lat"], pt["lon"])
        if dist < 0.05:
            prev = pt
            continue

        dt = (pt["ts"] - prev["ts"]).total_seconds() if pt["ts"] and prev["ts"] else 0
        dalt = pt["alt"] - prev["alt"]

        total_dist += dist

        profile.append({
            "lat": pt["lat"],
            "lon": pt["lon"],
            "alt": pt["alt"],
            "dist": total_dist,
            "ts": pt["ts"],
            "dt": dt,
            "speed": pt["speed"],
            "cad": pt["cad"],
            "fc": pt["fc"],
            "pwr": pt["pwr"],
            "bal": pt["bal"],
            "moving": pt["moving"]
        })

        prev = pt

    prof = pd.DataFrame(profile)

    # ---------------------------------------------------------
    # 2) CALCUL DU GRADIENT CUMULATIF SUR 200 m NON-OPTIMISE (08/04)
    # ---------------------------------------------------------
    # WINDOW = 200.0  # TrainingPeaks-like
    # grad = []
    # i0 = 0

    # for i in range(len(prof)):
    #     while prof.loc[i, "dist"] - prof.loc[i0, "dist"] > WINDOW:
    #         i0 += 1

    #     dwin = prof.loc[i, "dist"] - prof.loc[i0, "dist"]
    #     if dwin > 1:
    #         dp = prof.loc[i, "alt"] - prof.loc[i0, "alt"]
    #         pct = (dp / dwin) * 100
    #     else:
    #         pct = 0

    #     grad.append(pct)

    # prof["gradient"] = grad

    # ---------------------------------------------------------
    # 2) CALCUL DU GRADIENT CUMULATIF SUR 200 m OPTIMISE (08/04)
    # ---------------------------------------------------------
    WINDOW = 200.0  # m
    
    # ✅ Extraction des colonnes une seule fois
    dist_arr = prof["dist"].values
    alt_arr = prof["alt"].values
    
    grad = np.zeros(len(dist_arr), dtype=float)
    i0 = 0
    
    for i in range(len(dist_arr)):
        while dist_arr[i] - dist_arr[i0] > WINDOW:
            i0 += 1
    
        dwin = dist_arr[i] - dist_arr[i0]
        if dwin > 1:
            dp = alt_arr[i] - alt_arr[i0]
            grad[i] = (dp / dwin) * 100
        else:
            grad[i] = 0.0
    
    prof["gradient"] = grad
    
    # ---------------------------------------------------------
    # 2bis) ✅ PENTE INSTANTANÉE (pct) POUR LA CARTE (GPX-like)
    # ---------------------------------------------------------

    # On travaille en mètres : soit prof["dist"] existe, soit on reconstruit depuis dist_km
    if "dist" in prof.columns:
        dist_m = prof["dist"].astype(float)
    else:
        # Ton debug montre dist_km présent : on reconstruit dist_m
        dist_m = prof["dist_km"].astype(float) * 1000.0

    alt_m = prof["alt"].astype(float)

    # ---------------------------------------------------------
    # ancien code fonctionnel non-optimisé (08/04)
    # ---------------------------------------------------------
    
    #pct_list = [0.0] * len(prof)
    #prev_i = 0

    #for i in range(1, len(prof)):
    #    d = float(dist_m.iloc[i] - dist_m.iloc[prev_i])

        # Comme GPX : si < 2 m, on n'utilise pas ce point pour calculer une pente
    #    if d < 2.0:
    #        pct_list[i] = 0.0
    #        continue

    #    da = float(alt_m.iloc[i] - alt_m.iloc[prev_i])

        # Comme GPX : filtre micro-bruit altitude
    #    if abs(da) < 0.1:#1.8:
    #        da = 0.0

    #    pct_list[i] = (da / d) * 100.0 if d > 0 else 0.0
    #    prev_i = i
        
        # ✅ ICI : pd.Series pour pouvoir faire fillna()
    #    prof["pct"] = pd.to_numeric(pd.Series(pct_list, index=prof.index), errors="coerce").fillna(0.0)

    # ---------------------------------------------------------
    # nouveau code optimisé (08/04)
    # ---------------------------------------------------------
    pct_list = np.zeros(len(prof), dtype=float)
    prev_i = 0
    
    for i in range(1, len(prof)):
        d = dist_m.iloc[i] - dist_m.iloc[prev_i]
        if d < 2.0:
            continue
    
        da = alt_m.iloc[i] - alt_m.iloc[prev_i]
        if abs(da) < 0.1:
            da = 0.0
    
        pct_list[i] = (da / d) * 100.0 if d > 0 else 0.0
        prev_i = i
    
    # ✅ UNE SEULE assignation Pandas
    prof["pct"] = pct_list
    

    
    # ---------------------------------------------------------
    # 3) SEGMENTATION PRIMAIRE PAR GRADIENT
    # ---------------------------------------------------------
    segments = []

    def seg_type_from_grad(g):
        if g > 1.2:
            return "montee"
        if g < -1.0:
            return "descente"
        return "plat"

    current_type = seg_type_from_grad(prof.loc[0, "gradient"])
    idx_start = 0

    for i in range(1, len(prof)):
        t = seg_type_from_grad(prof.loc[i, "gradient"])
        if t != current_type:
            segments.append({"type": current_type, "i0": idx_start, "i1": i - 1})
            current_type = t
            idx_start = i

    segments.append({"type": current_type, "i0": idx_start, "i1": len(prof) - 1})

    # ---------------------------------------------------------
    # FONCTION UTILITAIRE : métriques d’un segment
    # ---------------------------------------------------------
    def seg_metrics(seg):
        p0 = prof.iloc[seg["i0"]]
        p1 = prof.iloc[seg["i1"]]

        dist = (p1["dist"] - p0["dist"]) / 1000  # km
        dplus = max(0, p1["alt"] - p0["alt"])
        dminus = min(0, p1["alt"] - p0["alt"])

        dt = prof.loc[seg["i0"]:seg["i1"], "dt"].sum()
        time_h = dt / 3600

        moving_dt = prof.loc[seg["i0"]:seg["i1"], "dt"]
        moving_dt = moving_dt.where(
            prof.loc[seg["i0"]:seg["i1"], "moving"], 0
        )
        moving_h = moving_dt.sum() / 3600

        vit = dist / moving_h if moving_h > 0 else 0

        cad_vals = prof.loc[seg["i0"]:seg["i1"], "cad"]
        cad_dts = prof.loc[seg["i0"]:seg["i1"], "dt"]
        fc_vals = prof.loc[seg["i0"]:seg["i1"], "fc"]
        pwr_vals = prof.loc[seg["i0"]:seg["i1"], "pwr"]

        def wmean(vals, dts):
            vals = vals.fillna(0)
            if dts.sum() == 0:
                return 0
            return (vals * dts).sum() / dts.sum()

        cad = wmean(cad_vals, cad_dts)
        fc = wmean(fc_vals, cad_dts)
        pwr = wmean(pwr_vals, cad_dts)

        return dist, dplus, dminus, time_h, moving_h, vit, cad, fc, pwr

    # ---------------------------------------------------------
    # 4) FUSION DES MONTÉES (TrainingPeaks)
    # ---------------------------------------------------------
    merged_climbs = []
    current = None

    MAX_REPLAT_DIST = 300.0    # m
    MAX_DESCENTE_DNEG = -7.0   # m

    for seg in segments:
        if seg["type"] == "montee":
            if current is None:
                current = {"i0": seg["i0"], "i1": seg["i1"]}
            else:
                current["i1"] = seg["i1"]
        else:
            if current is not None:
                p_end = prof.iloc[current["i1"]]
                p_now = prof.iloc[seg["i1"]]

                gap_dist = p_now["dist"] - p_end["dist"]
                gap_alt = p_now["alt"] - p_end["alt"]

                if gap_dist <= MAX_REPLAT_DIST and gap_alt >= MAX_DESCENTE_DNEG:
                    current["i1"] = seg["i1"]
                else:
                    merged_climbs.append(current)
                    current = None

    if current is not None:
        merged_climbs.append(current)

    # ---------------------------------------------------------
    # 5) FILTRAGE FINAL DES VRAIES MONTÉES (TrainingPeaks strict)
    # ---------------------------------------------------------
    # Critères retenus :
    # - distance >= 1.0 km
    # - D+ >= 30 m
    # - pente moyenne >= 2.0 %
    # ---------------------------------------------------------
    
    detailed_climbs = []
    
    MIN_CLIMB_DIST_KM = 1.0     # km
    MIN_CLIMB_DPLUS = 25.0      # m
    MIN_AVG_GRADE = 2.0         # %
    
    for seg in merged_climbs:
    
        dist, dplus, dminus, time_h, moving_h, vit, cad, fc, pwr = seg_metrics(seg)
    
        # Sécurités
        if dist <= 0 or time_h <= 0:
            continue
    
        # pente moyenne réelle
        avg_grade = (dplus / (dist * 1000)) * 100
    
        # Filtrage TrainingPeaks
        if (
            dist >= MIN_CLIMB_DIST_KM and
            dplus >= MIN_CLIMB_DPLUS and
            avg_grade >= MIN_AVG_GRADE
        ):
            detailed_climbs.append(seg)



    # ---------------------------------------------------------
    # 5bis) TABLEAU DÉTAILLÉ DES VRAIES MONTÉES (ENRICHI)
    # ---------------------------------------------------------
    
    def climb_category(dplus):
        if dplus >= 300:
            return "HC"
        elif dplus >= 200:
            return "1"
        elif dplus >= 120:
            return "2"
        elif dplus >= 60:
            return "3"
        elif dplus >= 30:
            return "4"
        else:
            return "NC"
    
    
    rows_detail = []
    
    for i, seg in enumerate(detailed_climbs, start=1):
    
        dist, dplus, dminus, time_h, moving_h, vit, cad, fc, pwr = seg_metrics(seg)
    
        # sécurité
        if time_h <= 0 or dist <= 0:
            continue
    
        pente_moy = (dplus / (dist * 1000)) * 100
        vam = dplus / time_h
        start_km = prof.iloc[seg["i0"]]["dist"] / 1000
        cat = climb_category(dplus)



        
        rows_detail.append({
            "Montée": f"Montée {i}",
            "Catégorie": cat,
            "Début_km": f"{start_km:.2f}",
            "Distance_km": f"{dist:.2f}",
            "D+": int(round(dplus)),
            "Pente_moy%": f"{pente_moy:.1f}",
            "VAM_mh": int(round(vam)),
            "Vitesse_kmh": f"{vit:.1f}",
            "Cadence": int(round(cad)),
            "FC": int(round(fc)),
            "Puissance": int(round(pwr)),
            "Durée": f"{int(time_h)}h {int((time_h - int(time_h)) * 60):02d}min"
        })
    
    df_detail = pd.DataFrame(rows_detail)
#old    df_detail["Durée"] = df_detail["Durée_h"].apply(
#        lambda h: f"{int(h)}h {int((h - int(h)) * 60):02d}min"
#    )

    # ---------------------------------------------------------
    # 6) TABLEAU GLOBAL (Montées / Plats / Descentes)
    # ---------------------------------------------------------
    def total_for_type(t):
        dist = 0
        dplus = 0
        dminus = 0
        time_h = 0
        moving_h = 0
        cad_vals = []
        cad_dts = []
        fc_vals = []
        pwr_vals = []

        for s in segments:
            if s["type"] == t:
                r = seg_metrics(s)
                dist += r[0]
                dplus += r[1]
                dminus += r[2]
                time_h += r[3]
                moving_h += r[4]

                i0, i1 = s["i0"], s["i1"]
                dts = prof.loc[i0:i1, "dt"]

                cad_vals.append(prof.loc[i0:i1, "cad"].fillna(0) * dts)
                fc_vals.append(prof.loc[i0:i1, "fc"].fillna(0) * dts)
                pwr_vals.append(prof.loc[i0:i1, "pwr"].fillna(0) * dts)
                cad_dts.append(dts)

        if dist > 0 and cad_vals:
            cad = pd.concat(cad_vals).sum() / pd.concat(cad_dts).sum()
            fc = pd.concat(fc_vals).sum() / pd.concat(cad_dts).sum()
            pwr = pd.concat(pwr_vals).sum() / pd.concat(cad_dts).sum()
        else:
            cad = fc = pwr = 0

        vit = dist / moving_h if moving_h > 0 else 0

        return dist, dplus, dminus, vit, cad, fc, pwr, time_h

    rows_global = []

    for t, label in [("montee", "Montées"), ("plat", "Plats"), ("descente", "Descentes")]:
        dist, dplus, dminus, vit, cad, fc, pwr, time_h = total_for_type(t)
        rows_global.append({
            "Type": label,
            "Distance_km": dist,
            "D+": dplus,
            "D-": dminus,
            "Vitesse_kmh": vit,
            "Cadence": cad,
            "FC": fc,
            "Puissance": pwr,
            "Durée_h": time_h
        })

    df_global = pd.DataFrame(rows_global)
    df_global["Durée"] = df_global["Durée_h"].apply(
        lambda h: f"{int(h)}h {int((h - int(h)) * 60):02d}min"
    )

    # ---------------------------------------------------------
    # FIN
    # ---------------------------------------------------------
    return df_global, df_detail, prof
