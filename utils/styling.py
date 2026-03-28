import pandas as pd

COLORS = {
    "plat": "#6ec1ff",
    "petite_montee": "#ff9f40",
    "forte_montee": "#ff3b30",
    "petite_descente": "#4cd964",
    "forte_descente": "#2f8f2f"
}

def style_table(df):
    df2 = df.copy()

    # ✅ Garder la colonne Durée brute (float) jusqu'au style
    def format_h_m(x):
        if not isinstance(x, (float, int)):
            return x  # déjà formaté → on ne le traite plus
        h = int(x)
        m = int((x - h) * 60)
        return f"{h}h {m:02d}min"

    # ✅ Nouvelle colonne formatée, l'ancienne reste disponible si besoin
    df2["Durée_fmt"] = df2["Durée"].apply(format_h_m)

    # ✅ Ligne TOTAL — parfaitement cohérente
    total_dur = df2["Durée"].sum()
    df2.loc["TOTAL"] = [
        "TOTAL",
        df2["Distance_km"].sum(),
        df2["D+"].sum(),
        df2["D-"].sum(),
        total_dur,
        format_h_m(total_dur)   # formaté proprement
    ]

    # ✅ On renomme les colonnes pour affichage final
    df2 = df2.rename(columns={"Durée_fmt": "Durée"})

    # ✅ Coloration conditionnelle
    def color_row(row):
        t = row["Type"]
        if t == "TOTAL":
            return ["background-color: #dddddd; color: black; font-weight: bold"] * len(row)
        if t in COLORS:
            return [f"background-color: {COLORS[t]}; color: black"] * len(row)
        return [""] * len(row)

    styler = df2.style.apply(color_row, axis=1)

    # ✅ Formats numériques pour les colonnes pertinentes
    styler = styler.format({
        "Distance_km": "{:.2f}",
        "D+": "{:.0f}",
        "D-": "{:.0f}",
    })

    return styler
