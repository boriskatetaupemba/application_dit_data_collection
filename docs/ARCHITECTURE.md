# Architecture technique

```text
Pages Web
   │
   ▼
Scrapers Selenium ──► données collectées en mémoire
   │
   ▼
Pipelines pandas ──► CSV nettoyés ──► SQLite
   │                                      │
   └──────────────────────────────────────┤
                                          ▼
                                  Application Streamlit
                                  ├─ tables et filtres
Exports Web Scraper ─────────────► ├─ téléchargements bruts
                                  ├─ dashboards Plotly
Google Forms / Kobo URLs ────────► └─ page d'évaluation
```

## Responsabilités

- `scrapers/` : navigation Selenium, pagination, extraction et reprise sur les
  erreurs de chargement.
- `cleaners/` : transformations explicites, types, cohérence et dédoublonnage.
- `database/` : schéma SQLite, insertions idempotentes et lectures.
- `dashboard/` : filtres, indicateurs et figures Plotly.
- `google_forms/` : source CSV du Google Sheet et Apps Script générateur.
- `kobo/` : XLSForm importable dans KoboToolbox.
- `data/raw/` : exports bruts de l'extension Web Scraper.
- `data/cleaned/` : sorties Selenium préparées pour l'analyse.

## Schéma SQL retenu

Deux tables métier évitent une abstraction inutile :

- `books` : identifiant stable dérivé de l'URL/UPC, champs du catalogue et date
  de collecte ; unicité de l'identifiant source.
- `cars` : identifiant stable dérivé de l'URL de l'annonce, champs automobiles
  et date de collecte ; unicité de l'URL source.

Les insertions utilisent un UPSERT. Un nouveau passage actualise une annonce
existante sans la dupliquer.

## Déploiement

SQLite convient à la démonstration locale et à un conteneur mono-instance. Sur
une plateforme dont le disque est éphémère ou avec plusieurs instances, il faut
remplacer la valeur `DATABASE_URL` par un service SQL persistant compatible avec
la couche d'accès, sans modifier les scrapers ni les nettoyeurs.

