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
    """Convertit minutes en 'Hh MMmin'."""
    h = int(minutes // 60)
    m = int(minutes % 60)
    return f"{h}h {m:02d}min"

def style_table(df):
    """
    Style un tableau GPX ou FIT :
    ✅ pas de Temps_h
    ✅ TOTAL dynamique
    ✅ vitesse totale correcte
    ✅ VAM totale vide
    ✅ cadence / FC / puissance moyennes
    """

    df2 = df.copy()

    # ----------------------------------------------------------------------
    # CALCUL DE LA LIGNE TOTAL
    # ----------------------------------------------------------------------

    total = {}

    # Distance totale
    if "Distance_km" in df2.columns:
        total["Distance_km"] = df2["Distance_km"].sum()
    # D+
    if "D+" in df2.columns:
        total["D+"] = df2["D+"].sum()
    # D-
    if "D-" in df2.columns:
        total["D-"] = df2["D-"].sum()

    # Durée totale
    if "Durée" in df2.columns:
        total_minutes = sum(hm_to_minutes(v) for v in df2["Durée"])
        total["Durée"] = minutes_to_hm(total_minutes)

    # Vitesse moyenne totale
    if ("Distance_km" in df2.columns) and ("Durée" in df2.columns):
        dist_tot = df2["Distance_km"].sum()
        min_tot = sum(hm_to_minutes(v) for v in df2["Durée"])
        if min_tot > 0:
            total["Vitesse_kmh"] = round(dist_tot / (min_tot / 60), 2)
        else:
            total["Vitesse_kmh"] = ""

    # VAM totale = vide
    if "VAM_mh" in df2.columns:
        total["VAM_mh"] = ""

    # Cadence moyenne totale
    if "Cadence" in df2.columns:
        total["Cadence"] = int(df2["Cadence"].mean()) if len(df2["Cadence"].dropna()) else ""

    # FC moyenne totale
    if "FC" in df2.columns:
        total["FC"] = int(df2["FC"].mean()) if len(df2["FC"].dropna()) else ""

    # Puissance moyenne totale
    if "Puissance" in df2.columns:
        total["Puissance"] = int(df2["Puissance"].mean()) if len(df2["Puissance"].dropna()) else ""

    # Equilibre moyen
    if "Equilibre_DG" in df2.columns:
        total["Equilibre_DG"] = round(df2["Equilibre_DG"].mean(), 1)

    # Type = TOTAL
    total["Type"] = "TOTAL"

    # ----------------------------------------------------------------------
    # AJOUT DE LA LIGNE TOTAL
    # ----------------------------------------------------------------------
    df2.loc["TOTAL"] = {col: total.get(col, "") for col in df2.columns}

    # ----------------------------------------------------------------------
    # COLORATION
    # ----------------------------------------------------------------------
    def color_row(row):
        if row["Type"] == "TOTAL":
            return ["background-color:#dddddd; color:black; font-weight:bold"] * len(row)
        if row["Type"] in COLORS:
            return [f"background-color:{COLORS[row['Type']]}; color:black"] * len(row)
        return [""] * len(row)

    styler = df2.style.apply(color_row, axis=1)

    # ----------------------------------------------------------------------
    # FORMATAGE
    # ----------------------------------------------------------------------
    fmt = {}

    if "Distance_km" in df2: fmt["Distance_km"] = "{:.2f}"
    if "D+" in df2:          fmt["D+"] = "{:.0f}"
    if "D-" in df2:          fmt["D-"] = "{:.0f}"
    if "Vitesse_kmh" in df2: fmt["Vitesse_kmh"] = "{:.2f}"
    if "Cadence" in df2:     fmt["Cadence"] = "{:.0f}"
    if "FC" in df2:          fmt["FC"] = "{:.0f}"
    if "Puissance" in df2:   fmt["Puissance"] = "{:.0f}"
    if "Equilibre_DG" in df2:fmt["Equilibre_DG"] = "{:.1f}"

    styler = styler.format(fmt)

    return styler
