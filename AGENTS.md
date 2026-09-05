# School Year agent instructions

## Product scope

Communicate in English.

School Year is a private-use Home Assistant custom integration distributed
through HACS. It fetches official school term and closure dates and exposes
calendar, binary sensor, and sensor entities. Optimize the maintainer's actual
household workflow before making the integration generic or broadly supported.

The integration name and entity model are generic, but the only supported
source/parser is currently Skellefteå kommun `Grundskola`. Do not imply support
for arbitrary municipalities or page formats.

## Goals

- Keep school-day state and closure calendars accurate when the source page is
  reachable and structurally supported.
- Preserve the last known-good coordinator data when fetching or parsing fails.
- Detect source-format drift explicitly instead of silently publishing partial
  or misleading schedules.
- Keep installation and upgrades simple through HACS.
- Prefer a small, understandable implementation over speculative abstraction.

## Architecture invariants

- `parser.py` owns source-specific HTML interpretation and normalized term/event
  data. Home Assistant entities must not parse source HTML.
- Parsed terms must be complete, ordered, non-overlapping, and internally valid.
- Internal event end dates are inclusive; Home Assistant all-day calendar end
  dates are exclusive.
- Weekdays inside a known term are school days unless an active closure exists.
- Inferred summer and Christmas breaks are optional and may only be derived from
  gaps between complete adjacent terms.
- The coordinator owns fetching and the single daily date-change notification.
- Config and options flows validate connectivity and parser compatibility before
  saving. Options changes reload the integration.
- Entity unique IDs derive from the config-entry identity and stable suffixes,
  never source labels or mutable display names.

## Development workflow

1. Inspect `git status`, the current branch, nearby code, and relevant tests.
2. For implementation, update `main` and work on a `codex/` branch. Never publish
   directly to `main`; use a pull request.
3. Check current Home Assistant Core code or official developer documentation
   before changing version-sensitive APIs.
4. Make the smallest complete change and add focused behavioral regression tests.
5. Do not add tests solely to execute lines or inflate coverage. Prioritize parser
   drift, date boundaries, recovery, configuration, and lifecycle behavior.
6. Run `./scripts/validate --fix`, then `./scripts/validate`.
7. Review `git diff --check` and the complete diff before declaring completion.
8. Report behavior, validation, and remaining risk. Do not claim live acceptance
   unless the authenticated local path was actually exercised.

## Validation and release

- `./scripts/validate` is the canonical local and pull-request check. It is terse
  by design so agents only need to inspect failures and the final result.
- Pull requests must pass HACS, Hassfest, and project validation.
- Weekly compatibility tests cover the current Home Assistant stable release and
  the next beta when available; they are not repeated during ordinary local work.
- Use semantic versions. Before a release, update `manifest.json` and
  `CHANGELOG.md`, run canonical validation once, and confirm the tag exactly
  matches the manifest version.
- Publish a GitHub release only from a validated commit on `main`.
- Review Dependabot pull requests independently and merge only after required
  checks pass.

## Local Home Assistant acceptance

- Local credentials and machine paths belong only in the ignored
  `.real_ha_acceptance.env`; never print, log, commit, or paste its token.
- `.real_ha_acceptance.env.example` is the public template and must contain only
  placeholders and generic paths.
- The Home Assistant development environment runs in a Docker container.
  Container names and IDs are ephemeral; discover the configured runtime from
  mounts or port 8123 instead of persisting machine-specific details.
- If the container is stopped, start that existing container. If Home Assistant
  is not running, start it inside the container from
  the configured Core directory with its existing virtual environment.
  Never start a competing Home Assistant process from the desktop checkout.
- Verify unauthenticated reachability, then authenticated `/api/` access without
  displaying the token. Use live acceptance only when it adds confidence beyond
  deterministic tests, especially for setup, reload, entity, or lifecycle work.
- Treat live acceptance as potentially state-changing. Inspect the target first
  and prefer read-only checks when sufficient.

## Security and repository hygiene

- Never commit credentials, private URLs, local paths, container identifiers, or
  acceptance output.
- Sanitize logs, fixtures, screenshots, issues, and pull requests.
- Keep GitHub Actions pinned to immutable commits and let Dependabot maintain them.
- Preserve unrelated user changes and do not rewrite shared history.
