# 🚴 Application d’analyse GPX & FIT

## Estimation de parcours et analyse détaillée des sorties réelles  
### *(Approche TrainingPeaks‑like)*

Cette application Streamlit fournit **deux modes complémentaires**, basés sur des algorithmes cohérents mais adaptés à la nature des données traitées (**GPX** vs **FIT**).

---

## ✅ Modes disponibles

### 🔵 Mode 1 — Estimation GPX (parcours théorique)

- Analyse d’un fichier **GPX**  
  *(OpenRunner, Komoot, Garmin, etc.)*
- Traitement **point‑par‑point** du parcours :
  - distance cumulée
  - altitude
  - pente instantanée (%)

Le point‑par‑point est **intégralement conservé** pour :
- la carte
- la coloration par pente
- le profil altimétrique

#### 📊 Résultats produits

**Tableau synthétique GPX par type de terrain**
- plat
- petites montées / fortes montées
- petites descentes / fortes descentes

**Calculs**
- distances
- D+ / D−
- temps estimés à partir de vitesses et de VAM paramétrables

**Tableau détaillé des montées (GPX)**
- détection automatique des montées continues
- identification *TrainingPeaks‑like*
- durée **estimée** par montée
- catégories :
  - HC
  - 1 / 2 / 3 / 4

**Affichages**
- carte Folium colorée par pente instantanée
- profil altimétrique
- tableaux stylés

---

### 🔵 Mode 2 — Analyse FIT (sortie réalisée)

- Analyse d’un fichier **FIT** issu d’une activité réelle  
  *(Garmin, Wahoo, Hammerhead, Zwift, etc.)*
- Extraction directe des données :
  - position
  - altitude barométrique lissée
  - vitesse
  - cadence
  - fréquence cardiaque
  - puissance
  - équilibre gauche / droite

- Traitement à **haute résolution temporelle** (≈ 1 Hz), optimisé pour de gros volumes de points

#### 📊 Résultats produits

**Tableau global FIT par type de terrain**
- distances
- D+ / D−
- durée roulée
- vitesse moyenne réelle
- cadence moyenne
- FC moyenne
- puissance moyenne

**Tableau détaillé des montées (FIT)**
- détection des montées continues par **gradient cumulé**
- fusion des segments :
  - replats tolérés
  - micro‑descentes tolérées
- filtrage *TrainingPeaks‑like* :
  - distance minimale
  - D+ minimal
  - pente moyenne minimale

**Métriques par montée**
- distance
- D+
- pente moyenne
- VAM réelle
- vitesse
- cadence
- FC
- puissance

**Affichages**
- carte Folium colorée par pente instantanée
- profil altimétrique FIT
- tableaux stylés

---

## ✅ Algorithmes et principes communs (GPX & FIT)

### 📐 Calculs de pente

**Pente instantanée (`pct`)**
- utilisée uniquement pour la carte
- filtrage adapté au type de données :
  - **GPX** : filtrage GPS plus strict
  - **FIT** : filtrage barométrique léger (1 Hz)

**Gradient cumulé (fenêtre 200 m)**
- utilisé pour la segmentation
- même logique algorithmique pour GPX et FIT

---

### ⛰️ Détection des montées (*TrainingPeaks‑like*)

**Pipeline commun**
1. segmentation primaire par gradient
2. fusion des segments montants adjacents :
   - tolérance sur les replats
   - tolérance sur les micro‑descentes
3. filtrage final par critères globaux :
   - distance minimale
   - D+ minimal
   - pente moyenne minimale

Les **seuils sont adaptés entre GPX et FIT** pour tenir compte :
- de la résolution temporelle
- du bruit altimétrique
- de la nature théorique (GPX) vs réelle (FIT) des données

---

## ✅ Architecture du projet

```text
analyse-gpx-streamlit/
│
├── app.py
│
├── utils/
│   ├── gpx_parser.py          # analyse GPX + estimation + montées GPX
│   ├── fit_parser.py          # analyse FIT + montées FIT optimisées
│   ├── map_tools.py           # génération carte Folium (pente instantanée)
│   └── styling.py             # mise en forme tableaux + ligne TOTAL
│
└── README.md
