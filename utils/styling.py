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

    # Ajout de TOTAL
    df2.loc["TOTAL"] = [
        "TOTAL",
        df2["Distance_km"].sum(),
        df2["D+"].sum(),
        df2["D-"].sum(),
        df2["Durée_h"].sum(),
    ]

    def color_row(row):
        if row["Type"] == "TOTAL":
            return ["background-color: #dddddd; color: black; font-weight: bold"] * len(row)
        if row["Type"] in COLORS:
            return [f"background-color: {COLORS[row['Type']]}; color: black"] * len(row)
        return [""] * len(row)

    styler = df2.style.apply(color_row, axis=1)

    # ✅ Remplace set_precision (incompatible)
    styler = styler.format({
        "Distance_km": "{:.2f}",
        "D+": "{:.2f}",
        "D-": "{:.2f}",
        "Durée_h": "{:.3f}"
    })

    return styler
