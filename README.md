# School Year

A custom Home Assistant integration that fetches school-year dates and breaks from a supported official source and exposes them as Home Assistant calendar, binary sensor, and sensor entities.

> [!IMPORTANT]
> This integration is maintained for my private Home Assistant setup. It is public so it can be installed and updated through HACS as a custom repository. Bug reports are welcome, but there is no support promise, no compatibility guarantee, and no ambition to make this a general-purpose school calendar integration.
>
> It is also vibe coded with AI assistance. The code is intended to be practical and understandable rather than polished as a broadly maintained open-source project.

## Supported source

Currently supported source:

- Municipality/source: `Skellefteå kommun`
- School form: `Grundskola`
- Parser: `skelleftea_grundskola`

Default source page:

<https://skelleftea.se/invanare/startsida/forskola-skola-och-utbildning/grundskola/lov-lasarstider-och-ledigheter>

The integration name is intentionally generic. The current parser is not generic; it supports the Skellefteå grundskola page and assumes that page keeps roughly the same structure: term sections with school start, breaks/free days, and term end dates.

## HACS installation

This is intended as a **HACS custom repository**, not a default HACS repository.

1. Make sure HACS is installed in Home Assistant.
2. In HACS, open the three-dot menu and choose **Custom repositories**.
3. Add this repository URL:

   ```text
   https://github.com/Caine72/ha-school-year
   ```

4. Select repository type **Integration**.
5. Install the integration.
6. Restart Home Assistant.
7. Add the integration from **Settings → Devices & services → Add integration → School Year**.

## Manual installation

Copy this directory:

```text
custom_components/school_year
```

to your Home Assistant config directory:

```text
/config/custom_components/school_year
```

Then restart Home Assistant and add the integration from the UI.

## Entities

Default entity IDs on a clean install are generated from the device name `School year` plus the entity name. Existing entity IDs may remain unchanged if Home Assistant already has registry entries from older versions.

Typical entities:

- `calendar.school_year_school_closures`  
  Calendar with school-closed events such as K-days, breaks, and inferred summer/Christmas breaks.

- `binary_sensor.school_year_school_day`  
  On when today is a school day.

- `binary_sensor.school_year_school_day_in_lookahead`  
  On when today is a school day or when the next school day is within the configured lookahead window. This is a generic helper for dashboards and automations.

- `sensor.school_year_next_school_day`  
  The next known school day on or after today.

- `sensor.school_year_status`  
  Human-readable status for today: `School Day`, `School Closed`, `Weekend`, `Outside School Term`, or `Unknown`.

- `sensor.school_year_current_closure`  
  Active closure event, or `No Active Closure`.

- `sensor.school_year_next_closure`  
  Next future closure event.

- `sensor.school_year_source_updated`  
  Diagnostic source page last-updated date.

## Options

- **Source URL**: official page to fetch.
- **Page check interval**: how often Home Assistant refetches the official page.
- **Include inferred long breaks**: creates summer and Christmas break events from gaps between term end/start dates.
- **School day lookahead days**: how many days ahead should count as having a school day soon. Default: `2`.

## Dashboard example

Use the generic lookahead helper when a card should be visible before the next school day, for example during weekends or on the last day before a break ends:

```yaml
type: conditional
conditions:
  - condition: state
    entity: binary_sensor.school_year_school_day_in_lookahead
    state: "on"
card:
  type: custom:mushroom-template-card
  icon: mdi:food-fork-drink
  primary: Matsedel
  tap_action:
    action: navigate
    navigation_path: /common-dashboards/school-meals
```

For strict "only show on actual school days", use `binary_sensor.school_year_school_day` instead.

## Disclaimer

This project is not affiliated with Skellefteå kommun, Home Assistant, or HACS. It currently scrapes/parses the public Skellefteå kommun grundskola school-year page. If that page changes format, the integration can break.

## Development

Create a virtual environment, install `requirements-dev.txt`, then run the same checks as CI:

```text
./scripts/validate --fix
./scripts/validate
```

CI also runs HACS and Hassfest validation. Parser tests use small representative HTML fixtures and do not contact the municipality website.

Run `./scripts/setup-dev` once if the local development dependencies are missing.

Releases are prepared and published manually. `./scripts/set-version X.Y.Z`
updates the manifest on a release branch, while `./scripts/publish-release`
verifies the exact `main` commit and creates a stable GitHub release using an
approved, user-focused notes file prepared from changes since the previous
release. Release notes describe functional outcomes and omit development detail.

## License

School Year is available under the [MIT License](LICENSE).
