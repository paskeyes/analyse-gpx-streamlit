import streamlit as st
import pandas as pd
from utils.gpx_parser import parse_gpx_and_compute
from utils.map_tools import build_map
from utils.styling import style_table
from streamlit_folium import st_folium

# -------------------------
# AUTHENTIFICATION (Mot de passe ajouté dans Streamlit Cloud)
# -------------------------
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

# -------------------------
# CONFIG PAGE
# -------------------------
st.set_page_config(
    page_title="Analyse GPX",
    layout="centered",
    initial_sidebar_state="expanded"
)

st.title("🚴 Analyse GPX & Estimation du Temps")

st.divider()

# -------------------------
# PARAMÈTRES AVEC SAUVEGARDE
# -------------------------
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

# Entrées utilisateur
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

# -------------------------
# UPLOAD GPX
# -------------------------
uploaded_file = st.file_uploader("📤 Importer un fichier GPX", type=["gpx"])

if uploaded_file:
    df_segments, profile, total_summary = parse_gpx_and_compute(uploaded_file, params)

    st.subheader("📈 Résumé automatique")
    st.markdown(total_summary["text"])

    col1, col2, col3 = st.columns(3)
    col1.metric("Distance totale", f"{total_summary['distance']:.1f} km")
    col2.metric("Dénivelé positif", f"{total_summary['d+']:.0f} m")
    col3.metric("Temps estimé", f"{total_summary['h_str']}")

    # -------------------------
    # TABLEAU DANS EXPANDER (TT-1)
    # -------------------------

    with st.expander("📊 Tableau détaillé des segments"):
        styled = style_table(df_segments)
        st.write(styled.to_html(), unsafe_allow_html=True)
    
        st.download_button(
            "⬇️ Exporter en CSV",
            df_segments.to_csv(index=False),
            "segments.csv"
        )

    # -------------------------
    # CARTE FOLIUM (en expander)
    # -------------------------
    with st.expander("🗺️ Carte interactive GPX"):
        folium_map = build_map(profile)
        st_folium(folium_map, width=700, height=500)

    # -------------------------
    # PROFIL ALT
    # -------------------------
    st.subheader("📉 Profil altimétrique")
    st.line_chart(profile.set_index("dist_km")["alt"])

else:
    st.info("👉 Importez un fichier GPX pour commencer.")
