/**
 * Génère le formulaire d'évaluation depuis le classeur Google Sheets lié.
 *
 * Le classeur est la source de vérité. Le script ne supprime jamais les
 * réponses existantes : il reconstruit uniquement les éléments du formulaire.
 */

const SHEET_NAMES = Object.freeze({
  CONFIG: 'CONFIG_FORM',
  QUESTIONS: 'QUESTIONS',
  CHOICES: 'CHOICES',
  LINKS: 'FORM_LINKS',
  LOG: 'GENERATION_LOG',
});

const CONFIG_KEYS = Object.freeze([
  'FORM_TITLE',
  'FORM_DESCRIPTION',
  'FORM_ID',
  'RESPONSE_SHEET_ID',
  'FORM_VERSION',
  'CONFIRMATION_MESSAGE',
]);

const QUESTION_HEADERS = Object.freeze([
  'section_order',
  'section_id',
  'section_title',
  'question_order',
  'question_id',
  'question_title',
  'question_type',
  'required',
  'choices_group',
  'help_text',
  'min_value',
  'max_value',
  'condition_question_id',
  'condition_value',
  'target_section_id',
  'active',
]);

const CHOICE_HEADERS = Object.freeze(['choices_group', 'value', 'order']);
const SUPPORTED_TYPES = Object.freeze([
  'TEXT',
  'PARAGRAPH',
  'DATE',
  'MULTIPLE_CHOICE',
  'CHECKBOX',
  'SCALE',
  'SECTION',
]);
const RATING_QUESTION_TITLE = "Note globale de l'application";
const SATISFACTION_HEADER = 'Niveau de satisfaction';
const SUBMIT_TARGET = '__SUBMIT__';

/** Ajoute le menu de pilotage dans le Google Spreadsheet. */
function onOpen() {
  SpreadsheetApp.getUi()
    .createMenu('Data Collection')
    .addItem(
      'Générer / Mettre à jour le formulaire',
      'generateEvaluationForm'
    )
    .addItem(
      'Reconstruire complètement le formulaire',
      'rebuildForm'
    )
    .addSeparator()
    .addItem('Afficher le lien du formulaire', 'showFormUrl')
    .addItem('Afficher la feuille de réponses', 'showResponsesUrl')
    .addToUi();
}

/**
 * Point d'entrée principal. La réexécution réutilise le même FORM_ID,
 * vide les items générés puis les recrée depuis QUESTIONS et CHOICES.
 */
function generateEvaluationForm() {
  return runGeneration_(false);
}

/** Demande confirmation avant une reconstruction explicite. */
function rebuildForm() {
  const ui = SpreadsheetApp.getUi();
  const answer = ui.alert(
    'Reconstruire le formulaire',
    'Les questions et sections du formulaire seront recréées depuis le ' +
      'Google Sheet. Les réponses existantes ne seront pas supprimées.',
    ui.ButtonSet.OK_CANCEL
  );
  if (answer !== ui.Button.OK) {
    return null;
  }
  return runGeneration_(true);
}

function runGeneration_(explicitRebuild) {
  const lock = LockService.getDocumentLock();
  if (!lock.tryLock(30000)) {
    throw new Error(
      'Une autre génération est en cours. Réessayez dans quelques instants.'
    );
  }

  let form = null;
  let questions = [];
  let sectionCount = 0;
  try {
    validateSpreadsheetStructure();
    ensureOutputSheets_();

    const config = loadFormConfig();
    questions = loadQuestionsConfig();
    const choices = loadChoicesConfig();
    validateConfigurationData_(config, questions, choices);
    sectionCount = getLogicalSections_(questions).length;

    writeGenerationLog(
      'START',
      explicitRebuild
        ? 'Reconstruction complète demandée.'
        : 'Génération / mise à jour demandée.',
      sectionCount,
      questions.length,
      config.formId || ''
    );

    form = getOrCreateForm(config);
    form
      .setTitle(config.formTitle)
      .setDescription(config.formDescription)
      .setConfirmationMessage(config.confirmationMessage)
      .setProgressBar(true)
      .setShuffleQuestions(false)
      .setPublished(true);

    clearExistingFormItems(form);
    const buildResult = createSections(form, questions, choices);
    configureConditionalNavigation(form, buildResult, choices);
    configureResponseDestination(form, config);
    ensureOnFormSubmitTrigger_();
    saveFormMetadata(form, config, questions.length, sectionCount);

    writeGenerationLog(
      'SUCCESS',
      'Formulaire généré avec ' +
        buildResult.plan.pages.length +
        ' pages physiques pour ' +
        sectionCount +
        ' sections logiques.',
      sectionCount,
      questions.length,
      form.getId()
    );
    Logger.log('Formulaire public : %s', form.getPublishedUrl());
    SpreadsheetApp.getActive().toast(
      'Formulaire généré : ' + questions.length + ' questions.',
      'Data Collection',
      8
    );
    return form.getPublishedUrl();
  } catch (error) {
    const message = error && error.message ? error.message : String(error);
    try {
      writeGenerationLog(
        'ERROR',
        message,
        sectionCount,
        questions.length,
        form ? form.getId() : ''
      );
    } catch (logError) {
      Logger.log('Impossible de journaliser l\'erreur : %s', logError.message);
    }
    Logger.log(error && error.stack ? error.stack : message);
    throw error;
  } finally {
    lock.releaseLock();
  }
}

/** Lit CONFIG_FORM et renvoie une configuration typée. */
function loadFormConfig() {
  const rows = readTable_(SHEET_NAMES.CONFIG);
  const values = {};
  rows.forEach(function (row) {
    const key = cleanString_(row.KEY);
    if (!key) {
      throw new Error(
        'CONFIG_FORM contient une clé vide à la ligne ' + row.__rowNumber + '.'
      );
    }
    if (Object.prototype.hasOwnProperty.call(values, key)) {
      throw new Error('La clé de configuration ' + key + ' est dupliquée.');
    }
    values[key] = cleanString_(row.VALUE);
  });

  CONFIG_KEYS.forEach(function (key) {
    if (!Object.prototype.hasOwnProperty.call(values, key)) {
      throw new Error('La clé ' + key + ' manque dans CONFIG_FORM.');
    }
  });
  ['FORM_TITLE', 'FORM_DESCRIPTION', 'FORM_VERSION', 'CONFIRMATION_MESSAGE']
    .forEach(function (key) {
      if (!values[key]) {
        throw new Error('La valeur ' + key + ' ne peut pas être vide.');
      }
    });

  return {
    formTitle: values.FORM_TITLE,
    formDescription: values.FORM_DESCRIPTION,
    formId: values.FORM_ID,
    responseSheetId: values.RESPONSE_SHEET_ID,
    formVersion: values.FORM_VERSION,
    confirmationMessage: values.CONFIRMATION_MESSAGE,
  };
}

/** Lit, normalise et trie les questions actives. */
function loadQuestionsConfig() {
  return readTable_(SHEET_NAMES.QUESTIONS)
    .map(function (row) {
      return {
        rowNumber: row.__rowNumber,
        sectionOrder: requiredNumber_(
          row.section_order,
          'section_order',
          row.__rowNumber
        ),
        sectionId: cleanString_(row.section_id),
        sectionTitle: cleanString_(row.section_title),
        questionOrder: requiredNumber_(
          row.question_order,
          'question_order',
          row.__rowNumber
        ),
        questionId: cleanString_(row.question_id),
        questionTitle: cleanString_(row.question_title),
        questionType: cleanString_(row.question_type).toUpperCase(),
        required: strictBoolean_(row.required, 'required', row.__rowNumber),
        choicesGroup: cleanString_(row.choices_group),
        helpText: cleanString_(row.help_text),
        minValue: optionalNumber_(row.min_value, 'min_value', row.__rowNumber),
        maxValue: optionalNumber_(row.max_value, 'max_value', row.__rowNumber),
        conditionQuestionId: cleanString_(row.condition_question_id),
        conditionValue: cleanString_(row.condition_value),
        targetSectionId: cleanString_(row.target_section_id),
        active: strictBoolean_(row.active, 'active', row.__rowNumber),
      };
    })
    .filter(function (question) {
      return question.active;
    })
    .sort(compareQuestions_);
}

/** Lit CHOICES et renvoie { GROUPE: [{value, order}, ...] }. */
function loadChoicesConfig() {
  const groups = {};
  readTable_(SHEET_NAMES.CHOICES).forEach(function (row) {
    const group = cleanString_(row.choices_group);
    const value = cleanString_(row.value);
    const order = requiredNumber_(row.order, 'order', row.__rowNumber);
    if (!group || !value) {
      throw new Error(
        'CHOICES : choices_group et value sont obligatoires à la ligne ' +
          row.__rowNumber +
          '.'
      );
    }
    if (!groups[group]) {
      groups[group] = [];
    }
    groups[group].push({ value: value, order: order, rowNumber: row.__rowNumber });
  });

  Object.keys(groups).forEach(function (group) {
    groups[group].sort(function (a, b) {
      return a.order - b.order;
    });
    const values = {};
    const orders = {};
    groups[group].forEach(function (choice) {
      if (values[choice.value]) {
        throw new Error(
          'Le choix ' + choice.value + ' est dupliqué dans le groupe ' + group + '.'
        );
      }
      if (orders[String(choice.order)]) {
        throw new Error(
          "L'ordre " + choice.order + ' est dupliqué dans le groupe ' + group + '.'
        );
      }
      values[choice.value] = true;
      orders[String(choice.order)] = true;
    });
  });
  return groups;
}

/** Vérifie les feuilles sources et leurs en-têtes avant toute création. */
function validateSpreadsheetStructure() {
  const spreadsheet = SpreadsheetApp.getActive();
  const requirements = {};
  requirements[SHEET_NAMES.CONFIG] = ['KEY', 'VALUE'];
  requirements[SHEET_NAMES.QUESTIONS] = QUESTION_HEADERS;
  requirements[SHEET_NAMES.CHOICES] = CHOICE_HEADERS;

  Object.keys(requirements).forEach(function (sheetName) {
    const sheet = spreadsheet.getSheetByName(sheetName);
    if (!sheet) {
      throw new Error('La feuille obligatoire ' + sheetName + " n'existe pas.");
    }
    if (sheet.getLastColumn() === 0) {
      throw new Error('La feuille ' + sheetName + ' ne contient aucun en-tête.');
    }
    const headers = sheet
      .getRange(1, 1, 1, sheet.getLastColumn())
      .getValues()[0]
      .map(cleanString_);
    const duplicates = headers.filter(function (header, index) {
      return header && headers.indexOf(header) !== index;
    });
    if (duplicates.length) {
      throw new Error(
        'En-tête dupliqué dans ' + sheetName + ' : ' + duplicates[0] + '.'
      );
    }
    requirements[sheetName].forEach(function (requiredHeader) {
      if (headers.indexOf(requiredHeader) === -1) {
        throw new Error(
          'La colonne ' + requiredHeader + ' manque dans la feuille ' + sheetName + '.'
        );
      }
    });
  });
  return true;
}

function validateConfigurationData_(config, questions, choices) {
  if (!questions.length) {
    throw new Error('QUESTIONS ne contient aucune question active.');
  }

  const ids = {};
  const sectionDefinitions = {};
  const orderKeys = {};
  questions.forEach(function (question) {
    if (!question.sectionId || !question.sectionTitle) {
      throw new Error(
        'section_id et section_title sont obligatoires à la ligne ' +
          question.rowNumber +
          '.'
      );
    }
    if (!Number.isInteger(question.sectionOrder) || question.sectionOrder < 1) {
      throw new Error(
        'section_order doit être un entier positif à la ligne ' +
          question.rowNumber +
          '.'
      );
    }
    if (!Number.isInteger(question.questionOrder) || question.questionOrder < 1) {
      throw new Error(
        'question_order doit être un entier positif à la ligne ' +
          question.rowNumber +
          '.'
      );
    }
    if (!question.questionId || !/^[A-Za-z][A-Za-z0-9_]*$/.test(question.questionId)) {
      throw new Error(
        'question_id doit être un identifiant unique sans espace à la ligne ' +
          question.rowNumber +
          '.'
      );
    }
    if (ids[question.questionId]) {
      throw new Error('question_id dupliqué : ' + question.questionId + '.');
    }
    ids[question.questionId] = question;
    if (!question.questionTitle) {
      throw new Error(
        'Le titre de la question ' + question.questionId + ' est obligatoire.'
      );
    }
    if (SUPPORTED_TYPES.indexOf(question.questionType) === -1) {
      throw new Error(
        'Type de question non supporté pour ' +
          question.questionId +
          ' : ' +
          question.questionType +
          '.'
      );
    }

    const sectionSignature =
      String(question.sectionOrder) + '|' + question.sectionTitle;
    if (
      sectionDefinitions[question.sectionId] &&
      sectionDefinitions[question.sectionId] !== sectionSignature
    ) {
      throw new Error(
        'La section ' + question.sectionId + ' a des définitions incohérentes.'
      );
    }
    sectionDefinitions[question.sectionId] = sectionSignature;

    const orderKey = question.sectionId + '|' + question.questionOrder;
    if (orderKeys[orderKey]) {
      throw new Error(
        "L'ordre de question " +
          question.questionOrder +
          ' est dupliqué dans la section ' +
          question.sectionId +
          '.'
      );
    }
    orderKeys[orderKey] = true;

    if (
      ['MULTIPLE_CHOICE', 'CHECKBOX'].indexOf(question.questionType) !== -1
    ) {
      if (!question.choicesGroup || !choices[question.choicesGroup]) {
        throw new Error(
          'Le groupe de choix ' +
            (question.choicesGroup || '(vide)') +
            ' utilisé par la question ' +
            question.questionId +
            " n'existe pas."
        );
      }
    }
    if (
      question.minValue !== null &&
      question.maxValue !== null &&
      question.minValue > question.maxValue
    ) {
      throw new Error(
        'min_value est supérieur à max_value pour ' + question.questionId + '.'
      );
    }
    if (
      question.questionType === 'SCALE' &&
      (question.minValue === null || question.maxValue === null)
    ) {
      throw new Error(
        'Une question SCALE doit fournir min_value et max_value : ' +
          question.questionId +
          '.'
      );
    }
  });

  questions.forEach(function (question) {
    const conditionParts = [
      question.conditionQuestionId,
      question.conditionValue,
      question.targetSectionId,
    ].filter(function (value) {
      return Boolean(value);
    });
    if (conditionParts.length !== 0 && conditionParts.length !== 3) {
      throw new Error(
        'Les trois colonnes de condition doivent être renseignées ensemble pour ' +
          question.questionId +
          '.'
      );
    }
    if (!question.conditionQuestionId) {
      return;
    }
    const parent = ids[question.conditionQuestionId];
    if (!parent) {
      throw new Error(
        'La question conditionnelle ' +
          question.questionId +
          ' référence une question absente : ' +
          question.conditionQuestionId +
          '.'
      );
    }
    if (parent.questionType !== 'MULTIPLE_CHOICE') {
      throw new Error(
        'La navigation conditionnelle Google Forms exige une question ' +
          'MULTIPLE_CHOICE : ' + parent.questionId + '.'
      );
    }
    if (parent.conditionQuestionId) {
      throw new Error(
        'Les conditions imbriquées ne sont pas prises en charge : ' +
          parent.questionId + '.'
      );
    }
    if (parent.sectionId !== question.sectionId) {
      throw new Error(
        'La condition de ' +
          question.questionId +
          ' doit rester dans la même section logique que ' +
          parent.questionId +
          '.'
      );
    }
    const parentValues = choices[parent.choicesGroup].map(function (choice) {
      return choice.value;
    });
    if (parentValues.indexOf(question.conditionValue) === -1) {
      throw new Error(
        'La valeur conditionnelle ' +
          question.conditionValue +
          " n'existe pas dans le groupe " +
          parent.choicesGroup +
          '.'
      );
    }
  });

  const conditionTargetSignatures = {};
  questions
    .filter(function (question) {
      return Boolean(question.conditionQuestionId);
    })
    .forEach(function (question) {
      const key = question.sectionId + '|' + question.targetSectionId;
      const signature =
        question.conditionQuestionId + '|' + question.conditionValue;
      if (
        conditionTargetSignatures[key] &&
        conditionTargetSignatures[key] !== signature
      ) {
        throw new Error(
          'La sous-section conditionnelle ' +
            question.targetSectionId +
            ' est associée à plusieurs conditions.'
        );
      }
      conditionTargetSignatures[key] = signature;
    });

  if (config.responseSheetId) {
    const activeId = SpreadsheetApp.getActive().getId();
    if (config.responseSheetId !== activeId) {
      throw new Error(
        'RESPONSE_SHEET_ID ne correspond pas au classeur actif. Videz cette ' +
          'valeur pour laisser le script la renseigner, ou utilisez le bon classeur.'
      );
    }
  }
}

/** Réutilise le FORM_ID mémorisé ou crée un seul nouveau formulaire. */
function getOrCreateForm(config) {
  const spreadsheetId = SpreadsheetApp.getActive().getId();
  if (config.formId) {
    const existingForm = FormApp.openById(config.formId);
    saveFormId(existingForm.getId());
    return existingForm;
  }

  const form = FormApp.create(config.formTitle);
  form.setPublished(true);
  saveFormId(form.getId());
  PropertiesService.getScriptProperties().setProperty(
    createdAtPropertyKey_(spreadsheetId),
    new Date().toISOString()
  );
  return form;
}

/** Supprime les items du formulaire en ordre inverse, jamais ses réponses. */
function clearExistingFormItems(form) {
  const items = form.getItems();
  for (let index = items.length - 1; index >= 0; index -= 1) {
    form.deleteItem(index);
  }
}

/**
 * Construit les sections logiques et sous-sections conditionnelles, puis les
 * questions qu'elles contiennent. La première page utilise un en-tête afin de
 * ne pas créer une page vide avant SECTION 1.
 */
function createSections(form, questions, choices) {
  const plan = buildNavigationPlan_(questions);
  const pageItems = {};
  const itemByQuestionId = {};
  const questionsById = {};
  questions.forEach(function (question) {
    questionsById[question.questionId] = question;
  });

  plan.pages.forEach(function (page, pageIndex) {
    if (pageIndex === 0) {
      const header = form.addSectionHeaderItem().setTitle(page.title);
      if (page.helpText) {
        header.setHelpText(page.helpText);
      }
      pageItems[page.key] = null;
    } else {
      const pageBreak = form.addPageBreakItem().setTitle(page.title);
      if (page.helpText) {
        pageBreak.setHelpText(page.helpText);
      }
      pageItems[page.key] = pageBreak;
    }

    page.questions.forEach(function (question) {
      itemByQuestionId[question.questionId] = createQuestion(
        form,
        question,
        choices
      );
    });
  });

  return {
    plan: plan,
    pageItems: pageItems,
    itemByQuestionId: itemByQuestionId,
    questionsById: questionsById,
  };
}

/** Convertit question_type vers le bon item FormApp. */
function createQuestion(form, question, choices) {
  switch (question.questionType) {
    case 'TEXT':
      return createTextQuestion(form, question);
    case 'PARAGRAPH':
      return createParagraphQuestion(form, question);
    case 'DATE':
      return createDateQuestion(form, question);
    case 'MULTIPLE_CHOICE':
      return createMultipleChoiceQuestion(form, question, choices);
    case 'CHECKBOX':
      return createCheckboxQuestion(form, question, choices);
    case 'SCALE':
      return createScaleQuestion_(form, question, choices);
    case 'SECTION':
      return createInlineSection_(form, question);
    default:
      throw new Error(
        'Type de question non supporté : ' + question.questionType
      );
  }
}

function createTextQuestion(form, question) {
  const item = form
    .addTextItem()
    .setTitle(question.questionTitle)
    .setRequired(question.required);
  if (question.helpText) {
    item.setHelpText(question.helpText);
  }
  applyNumericValidation(item, question);
  return item;
}

function createParagraphQuestion(form, question) {
  const item = form
    .addParagraphTextItem()
    .setTitle(question.questionTitle)
    .setRequired(question.required);
  if (question.helpText) {
    item.setHelpText(question.helpText);
  }
  return item;
}

function createDateQuestion(form, question) {
  const item = form
    .addDateItem()
    .setTitle(question.questionTitle)
    .setIncludesYear(true)
    .setRequired(question.required);
  if (question.helpText) {
    item.setHelpText(question.helpText);
  }
  return item;
}

function createMultipleChoiceQuestion(form, question, choices) {
  const values = choiceValues_(choices, question.choicesGroup);
  const item = form
    .addMultipleChoiceItem()
    .setTitle(question.questionTitle)
    .setChoiceValues(values)
    .setRequired(question.required);
  if (question.helpText) {
    item.setHelpText(question.helpText);
  }
  return item;
}

function createCheckboxQuestion(form, question, choices) {
  const values = choiceValues_(choices, question.choicesGroup);
  const item = form
    .addCheckboxItem()
    .setTitle(question.questionTitle)
    .setChoiceValues(values)
    .setRequired(question.required);
  if (question.helpText) {
    item.setHelpText(question.helpText);
  }
  return item;
}

function createScaleQuestion_(form, question, choices) {
  const item = form
    .addScaleItem()
    .setTitle(question.questionTitle)
    .setBounds(question.minValue, question.maxValue)
    .setRequired(question.required);
  if (question.helpText) {
    item.setHelpText(question.helpText);
  }
  if (question.choicesGroup && choices[question.choicesGroup]) {
    const labels = choiceValues_(choices, question.choicesGroup);
    if (labels.length >= 2) {
      item.setLabels(labels[0], labels[labels.length - 1]);
    }
  }
  return item;
}

function createInlineSection_(form, question) {
  const item = form.addSectionHeaderItem().setTitle(question.questionTitle);
  if (question.helpText) {
    item.setHelpText(question.helpText);
  }
  return item;
}

/** Applique une validation d'entier et, si fournie, une plage inclusive. */
function applyNumericValidation(item, question) {
  if (question.minValue === null && question.maxValue === null) {
    return item;
  }
  let builder = FormApp.createTextValidation().requireWholeNumber();
  if (question.minValue !== null && question.maxValue !== null) {
    builder = builder.requireNumberBetween(
      question.minValue,
      question.maxValue
    );
  } else if (question.minValue !== null) {
    builder = builder.requireNumberGreaterThanOrEqualTo(question.minValue);
  } else {
    builder = builder.requireNumberLessThanOrEqualTo(question.maxValue);
  }
  builder = builder.setHelpText(
    question.helpText || 'Saisissez un entier dans la plage autorisée.'
  );
  item.setValidation(builder.build());
  return item;
}

/**
 * Remplace les choix des questions déclencheuses par des choix navigants.
 * Toutes les destinations sont des PageBreakItem créés depuis le plan.
 */
function configureConditionalNavigation(form, buildResult, choices) {
  buildResult.plan.navigations.forEach(function (navigation) {
    const item = buildResult.itemByQuestionId[navigation.parentQuestionId];
    const question = buildResult.questionsById[navigation.parentQuestionId];
    if (!item || !question) {
      throw new Error(
        'Impossible de configurer la navigation de ' +
          navigation.parentQuestionId +
          '.'
      );
    }
    const values = choiceValues_(choices, question.choicesGroup);
    const navigableChoices = values.map(function (value) {
      const matchingCase = navigation.cases.filter(function (conditionCase) {
        return conditionCase.value === value;
      })[0];
      const targetKey = matchingCase
        ? matchingCase.targetKey
        : navigation.defaultTargetKey;
      if (targetKey === SUBMIT_TARGET) {
        return item.createChoice(value, FormApp.PageNavigationType.SUBMIT);
      }
      const targetPage = buildResult.pageItems[targetKey];
      if (!targetPage) {
        throw new Error(
          'Page cible introuvable pour la navigation : ' + targetKey + '.'
        );
      }
      return item.createChoice(value, targetPage);
    });
    item.setChoices(navigableChoices);
  });

  // Si plusieurs branches suivent le même déclencheur, la limite de page
  // placée après une branche saute les autres branches et rejoint la suite.
  buildResult.plan.pages.forEach(function (page, index) {
    if (!page.afterTargetKey || index + 1 >= buildResult.plan.pages.length) {
      return;
    }
    const nextPage = buildResult.plan.pages[index + 1];
    if (page.afterTargetKey === nextPage.key) {
      return;
    }
    const boundary = buildResult.pageItems[nextPage.key];
    if (!boundary) {
      throw new Error('Limite de page conditionnelle introuvable.');
    }
    if (page.afterTargetKey === SUBMIT_TARGET) {
      boundary.setGoToPage(FormApp.PageNavigationType.SUBMIT);
    } else {
      const destination = buildResult.pageItems[page.afterTargetKey];
      if (!destination) {
        throw new Error(
          'Destination de sortie de branche introuvable : ' +
            page.afterTargetKey +
            '.'
        );
      }
      boundary.setGoToPage(destination);
    }
  });
  return form;
}

/** Lie le formulaire au classeur actif sans détourner un formulaire lié ailleurs. */
function configureResponseDestination(form, config) {
  const spreadsheet = SpreadsheetApp.getActive();
  const destinationId = form.getDestinationId();
  if (destinationId && destinationId !== spreadsheet.getId()) {
    throw new Error(
      'Le FORM_ID pointe vers un formulaire déjà lié à un autre ' +
        'Google Spreadsheet. Corrigez FORM_ID au lieu de modifier cette destination.'
    );
  }
  if (!destinationId) {
    form.setDestination(
      FormApp.DestinationType.SPREADSHEET,
      spreadsheet.getId()
    );
  }
  updateConfigValue_('RESPONSE_SHEET_ID', spreadsheet.getId());
  return spreadsheet.getId();
}

/** Enregistre les URLs et compteurs dans FORM_LINKS (une ligne courante). */
function saveFormMetadata(form, config, questionCount, sectionCount) {
  const spreadsheet = SpreadsheetApp.getActive();
  const sheet = getOrCreateSheet_(SHEET_NAMES.LINKS);
  const headers = [
    'FORM_ID',
    'EDIT_URL',
    'PUBLIC_URL',
    'RESPONSE_SHEET_URL',
    'CREATED_AT',
    'LAST_GENERATED_AT',
    'FORM_VERSION',
    'QUESTION_COUNT',
    'SECTION_COUNT',
  ];
  const properties = PropertiesService.getScriptProperties();
  const createdKey = createdAtPropertyKey_(spreadsheet.getId());
  let createdAtIso = properties.getProperty(createdKey);
  if (!createdAtIso) {
    createdAtIso = new Date().toISOString();
    properties.setProperty(createdKey, createdAtIso);
  }

  sheet.clearContents();
  sheet.getRange(1, 1, 1, headers.length).setValues([headers]);
  sheet.getRange(2, 1, 1, headers.length).setValues([
    [
      form.getId(),
      form.getEditUrl(),
      form.getPublishedUrl(),
      spreadsheet.getUrl(),
      new Date(createdAtIso),
      new Date(),
      config.formVersion,
      questionCount,
      sectionCount,
    ],
  ]);
  formatOutputTable_(sheet, headers.length);
  sheet.getRange(2, 5, 1, 2).setNumberFormat('yyyy-mm-dd hh:mm:ss');
  updateConfigValue_('FORM_ID', form.getId());
}

/** Ajoute une entrée traçable dans GENERATION_LOG. */
function writeGenerationLog(
  status,
  message,
  sectionCount,
  questionCount,
  formId
) {
  const sheet = getOrCreateSheet_(SHEET_NAMES.LOG);
  const headers = [
    'TIMESTAMP',
    'STATUS',
    'MESSAGE',
    'SECTION_COUNT',
    'QUESTION_COUNT',
    'FORM_ID',
  ];
  if (sheet.getLastRow() === 0) {
    sheet.getRange(1, 1, 1, headers.length).setValues([headers]);
    formatOutputTable_(sheet, headers.length);
  }
  sheet.appendRow([
    new Date(),
    status,
    message,
    sectionCount || 0,
    questionCount || 0,
    formId || '',
  ]);
  sheet
    .getRange(Math.max(2, sheet.getLastRow()), 1)
    .setNumberFormat('yyyy-mm-dd hh:mm:ss');
}

function showFormUrl() {
  const config = loadFormConfig();
  if (!config.formId) {
    SpreadsheetApp.getUi().alert(
      "Aucun FORM_ID. Lancez d'abord la génération."
    );
    return;
  }
  const url = FormApp.openById(config.formId).getPublishedUrl();
  SpreadsheetApp.getUi().alert('Lien public du formulaire', url, SpreadsheetApp.getUi().ButtonSet.OK);
}

function showResponsesUrl() {
  SpreadsheetApp.getUi().alert(
    'Google Spreadsheet des réponses',
    SpreadsheetApp.getActive().getUrl(),
    SpreadsheetApp.getUi().ButtonSet.OK
  );
}

/** Fonction publique utile pour réinstaller manuellement le trigger si besoin. */
function installOnFormSubmitTrigger() {
  const created = ensureOnFormSubmitTrigger_();
  SpreadsheetApp.getUi().alert(
    created
      ? 'Trigger onFormSubmit installé.'
      : 'Le trigger onFormSubmit est déjà installé.'
  );
}

function ensureOnFormSubmitTrigger_() {
  const spreadsheet = SpreadsheetApp.getActive();
  const exists = ScriptApp.getProjectTriggers().some(function (trigger) {
    return (
      trigger.getHandlerFunction() === 'onFormSubmit' &&
      trigger.getEventType() === ScriptApp.EventType.ON_FORM_SUBMIT &&
      trigger.getTriggerSourceId() === spreadsheet.getId()
    );
  });
  if (exists) {
    return false;
  }
  ScriptApp.newTrigger('onFormSubmit')
    .forSpreadsheet(spreadsheet)
    .onFormSubmit()
    .create();
  return true;
}

/** Retourne le libellé métier exact associé à une note de 0 à 10. */
function getSatisfactionLevel(rating) {
  const numericRating = Number(rating);
  if (!Number.isFinite(numericRating) || numericRating < 0 || numericRating > 10) {
    throw new Error('La note de satisfaction doit être comprise entre 0 et 10.');
  }
  if (numericRating >= 9) return 'Excellent';
  if (numericRating >= 7) return 'Très bon';
  if (numericRating >= 5) return 'Bon';
  if (numericRating >= 3) return 'Passable';
  return 'Médiocre';
}

/**
 * Trigger installable de type « Depuis le tableur > Lors de l'envoi du
 * formulaire ». Il ajoute uniquement une valeur dérivée à la ligne soumise.
 */
function onFormSubmit(e) {
  if (!e || !e.range) {
    throw new Error(
      'onFormSubmit doit être exécuté par un trigger de soumission du tableur.'
    );
  }
  const rating = getRatingFromResponse(e);
  if (rating === null) {
    writeGenerationLog(
      'WARNING',
      'Soumission reçue sans colonne de note globale ; aucun calcul effectué.',
      0,
      0,
      loadFormConfig().formId
    );
    return;
  }
  const level = getSatisfactionLevel(rating);
  saveSatisfactionLevel(e, level);
  Logger.log('Niveau de satisfaction calculé : %s', level);
}

function getRatingFromResponse(e) {
  if (e.namedValues && e.namedValues[RATING_QUESTION_TITLE]) {
    const value = e.namedValues[RATING_QUESTION_TITLE];
    return Array.isArray(value) ? value[0] : value;
  }
  const sheet = e.range.getSheet();
  const headers = sheet
    .getRange(1, 1, 1, sheet.getLastColumn())
    .getDisplayValues()[0];
  const columnIndex = headers.indexOf(RATING_QUESTION_TITLE);
  if (columnIndex === -1) {
    return null;
  }
  return sheet.getRange(e.range.getRow(), columnIndex + 1).getValue();
}

function saveSatisfactionLevel(e, level) {
  const lock = LockService.getDocumentLock();
  lock.waitLock(30000);
  try {
    const sheet = e.range.getSheet();
    let lastColumn = sheet.getLastColumn();
    const headers = sheet
      .getRange(1, 1, 1, lastColumn)
      .getDisplayValues()[0];
    let columnIndex = headers.indexOf(SATISFACTION_HEADER) + 1;
    if (columnIndex === 0) {
      columnIndex = lastColumn + 1;
      sheet.getRange(1, columnIndex).setValue(SATISFACTION_HEADER);
    }
    sheet.getRange(e.range.getRow(), columnIndex).setValue(level);
  } finally {
    lock.releaseLock();
  }
}

function buildNavigationPlan_(questions) {
  const sections = getLogicalSections_(questions);
  const pages = [];
  const navigations = [];

  sections.forEach(function (section, sectionIndex) {
    const conditionalByParent = {};
    const regularQuestions = [];
    section.questions.forEach(function (question) {
      if (question.conditionQuestionId) {
        if (!conditionalByParent[question.conditionQuestionId]) {
          conditionalByParent[question.conditionQuestionId] = [];
        }
        conditionalByParent[question.conditionQuestionId].push(question);
      } else {
        regularQuestions.push(question);
      }
    });
    if (!regularQuestions.length) {
      throw new Error(
        'La section ' + section.sectionId + ' ne contient aucune question principale.'
      );
    }

    let currentKey = logicalPageKey_(section.sectionId);
    let currentTitle = section.sectionTitle;
    let currentQuestions = [];
    let continuationNumber = 0;

    regularQuestions.forEach(function (question, questionIndex) {
      currentQuestions.push(question);
      const children = conditionalByParent[question.questionId] || [];
      if (!children.length) {
        return;
      }

      pages.push({
        key: currentKey,
        title: currentTitle,
        helpText: '',
        kind: currentKey.indexOf('logical:') === 0 ? 'logical' : 'continuation',
        questions: currentQuestions,
        afterTargetKey: '',
      });

      const hasMoreQuestions = questionIndex < regularQuestions.length - 1;
      const defaultTargetKey = hasMoreQuestions
        ? 'continuation:' +
          section.sectionId +
          ':' +
          String(++continuationNumber)
        : '';
      const navigation = {
        parentQuestionId: question.questionId,
        sectionIndex: sectionIndex,
        defaultTargetKey: defaultTargetKey,
        cases: [],
      };
      const navigationIndex = navigations.length;
      navigations.push(navigation);

      const branches = groupConditionalBranches_(children);
      branches.forEach(function (branch) {
        const branchKey =
          'branch:' + section.sectionId + ':' + branch.targetSectionId;
        if (
          pages.some(function (page) {
            return page.key === branchKey;
          })
        ) {
          throw new Error('Sous-section conditionnelle dupliquée : ' + branchKey + '.');
        }
        pages.push({
          key: branchKey,
          title: section.sectionTitle + ' — complément conditionnel',
          helpText:
            'Affiché lorsque « ' +
            question.questionTitle +
            ' » = « ' +
            branch.conditionValue +
            ' ».',
          kind: 'branch',
          questions: branch.questions,
          afterTargetKey: '',
          navigationIndex: navigationIndex,
        });
        navigation.cases.push({
          value: branch.conditionValue,
          targetKey: branchKey,
        });
      });

      currentKey = defaultTargetKey;
      currentTitle = section.sectionTitle + ' — suite';
      currentQuestions = [];
    });

    if (currentQuestions.length) {
      pages.push({
        key: currentKey,
        title: currentTitle,
        helpText: '',
        kind: currentKey.indexOf('logical:') === 0 ? 'logical' : 'continuation',
        questions: currentQuestions,
        afterTargetKey: '',
      });
    }
  });

  navigations.forEach(function (navigation) {
    if (!navigation.defaultTargetKey) {
      navigation.defaultTargetKey =
        navigation.sectionIndex + 1 < sections.length
          ? logicalPageKey_(sections[navigation.sectionIndex + 1].sectionId)
          : SUBMIT_TARGET;
    }
  });
  pages.forEach(function (page) {
    if (page.kind === 'branch') {
      page.afterTargetKey = navigations[page.navigationIndex].defaultTargetKey;
    }
  });

  const pageKeys = {};
  pages.forEach(function (page) {
    if (!page.key) {
      throw new Error('Le plan de navigation contient une page sans identifiant.');
    }
    if (pageKeys[page.key]) {
      throw new Error('Identifiant de page dupliqué : ' + page.key + '.');
    }
    pageKeys[page.key] = true;
  });
  navigations.forEach(function (navigation) {
    const targets = navigation.cases
      .map(function (conditionCase) {
        return conditionCase.targetKey;
      })
      .concat([navigation.defaultTargetKey]);
    targets.forEach(function (target) {
      if (target !== SUBMIT_TARGET && !pageKeys[target]) {
        throw new Error('La page cible ' + target + " n'existe pas dans le plan.");
      }
    });
  });
  return { pages: pages, navigations: navigations };
}

function groupConditionalBranches_(questions) {
  const groups = {};
  questions.forEach(function (question) {
    const key = question.targetSectionId;
    if (!groups[key]) {
      groups[key] = {
        targetSectionId: key,
        conditionValue: question.conditionValue,
        questions: [],
      };
    }
    if (groups[key].conditionValue !== question.conditionValue) {
      throw new Error(
        'La sous-section ' + key + ' contient plusieurs valeurs conditionnelles.'
      );
    }
    groups[key].questions.push(question);
  });
  return Object.keys(groups)
    .map(function (key) {
      groups[key].questions.sort(compareQuestions_);
      return groups[key];
    })
    .sort(function (a, b) {
      return a.questions[0].questionOrder - b.questions[0].questionOrder;
    });
}

function getLogicalSections_(questions) {
  const sectionsById = {};
  questions.forEach(function (question) {
    if (!sectionsById[question.sectionId]) {
      sectionsById[question.sectionId] = {
        sectionId: question.sectionId,
        sectionOrder: question.sectionOrder,
        sectionTitle: question.sectionTitle,
        questions: [],
      };
    }
    sectionsById[question.sectionId].questions.push(question);
  });
  return Object.keys(sectionsById)
    .map(function (sectionId) {
      sectionsById[sectionId].questions.sort(compareQuestions_);
      return sectionsById[sectionId];
    })
    .sort(function (a, b) {
      return a.sectionOrder - b.sectionOrder;
    });
}

function ensureOutputSheets_() {
  getOrCreateSheet_(SHEET_NAMES.LINKS);
  getOrCreateSheet_(SHEET_NAMES.LOG);
}

function getOrCreateSheet_(sheetName) {
  const spreadsheet = SpreadsheetApp.getActive();
  return spreadsheet.getSheetByName(sheetName) || spreadsheet.insertSheet(sheetName);
}

function formatOutputTable_(sheet, columnCount) {
  sheet.setFrozenRows(1);
  sheet
    .getRange(1, 1, 1, columnCount)
    .setFontWeight('bold')
    .setBackground('#1F4E78')
    .setFontColor('#FFFFFF');
  sheet.autoResizeColumns(1, columnCount);
}

function saveFormId(formId) {
  const spreadsheetId = SpreadsheetApp.getActive().getId();
  updateConfigValue_('FORM_ID', formId);
  PropertiesService.getScriptProperties().setProperty(
    formPropertyKey_(spreadsheetId),
    formId
  );
}

function updateConfigValue_(key, value) {
  const sheet = SpreadsheetApp.getActive().getSheetByName(SHEET_NAMES.CONFIG);
  if (!sheet) {
    throw new Error('La feuille ' + SHEET_NAMES.CONFIG + " n'existe pas.");
  }
  const data = sheet.getDataRange().getValues();
  const headers = data[0].map(cleanString_);
  const keyColumn = headers.indexOf('KEY');
  const valueColumn = headers.indexOf('VALUE');
  if (keyColumn === -1 || valueColumn === -1) {
    throw new Error('CONFIG_FORM doit contenir les colonnes KEY et VALUE.');
  }
  for (let rowIndex = 1; rowIndex < data.length; rowIndex += 1) {
    if (cleanString_(data[rowIndex][keyColumn]) === key) {
      sheet.getRange(rowIndex + 1, valueColumn + 1).setValue(value);
      return;
    }
  }
  throw new Error('La clé ' + key + " n'existe pas dans CONFIG_FORM.");
}

function readTable_(sheetName) {
  const sheet = SpreadsheetApp.getActive().getSheetByName(sheetName);
  if (!sheet) {
    throw new Error('La feuille ' + sheetName + " n'existe pas.");
  }
  const values = sheet.getDataRange().getValues();
  if (!values.length) {
    return [];
  }
  const headers = values[0].map(cleanString_);
  return values
    .slice(1)
    .map(function (row, index) {
      const object = { __rowNumber: index + 2 };
      headers.forEach(function (header, columnIndex) {
        object[header] = row[columnIndex];
      });
      return object;
    })
    .filter(function (row) {
      return headers.some(function (header) {
        return cleanString_(row[header]) !== '';
      });
    });
}

function choiceValues_(choices, group) {
  if (!group || !choices[group]) {
    throw new Error('Groupe de choix introuvable : ' + (group || '(vide)') + '.');
  }
  return choices[group].map(function (choice) {
    return choice.value;
  });
}

function cleanString_(value) {
  if (value === null || value === undefined) return '';
  return String(value).trim();
}

function requiredNumber_(value, fieldName, rowNumber) {
  const number = optionalNumber_(value, fieldName, rowNumber);
  if (number === null) {
    throw new Error(
      fieldName + ' est obligatoire à la ligne ' + rowNumber + '.'
    );
  }
  return number;
}

function optionalNumber_(value, fieldName, rowNumber) {
  if (value === '' || value === null || value === undefined) return null;
  const number = Number(value);
  if (!Number.isFinite(number)) {
    throw new Error(
      fieldName + ' doit être numérique à la ligne ' + rowNumber + '.'
    );
  }
  return number;
}

function strictBoolean_(value, fieldName, rowNumber) {
  if (value === true || value === false) return value;
  const normalized = cleanString_(value).toUpperCase();
  if (normalized === 'TRUE') return true;
  if (normalized === 'FALSE') return false;
  throw new Error(
    fieldName + ' doit valoir TRUE ou FALSE à la ligne ' + rowNumber + '.'
  );
}

function compareQuestions_(a, b) {
  if (a.sectionOrder !== b.sectionOrder) {
    return a.sectionOrder - b.sectionOrder;
  }
  if (a.questionOrder !== b.questionOrder) {
    return a.questionOrder - b.questionOrder;
  }
  return a.rowNumber - b.rowNumber;
}

function logicalPageKey_(sectionId) {
  return 'logical:' + sectionId;
}

function formPropertyKey_(spreadsheetId) {
  return 'FORM_ID_' + spreadsheetId;
}

function createdAtPropertyKey_(spreadsheetId) {
  return 'FORM_CREATED_AT_' + spreadsheetId;
}
