# Déploiement

## Option recommandée pour l'examen : conteneur Docker

Le conteneur fournit Python, Chromium et ChromeDriver dans un environnement
reproductible. Depuis la racine du dépôt :

```bash
docker build -t data-collection-dit .
docker run --rm -p 8501:8501 \
  -e GOOGLE_FORM_URL="https://docs.google.com/forms/..." \
  -e KOBO_FORM_URL="https://ee.kobotoolbox.org/..." \
  -v data_collection_data:/app/data \
  data-collection-dit
```

Ouvrir ensuite `http://localhost:8501`.

Le volume conserve SQLite et les CSV entre deux exécutions. Sur une plateforme
de conteneurs, monter un volume persistant ou configurer un service SQL externe
avant de présenter la collecte comme durable.

## Streamlit Community Cloud

Le dépôt contient les deux fichiers reconnus par la plateforme :

- `requirements.txt` pour les paquets Python ;
- `packages.txt` pour `chromium` et `chromium-driver` installés via `apt`.

Procédure :

1. Publier le dépôt GitHub.
2. Dans Streamlit Community Cloud, créer une application avec `app.py` comme
   point d'entrée et choisir la même version de Python que celle testée (3.12).
3. Dans **Secrets**, saisir uniquement les valeurs réelles :

   ```toml
   google_form_url = "https://docs.google.com/forms/..."
   kobo_form_url = "https://ee.kobotoolbox.org/..."
   ```

4. Déployer puis exécuter d'abord une collecte d'une seule page.
5. Tester les téléchargements, la base et les deux liens d'évaluation.

Références officielles :

- https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/app-dependencies
- https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/file-organization

### Limites à annoncer

- Les collectes longues immobilisent l'exécution Streamlit jusqu'à la fin du
  navigateur ; l'interface demande donc une confirmation et recommande un test
  court.
- Les ressources de Community Cloud sont partagées et peuvent être insuffisantes
  pour 1 000 fiches détaillées dans une seule session.
- Le disque d'une application cloud ne doit pas être considéré comme une base
  durable. SQLite convient au jury/local/Docker mono-instance ; une production
  durable nécessite un volume ou une base SQL gérée.
- Une modification du DOM d'une source peut imposer une mise à jour des
  sélecteurs Selenium et des sitemaps Web Scraper.

## Exécution locale sans Docker

PowerShell :

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
Copy-Item .streamlit\secrets.toml.example .streamlit\secrets.toml
streamlit run app.py
```

Chrome ou Chromium doit être installé. Selenium 4 essaie de gérer le pilote
automatiquement ; si l'environnement bloque ce téléchargement, installer un
ChromeDriver compatible ou utiliser le conteneur.

## Vérifications avant remise

```bash
python -m pytest
python -m compileall app.py scrapers cleaners database dashboard pages_components
```

Effectuer ensuite un test réel d'une page pour chaque source, puis une collecte
complète dans l'environnement prévu pour la présentation.

