import pandas as pd

# -----------------------------------------------------------
# COULEURS COHÉRENTES AVEC LA CARTE & LES PENTES
# -----------------------------------------------------------
COLORS = {
    "plat": "#6ec1ff",            # bleu clair
    "petite_montee": "#ff9f40",   # orange
    "forte_montee": "#ff3b30",    # rouge
    "petite_descente": "#4cd964", # vert clair
    "forte_descente": "#2f8f2f"   # vert foncé
}

# -----------------------------------------------------------
# FORMAT D'UNE DURÉE (float heures) EN "Hh MMmin"
# -----------------------------------------------------------
def format_h_m(x):
    if isinstance(x, str):
        return x  # déjà formaté
    if x is None:
        return "0h00"
    h = int(x)
    m = int(round((x - h) * 60))
    return f"{h}h {m:02d}min"


# -----------------------------------------------------------
# STYLE DU TABLEAU DÉTAILLÉ
# -----------------------------------------------------------
def style_table(df):
    """
    Transforme le DataFrame des segments en tableau stylé :
    ✅ couleurs par type de segment
    ✅ ligne TOTAL mise en avant
    ✅ formatage de la durée
    ✅ tableau lisible sur mobile
    """

    if df.empty:
        return df.style

    df2 = df.copy()

    # Formatage durée (remplace la colonne "Durée")
    if "Durée" in df2.columns:
        df2["Durée"] = df2["Durée"].apply(format_h_m)

    # ✅ Ajouter ligne TOTAL si absente
    if "TOTAL" not in df2["Type"].values:

        total_distance = df2["Distance_km"].astype(float).sum()
        total_dplus = df2["D+"].astype(float).sum()
        total_dminus = df2["D-"].astype(float).sum()

        # Durée brute totale en heures
        if "Durée_raw" in df2.columns:
            total_dur = df2["Durée_raw"].sum()
        else:
            # fallback : convertir Durée formatée
            total_dur = df["Durée"].astype(float).sum()

        df2.loc[len(df2)] = [
            "TOTAL",
            total_distance,
            total_dplus,
            total_dminus,
            format_h_m(total_dur),
            total_dur if "Durée_raw" in df2.columns else None
        ]

    # ✅ COLORATION CONDITIONS SUR LES LIGNES
    def color_row(row):
        if row["Type"] == "TOTAL":
            return [
                "background-color:#dddddd; color:black; font-weight:bold"
            ] * len(row)

        color = COLORS.get(row["Type"], "#ffffff")
        return [
            f"background-color:{color}; color:black"
        ] * len(row)

    styler = df2.style.apply(color_row, axis=1)

    # ✅ FORMAT DES CHIFFRES
    fmt = {
        "Distance_km": "{:.2f}",
        "D+": "{:.0f}",
        "D-": "{:.0f}",
    }
    styler = styler.format(fmt, na_rep="")

    # ✅ STYLE GLOBAL TABLE (CSS Streamlit-safe)
    styler = styler.set_table_styles([
        {"selector": "th", "props": [
            ("background-color", "#333"),
            ("color", "white"),
            ("font-weight", "bold"),
            ("text-align", "center"),
            ("padding", "6px")
        ]},
        {"selector": "td", "props": [
            ("padding", "6px"),
            ("text-align", "center"),
            ("font-size", "14px")
        ]}
    ])

    return styler
