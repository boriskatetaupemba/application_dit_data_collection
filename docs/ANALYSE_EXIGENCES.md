# Analyse du cahier des charges

Ce document distingue les obligations explicites des choix techniques retenus
pour la première version du projet.

## Exigences obligatoires

- Collecter **Books to Scrape** sur l'ensemble du catalogue avec Selenium et
  extraire titre, prix, disponibilité, nombre de produits sur la page, note,
  nombre de reviews, description, catégorie/type et taxe.
- Collecter **Gaaraas / Dakar Auto** avec Selenium sur une borne de 100 pages et
  extraire marque, modèle, année, prix, kilométrage, boîte et région.
- Ne pas utiliser BeautifulSoup dans les scrapers codés.
- Nettoyer, typer, contrôler et dédupliquer les données Selenium.
- Conserver séparément les exports bruts réalisés avec l'extension Chrome Web
  Scraper et permettre leur téléchargement dans Streamlit.
- Proposer une application Streamlit avec collecte, consultation, dashboard,
  téléchargements et accès aux deux formulaires d'évaluation.
- Stocker les données dans une base SQL avec gestion des doublons.
- Fournir un XLSForm Kobo et un Google Form généré depuis un Google Sheet par
  Apps Script. Le Google Sheet reste la source de vérité.
- Ne pas versionner de secrets.
- Documenter installation, utilisation, déploiement, limites et démonstration.

## Choix techniques proposés

- **SQLite** pour la version académique locale : aucune infrastructure externe,
  fichier facilement démontrable et SQL standard pour les opérations utiles.
- **pandas** pour les transformations et **Plotly** pour les visualisations.
- **Chrome/Chromium** avec Selenium 4 et attentes explicites.
- Une application Streamlit à navigation interne, afin de garder un seul point
  d'entrée pour le déploiement.
- Des URLs de formulaires chargées depuis `st.secrets` ou l'environnement.

## Ambiguïtés et écarts constatés

1. Le 18 août 2026, le profil Dakar Auto annonce 245 véhicules et sa pagination
   visible s'arrête à la page 13. Le scraper conserve `100` comme borne maximale
   demandée, mais s'arrête lorsqu'une page est vide ou répète les mêmes annonces.
   Parcourir artificiellement 87 pages sans contenu n'ajouterait aucune donnée.
2. Pour Books to Scrape, « nombre de produits sur la page » est enregistré pour
   chaque livre comme métadonnée de sa page catalogue (habituellement 20, sauf
   la dernière page), car la variable n'est pas une propriété du livre.
3. Les exports Web Scraper doivent être produits depuis l'extension Chrome par
   l'étudiant. Le dépôt fournit l'emplacement et le téléchargement, mais ne peut
   pas fabriquer à leur place une collecte déclarée « no-code ».
4. La création effective des formulaires, du déploiement, du dépôt distant et de
   la vidéo nécessite les comptes et décisions de publication de l'étudiant.
   Le dépôt fournit les artefacts reproductibles et les procédures.
5. Google Forms ne permet pas d'afficher/masquer une question isolée : la logique
   conditionnelle repose sur des sauts de section. Les différences nécessaires
   sont documentées dans le dossier `google_forms`.

