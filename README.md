✅ README.md — Analyse GPX & Estimation du Temps
🚴 Analyse GPX — Web App Streamlit
Analyse complète de fichiers GPX : distances, dénivelés, segmentation des pentes, estimation de temps, carte interactive & profil altimétrique.
Cette application permet d’analyser n’importe quel fichier GPX de parcours vélo, running, trail ou randonnée, d’en extraire les segments par pente, de calculer les temps estimés selon vos paramètres personnels, et d’afficher une carte et un profil altimétrique interactif.

⭐ Fonctionnalités principales
✅ Analyse GPX robuste

Interpolation des altitudes manquantes
Lissage Savitzky–Golay
Anti-outliers
Pente calculée via distance haversine (fiable)
Segmentation en 5 types :

Plat (−1% à +1%)
Petite montée (+1% à +5%)
Forte montée (> +5%)
Petite descente (−5% à −1%)
Forte descente (< −5%)



✅ Estimation du temps personnalisée
Vous pouvez ajuster dans la sidebar :

Vitesse sur plat
Vitesse en petite descente
Vitesse en forte descente
VAM petite montée (m/h)
VAM forte montée (m/h)
✅ Un bouton permet de sauvegarder vos paramètres (persistance session Streamlit).
✅ Un bouton permet de les réinitialiser.

✅ Visualisations avancées

Profil altimétrique Plotly (interactif, zoom, couleur par pente)
Carte Folium colorée par pente (%)
Tableau stylé coloré selon le type de segment
Résumé automatique intelligent

✅ Fonctionnement 100% mobile
L’app est optimisée pour :

smartphone
usage depuis WhatsApp
écrans étroits
thèmes Streamlit modernes

✅ Sécurité
Un mot de passe protège l’accès (géré via la section Secrets de Streamlit Cloud).

🎯 Exemple de sortie

Distance totale : XX.X km
D+ total : XXX m
Temps estimé : XhXX
Tableau segmenté : plat / montées / descentes
Carte interactive du parcours
Profil altimétrique coloré


📁 Structure du projet
📦 project/
 ├── app.py
 ├── requirements.txt
 └── utils/
      ├── gpx_parser.py
      ├── map_tools.py
      └── styling.py

app.py
Interface principale Streamlit
(Upload GPX → analyse → affichage tableau + carte + profil)
utils/gpx_parser.py

Lecture GPX
Interpolation & lissage altitudes
Filtre anti‑noise
Segmentation par pente
Résumé automatique
Construction du profile_df

utils/map_tools.py

Carte Folium
Segments colorés selon pente
Légende dynamique

utils/styling.py

Mise en forme du tableau
Coloration selon type de segment
Ligne TOTAL stylée


🚀 Déploiement sur Streamlit Cloud

Créer un repository (public ou privé) sur GitHub
Ajouter :

app.py
utils/
requirements.txt
README.md


Aller sur https://streamlit.io/cloud
Connecter votre GitHub
Cliquer New app
Sélectionner app.py
Déployer 🚀
