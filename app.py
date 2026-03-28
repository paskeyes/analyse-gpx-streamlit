import streamlit as st
import pandas as pd
import plotly.express as px
from streamlit_folium import st_folium

from utils.gpx_parser import parse_gpx_and_compute
from utils.map_tools import build_map
from utils.styling import style_table

# =====================================================================
# 🔐 AUTHENTIFICATION SIMPLIFIÉE (mot de passe défini dans Streamlit Cloud > Secrets)
# =====================================================================
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

# =====================================================================
# ✅ CONFIGURATION DE LA PAGE
# =====================================================================
st.set_page_config(
    page_title="Analyse GPX",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.title("🚴 Analyse GPX & Estimation du Temps")
st.caption("Application optimisée mobile & WhatsApp — Profils lissés — Carte colorée par pente")

st.divider()

# =====================================================================
# ✅ PARAMÈTRES AVEC SAUVEGARDE (5.1)
# =====================================================================
st.sidebar.header("⚙️ Paramètres personnalisables")

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

# =====================================================================
# ✅ ZONES DE PENTES (affichage explicatif)
# =====================================================================
st.subheader("📐 Segmentation des pentes (%) utilisée pour l'analyse")

st.markdown("""
- **Plat** : -1% → +1%  
- **Petite montée** : +1% → +5%  
- **Forte montée** : +5% → +∞%  
- **Petite descente** : -5% → -1%  
- **Forte descente** : -∞% → -5%  
""")

# =====================================================================
# ✅ ZONE UPLOAD GPX
# =====================================================================
uploaded_file = st.file_uploader("📤 Importer un fichier GPX", type=["gpx"])

if not uploaded_file:
    st.info("👉 Importez un fichier GPX pour commencer.")
    st.stop()

# =====================================================================
# ✅ PARSING + ANALYSE GPX
# =====================================================================
df_segments, profile_df, total_summary = parse_gpx_and_compute(uploaded_file, params)

# =====================================================================
# ✅ RÉSUMÉ AUTOMATIQUE (7)
# =====================================================================
st.subheader("📈 Résumé automatique")
st.markdown(total_summary["text"])

col1, col2, col3 = st.columns(3)

col1.metric("Distance totale", f"{total_summary['distance']:.1f} km")
col2.metric("Dénivelé positif", f"{total_summary['d+']:.0f} m")
col3.metric("Temps estimé", f"{total_summary['h_str']}")

# =====================================================================
# ✅ TABLEAU STYLÉ (1.2)
# =====================================================================
with st.expander("📊 Tableau détaillé des segments"):
    styled = style_table(df_segments)
    st.write(styled.to_html(), unsafe_allow_html=True)

    st.download_button(
        "⬇️ Exporter en CSV",
        df_segments.to_csv(index=False),
        "segments.csv"
    )

# =====================================================================
# ✅ CARTE FOLIUM AMÉLIORÉE (6.2)
# =====================================================================
with st.expander("🗺️ Carte interactive colorée par pente (%)"):
    folium_map = build_map(profile_df)
    st_folium(folium_map, width=900, height=550)

# =====================================================================
# ✅ PROFIL ALTIMÉTRIQUE PLOTLY INTERACTIF ET LISSÉ (Option 2 + A)
# =====================================================================
st.subheader("📉 Profil altimétrique interactif (lissé)")

# Courbe lissée déjà calculée dans gpx_parser
fig = px.scatter(
    profile_df,
    x="dist_km",
    y="alt",
    color="pct",
    color_continuous_scale=[
        "#2f8f2f",  # forte descente
        "#4cd964",  # petite descente
        "#6ec1ff",  # plat
        "#ff9f40",  # petite montée
        "#ff3b30"   # forte montée
    ],
    labels={"dist_km": "Distance (km)", "alt": "Altitude (m)", "pct": "Pente (%)"},
    title="Profil altimétrique coloré par pente (%)"
)

fig.update_traces(marker=dict(size=5), mode="lines+markers")
fig.update_layout(height=500, template="plotly_white")

st.plotly_chart(fig, use_container_width=True)
