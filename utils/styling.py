import pandas as pd

COLORS = {
    "plat": "#6ec1ff",
    "petite_montee": "#ff9f40",
    "forte_montee": "#ff3b30",
    "petite_descente": "#4cd964",
    "forte_descente": "#2f8f2f"
}

def style_table(df):
    # Copie de sécurité
    df2 = df.copy()

    # ✅ FORMATAGE DURÉE EN Hh MMmin
    def format_h_m(x):
        if isinstance(x, str):
            return x    # déjà formaté → ne pas retraiter
        h = int(x)
        m = int((x - h) * 60)
        return f"{h}h {m:02d}min"

    # ✅ Convertir Durée brute en Durée formatée
    df2["Durée"] = df2["Durée"].apply(format_h_m)

    # ✅ AJOUT LIGNE TOTAL — EXACTEMENT LES MÊMES 5 COLONNES
    total_distance = df2["Distance_km"].astype(float).sum()
    total_dplus = df2["D+"].astype(float).sum()
    total_dminus = df2["D-"].astype(float).sum()

    # durée totale
    raw_total_duration = df["Durée"].replace("", 0)
    total_duration_h = df["Durée_raw"].sum() if "Durée_raw" in df else df["Durée"].sum()

    df2.loc["TOTAL"] = [
        "TOTAL",
        total_distance,
        total_dplus,
        total_dminus,
        format_h_m(total_duration_h)   # ⭐ Formaté directement
    ]

    # ✅ COLORATION CONDITIONNELLE
    def color_row(row):
        if row["Type"] == "TOTAL":
            return ["background-color: #dddddd; color: black; font-weight: bold"] * len(row)

        color = COLORS.get(row["Type"], "")
        return [f"background-color: {color}; color: black"] * len(row)

    styler = df2.style.apply(color_row, axis=1)

    # ✅ Format chiffres
    styler = styler.format({
        "Distance_km": "{:.2f}",
        "D+": "{:.0f}",
        "D-": "{:.0f}",
    })

    return styler
