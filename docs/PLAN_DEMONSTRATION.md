# Trame de démonstration (10 minutes)

## Présentation technique — 8 minutes

1. **Contexte et architecture (45 s)** : deux sources, séparation brut/nettoyé,
   flux Selenium → pandas → SQL → Streamlit.
2. **Scraper Books (1 min 15)** : pagination complète, accès aux détails, neuf
   variables, attentes Selenium et dédoublonnage.
3. **Scraper Gaaraas (1 min)** : cartes d'annonces, borne 100 pages, arrêt sur
   fin réelle de pagination, extraction des sept variables.
4. **Nettoyage (1 min)** : conversions prix/année/km/note, valeurs manquantes,
   contrôles de cohérence et doublons.
5. **Base SQL (45 s)** : tables, clés uniques et UPSERT.
6. **Application et dashboards (1 min 30)** : navigation, filtres, indicateurs,
   graphiques et téléchargements.
7. **Formulaires (1 min 15)** : XLSForm Kobo puis Google Sheet → Apps Script →
   Google Forms, logs, liens et calcul de satisfaction.
8. **Limites et déploiement (30 s)** : pagination Gaaraas réelle, contraintes de
   Chromium, secrets et persistance SQL.

## Démonstration fonctionnelle — 2 minutes

1. Lancer une collecte courte (une page) ou charger les données déjà collectées.
2. Afficher les données nettoyées puis un filtre du dashboard.
3. Télécharger un export brut Web Scraper.
4. Ouvrir la page Évaluation et montrer les deux liens.

