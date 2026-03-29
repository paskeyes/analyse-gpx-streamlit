import pandas as pd

# Couleurs par type de segment
COLORS = {
    "plat": "#6ec1ff",
    "petite_montee": "#ff9f40",
    "forte_montee": "#ff3b30",
    "petite_descente": "#4cd964",
    "forte_descente": "#2f8f2f"
}

def style_table(df):
    """
    Style un tableau GPX ou FIT :
    ✅ n'utilise jamais Temps_h (car toujours supprimé dans df_display)
    ✅ ajoute une ligne TOTAL cohérente selon les colonnes présentes
    ✅ coloration par type
    ✅ formatage propre
    """

    df2 = df.copy()

    # ----------------------------------------------------------
    # ✅ Construction de la ligne TOTAL en fonction des colonnes présentes
    # ----------------------------------------------------------
    total_row = []

    for col in df2.columns:

        if col == "Type":
            total_row.append("TOTAL")

        elif col in ["Distance_km", "D+", "D-", "Vitesse_kmh", "VAM_mh"]:
            total_row.append(df2[col].astype(float).sum())

        elif col in ["Cadence", "FC", "Puissance", "Equilibre_DG"]:
            total_row.append(df2[col].astype(float).mean() if df2[col].count() > 0 else 0)

        elif col == "Durée":
            # Durée totale = somme convertie par le parser
            total_row.append(df2[col][:-1].tolist() + [df2[col].iloc[-1]]) 
            # mais comme Durée est déjà dans df2, on mettra juste TOTAL à la fin
            total_row[-1] = ""   # laissé vide pour éviter incohérences

        else:
            total_row.append("")

    df2.loc["TOTAL"] = total_row

    # ----------------------------------------------------------
    # ✅ Coloration par type
    # ----------------------------------------------------------
    def color_row(row):
        if row["Type"] == "TOTAL":
            return ["background-color:#dddddd; color:black; font-weight:bold"] * len(row)

        t = row["Type"]
        if t in COLORS:
            return [f"background-color:{COLORS[t]}; color:black"] * len(row)

        return [""] * len(row)

    styler = df2.style.apply(color_row, axis=1)

    # ----------------------------------------------------------
    # ✅ Formatage
    # ----------------------------------------------------------
    fmt = {}

    if "Distance_km" in df2:
        fmt["Distance_km"] = "{:.2f}"
    if "D+" in df2:
        fmt["D+"] = "{:.0f}"
    if "D-" in df2:
        fmt["D-"] = "{:.0f}"
    if "Vitesse_kmh" in df2:
        fmt["Vitesse_kmh"] = "{:.2f}"
    if "VAM_mh" in df2:
        fmt["VAM_mh"] = "{:.1f}"
    if "Cadence" in df2:
        fmt["Cadence"] = "{:.0f}"
    if "FC" in df2:
        fmt["FC"] = "{:.0f}"
    if "Puissance" in df2:
        fmt["Puissance"] = "{:.0f}"
    if "Equilibre_DG" in df2:
        fmt["Equilibre_DG"] = "{:.1f}"

    styler = styler.format(fmt)

    return styler
