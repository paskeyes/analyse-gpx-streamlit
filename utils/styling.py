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

def hm_to_minutes(hm: str) -> float:
    """Convertit '1h 42min' en minutes."""
    if isinstance(hm, str) and "h" in hm:
        h = int(hm.split("h")[0])
        m = int(hm.split("h")[1].replace("min", "").strip())
        return h * 60 + m
    return 0

def minutes_to_hm(minutes: float) -> str:
    h = int(minutes // 60)
    m = int(minutes % 60)
    return f"{h}h {m:02d}min"

def style_table(df):
    df2 = df.copy()

    # ------------------------------------------------------
    # TOTAL ROW CALCULATION
    # ------------------------------------------------------
    total = {}

    # Distance
    if "Distance_km" in df2:
        total["Distance_km"] = df2["Distance_km"].sum()

    # D+/D-
    if "D+" in df2:
        total["D+"] = df2["D+"].sum()
    if "D-" in df2:
        total["D-"] = df2["D-"].sum()

    # Durée totale
    if "Durée" in df2:
        tot_min = sum(hm_to_minutes(v) for v in df2["Durée"])
        total["Durée"] = minutes_to_hm(tot_min)

    # Vitesse moyenne totale = dist_tot / durée_tot
    if "Vitesse_kmh" in df2:
        dist = df2["Distance_km"].sum()
        tot_min = sum(hm_to_minutes(v) for v in df2["Durée"])
        if tot_min > 0:
            total["Vitesse_kmh"] = round(dist / (tot_min / 60), 2)
        else:
            total["Vitesse_kmh"] = ""

    # VAM totale vide
    if "VAM_mh" in df2:
        total["VAM_mh"] = ""

    # Moyennes simples FIT
    for col in ["Cadence", "FC", "Puissance", "Equilibre_DG"]:
        if col in df2:
            vals = df2[col].dropna().astype(float)
            total[col] = round(vals.mean(), 1) if len(vals) else ""

    # Type
    total["Type"] = "TOTAL"

    # Ajout TOTAL
    df2.loc["TOTAL"] = {col: total.get(col, "") for col in df2.columns}

    # ------------------------------------------------------
    # COLORATION
    # ------------------------------------------------------
    def color_row(row):
        if row["Type"] == "TOTAL":
            return ["background-color:#dddddd; font-weight:bold; color:black"] * len(row)
        if row["Type"] in COLORS:
            return [f"background-color:{COLORS[row['Type']]}; color:black"] * len(row)
        return [""] * len(row)

    styler = df2.style.apply(color_row, axis=1)

    # ------------------------------------------------------
    # FORMATTEURS SÉCURISES
    # ------------------------------------------------------
    def safe_formatter(pattern):
        return lambda x: pattern.format(x) if isinstance(x, (int, float, np.number)) else x

    fmt = {}

    if "Distance_km" in df2:
        fmt["Distance_km"] = safe_formatter("{:.2f}")
    if "D+" in df2:
        fmt["D+"] = safe_formatter("{:.0f}")
    if "D-" in df2:
        fmt["D-"] = safe_formatter("{:.0f}")
    if "Vitesse_kmh" in df2:
        fmt["Vitesse_kmh"] = safe_formatter("{:.2f}")
    if "Cadence" in df2:
        fmt["Cadence"] = safe_formatter("{:.0f}")
    if "FC" in df2:
        fmt["FC"] = safe_formatter("{:.0f}")
    if "Puissance" in df2:
        fmt["Puissance"] = safe_formatter("{:.0f}")
    if "Equilibre_DG" in df2:
        fmt["Equilibre_DG"] = safe_formatter("{:.1f}")

    styler = styler.format(fmt)

    return styler
