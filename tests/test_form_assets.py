from __future__ import annotations

import csv
import re
import zipfile
from pathlib import Path, PurePosixPath
from xml.etree import ElementTree as ET


ROOT = Path(__file__).resolve().parents[1]
GOOGLE_DIR = ROOT / "google_forms"
KOBO_DIR = ROOT / "kobo"
GOOGLE_WORKBOOK = GOOGLE_DIR / "google_forms_config.xlsx"
KOBO_WORKBOOK = KOBO_DIR / "evaluation_application_kobo.xlsx"

QUESTION_HEADERS = [
    "section_order",
    "section_id",
    "section_title",
    "question_order",
    "question_id",
    "question_title",
    "question_type",
    "required",
    "choices_group",
    "help_text",
    "min_value",
    "max_value",
    "condition_question_id",
    "condition_value",
    "target_section_id",
    "active",
]

EXPECTED_SECTION_TITLES = [
    "SECTION 1 — Informations sur l'évaluateur",
    "SECTION 2 — Première impression et interface",
    "SECTION 3 — Fonctionnalités et performances",
    "SECTION 4 — Problèmes rencontrés",
    "SECTION 5 — Satisfaction globale",
    "SECTION 6 — Suggestions d'amélioration",
]


def _read_csv(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    with path.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        rows = list(reader)
    assert reader.fieldnames is not None
    assert all(None not in row for row in rows), f"Colonnes en trop dans {path.name}"
    return reader.fieldnames, rows


def _xlsx_shared_strings(archive: zipfile.ZipFile) -> list[str]:
    try:
        xml = archive.read("xl/sharedStrings.xml")
    except KeyError:
        return []
    root = ET.fromstring(xml)
    namespace = {"m": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
    return [
        "".join(node.text or "" for node in item.findall(".//m:t", namespace))
        for item in root.findall("m:si", namespace)
    ]


def _xlsx_sheet_targets(archive: zipfile.ZipFile) -> dict[str, str]:
    main_ns = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
    rel_ns = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
    package_rel_ns = "http://schemas.openxmlformats.org/package/2006/relationships"

    workbook = ET.fromstring(archive.read("xl/workbook.xml"))
    relationships = ET.fromstring(archive.read("xl/_rels/workbook.xml.rels"))
    targets = {
        relationship.attrib["Id"]: relationship.attrib["Target"]
        for relationship in relationships.findall(f"{{{package_rel_ns}}}Relationship")
    }
    result: dict[str, str] = {}
    for sheet in workbook.findall(f".//{{{main_ns}}}sheet"):
        target = targets[sheet.attrib[f"{{{rel_ns}}}id"]]
        if target.startswith("/"):
            normalized = target.lstrip("/")
        else:
            normalized = str(PurePosixPath("xl") / target)
        result[sheet.attrib["name"]] = normalized
    return result


def _column_index(reference: str) -> int:
    letters = re.match(r"[A-Z]+", reference)
    assert letters
    index = 0
    for letter in letters.group(0):
        index = index * 26 + ord(letter) - ord("A") + 1
    return index - 1


def _xlsx_sheet_rows(path: Path, sheet_name: str) -> list[list[str]]:
    main_ns = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
    namespace = {"m": main_ns}
    with zipfile.ZipFile(path) as archive:
        shared_strings = _xlsx_shared_strings(archive)
        targets = _xlsx_sheet_targets(archive)
        root = ET.fromstring(archive.read(targets[sheet_name]))

    rows: list[list[str]] = []
    for row_node in root.findall(".//m:sheetData/m:row", namespace):
        values: dict[int, str] = {}
        for cell in row_node.findall("m:c", namespace):
            index = _column_index(cell.attrib["r"])
            cell_type = cell.attrib.get("t")
            if cell_type == "inlineStr":
                value = "".join(
                    node.text or "" for node in cell.findall(".//m:t", namespace)
                )
            else:
                value_node = cell.find("m:v", namespace)
                value = value_node.text if value_node is not None else ""
                if cell_type == "s" and value:
                    value = shared_strings[int(value)]
            values[index] = value
        if values:
            rows.append([values.get(index, "") for index in range(max(values) + 1)])
    return rows


def _xlsx_table(path: Path, sheet_name: str) -> list[dict[str, str]]:
    rows = _xlsx_sheet_rows(path, sheet_name)
    assert rows, f"La feuille {sheet_name} est vide"
    headers = rows[0]
    return [
        {
            header: row[index] if index < len(row) else ""
            for index, header in enumerate(headers)
        }
        for row in rows[1:]
    ]


def test_google_form_templates_cover_the_exact_specification() -> None:
    expected_files = {
        "Code.gs",
        "README.md",
        "config_template.csv",
        "questions_template.csv",
        "choices_template.csv",
        "google_forms_config.xlsx",
    }
    assert expected_files.issubset({path.name for path in GOOGLE_DIR.iterdir()})

    config_headers, config_rows = _read_csv(GOOGLE_DIR / "config_template.csv")
    assert config_headers == ["KEY", "VALUE"]
    config = {row["KEY"]: row["VALUE"] for row in config_rows}
    assert config == {
        "FORM_TITLE": "Évaluation de l'application Web",
        "FORM_DESCRIPTION": "Formulaire d'évaluation de l'application Streamlit",
        "FORM_ID": "",
        "RESPONSE_SHEET_ID": "",
        "FORM_VERSION": "1.0",
        "CONFIRMATION_MESSAGE": (
            "Merci pour votre précieux retour ! Vos commentaires nous aideront "
            "à améliorer l'application."
        ),
    }

    question_headers, questions = _read_csv(
        GOOGLE_DIR / "questions_template.csv"
    )
    assert question_headers == QUESTION_HEADERS
    assert len(questions) == 28
    assert all(row["active"] == "TRUE" for row in questions)
    assert len({row["question_id"] for row in questions}) == 28
    assert {row["question_type"] for row in questions} <= {
        "TEXT",
        "PARAGRAPH",
        "DATE",
        "MULTIPLE_CHOICE",
        "CHECKBOX",
        "SCALE",
        "SECTION",
    }
    section_titles = {
        int(row["section_order"]): row["section_title"] for row in questions
    }
    assert [section_titles[index] for index in range(1, 7)] == EXPECTED_SECTION_TITLES

    by_id = {row["question_id"]: row for row in questions}
    assert by_id["rating"]["question_type"] == "TEXT"
    assert by_id["rating"]["required"] == "TRUE"
    assert by_id["rating"]["min_value"] == "0"
    assert by_id["rating"]["max_value"] == "10"
    assert (
        by_id["other_profession"]["condition_question_id"],
        by_id["other_profession"]["condition_value"],
        by_id["other_profession"]["target_section_id"],
    ) == ("role", "Autre", "role_other")
    assert by_id["other_profession"]["required"] == "TRUE"
    assert (
        by_id["previous_usage_count"]["condition_question_id"],
        by_id["previous_usage_count"]["condition_value"],
        by_id["previous_usage_count"]["target_section_id"],
    ) == ("first_usage", "Non", "previous_usage")
    for question_id in ("problem_types", "problem_description"):
        assert (
            by_id[question_id]["condition_question_id"],
            by_id[question_id]["condition_value"],
            by_id[question_id]["target_section_id"],
        ) == ("problem_yes_no", "Oui", "problem_details")

    choice_headers, choice_rows = _read_csv(GOOGLE_DIR / "choices_template.csv")
    assert choice_headers == ["choices_group", "value", "order"]
    groups: dict[str, list[str]] = {}
    for row in choice_rows:
        groups.setdefault(row["choices_group"], []).append(row["value"])
    assert set(groups) == {
        "ROLE",
        "DEVICE",
        "FIRST_USAGE",
        "PREVIOUS_USAGE_COUNT",
        "LIKERT_5",
        "FEATURES_TESTED",
        "PROBLEM_YES_NO",
        "PROBLEM_TYPES",
        "RECOMMENDATION",
        "REUSE",
    }
    assert groups["LIKERT_5"] == [
        "Tout à fait en désaccord",
        "En désaccord",
        "Neutre",
        "D'accord",
        "Tout à fait d'accord",
    ]


def test_apps_script_is_complete_idempotent_and_non_destructive() -> None:
    code = (GOOGLE_DIR / "Code.gs").read_text(encoding="utf-8")
    required_functions = {
        "onOpen",
        "generateEvaluationForm",
        "loadFormConfig",
        "loadQuestionsConfig",
        "loadChoicesConfig",
        "validateSpreadsheetStructure",
        "getOrCreateForm",
        "clearExistingFormItems",
        "createSections",
        "createQuestion",
        "createTextQuestion",
        "createParagraphQuestion",
        "createDateQuestion",
        "createMultipleChoiceQuestion",
        "createCheckboxQuestion",
        "applyNumericValidation",
        "configureConditionalNavigation",
        "configureResponseDestination",
        "saveFormMetadata",
        "writeGenerationLog",
        "rebuildForm",
        "getSatisfactionLevel",
        "onFormSubmit",
    }
    declared = set(re.findall(r"^function\s+([A-Za-z0-9_]+)\s*\(", code, re.MULTILINE))
    assert required_functions <= declared

    assert "FormApp.openById(config.formId)" in code
    assert "FormApp.create(config.formTitle)" in code
    assert "for (let index = items.length - 1" in code
    assert "form.deleteItem(index)" in code
    assert "deleteAllResponses" not in code
    assert "FormApp.DestinationType.SPREADSHEET" in code
    assert "ScriptApp.newTrigger('onFormSubmit')" in code
    assert ".onFormSubmit()" in code
    assert ".requireWholeNumber()" in code
    assert ".requireNumberBetween(" in code
    assert "item.createChoice(value, targetPage)" in code
    assert "PropertiesService" in code
    assert "Logger" in code
    assert "setConfirmationMessage" in code
    assert "Étudiant" not in code, "Les choix doivent venir de CHOICES"
    for level in ("Excellent", "Très bon", "Bon", "Passable", "Médiocre"):
        assert level in code


def test_google_import_workbook_has_the_expected_sheets_and_rows() -> None:
    assert GOOGLE_WORKBOOK.is_file()
    with zipfile.ZipFile(GOOGLE_WORKBOOK) as archive:
        sheet_names = list(_xlsx_sheet_targets(archive))
    assert sheet_names == [
        "CONFIG_FORM",
        "QUESTIONS",
        "CHOICES",
        "FORM_LINKS",
        "GENERATION_LOG",
    ]

    questions = _xlsx_table(GOOGLE_WORKBOOK, "QUESTIONS")
    assert len(questions) == 28
    assert {row["question_id"] for row in questions} == {
        row["question_id"]
        for row in _read_csv(GOOGLE_DIR / "questions_template.csv")[1]
    }
    assert all(row["active"] == "TRUE" for row in questions)

    links = _xlsx_sheet_rows(GOOGLE_WORKBOOK, "FORM_LINKS")
    assert links[0] == [
        "FORM_ID",
        "EDIT_URL",
        "PUBLIC_URL",
        "RESPONSE_SHEET_URL",
        "CREATED_AT",
        "LAST_GENERATED_AT",
        "FORM_VERSION",
        "QUESTION_COUNT",
        "SECTION_COUNT",
    ]


def test_kobo_xlsform_structure_logic_and_calculation() -> None:
    assert KOBO_WORKBOOK.is_file()
    with zipfile.ZipFile(KOBO_WORKBOOK) as archive:
        sheet_names = list(_xlsx_sheet_targets(archive))
    assert sheet_names == ["survey", "choices", "settings"]

    survey_rows = _xlsx_sheet_rows(KOBO_WORKBOOK, "survey")
    assert survey_rows[0] == [
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
    ]
    survey = _xlsx_table(KOBO_WORKBOOK, "survey")
    by_name = {row["name"]: row for row in survey if row.get("name")}

    begin_groups = [row for row in survey if row["type"] == "begin_group"]
    assert [row["label"] for row in begin_groups] == EXPECTED_SECTION_TITLES
    input_rows = [
        row
        for row in survey
        if row["type"]
        not in {"begin_group", "end_group", "calculate", "note"}
    ]
    assert len(input_rows) == 28

    assert by_name["other_profession"]["relevant"] == "${role} = 'other'"
    assert by_name["other_profession"]["required"] == "yes"
    assert (
        by_name["previous_usage_count"]["relevant"]
        == "${first_usage} = 'no'"
    )
    assert by_name["previous_usage_count"]["required"] == ""
    for name in ("problem_types", "problem_description"):
        assert by_name[name]["relevant"] == "${problem_yes_no} = 'yes'"

    rating = by_name["rating"]
    assert rating["type"] == "integer"
    assert rating["required"] == "yes"
    assert rating["constraint"] == ". >= 0 and . <= 10"
    assert "0 et 10" in rating["constraint_message"]

    satisfaction = by_name["satisfaction_level"]
    assert satisfaction["type"] == "calculate"
    calculation = satisfaction["calculation"]
    for threshold in (">= 9", ">= 7", ">= 5", ">= 3"):
        assert threshold in calculation
    for level in ("Excellent", "Très bon", "Bon", "Passable", "Médiocre"):
        assert level in calculation
    assert (
        by_name["satisfaction_level_display"]["label"]
        == "Niveau de satisfaction : ${satisfaction_level}"
    )

    choices = _xlsx_table(KOBO_WORKBOOK, "choices")
    list_names = {row["list_name"] for row in choices}
    assert list_names == {
        "role",
        "device",
        "yes_no",
        "previous_usage_count",
        "likert_5",
        "features_tested",
        "problem_types",
        "recommendation",
        "reuse",
    }
    likert = [row["label"] for row in choices if row["list_name"] == "likert_5"]
    assert likert == [
        "Tout à fait en désaccord",
        "En désaccord",
        "Neutre",
        "D'accord",
        "Tout à fait d'accord",
    ]

    settings = _xlsx_table(KOBO_WORKBOOK, "settings")
    assert len(settings) == 1
    assert settings[0]["form_title"] == "Évaluation de l'application Web"
    assert settings[0]["form_id"] == "evaluation_application_web"
    assert settings[0]["version"] in {"1", "1.0"}
    assert settings[0]["default_language"] == "French (fr)"
