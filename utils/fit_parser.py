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
    a = math.sin(dphi/2)**2 + math.cos(phi1)*math.cos(phi2)*math.sin(dlam/2)**2
    return 2 * R * math.atan2(math.sqrt(a), math.sqrt(1 - a))


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
            "lat": d["position_lat"]*(180/2**31),
            "lon": d["position_long"]*(180/2**31),
            "alt": d.get("enhanced_altitude", d.get("altitude", None)),
            "ts": d.get("timestamp", None),
            "speed": (d.get("speed",0)) * 3.6,
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
    for i,p in enumerate(raw):
        p["alt"] = alts[i]

    # --------------------------
    # DÉTECTION MOUVEMENT
    # moving = vitesse > 1 km/h (Strava-like stable)
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
    # 2) CALCUL DU GRADIENT CUMULATIF SUR 200 m
    # ---------------------------------------------------------

    WINDOW = 200.0  # 200 m TrainingPeaks
    grad = []
    i0 = 0

    for i in range(len(prof)):
        while prof.loc[i,"dist"] - prof.loc[i0,"dist"] > WINDOW:
            i0 += 1

        dwin = prof.loc[i,"dist"] - prof.loc[i0,"dist"]
        if dwin > 1:
            dp = prof.loc[i,"alt"] - prof.loc[i0,"alt"]
            pct = (dp / dwin) * 100
        else:
            pct = 0

        grad.append(pct)

    prof["gradient"] = grad

    # ---------------------------------------------------------
    # 3) SEGMENTATION PAR GRADIENT CUMULATIF
    # ---------------------------------------------------------
    segments = []
    current = {"type": None, "idx_start": 0}

    def seg_type_from_grad(g):
        if g > 1.2:
            return "montee"
        if g < -1.0:
            return "descente"
        return "plat"

    prev_type = seg_type_from_grad(prof.loc[0,"gradient"])

    for i in range(1,len(prof)):
        t = seg_type_from_grad(prof.loc[i,"gradient"])
        if t != prev_type:
            segments.append({"type": prev_type,
                             "i0": current["idx_start"],
                             "i1": i-1})
            current = {"type": t, "idx_start": i}
            prev_type = t

    segments.append({"type": prev_type,
                     "i0": current["idx_start"],
                     "i1": len(prof)-1})

# ---------------------------------------------------------
# 4) CONSTRUCTION DES "VRAIES MONTÉES" (fusion TrainingPeaks)
# ---------------------------------------------------------
merged_climbs = []

current = None

MAX_REPLAT_DIST = 150.0   # m
MAX_DESCENTE_DNEG = -3.0  # m

for seg in segments:

    if seg["type"] == "montee":

        if current is None:
            current = {
                "i0": seg["i0"],
                "i1": seg["i1"]
            }
        else:
            current["i1"] = seg["i1"]

    else:
        # segment non-montant
        if current is not None:
            # mesurer la coupure
            p_end = prof.iloc[current["i1"]]
            p_now = prof.iloc[seg["i1"]]

            gap_dist = p_now["dist"] - p_end["dist"]
            gap_alt = p_now["alt"] - p_end["alt"]

            # tolérance de replat / micro-descente
            if gap_dist <= MAX_REPLAT_DIST and gap_alt >= MAX_DESCENTE_DNEG:
                current["i1"] = seg["i1"]
            else:
                merged_climbs.append(current)
                current = None

# fin de boucle
if current is not None:
    merged_climbs.append(current)


    # ---------------------------------------------------------
    # 5) TABLEAU DÉTAILLÉ DES MONTÉES
    # ---------------------------------------------------------
# ---------------------------------------------------------
# 5) FILTRAGE FINAL DES VRAIES MONTÉES
# ---------------------------------------------------------
detailed_climbs = []

for s in merged_climbs:
    dist, dplus, _, _, _, _, _, _, _ = seg_metrics(s)

    if dist >= 0.300 and dplus >= 10:
        detailed_climbs.append(s)
    # ---------------------------------------------------------
    # 6) TABLEAU GLOBAL (Montées / Plats / Descentes)
    # ---------------------------------------------------------

    def total_for_type(t):
        dist = 0
        dplus=0
        dminus=0
        time_h=0
        moving_h=0
        cad_vals=[]
        cad_dts=[]
        fc_vals=[]
        pwr_vals=[]
        for s in segments:
            if s["type"]==t:
                r = seg_metrics(s)
                dist  += r[0]
                dplus += r[1]
                dminus+= r[2]
                time_h+= r[3]
                moving_h+=r[4]
                # pour moyennes pondérées :
                i0,i1 = s["i0"], s["i1"]
                dts  = prof.loc[i0:i1,"dt"]
                cad_vals.append(prof.loc[i0:i1,"cad"].fillna(0)*dts)
                fc_vals.append(prof.loc[i0:i1,"fc"].fillna(0)*dts)
                pwr_vals.append(prof.loc[i0:i1,"pwr"].fillna(0)*dts)
                cad_dts.append(dts)
        if dist>0:
            cad = (pd.concat(cad_vals).sum() / pd.concat(cad_dts).sum()) if cad_vals else 0
            fc  = (pd.concat(fc_vals).sum()  / pd.concat(cad_dts).sum()) if fc_vals else 0
            pwr = (pd.concat(pwr_vals).sum() / pd.concat(cad_dts).sum()) if pwr_vals else 0
        else:
            cad=fc=pwr=0

        vit = dist/moving_h if moving_h>0 else 0

        return dist,dplus,dminus,vit,cad,fc,pwr,time_h

    rows_global=[]
    for t,label in [("montee","Montées"),
                    ("plat","Plats"),
                    ("descente","Descentes")]:

        dist,dplus,dminus,vit,cad,fc,pwr,time_h = total_for_type(t)
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
    df_global["Durée"] = df_global["Durée_h"].apply(lambda h: f"{int(h)}h {int((h-int(h))*60):02d}min")

    # ---------------------------------------------------------
    # FIN — retour triple
    # ---------------------------------------------------------
    return df_global, df_detail, prof
