# 🚴 Application d’analyse GPX & FIT
### *Prédiction de temps sur parcours + analyse avancée des sorties réelles*

Cette application Streamlit permet :

✅ **Mode 1 – Estimation GPX**  
– Analyse un fichier GPX (OpenRunner, Komoot, Garmin…)  
– Segmente automatiquement le parcours : plat, montées, descentes  
– Calcule : distances, D+, D−, VAM, vitesse estimée  
– Produit une **prévision réaliste du temps total**  
– Affiche :  
  • tableau synthétique  
  • profil altimétrique  
  • carte Folium colorée par pente  

✅ **Mode 2 – Analyse FIT (sortie réelle)**  
– Analyse un fichier FIT d’une activité réelle (Garmin, Wahoo, Hammerhead, Zwift…)  
– Segmente selon les mêmes règles de pente qu’en GPX  
– Calcule :  
  • vitesse moyenne (km/h)  
  • VAM (m/h)  
  • cadence moyenne (rpm)  
  • fréquence cardiaque moyenne (bpm)  
  • puissance moyenne (W)  
  • équilibre droite/gauche (%, 1 décimale)  
– Affiche :  
  • tableau complet par type de segment  
  • profil altimétrique  
  • carte Folium colorée par pente  

---

# ✅ 1. Fonctionnalités en détail

## 🔵 Mode GPX – Estimation d’un parcours
- Analyse point‑à‑point du fichier GPX  
- Filtrage du bruit GPS :  
  • déplacements < 0,5 m ignorés  
  • variations alt < 1 m ignorées  
- Classification selon la pente (%) :
  - **Plat** : -1 → +1  
  - **Petite montée** : +1 → +5  
  - **Forte montée** : > +5  
  - **Petite descente** : -1 → -5  
  - **Forte descente** : < -5  
- Calcul de :  
  • D+, D−  
  • distances segmentées  
  • temps estimés selon vitesse/VAM configurables  
- Affichage :  
  • tableau stylé coloré  
  • carte Folium  
  • profil altitude  

---

## 🔵 Mode FIT – Analyse d’une sortie réelle
- Extraction directe des données FIT :  
  • position  
  • altitude  
  • vitesse  
  • cadence  
  • fréquence cardiaque  
  • puissance  
  • left/right balance  
- Même classification par pente que pour GPX  
- Calcul de métriques par segment :  
  • distance  
  • D+ / D−  
  • temps  
  • vitesse moyenne  
  • VAM (montées uniquement)  
  • cadence moyenne  
  • FC moyenne  
  • puissance moyenne  
  • équilibre droite/gauche  
- Affichage :  
  • tableau stylé  
  • carte interactive  
  • profil altitude  

---

# ✅ 2. Architecture du projet







## 🚧 Roadmap (Fonctionnalités prévues)

### ✅ Court terme (1–2 semaines)
- [ ] Ajouter légende couleur sur carte
- [ ] le calcul de durée FIT ne doit pas compter le temps où l'on est à l'arrêt (vitesse = 0)
- [ ] la carte doit s'ouvrir en zoomant sur l'itinéraire pour avoir la meilleure vue centrée.
- [ ] sur les deux modes, rajouter un tableau détaillé en indiquant les montées1/2/3... ou plats ou descentes...
- [ ] ajouter sur le FIT => la courbe de puissance en fonction des km
- [ ] ajouter sur le FIT => une courbe des VAM en fonction des durées de montées : chaque courbe doit avoir la même couleurs mais avec une nuance entre les numéros de montées, et distinguer petite et grande montée
- [ ] 
