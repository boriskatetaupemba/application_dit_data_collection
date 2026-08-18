# Projet Data Collection DIT

Application d'examen consacrée à la collecte, au nettoyage, au stockage et à la
visualisation de deux sources publiques : **Books to Scrape** et les annonces
automobiles **Gaaraas / Dakar Auto**.

Le scraping codé utilise exclusivement **Selenium**. Les exports bruts réalisés
avec l'extension Chrome **Web Scraper** suivent un flux séparé et ne sont jamais
présentés comme des données Selenium.

## Fonctionnalités

- collecte Selenium du catalogue Books to Scrape, fiches détaillées comprises ;
- collecte Gaaraas sur une borne maximale de 100 pages, avec arrêt sûr lorsque
  le site ne renvoie plus de nouvelles annonces ;
- retries, attentes explicites, dédoublonnage et export CSV ;
- nettoyage pandas documenté et types nullables ;
- deux tables SQLite avec contraintes, index et UPSERT ;
- application Streamlit à sept rubriques ;
- dashboards Plotly avec filtres, KPI et neuf visualisations ;
- téléchargement séparé des exports bruts Web Scraper ;
- XLSForm Kobo prêt à importer ;
- Google Sheet modèle et `Code.gs` complet pour générer le Google Form ;
- configuration Docker, Streamlit Community Cloud et CI GitHub Actions.

## Architecture

```text
Pages Web ──Selenium──► données brutes en mémoire
                              │
                              ▼
                       nettoyeurs pandas
                              │
                       ┌──────┴──────┐
                       ▼             ▼
                 CSV nettoyés     SQLite
                       └──────┬──────┘
                              ▼
                         Streamlit

Extension Web Scraper ──► data/raw ──► aperçu + téléchargement
Kobo / Google Forms ─────────────────► page Évaluation
```

Voir [l'architecture détaillée](docs/ARCHITECTURE.md) et
[l'analyse des exigences](docs/ANALYSE_EXIGENCES.md).

## Installation locale

Prérequis : Python 3.12 recommandé et Chrome/Chromium.

### Windows / PowerShell

```powershell
git clone https://github.com/boriskatetaupemba/application_dit_data_collection.git
cd application_dit_data_collection
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
streamlit run app.py
```

### Linux / macOS

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
streamlit run app.py
```

Ouvrir `http://localhost:8501`.

## Configuration

Le fichier `.streamlit/secrets.toml` est suivi par Git dans ce projet, car il ne
contient que le chemin SQLite et des URL publiques de formulaires. Ne jamais y
ajouter de mot de passe, jeton, clé API ou identifiant privé. Pour ces valeurs
sensibles, utiliser les secrets de la plateforme ou des variables
d'environnement non versionnées.

### Secrets Streamlit

```toml
database_url = "sqlite:///data/data_collection.db"
google_form_url = "https://docs.google.com/forms/..."
kobo_form_url = "https://ee.kobotoolbox.org/..."
```

### Variables d'environnement

```text
DATABASE_URL=sqlite:///data/data_collection.db
GOOGLE_FORM_URL=https://docs.google.com/forms/...
KOBO_FORM_URL=https://ee.kobotoolbox.org/...
SELENIUM_HEADLESS=1
```

`DATA_COLLECTION_DB_PATH` peut remplacer `DATABASE_URL` pour fournir directement
un chemin SQLite.

## Utilisation de l'application

1. **Accueil** : état de la base et parcours conseillé.
2. **Scraping** : choisir la source, tester une page, puis lancer le périmètre
   complet. L'interface demande une confirmation avant de démarrer Selenium.
3. **Données brutes** : télécharger les exports de l'extension Web Scraper
   déposés dans `data/raw/`.
4. **Données nettoyées** : consulter et télécharger les sorties Selenium.
5. **Dashboard** : filtrer et analyser chaque source.
6. **Évaluation** : ouvrir les formulaires Kobo et Google configurés.
7. **Documentation** : rappeler le flux et la configuration depuis l'application.

## Collecte Selenium

### Books to Scrape

```python
from scrapers.books_scraper import scrape_books
from cleaners.books_cleaner import clean_books_data

raw = scrape_books()             # suit la pagination jusqu'à la fin
cleaned = clean_books_data(raw)
```

Le scraper collecte titre, prix, disponibilité, nombre de produits de la page,
note, reviews, description, type/catégorie et taxe. Il conserve également URL
et page source pour la traçabilité.

### Gaaraas

```python
from scrapers.gaaraas_scraper import scrape_gaaraas
from cleaners.gaaraas_cleaner import clean_gaaraas_data

raw = scrape_gaaraas(max_pages=100)
cleaned = clean_gaaraas_data(raw)
```

En août 2026, le profil Dakar Auto expose 245 annonces sur 13 pages visibles.
La borne de 100 est conservée conformément au cahier des charges, mais le mode
normal s'arrête sur une page vide ou répétée. `strict_pages=True` force la
tentative des 100 numéros pour une vérification spécifique.

## Collecte no-code Web Scraper

Le dossier [`web_scraper/`](web_scraper/) contient deux sitemaps JSON importables
et une procédure détaillée. Après la collecte dans l'extension Chrome, déposer :

```text
data/raw/books_webscraper_raw.csv
data/raw/gaaraas_webscraper_raw.csv
```

Ces fichiers restent bruts et distincts des CSV présents dans `data/cleaned/`.

## Base SQL

SQLite est initialisée automatiquement dans `data/data_collection.db` :

- `books` : clé source unique, variables du catalogue et métadonnées ;
- `cars` : clé source unique, variables automobiles et métadonnées.

Les fonctions de [`database/repository.py`](database/repository.py) normalisent
les alias, calculent une clé stable et utilisent `ON CONFLICT ... DO UPDATE`.

## Formulaire Kobo

Importer [`kobo/evaluation_application_kobo.xlsx`](kobo/evaluation_application_kobo.xlsx)
dans KoboToolbox comme XLSForm. Il contient :

- les six sections ;
- les questions et choix exacts ;
- les champs obligatoires et les trois affichages conditionnels ;
- la contrainte entière `0..10` ;
- le niveau de satisfaction calculé et affiché en lecture seule ;
- le message final.

La procédure détaillée se trouve dans [`kobo/README.md`](kobo/README.md).

## Google Forms généré depuis Google Sheets

1. Importer
   [`google_forms/google_forms_config.xlsx`](google_forms/google_forms_config.xlsx)
   dans Google Drive en tant que Google Sheet.
2. Vérifier `CONFIG_FORM`, `QUESTIONS`, `CHOICES`, `FORM_LINKS` et
   `GENERATION_LOG`.
3. Ouvrir **Extensions > Apps Script**.
4. Coller le contenu complet de [`google_forms/Code.gs`](google_forms/Code.gs).
5. Exécuter `generateEvaluationForm()` et accepter les autorisations demandées.
6. Récupérer `PUBLIC_URL` dans `FORM_LINKS`, puis configurer
   `google_form_url` dans Streamlit.

Le script réutilise `FORM_ID`, valide la source, reconstruit les items, crée les
branches conditionnelles par sections, lie la feuille de réponses, installe le
trigger de soumission, calcule le niveau de satisfaction et journalise chaque
génération. La feuille de réponses est créée par Google Forms lors de la liaison.

La procédure, les autorisations et les limites natives de Google Forms sont
détaillées dans [`google_forms/README.md`](google_forms/README.md).

## Tests

```bash
python -m pip install -r requirements-dev.txt
python -m pytest -q
python -m compileall -q app.py scrapers cleaners database dashboard pages_components
```

Les tests couvrent nettoyeurs, scrapers avec driver injecté, schéma/UPSERT SQL,
calculs de dashboard, intégration des colonnes et chargement des pages Streamlit.
Un test réel court doit aussi être réalisé avant la présentation, car les DOM
des sites sont externes au dépôt.

## Déploiement

- **Docker** est l'option la plus reproductible pour Selenium ;
- **Streamlit Community Cloud** utilise `requirements.txt` et `packages.txt` ;
- les secrets doivent être saisis dans l'interface de la plateforme ;
- SQLite exige un disque/volume persistant pour survivre aux redémarrages.

Consulter le [guide de déploiement](docs/DEPLOIEMENT.md).

## Limites connues

- Gaaraas présente actuellement moins de 100 pages réelles.
- Google Forms ne sait pas masquer une question isolée : le script utilise des
  sous-sections et des sauts conditionnels, alternative native la plus fidèle.
- Les exports no-code doivent être réellement produits avec l'extension Chrome.
- Les liens publiés, l'application déployée et la vidéo nécessitent les comptes
  de l'étudiant et ne sont pas créés automatiquement par le dépôt local.
- Une collecte complète Books ouvre 1 000 fiches ; prévoir plusieurs minutes et
  tester le navigateur avant la démonstration.

## Préparation de la soutenance

Une trame chronométrée de 10 minutes est disponible dans
[`docs/PLAN_DEMONSTRATION.md`](docs/PLAN_DEMONSTRATION.md).
