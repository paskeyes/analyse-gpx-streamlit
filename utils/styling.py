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
    Style un tableau pour GPX ou FIT :
    - Ajoute colonne Durée formatée HhMM
    - Ajoute ligne TOTAL
    - Applique coloration par type
    - Formate les colonnes numériques (2 ou 1 décimales)
    """

    # Copie de sécurité
    df2 = df.copy()

    # ✅ Durée_formatée (à partir de Temps_h)
    def format_h_m(val):
        if isinstance(val, str):
            return val  # déjà formaté
        h = int(val)
        m = int((val - h) * 60)
        return f"{h}h {m:02d}min"

    # Toujours créer la colonne Durée
    if "Temps_h" in df2.columns:
        df2["Durée"] = df2["Temps_h"].apply(format_h_m)
    else:
        df2["Durée"] = ""

    # ✅ Ligne TOTAL — calcul dynamique selon les colonnes réellement présentes
    total_row = []
    for col in df2.columns:

        if col == "Type":
            total_row.append("TOTAL")

        elif col in ["Distance_km", "D+", "D-", "Temps_h"]:
            total_row.append(df2[col].astype(float).sum())

        elif col in ["Vitesse_kmh", "VAM_mh", "Cadence", "FC", "Puissance", "Equilibre_DG"]:
            # moyenne simple
            total_row.append(df2[col].astype(float).mean() if df2[col].count() > 0 else 0)

        elif col == "Durée":
            # on reformate la durée totale en HhMM
            total_row.append(format_h_m(df2["Temps_h"].sum()))

        else:
            total_row.append("")

    # Ajout ligne TOTAL
    df2.loc["TOTAL"] = total_row

    # ✅ Coloration par ligne
    def color_row(row):
        if row["Type"] == "TOTAL":
            return ["background-color: #dddddd; color: black; font-weight: bold"] * len(row)

        t = row["Type"]
        if t in COLORS:
            return [f"background-color: {COLORS[t]}; color: black"] * len(row)

        return [""] * len(row)

    styler = df2.style.apply(color_row, axis=1)

    # ✅ Format numérique selon les colonnes existantes
    format_dict = {}

    if "Distance_km" in df2:
        format_dict["Distance_km"] = "{:.2f}"
    if "D+" in df2:
        format_dict["D+"] = "{:.0f}"
    if "D-" in df2:
        format_dict["D-"] = "{:.0f}"
    if "Temps_h" in df2:
        format_dict["Temps_h"] = "{:.3f}"
    if "Vitesse_kmh" in df2:
        format_dict["Vitesse_kmh"] = "{:.2f}"
    if "VAM_mh" in df2:
        format_dict["VAM_mh"] = "{:.1f}"
    if "Cadence" in df2:
        format_dict["Cadence"] = "{:.0f}"
    if "FC" in df2:
        format_dict["FC"] = "{:.0f}"
    if "Puissance" in df2:
        format_dict["Puissance"] = "{:.0f}"
    if "Equilibre_DG" in df2:
        format_dict["Equilibre_DG"] = "{:.1f}"

    styler = styler.format(format_dict)

    return styler
