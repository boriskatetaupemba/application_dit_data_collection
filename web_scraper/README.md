# Collecte no-code avec Web Scraper

Ce dossier contient deux sitemaps JSON importables dans l'extension Chrome
**Web Scraper**. Ils servent uniquement à la collecte brute et ne remplacent pas
les scrapers Selenium.

## Procédure

1. Installer l'extension Web Scraper dans Chrome.
2. Ouvrir les outils de développement (`F12`), puis l'onglet **Web Scraper**.
3. Dans **Create new sitemap > Import sitemap**, coller le contenu du fichier
   JSON correspondant.
4. Vérifier chaque sélecteur avec **Element preview** et **Data preview**.
5. Lancer **Scrape** avec un délai de chargement raisonnable (2 000 à 3 000 ms
   pour Gaaraas).
6. Dans **Export data as CSV**, exporter sans modifier les valeurs.
7. Renommer et déposer les résultats dans `data/raw/` :
   - `books_webscraper_raw.csv`
   - `gaaraas_webscraper_raw.csv`
8. Ouvrir la page **Données brutes** de l'application pour vérifier le
   téléchargement.

## Structure des sitemaps

### Books to Scrape

L'URL de départ utilise la plage `[1-50]`. Le sélecteur `book_url` ouvre chaque
fiche puis extrait les valeurs telles qu'affichées (symboles monétaires, espaces
et classe CSS de la note inclus). Le nombre de produits par page n'est pas
répété artificiellement dans chaque ligne brute ; il est obtenu de manière
explicite par le scraper Selenium, où il fait partie des neuf variables.

### Gaaraas

L'URL de départ utilise la plage `[1-100]` exigée. En août 2026, seules les
treize premières pages contiennent des annonces sur ce profil ; les autres URLs
peuvent produire des pages vides. `vehicle_title_raw` conserve volontairement
année, marque et modèle dans la chaîne source : leur séparation est une étape de
nettoyage réservée au pipeline Selenium.

## Contrôles avant remise

- Conserver les colonnes automatiques d'URL/source ajoutées par l'extension.
- Ne pas ouvrir puis réenregistrer les CSV dans un outil susceptible de changer
  les séparateurs ou les encodages avant de garder une copie originale.
- Noter la date, l'heure, le délai et le nombre de lignes de chaque collecte.
- Ne jamais présenter ces exports comme des sorties Selenium.

