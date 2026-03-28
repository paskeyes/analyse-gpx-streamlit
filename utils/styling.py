import pandas as pd

COLORS = {
    "plat": "#6ec1ff",
    "petite_montee": "#ff9f40",
    "forte_montee": "#ff3b30",
    "petite_descente": "#4cd964",
    "forte_descente": "#2f8f2f"
}

def style_table(df):
    # Toujours travailler sur une copie
    df2 = df.copy()

    # ✅ Colonne Durée formatée en HhMM
    def format_h_m(x):
        h = int(x)
        m = int((x - h) * 60)
        return f"{h}h {m:02d}min"

    df2["Durée"] = df2["Durée_h"].apply(format_h_m)

    # ✅ AJOUT DE LA LIGNE TOTAL (6 colonnes EXACTES)
    df2.loc["TOTAL"] = [
        "TOTAL",
        df2["Distance_km"].sum(),
        df2["D+"].sum(),
        df2["D-"].sum(),
        df2["Durée_h"].sum(),
        format_h_m(df2["Durée_h"].sum())   # ✅ colonne Durée formatée
    ]

    # ✅ COLORATION CONDITIONNELLE
    def color_row(row):
        t = row["Type"]
        if t == "TOTAL":
            return ["background-color: #dddddd; color: black; font-weight: bold"] * len(row)

        if t in COLORS:
            return [f"background-color: {COLORS[t]}; color: black"] * len(row)

        return [""] * len(row)

    styler = df2.style.apply(color_row, axis=1)

    # ✅ Format Pandas >= 2.0
    styler = styler.format({
        "Distance_km": "{:.2f}",
        "D+": "{:.0f}",
        "D-": "{:.0f}",
        "Durée_h": "{:.3f}"
    })

    return styler
