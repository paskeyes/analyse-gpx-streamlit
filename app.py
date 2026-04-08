import streamlit as st
import pandas as pd
from utils.gpx_parser import parse_gpx_and_compute
from utils.fit_parser import parse_fit_and_compute
from utils.map_tools import build_map
from utils.styling import style_table
from streamlit_folium import st_folium

# ----------------------------------------------------------
# AUTHENTIFICATION
# ----------------------------------------------------------
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

if not st.session_state.authenticated:
    pwd = st.text_input("🔐 Entrez le mot de passe :", type="password")
    if pwd:
        if "password" in st.secrets and pwd == st.secrets["password"]:
            st.session_state.authenticated = True
        else:
            st.error("❌ Mot de passe incorrect.")
            st.stop()
    else:
        st.stop()

# ----------------------------------------------------------
# CONFIG PAGE
# ----------------------------------------------------------
st.set_page_config(
    page_title="Analyse GPX & FIT",
    layout="centered",
    initial_sidebar_state="expanded"
)

#st.title("🚴 Analyse GPX & FIT — Mode Dual || par PaskEyes rev 1.0")

st.markdown(
    """
    <div style="display: flex; flex-direction: column;">
        <div style="font-size: 2.2rem; font-weight: 700;">
            🚴 Analyse GPX &amp; FIT — Mode Dual
        </div>
        <div style="font-size: 0.9rem; text-align: right; color: #666;">
            par PaskEyes — rev 1.0
        </div>
    </div>
    """,
    unsafe_allow_html=True
)


# ----------------------------------------------------------
# CHOIX DU MODE
# ----------------------------------------------------------
mode = st.radio(
    "Choisir un mode d’utilisation :",
    ["📍 Estimation GPX", "📈 Analyse FIT"]
)

st.divider()

# ==========================================================
# ======================= MODE GPX ==========================
# ==========================================================
if mode == "📍 Estimation GPX":

    st.header("📍 Estimation d’un parcours GPX")

    st.sidebar.header("⚙️ Paramètres Vitesse & VAM")

    if "params" not in st.session_state:
        st.session_state.params = {
            "plat_speed": 27,
            "petite_descente_speed": 30,
            "forte_descente_speed": 40,
            "petite_montee_vam": 1000,
            "forte_montee_vam": 800
        }

    params = st.session_state.params

    params["plat_speed"] = st.sidebar.number_input("Vitesse sur plat (km/h)", 5, 60, params["plat_speed"])
    params["petite_descente_speed"] = st.sidebar.number_input("Vitesse petite descente (km/h)", 5, 80, params["petite_descente_speed"])
    params["forte_descente_speed"] = st.sidebar.number_input("Vitesse forte descente (km/h)", 5, 100, params["forte_descente_speed"])
    params["petite_montee_vam"] = st.sidebar.number_input("VAM petite montée (m/h)", 200, 3000, params["petite_montee_vam"])
    params["forte_montee_vam"] = st.sidebar.number_input("VAM forte montée (m/h)", 200, 3000, params["forte_montee_vam"])

    colA, colB = st.sidebar.columns(2)
    if colA.button("✅ Sauver par défaut"):
        st.success("✅ Paramètres sauvegardés.")
    if colB.button("♻️ Réinitialiser"):
        st.session_state.params = {
            "plat_speed": 27,
            "petite_descente_speed": 30,
            "forte_descente_speed": 40,
            "petite_montee_vam": 1000,
            "forte_montee_vam": 800
        }
        st.rerun()

    # ------------------------------
    # Upload GPX
    # ------------------------------
    uploaded_file = st.file_uploader("📤 Importer un fichier GPX", type=["gpx"])

    if uploaded_file:
        df_segments, profile, total_summary = parse_gpx_and_compute(uploaded_file, params)
        df_gpx_montees = total_summary.get("montees")
        
        # Résumé
        st.subheader("📈 Résumé automatique")
        st.markdown(total_summary["text"])

        col1, col2, col3 = st.columns(3)
        col1.metric("Distance totale", f"{total_summary['distance']:.1f} km")
        col2.metric("Dénivelé positif", f"{total_summary['d+']:.0f} m")
        col3.metric("Temps estimé", total_summary['h_str'])

        # Tableau GPX
        with st.expander("📊 Tableau détaillé des segments"):

            # ✅ On masque Temps_h
            df_display = df_segments.drop(columns=["Temps_h"])

            styled = style_table(df_display)
            st.write(styled.to_html(), unsafe_allow_html=True)

            # ✅ Export CSV : même colonnes que tableau affiché
            st.download_button(
                "⬇️ Exporter en CSV",
                df_display.to_csv(index=False),
                "segments_gpx.csv"
            )

        
        # ------------------------------------------------------
        # ✅ TABLEAU DÉTAILLÉ DES MONTÉES (GPX – estimées)
        # ------------------------------------------------------
        if df_gpx_montees is not None and len(df_gpx_montees) > 0:
        
            st.subheader("⛰️ Détail des montées (GPX – estimation)")
        
            df_gpx_montees_display = df_gpx_montees.copy()
        
            # ✅ styling.py exige la colonne "Type"
            df_gpx_montees_display["Type"] = df_gpx_montees_display["Montée"]
        
            styled_gpx_montees = style_table(df_gpx_montees_display)
            st.write(styled_gpx_montees.to_html(), unsafe_allow_html=True)
        
            st.download_button(
                "⬇️ Exporter montées GPX (CSV)",
                df_gpx_montees_display.to_csv(index=False),
                "gpx_montees.csv"
            )
        
        else:
            st.info("Aucune montée significative détectée sur ce parcours.")


        # ------------------------------------------------------        
        # Carte
        # ------------------------------------------------------
        with st.expander("🗺️ Carte interactive GPX"):
            folium_map = build_map(profile)
            st_folium(folium_map, width=700, height=500)

        # Profil altitude
        st.subheader("📉 Profil altimétrique")
        st.line_chart(profile.set_index("dist_km")["alt"])




# ==========================================================
# ======================= MODE FIT ==========================
# ==========================================================
if mode == "📈 Analyse FIT":

    st.header("📈 Analyse d’une sortie FIT")

    uploaded_fit = st.file_uploader("📤 Importer un fichier FIT", type=["fit"])

    if uploaded_fit:

        # ✅ Le nouveau parser renvoie 3 objets, pas 2
        df_global, df_detail, profile_fit = parse_fit_and_compute(uploaded_fit)

        # ✅ Correction carte : profile_fit doit avoir "dist_km"
        if "dist_km" not in profile_fit.columns:
            if "dist" in profile_fit.columns:
                profile_fit = profile_fit.rename(columns={"dist": "dist_km"})

        # ------------------------------------------------------
        # ✅ TABLEAU GLOBAL (Montées / Plats / Descentes)
        # ------------------------------------------------------
        st.subheader("📊 Synthèse globale (Montées / Plats / Descentes)")

        df_global_display = df_global.copy()

        # ✅ Pas de "Temps_h" dans df_global → pas de drop inutile
        df_global_display = df_global_display.drop(columns=["Durée_h"], errors="ignore")

        styled_global = style_table(df_global_display)
        st.write(styled_global.to_html(), unsafe_allow_html=True)

        st.download_button(
            "⬇️ Exporter synthèse (CSV)",
            df_global_display.to_csv(index=False),
            "fit_global.csv"
        )

        st.divider()

        # ------------------------------------------------------
        # ✅ TABLEAU DÉTAILLÉ DES MONTÉES
        # ------------------------------------------------------
        st.subheader("⛰️ Détail des montées détectées")

        if df_detail is not None and len(df_detail) > 0:

            df_detail_display = df_detail.copy()

            # ✅ styling.py exige la colonne “Type”
            df_detail_display["Type"] = df_detail_display["Montée"]

            df_detail_display = df_detail_display.drop(columns=["Durée_h"], errors="ignore")

            styled_detail = style_table(df_detail_display)
            st.write(styled_detail.to_html(), unsafe_allow_html=True)

            st.download_button(
                "⬇️ Exporter montées (CSV)",
                df_detail_display.to_csv(index=False),
                "fit_montees.csv"
            )

        else:
            st.info("Aucune montée significative détectée.")

        st.divider()

        # ------------------------------------------------------
        # ✅ CARTE FIT
        # ------------------------------------------------------
        with st.expander("🗺️ Carte interactive FIT"):
            
            #st.write("FIT columns:", list(profile_fit.columns))
            #st.write("FIT head:", profile_fit.head(3))
            #if "pct" in profile_fit.columns:
            #    st.write("pct describe:", profile_fit["pct"].describe())
            #    st.write("pct non-plat count (|pct|>1):", int((profile_fit["pct"].abs() > 1).sum()))
            #else:
            #    st.error("⚠️ colonne 'pct' absente dans profile_fit")
            
            folium_map = build_map(profile_fit)
            st_folium(folium_map, width=700, height=500)

        # ------------------------------------------------------
        # ✅ PROFIL ALT FIT
        # ------------------------------------------------------
        st.subheader("📉 Profil altimétrique FIT")
        st.line_chart(profile_fit.set_index("dist_km")["alt"])
