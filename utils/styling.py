import pandas as pd
import numpy as np

# Couleurs par type de segment
COLORS = {
    "plat": "#6ec1ff",
    "petite_montee": "#ff9f40",
    "forte_montee": "#ff3b30",
    "petite_descente": "#4cd964",
    "forte_descente": "#2f8f2f"
}

# ---------------------------------------------------------
# Conversion Durée ("Hh MMmin") <-> minutes
# ---------------------------------------------------------
def hm_to_minutes(hm: str) -> float:
    """Convertit '1h 42min' → minutes (102)."""
    if isinstance(hm, str) and "h" in hm:
        h = int(hm.split("h")[0])
        m = int(hm.split("h")[1].replace("min", "").strip())
        return h * 60 + m
    return 0

def minutes_to_hm(minutes: float) -> str:
    """Convertit minutes → 'Hh MMmin'."""
    h = int(minutes // 60)
    m = int(minutes % 60)
    return f"{h}h {m:02d}min"


# ---------------------------------------------------------
# STYLING PRINCIPAL
# ---------------------------------------------------------
def style_table(df):
    """
    Style un tableau GPX ou FIT.

    ✅ Ne dépend plus jamais de Temps_h
    ✅ Ligne TOTAL dynamique
    ✅ Vitesse totale correcte (distance / durée_mouv)
    ✅ VAM totale vide
    ✅ Moyenne totale de cadence / FC / puissance / équilibrage
    ✅ Formatage sécurisé
    ✅ Coloration par Type
    """

    df2 = df.copy()

    # ---------------------------------------------------------
    # ✅ CALCUL DE LA LIGNE TOTAL
    # ---------------------------------------------------------
    total = {}

    # DISTANCE
    if "Distance_km" in df2:
        dist_vals = pd.to_numeric(df2["Distance_km"], errors="coerce")
        total["Distance_km"] = round(dist_vals.sum(), 2)


    # D+
    if "D+" in df2:
        total["D+"] = df2["D+"].sum()

    # D-
    if "D-" in df2:
        total["D-"] = df2["D-"].sum()

    # 🔥 TOTAL DURÉE
    if "Durée" in df2:
        total_minutes = sum(hm_to_minutes(v) for v in df2["Durée"])
        total["Durée"] = minutes_to_hm(total_minutes)

    # 🔥 VITESSE MOYENNE TOTALE = distance_totale / durée_totale
    if "Vitesse_kmh" in df2 and "Durée" in df2:
        #dist_tot = df2["Distance_km"].sum()       
        dist_vals = pd.to_numeric(df2["Distance_km"], errors="coerce")
        dist_tot = dist_vals.sum()
        min_tot = sum(hm_to_minutes(v) for v in df2["Durée"])
        if min_tot > 0:
            total["Vitesse_kmh"] = round(dist_tot / (min_tot / 60), 2)
        else:
            total["Vitesse_kmh"] = ""

    # 🔥 VAM totale = VIDE (jamais affichée)
    if "VAM_mh" in df2:
        total["VAM_mh"] = ""

    # 🔥 Moyennes FIT (cadence, FC, puissance)
    for col in ["Cadence", "FC", "Puissance", "Equilibre_DG"]:
        if col in df2:
            clean_vals = pd.to_numeric(df2[col], errors="coerce").dropna()
            total[col] = round(clean_vals.mean(), 1) if len(clean_vals) else ""

    # TYPE = TOTAL
    total["Type"] = "TOTAL"

    # AJOUT LIGNE TOTAL
    df2.loc["TOTAL"] = {col: total.get(col, "") for col in df2.columns}

    # ---------------------------------------------------------
    # ✅ COLORATION LIGNES
    # ---------------------------------------------------------
    def color_row(row):
        if row["Type"] == "TOTAL":
            return ["background-color:#dddddd; color:black; font-weight:bold"] * len(row)

        t = row["Type"]
        if t in COLORS:
            return [f"background-color:{COLORS[t]}; color:black"] * len(row)

        return [""] * len(row)

    styler = df2.style.apply(color_row, axis=1)

    # ---------------------------------------------------------
    # ✅ FORMATAGE SÉCURISÉ
    # ---------------------------------------------------------
    def safe(pattern):
        return lambda x: pattern.format(x) if isinstance(x, (int, float, np.number)) else x

    fmt = {}

    if "Distance_km" in df2: fmt["Distance_km"] = safe("{:.2f}")
    if "D+" in df2: fmt["D+"] = safe("{:.0f}")
    if "D-" in df2: fmt["D-"] = safe("{:.0f}")
    if "Vitesse_kmh" in df2: fmt["Vitesse_kmh"] = safe("{:.2f}")
    if "Cadence" in df2: fmt["Cadence"] = safe("{:.0f}")
    if "FC" in df2: fmt["FC"] = safe("{:.0f}")
    if "Puissance" in df2: fmt["Puissance"] = safe("{:.0f}")
    if "Equilibre_DG" in df2: fmt["Equilibre_DG"] = safe("{:.1f}")

    styler = styler.format(fmt)

    return styler
