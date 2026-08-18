# Google Forms piloté par Google Sheets

Ce dossier fournit une version reproductible du formulaire d'évaluation. Le
Google Spreadsheet est la source de vérité ; `Code.gs` lit ses feuilles,
valide la configuration, puis crée ou reconstruit le même Google Form.
Aucune question ne doit être ressaisie manuellement dans Google Forms.

## Livrables

| Fichier | Rôle |
|---|---|
| `google_forms_config.xlsx` | Classeur prêt à importer dans Google Sheets, avec les cinq feuilles requises |
| `config_template.csv` | Valeurs initiales de `CONFIG_FORM` |
| `questions_template.csv` | Les 28 questions, leur ordre, leurs obligations et leurs conditions |
| `choices_template.csv` | Les choix centralisés, sans listes métier codées en dur dans le script |
| `Code.gs` | Générateur Apps Script complet |

`Form Responses 1` n'est volontairement pas précréée : Google Forms la
crée lors de `setDestination`. Son nom peut être localisé par Google (par
exemple `Réponses au formulaire 1`). Le code n'est pas dépendant de ce nom.

## Installation pas à pas

1. Dans Google Drive, importer `google_forms_config.xlsx`, puis choisir
   **Ouvrir avec > Google Sheets**. Il est aussi possible de créer un classeur
   vide et d'importer les trois CSV dans des feuilles nommées exactement
   `CONFIG_FORM`, `QUESTIONS` et `CHOICES`.
2. Vérifier la présence des feuilles `CONFIG_FORM`, `QUESTIONS`, `CHOICES`,
   `FORM_LINKS` et `GENERATION_LOG`. Ne pas renommer les en-têtes.
3. Ouvrir **Extensions > Apps Script** depuis ce classeur.
4. Remplacer le contenu du fichier `Code.gs` par le contenu complet de ce
   dossier, puis enregistrer le projet.
5. Sélectionner `generateEvaluationForm` dans la barre Apps Script et cliquer
   **Exécuter**. Lors du premier lancement, choisir le compte propriétaire du
   classeur et accepter les autorisations demandées pour gérer le classeur,
   créer/modifier le Google Form et installer le trigger de soumission. Les
   portées exactes sont déterminées automatiquement par Apps Script.
6. Revenir au classeur et l'actualiser. Le menu **Data Collection** permet
   ensuite de générer, reconstruire et afficher les liens sans retourner dans
   l'éditeur.

Le compte qui exécute la première génération devient propriétaire du
formulaire et du trigger installable. Un autre utilisateur doit avoir les
droits suffisants sur le classeur et le formulaire pour relancer le script.

## Structure du classeur

### `CONFIG_FORM`

Deux colonnes, `KEY` et `VALUE`, contiennent les paramètres généraux :

- `FORM_TITLE`, `FORM_DESCRIPTION`, `FORM_VERSION` et
  `CONFIRMATION_MESSAGE` sont obligatoires ;
- `FORM_ID` reste vide avant la première exécution, puis le script le renseigne ;
- `RESPONSE_SHEET_ID` reste vide avant la première exécution, puis reçoit
  l'identifiant du classeur actif.

Si `FORM_ID` est rempli, le script ouvre strictement ce formulaire. Un ID
invalide ou un formulaire déjà relié à un autre classeur provoque une erreur
explicite ; le script ne crée alors pas de doublon et ne détourne pas la
destination existante. Pour créer volontairement un nouveau formulaire, vider
`FORM_ID` avant d'exécuter la génération.

### `QUESTIONS`

Chaque ligne active décrit une question. Les colonnes sont :

| Colonne | Contenu |
|---|---|
| `section_order` | Ordre entier de la section logique |
| `section_id` | Identifiant technique stable de la section |
| `section_title` | Titre affiché de la section |
| `question_order` | Ordre entier, unique dans la section |
| `question_id` | Identifiant technique unique, sans espace |
| `question_title` | Libellé affiché et en-tête de réponse |
| `question_type` | `TEXT`, `PARAGRAPH`, `DATE`, `MULTIPLE_CHOICE`, `CHECKBOX`, `SCALE` ou `SECTION` |
| `required` | Strictement `TRUE` ou `FALSE` |
| `choices_group` | Clé de `CHOICES` pour une sélection |
| `help_text` | Aide facultative |
| `min_value`, `max_value` | Bornes numériques facultatives |
| `condition_question_id` | Question de sélection unique qui déclenche la branche |
| `condition_value` | Choix exact qui affiche la branche |
| `target_section_id` | Identifiant de la sous-section conditionnelle |
| `active` | Strictement `TRUE` ou `FALSE` |

Les trois colonnes de condition doivent être remplies ensemble. Plusieurs
questions peuvent partager le même `target_section_id`, comme les deux détails
de problème. Les conditions imbriquées sont rejetées avec un message clair.

La note globale est un `TEXT` avec `min_value = 0` et `max_value = 10` : le
script applique simultanément `requireWholeNumber()` et
`requireNumberBetween(0, 10)`. Elle reste obligatoire.

### `CHOICES`

Les colonnes `choices_group`, `value` et `order` centralisent toutes les listes.
Le script vérifie les groupes absents, les libellés dupliqués et les ordres
dupliqués. Les groupes fournis sont `ROLE`, `DEVICE`, `FIRST_USAGE`,
`PREVIOUS_USAGE_COUNT`, `LIKERT_5`, `FEATURES_TESTED`, `PROBLEM_YES_NO`,
`PROBLEM_TYPES`, `RECOMMENDATION` et `REUSE`.

### `FORM_LINKS` et `GENERATION_LOG`

`FORM_LINKS` est remplacé par une ligne de métadonnées à chaque génération :
ID, URL d'édition, URL publique, URL du classeur de réponses, dates,
version et compteurs. `GENERATION_LOG` est cumulatif et enregistre les statuts
`START`, `SUCCESS`, `ERROR` et, le cas échéant, `WARNING`.

## Réexécution et reconstruction

`generateEvaluationForm()` est idempotente vis-à-vis du fichier Google Form :
elle réutilise `FORM_ID`, supprime les items en ordre inverse, puis les recrée
depuis les feuilles. Elle ne fait jamais appel à `deleteAllResponses` et ne
supprime pas les lignes de la feuille de réponses.

Le menu **Reconstruire complètement le formulaire** appelle `rebuildForm()`
après confirmation. Il s'agit d'une reconstruction explicite du contenu du
même formulaire, pas de la création d'un second formulaire.

Après avoir renommé ou retiré une question, contrôler la feuille de réponses :
Google peut conserver des colonnes historiques. Tester les changements de
schéma dans une copie du classeur avant une collecte réelle.

## Navigation conditionnelle et limite Google Forms

Google Forms ne sait pas afficher/masquer une question isolée sur la même page.
Sa logique native agit depuis une question à choix unique vers des sections.
Le script transforme donc automatiquement chaque condition en sous-section :

- `Rôle = Autre` ouvre **Autre profession**, puis rejoint la suite de la
  section 1 ;
- `Première utilisation = Non` ouvre le nombre d'utilisations précédentes ;
- `Problèmes = Oui` ouvre le type et la description des problèmes.

Les six titres réglementaires restent les six sections **logiques**. Le Form
contient en plus des pages techniques « suite » et « complément conditionnel ».
Ce découpage est l'alternative native la plus fidèle. La navigation ne peut
pas être déclenchée depuis une case à cocher, et le script refuse les conditions
imbriquées plutôt que de simuler un comportement inexistant.

Références API officielles : [navigation des choix](https://developers.google.com/apps-script/reference/forms/multiple-choice-item),
[sauts de page](https://developers.google.com/apps-script/reference/forms/page-break-item)
et [validation de texte](https://developers.google.com/apps-script/reference/forms/text-validation-builder).

## Niveau de satisfaction et trigger

Google Forms ne propose pas de champ calculé en lecture seule. Le script crée
donc un trigger installable **Depuis le tableur > Lors de l'envoi du
formulaire**. `onFormSubmit(e)` lit la note originale, ajoute si nécessaire la
colonne `Niveau de satisfaction`, puis écrit uniquement la valeur dérivée :

| Note | Niveau |
|---:|---|
| 9–10 | Excellent |
| 7–8 | Très bon |
| 5–6 | Bon |
| 3–4 | Passable |
| 0–2 | Médiocre |

La génération appelle automatiquement la vérification du trigger et n'en
crée qu'un. Si le propriétaire le supprime dans Apps Script, exécuter
`installOnFormSubmitTrigger()` une fois. L'événement attendu est celui du
**tableur**, car il fournit `namedValues` et la plage de la ligne soumise.

## Récupérer et intégrer le lien

Après une génération réussie, copier `PUBLIC_URL` dans `FORM_LINKS`, ou utiliser
le menu **Afficher le lien du formulaire**. Dans `.streamlit/secrets.toml` :

```toml
google_form_url = "https://docs.google.com/forms/d/e/.../viewform"
```

Puis dans Streamlit :

```python
st.link_button(
    "Évaluer l'application avec Google Forms",
    st.secrets["google_form_url"],
)
```

Ne jamais placer un identifiant de compte, un token ou une autre donnée
sensible dans le dépôt.

## Contrôle fonctionnel conseillé

1. Soumettre le chemin `Rôle = Autre`, `Première utilisation = Non`,
   `Problèmes = Oui` et vérifier les trois sous-sections.
2. Soumettre le chemin inverse et vérifier qu'elles sont sautées.
3. Tester les notes `-1`, `0`, `2`, `3`, `5`, `7`, `9`, `10` et `11` ; seules
   les valeurs entières de 0 à 10 doivent passer.
4. Contrôler la valeur calculée dans la feuille de réponses.
5. Relancer la génération et confirmer que `FORM_ID` et l'URL publique restent
   identiques et qu'aucun second trigger n'apparaît.
