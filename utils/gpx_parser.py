import gpxpy
import pandas as pd
import math

# Classification thresholds
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
    for k,(lo,hi) in TOL.items():
        if lo <= pct <= hi:
            return k
    return "plat"

def parse_gpx_and_compute(uploaded_file, params):

    gpx = gpxpy.parse(uploaded_file)

    seg_stats = {
        k: {"dist":0, "d+":0, "d-":0, "dur":0}
        for k in TOL.keys()
    }

    profile = []
    prev = None
    total_dist = 0

    # Parse tracks
    for track in gpx.tracks:
        for seg in track.segments:
            for pt in seg.points:

                if prev:
                    dist = haversine(prev.latitude, prev.longitude, pt.latitude, pt.longitude)
                    if dist < 0.5:   # Ignore GPS noise
                        prev = pt
                        continue

                    total_dist += dist
                    dalt = (pt.elevation or 0) - (prev.elevation or 0)
                    pct = (dalt / dist * 100) if dist > 0 else 0
                    cat = classify(pct)

                    # accumulate
                    seg_stats[cat]["dist"] += dist
                    if dalt > 0:
                        seg_stats[cat]["d+"] += dalt
                    else:
                        seg_stats[cat]["d-"] += dalt

                    profile.append({"dist_km": total_dist/1000,
                                    "alt": pt.elevation})

                prev = pt

    # Compute durations
    for k,v in seg_stats.items():
        if k == "plat":
            v["dur"] = (v["dist"]/1000) / params["plat_speed"]
        elif k == "petite_descente":
            v["dur"] = (v["dist"]/1000) / params["petite_descente_speed"]
        elif k == "forte_descente":
            v["dur"] = (v["dist"]/1000) / params["forte_descente_speed"]
        elif k == "petite_montee":
            v["dur"] = v["d+"] / params["petite_montee_vam"]
        elif k == "forte_montee":
            v["dur"] = v["d+"] / params["forte_montee_vam"]

    df = pd.DataFrame([
        {"Type": k,
         "Distance_km": v["dist"]/1000,
         "D+": v["d+"],
         "D-": v["d-"],
         "Durée_h": v["dur"]}
        for k,v in seg_stats.items()
    ])

    # summary
    tot_dist = df["Distance_km"].sum()
    tot_dplus = df["D+"].sum()
    tot_dur = df["Durée_h"].sum()

    h = int(tot_dur)
    m = int((tot_dur - h) * 60)
    h_str = f"{h}h{m:02d}"

    profile_df = pd.DataFrame(profile)

    summary_text = (
        f"✅ Votre parcours fait **{tot_dist:.1f} km**  \n"
        f"✅ Dénivelé positif **{tot_dplus:.0f} m**  \n"
        f"⏱️ Temps estimé : **{h_str}**"
    )

    return df, profile_df, {
        "distance": tot_dist,
        "d+": tot_dplus,
        "h_str": h_str,
        "duration_h": tot_dur,
        "text": summary_text,
    }
