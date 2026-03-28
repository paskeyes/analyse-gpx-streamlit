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
    df2.loc["TOTAL"] = [
        "TOTAL",
        df2["Distance_km"].sum(),
        df2["D+"].sum(),
        df2["D-"].sum(),
        df2["Durée_h"].sum(),
    ]

    def color_row(row):
        t = row["Type"]
        if t == "TOTAL":
            return ["background-color: #ddd; font-weight: bold"] * len(row)
        if t in COLORS:
            return [f"background-color: {COLORS[t]}; color: black"] * len(row)
        return [""] * len(row)

    return df2.style.apply(color_row, axis=1).set_precision(2)
