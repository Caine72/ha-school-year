# Changelog

## 0.1.9

- Renamed the HACS repository and integration domain to generic `school_year`.
- Kept Skellefteå kommun grundskola as the currently supported source/parser instead of baking it into the integration name.
- Added source/school-form/parser metadata to diagnostics.
- Updated documentation and release examples for the generic repository name.

## 0.1.8

- Prepared repository structure for HACS custom repository use.
- Added `hacs.json`.
- Added repository metadata files and GitHub workflows.
- Added local brand icon assets.
- Updated manifest documentation, issue tracker, code owner, and version.

## 0.1.7

- Renamed use-case-specific menu helper entities to generic school-day lookahead entities.
- Added configurable school-day lookahead days.
- Removed Skellefteå from suggested entity IDs; source/location now lives in metadata.

## 0.1.6

- Added menu-oriented visibility helper and date sensor. Superseded by generic lookahead naming in 0.1.7.

## 0.1.5

- Added icon translations.

## 0.1.4

- Changed visible status label from `Outside Term` to `Outside School Term`.

## 0.1.3

- Split current and next closure into separate sensors.
- Made status sensor display-friendly.

## 0.1.2

- Made config option keys more readable when translations are not loaded.

## 0.1.1

- Improved entity naming and parser handling of collapsed closure rows.

## 0.1.0

- Initial custom integration.
