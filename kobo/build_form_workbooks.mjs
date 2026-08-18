import fs from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { SpreadsheetFile, Workbook } from "@oai/artifact-tool";

const scriptDir = path.dirname(fileURLToPath(import.meta.url));
const projectDir = path.resolve(scriptDir, "..");
const previewDir = path.join(scriptDir, ".artifact_work", "previews");

const googleOutput = path.join(
  projectDir,
  "google_forms",
  "google_forms_config.xlsx",
);
const koboOutput = path.join(scriptDir, "evaluation_application_kobo.xlsx");

const COLORS = {
  google: "#1F4E78",
  survey: "#1B5E20",
  choices: "#1565C0",
  settings: "#8A4B08",
  headerText: "#FFFFFF",
  bodyText: "#1F2937",
  alternate: "#F5F8FA",
  border: "#D9E2F3",
};

await fs.mkdir(previewDir, { recursive: true });
await buildGoogleFormsConfig();
await buildKoboXlsForm();

async function buildGoogleFormsConfig() {
  const configCsv = await fs.readFile(
    path.join(projectDir, "google_forms", "config_template.csv"),
    "utf8",
  );
  const questionsCsv = await fs.readFile(
    path.join(projectDir, "google_forms", "questions_template.csv"),
    "utf8",
  );
  const choicesCsv = await fs.readFile(
    path.join(projectDir, "google_forms", "choices_template.csv"),
    "utf8",
  );

  const workbook = await Workbook.fromCSV(configCsv, {
    sheetName: "CONFIG_FORM",
  });
  await workbook.fromCSV(questionsCsv, { sheetName: "QUESTIONS" });
  await workbook.fromCSV(choicesCsv, { sheetName: "CHOICES" });
  workbook.worksheets.getItem("CONFIG_FORM").getRange("B6").format.numberFormat =
    "0.0";

  const links = workbook.worksheets.add("FORM_LINKS");
  links.getRange("A1:I1").values = [[
    "FORM_ID",
    "EDIT_URL",
    "PUBLIC_URL",
    "RESPONSE_SHEET_URL",
    "CREATED_AT",
    "LAST_GENERATED_AT",
    "FORM_VERSION",
    "QUESTION_COUNT",
    "SECTION_COUNT",
  ]];

  const log = workbook.worksheets.add("GENERATION_LOG");
  log.getRange("A1:F1").values = [[
    "TIMESTAMP",
    "STATUS",
    "MESSAGE",
    "SECTION_COUNT",
    "QUESTION_COUNT",
    "FORM_ID",
  ]];

  styleGoogleSheet(workbook.worksheets.getItem("CONFIG_FORM"), "A1:B7", {
    widths: [26, 82],
    bodyHeight: 34,
  });
  styleGoogleSheet(workbook.worksheets.getItem("QUESTIONS"), "A1:P29", {
    widths: [13, 20, 47, 14, 24, 58, 20, 11, 25, 42, 11, 11, 27, 20, 24, 11],
    bodyHeight: 42,
  });
  styleGoogleSheet(workbook.worksheets.getItem("CHOICES"), "A1:C44", {
    widths: [26, 57, 10],
    bodyHeight: 24,
  });
  styleGoogleSheet(links, "A1:I2", {
    widths: [28, 45, 45, 45, 22, 22, 15, 17, 16],
    bodyHeight: 26,
  });
  styleGoogleSheet(log, "A1:F2", {
    widths: [22, 14, 65, 17, 18, 28],
    bodyHeight: 26,
  });

  const inspections = [];
  inspections.push(
    await workbook.inspect({
      kind: "table",
      range: "QUESTIONS!A1:P12",
      include: "values,formulas",
      tableMaxRows: 12,
      tableMaxCols: 16,
      maxChars: 9000,
    }),
  );
  inspections.push(
    await workbook.inspect({
      kind: "match",
      searchTerm: "#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A",
      options: { useRegex: true, maxResults: 100 },
      summary: "google forms workbook formula error scan",
      maxChars: 3000,
    }),
  );
  for (const inspection of inspections) {
    console.log(inspection.ndjson);
  }

  for (const sheetName of [
    "CONFIG_FORM",
    "QUESTIONS",
    "CHOICES",
    "FORM_LINKS",
    "GENERATION_LOG",
  ]) {
    await renderSheet(workbook, sheetName, `google_${sheetName}.png`);
  }

  const output = await SpreadsheetFile.exportXlsx(workbook);
  await output.save(googleOutput);
  console.log(`GOOGLE_OUTPUT=${googleOutput}`);
}

async function buildKoboXlsForm() {
  const workbook = Workbook.create();
  const survey = workbook.worksheets.add("survey");
  const choices = workbook.worksheets.add("choices");
  const settings = workbook.worksheets.add("settings");

  const surveyHeaders = [
    "type",
    "name",
    "label",
    "required",
    "relevant",
    "constraint",
    "constraint_message",
    "calculation",
    "appearance",
    "hint",
  ];
  const surveyRows = [
    ["begin_group", "section_evaluator", "SECTION 1 — Informations sur l'évaluateur", "", "", "", "", "", "", ""],
    ["date", "evaluation_date", "Date de l'évaluation", "yes", "", "", "", "", "", ""],
    ["text", "evaluator_name", "Votre nom", "", "", "", "", "", "", ""],
    ["select_one role", "role", "Votre rôle / profession", "yes", "", "", "", "", "", ""],
    ["text", "other_profession", "Autre profession", "yes", "${role} = 'other'", "", "", "", "", "Obligatoire lorsque le rôle sélectionné est Autre."],
    ["select_one device", "device", "Comment avez-vous accédé à l'application ?", "yes", "", "", "", "", "", ""],
    ["select_one yes_no", "first_usage", "Est-ce votre première utilisation de l'application ?", "yes", "", "", "", "", "", ""],
    ["select_one previous_usage_count", "previous_usage_count", "Combien de fois l'avez-vous utilisée auparavant ?", "", "${first_usage} = 'no'", "", "", "", "", ""],
    ["end_group", "", "", "", "", "", "", "", "", ""],

    ["begin_group", "section_interface", "SECTION 2 — Première impression et interface", "", "", "", "", "", "", ""],
    ["select_one likert_5", "interface_attractive", "L'interface est attrayante et bien conçue", "yes", "", "", "", "", "", ""],
    ["select_one likert_5", "easy_navigation", "L'application est facile à naviguer", "yes", "", "", "", "", "", ""],
    ["select_one likert_5", "clear_labels", "Les menus et les boutons sont clairement libellés", "yes", "", "", "", "", "", ""],
    ["select_one likert_5", "loading_speed", "L'application se charge rapidement", "yes", "", "", "", "", "", ""],
    ["select_one likert_5", "device_compatibility", "L'application fonctionne bien sur mon appareil", "yes", "", "", "", "", "", ""],
    ["end_group", "", "", "", "", "", "", "", "", ""],

    ["begin_group", "section_features", "SECTION 3 — Fonctionnalités et performances", "", "", "", "", "", "", ""],
    ["select_multiple features_tested", "features_tested", "Quelles fonctionnalités avez-vous testées ?", "yes", "", "", "", "", "", ""],
    ["select_one likert_5", "needs_fit", "Les fonctionnalités répondent à mes besoins", "yes", "", "", "", "", "", ""],
    ["select_one likert_5", "features_ease", "Les fonctionnalités sont faciles à utiliser", "yes", "", "", "", "", "", ""],
    ["select_one likert_5", "result_accuracy", "Les résultats fournis sont précis", "yes", "", "", "", "", "", ""],
    ["select_one likert_5", "task_efficiency", "L'application m'aide à accomplir mes tâches efficacement", "yes", "", "", "", "", "", ""],
    ["select_one likert_5", "instructions_clarity", "Les instructions et l'aide sont claires et utiles", "yes", "", "", "", "", "", ""],
    ["end_group", "", "", "", "", "", "", "", "", ""],

    ["begin_group", "section_problems", "SECTION 4 — Problèmes rencontrés", "", "", "", "", "", "", ""],
    ["select_one yes_no", "problem_yes_no", "Avez-vous rencontré des problèmes ou des erreurs ?", "yes", "", "", "", "", "", ""],
    ["select_multiple problem_types", "problem_types", "Quel(s) type(s) de problème(s) ?", "", "${problem_yes_no} = 'yes'", "", "", "", "", ""],
    ["text", "problem_description", "Veuillez décrire le(s) problème(s) en détail", "", "${problem_yes_no} = 'yes'", "", "", "", "multiline", ""],
    ["end_group", "", "", "", "", "", "", "", "", ""],

    ["begin_group", "section_satisfaction", "SECTION 5 — Satisfaction globale", "", "", "", "", "", "", ""],
    ["integer", "rating", "Note globale de l'application", "yes", "", ". >= 0 and . <= 10", "La note doit être un entier compris entre 0 et 10.", "", "", ""],
    ["calculate", "satisfaction_level", "Niveau de satisfaction", "", "", "", "", "if(${rating} >= 9, 'Excellent', if(${rating} >= 7, 'Très bon', if(${rating} >= 5, 'Bon', if(${rating} >= 3, 'Passable', 'Médiocre'))))", "", ""],
    ["note", "satisfaction_level_display", "Niveau de satisfaction : ${satisfaction_level}", "", "${rating} >= 0", "", "", "", "", "Champ calculé en lecture seule."],
    ["select_one recommendation", "recommendation", "Recommanderiez-vous cette application ?", "yes", "", "", "", "", "", ""],
    ["select_one reuse", "reuse", "Utiliseriez-vous cette application à nouveau ?", "yes", "", "", "", "", "", ""],
    ["end_group", "", "", "", "", "", "", "", "", ""],

    ["begin_group", "section_improvements", "SECTION 6 — Suggestions d'amélioration", "", "", "", "", "", "", ""],
    ["text", "strengths", "Quels sont les principaux points forts de cette application ?", "yes", "", "", "", "", "multiline", ""],
    ["text", "improvements", "Qu'est-ce qui pourrait être amélioré ?", "yes", "", "", "", "", "multiline", ""],
    ["text", "missing_features", "Quelles fonctionnalités manquantes aimeriez-vous voir ajoutées ?", "", "", "", "", "", "multiline", ""],
    ["text", "additional_comments", "Commentaires ou suggestions supplémentaires", "", "", "", "", "", "multiline", ""],
    ["note", "final_message", "Merci pour votre précieux retour ! Vos commentaires nous aideront à améliorer l'application.", "", "", "", "", "", "", ""],
    ["end_group", "", "", "", "", "", "", "", "", ""],
  ];

  survey.getRangeByIndexes(0, 0, surveyRows.length + 1, surveyHeaders.length).values = [
    surveyHeaders,
    ...surveyRows,
  ];

  const choiceHeaders = ["list_name", "name", "label"];
  const choiceRows = [
    ["role", "student", "Étudiant"],
    ["role", "teacher", "Enseignant"],
    ["role", "researcher", "Chercheur"],
    ["role", "data_analyst", "Analyste de données"],
    ["role", "developer", "Développeur"],
    ["role", "project_manager", "Chef de projet"],
    ["role", "other", "Autre"],
    ["device", "computer", "Ordinateur"],
    ["device", "tablet", "Tablette"],
    ["device", "smartphone", "Smartphone"],
    ["yes_no", "yes", "Oui"],
    ["yes_no", "no", "Non"],
    ["previous_usage_count", "times_2_3", "2 à 3 fois"],
    ["previous_usage_count", "times_4_5", "4 à 5 fois"],
    ["previous_usage_count", "times_gt_5", "Plus de 5 fois"],
    ["likert_5", "strongly_disagree", "Tout à fait en désaccord"],
    ["likert_5", "disagree", "En désaccord"],
    ["likert_5", "neutral", "Neutre"],
    ["likert_5", "agree", "D'accord"],
    ["likert_5", "strongly_agree", "Tout à fait d'accord"],
    ["features_tested", "scraping", "Collecte (scraping) de données"],
    ["features_tested", "download", "Téléchargement"],
    ["features_tested", "form", "Remplissage du formulaire"],
    ["features_tested", "dashboard", "Tableau de bord des données"],
    ["problem_types", "loading", "Erreur de chargement"],
    ["problem_types", "display", "Problème d'affichage"],
    ["problem_types", "broken_feature", "Fonctionnalité non fonctionnelle"],
    ["problem_types", "data_loss", "Perte de données"],
    ["problem_types", "slow", "Performance lente"],
    ["problem_types", "confusing_ui", "Interface confuse"],
    ["problem_types", "other", "Autre"],
    ["recommendation", "yes_definitely", "Oui, sans hésiter"],
    ["recommendation", "yes_probably", "Oui, probablement"],
    ["recommendation", "maybe", "Peut-être"],
    ["recommendation", "probably_not", "Probablement pas"],
    ["recommendation", "no", "Non"],
    ["reuse", "yes_regularly", "Oui, régulièrement"],
    ["reuse", "yes_occasional", "Oui, occasionnellement"],
    ["reuse", "maybe", "Peut-être"],
    ["reuse", "probably_not", "Probablement pas"],
    ["reuse", "no", "Non"],
  ];
  choices.getRangeByIndexes(0, 0, choiceRows.length + 1, choiceHeaders.length).values = [
    choiceHeaders,
    ...choiceRows,
  ];

  const settingsRows = [
    ["form_title", "form_id", "version", "default_language"],
    ["Évaluation de l'application Web", "evaluation_application_web", "1.0", "French (fr)"],
  ];
  settings.getRange("A1:D2").values = settingsRows;
  settings.getRange("C2").format.numberFormat = "0.0";

  styleXlsFormSheet(survey, `A1:J${surveyRows.length + 1}`, COLORS.survey, [
    31, 30, 67, 11, 38, 31, 48, 76, 17, 48,
  ], 42);
  styleXlsFormSheet(choices, `A1:C${choiceRows.length + 1}`, COLORS.choices, [
    27, 28, 57,
  ], 25);
  styleXlsFormSheet(settings, "A1:D2", COLORS.settings, [45, 35, 16, 22], 28);

  const surveyCheck = await workbook.inspect({
    kind: "table",
    range: "survey!A1:J44",
    include: "values,formulas",
    tableMaxRows: 44,
    tableMaxCols: 10,
    maxChars: 18000,
  });
  console.log(surveyCheck.ndjson);
  const errors = await workbook.inspect({
    kind: "match",
    searchTerm: "#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A",
    options: { useRegex: true, maxResults: 100 },
    summary: "xlsform formula error scan",
    maxChars: 3000,
  });
  console.log(errors.ndjson);

  for (const sheetName of ["survey", "choices", "settings"]) {
    await renderSheet(workbook, sheetName, `kobo_${sheetName}.png`);
  }

  const output = await SpreadsheetFile.exportXlsx(workbook);
  await output.save(koboOutput);
  console.log(`KOBO_OUTPUT=${koboOutput}`);
}

function styleGoogleSheet(sheet, rangeAddress, options) {
  const range = sheet.getRange(rangeAddress);
  const matrix = range.values;
  const rowCount = matrix.length;
  const columnCount = matrix[0].length;
  sheet.showGridLines = false;
  sheet.freezePanes.freezeRows(1);
  range.format = {
    font: { name: "Aptos", size: 10, color: COLORS.bodyText },
    verticalAlignment: "center",
    wrapText: true,
  };
  range.format.borders = {
    insideHorizontal: { style: "thin", color: COLORS.border },
    bottom: { style: "thin", color: COLORS.border },
  };
  const header = range.getRow(0);
  header.format = {
    fill: COLORS.google,
    font: { name: "Aptos Display", size: 10, bold: true, color: COLORS.headerText },
    verticalAlignment: "center",
    wrapText: true,
  };
  header.format.rowHeight = 34;
  if (rowCount > 1) {
    range.getRangeByIndexes(1, 0, rowCount - 1, columnCount).format.rowHeight =
      options.bodyHeight;
  }
  setColumnWidths(range, options.widths);
}

function styleXlsFormSheet(sheet, rangeAddress, headerColor, widths, bodyHeight) {
  const range = sheet.getRange(rangeAddress);
  const matrix = range.values;
  const rowCount = matrix.length;
  const columnCount = matrix[0].length;
  sheet.showGridLines = false;
  sheet.freezePanes.freezeRows(1);
  range.format = {
    font: { name: "Aptos", size: 10, color: COLORS.bodyText },
    verticalAlignment: "center",
    wrapText: true,
  };
  range.format.borders = {
    insideHorizontal: { style: "thin", color: "#DDE5ED" },
    bottom: { style: "thin", color: "#DDE5ED" },
  };
  range.getRow(0).format = {
    fill: headerColor,
    font: { name: "Aptos Display", size: 10, bold: true, color: COLORS.headerText },
    verticalAlignment: "center",
    wrapText: true,
  };
  range.getRow(0).format.rowHeight = 34;
  if (rowCount > 1) {
    range.getRangeByIndexes(1, 0, rowCount - 1, columnCount).format.rowHeight =
      bodyHeight;
  }
  setColumnWidths(range, widths);
}

function setColumnWidths(range, widths) {
  widths.forEach((width, index) => {
    range.getColumn(index).format.columnWidth = width;
  });
}

async function renderSheet(workbook, sheetName, fileName) {
  const preview = await workbook.render({
    sheetName,
    autoCrop: "all",
    scale: 1,
    format: "png",
  });
  const bytes = new Uint8Array(await preview.arrayBuffer());
  await fs.writeFile(path.join(previewDir, fileName), bytes);
  console.log(`PREVIEW=${path.join(previewDir, fileName)}`);
}
