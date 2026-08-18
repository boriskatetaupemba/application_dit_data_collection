# Formulaire KoboToolbox (XLSForm)

`evaluation_application_kobo.xlsx` est la version Kobo du même formulaire
d'évaluation que la version Google Forms. Le classeur respecte la structure
XLSForm standard avec exactement trois feuilles : `survey`, `choices` et
`settings`.

## Importer et déployer

1. Se connecter à KoboToolbox et créer un nouveau projet.
2. Choisir l'import d'un **XLSForm**, puis envoyer
   `evaluation_application_kobo.xlsx`.
3. Attendre la validation Kobo, ouvrir l'aperçu et tester les trois branches
   conditionnelles.
4. Déployer le formulaire seulement après ce contrôle.
5. Copier l'URL publique Enketo/Kobo du formulaire déployé pour l'intégrer à
   Streamlit.

Le fichier local ne peut pas fournir lui-même une URL publique : cette URL est
attribuée par le compte Kobo lors du déploiement.

## Feuille `survey`

Les colonnes utilisées sont :

- `type`, `name` et `label` pour la structure et les libellés ;
- `required` pour les questions obligatoires ;
- `relevant` pour la visibilité conditionnelle ;
- `constraint` et `constraint_message` pour la note ;
- `calculation` pour le niveau de satisfaction ;
- `appearance` pour les champs multilignes ;
- `hint` pour les aides courtes.

Les six sections sont des groupes `begin_group` / `end_group`. Les 28 entrées
de la spécification sont présentes, auxquelles s'ajoutent un champ `calculate`
et une `note` d'affichage en lecture seule.

### Conditions

| Question affichée | Expression `relevant` |
|---|---|
| Autre profession | `${role} = 'other'` |
| Nombre d'utilisations précédentes | `${first_usage} = 'no'` |
| Types et description des problèmes | `${problem_yes_no} = 'yes'` |

`other_profession` reste `required = yes` : Kobo n'applique cette obligation
que lorsque la ligne est pertinente. Le nombre d'utilisations précédentes et
les détails des problèmes restent facultatifs, conformément à la spécification.

### Note et calcul

`rating` est de type `integer`, obligatoire, avec la contrainte inclusive :

```text
. >= 0 and . <= 10
```

`satisfaction_level` est un champ `calculate` contenant la règle exacte :

```text
if(${rating} >= 9, 'Excellent',
   if(${rating} >= 7, 'Très bon',
      if(${rating} >= 5, 'Bon',
         if(${rating} >= 3, 'Passable', 'Médiocre'))))
```

La ligne `satisfaction_level_display` affiche ensuite la valeur au répondant
sous forme de `note`, sans permettre sa modification.

## Feuille `choices`

Les colonnes `list_name`, `name` et `label` définissent les listes. Les valeurs
techniques de `name` sont stables, sans accent ni espace ; les `label` conservent
exactement les libellés français de la spécification. Les listes couvrent le
rôle, l'appareil, Oui/Non, le nombre d'utilisations, le Likert à cinq niveaux,
les fonctionnalités, les problèmes, la recommandation et la réutilisation.

## Feuille `settings`

Le formulaire utilise :

- `form_title` : `Évaluation de l'application Web` ;
- `form_id` : `evaluation_application_web` ;
- `version` : `1.0` ;
- `default_language` : `French (fr)`.

Avant de remplacer un formulaire Kobo déjà déployé, incrémenter `version` et
tester le nouvel XLSForm dans un projet de brouillon afin de protéger les
données collectées.

## Intégration Streamlit

Stocker l'URL publique fournie par Kobo dans un secret, jamais en dur si elle
contient un jeton :

```toml
kobo_form_url = "https://ee.kobotoolbox.org/x/..."
```

```python
st.link_button(
    "Évaluer l'application avec Kobo",
    st.secrets["kobo_form_url"],
)
```

## Tests d'acceptation

Tester au minimum les chemins `Autre`, `Non` à la première utilisation et
`Oui` aux problèmes, puis leurs chemins inverses. Tester aussi les frontières
`0`, `2`, `3`, `4`, `5`, `6`, `7`, `8`, `9`, `10`, ainsi que les valeurs
invalides `-1`, `11` et une valeur décimale. Enfin, exporter une soumission et
vérifier que `satisfaction_level` est bien stocké.
