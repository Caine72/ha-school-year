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

## Home Assistant conventions

- Follow current Home Assistant developer patterns and inspect the checked-out
  Home Assistant Core source when uncertain. For version-sensitive APIs, syntax,
  or deprecations, check current official documentation and release notes.
- Prefer official Home Assistant developer documentation over third-party examples.
- Preserve the config-entry model and coordinator ownership of fetched data.
- Keep source retrieval, validation, and normalized school-year data in the
  integration; entities only present coordinator data.
- Keep `strings.json` and `translations/en.json` synchronized when user-visible
  configuration or entity text changes.
- Use the repository's current Python syntax and do not use YAML anchors.

## Development workflow

1. Start from the repository root, inspect `git status`, switch to `main`, and
   update from `origin/main` before creating a development branch.
2. Do all implementation work on a separate `codex/` branch. Bring changes back
   to `main` only after validation passes and the user explicitly approves.
3. When publishing to `origin`, always push a branch and open a pull request,
   even when direct pushes to `main` are technically allowed.
4. Inspect nearby code and relevant tests. Check current Home Assistant Core code
   or official developer documentation before changing version-sensitive APIs.
5. For non-trivial changes, present a concise plan before coding.
6. Make the smallest complete change and add focused behavioral regression tests.
   Do not add tests solely to execute lines or inflate coverage. Prioritize parser
   drift, date boundaries, recovery, configuration, and lifecycle behavior.
7. Run `./scripts/validate --fix`, then `./scripts/validate` on the branch before
   every initial PR push and before every later push that updates the PR. Do not
   push a branch whose validation is failing.
8. After pushing, wait for HACS, Hassfest, and Project validation on the PR and
   correct every failure before asking to merge.
9. Review `git diff --check` and the complete diff before declaring completion.
10. Report changed files, behavior, validation, and remaining risk. Do not claim
    live acceptance unless the authenticated local path was actually exercised.
11. Do not commit, push, rewrite history, or modify unrelated files unless the
    user requested the implementation work.

## Environment

- Integration source: `custom_components/school_year`
- Tests: `tests`
- Full validation entry point: `./scripts/validate`
- Real Home Assistant credentials and paths: ignored `.real_ha_acceptance.env`
- Public environment template: `.real_ha_acceptance.env.example`
- Home Assistant runtime: the existing development Docker container discovered
  at runtime; never persist its name or ID

## Validation and release

- `./scripts/validate` is the canonical local and pull-request check. It is terse
  by design so agents only need to inspect failures and the final result.
- Pull requests must pass HACS, Hassfest, and project validation.
- Weekly compatibility tests cover the current Home Assistant stable release and
  the next beta when available; they are not repeated during ordinary local work.
- Releases are manual and stable-only. Do not add an automatic release workflow
  and do not publish beta, release-candidate, or other prerelease versions.
- When the user asks to prepare a release, inspect the commits and diff since the
  latest GitHub release and choose the next semantic version: patch for compatible
  fixes and maintenance, minor for compatible user-facing functionality, and
  major for breaking behavior or contracts.
- Prepare the version on a `codex/release-vX.Y.Z` branch with
  `./scripts/set-version X.Y.Z`. Validate that branch before pushing it as a PR,
  then wait for all required PR checks. Accumulated unreleased work may remain on
  `main` indefinitely; a passing version PR is not permission to publish.
- Keep no changelog file. Draft GitHub release notes from the commits and diff
  since the previous release, but rewrite them for Home Assistant users at the
  functional and business-requirement level. Describe what improved and why it
  matters; omit implementation details, file names, test tooling, CI changes,
  commits, and pull-request mechanics unless they directly change the user
  experience. Keep the draft outside the repository and show it to the user for
  approval before publication. Do not use GitHub's automatically generated notes.
- Publish only when the user explicitly says the prepared version should be
  published and has approved the release text. From a clean, synchronized `main`,
  run `./scripts/publish-release PATH_TO_APPROVED_NOTES`. It must verify the
  version, notes, existing tags, and successful checks on the exact commit before
  creating the stable tag and GitHub release.
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
- A failed sandbox request to `localhost:8123` is not decisive. Perform the health
  check at host level: an unauthenticated `401` proves reachability, then require
  an authenticated `/api/` response using the ignored token without displaying it.
- If Home Assistant is unreachable, discover the existing container. Start it if
  stopped, check for an existing Home Assistant process, and start Home Assistant
  inside that container from the configured Core directory with its existing
  virtual environment when absent. Wait for port 8123 and authenticated API access.
- Never start a competing Home Assistant process from the desktop checkout. If
  Docker access is unavailable, stop instead of improvising and report the exact
  permission blocker.
- Inspect startup logs for `school_year` setup failures. Use an integration reload
  when sufficient and a full restart only for module loading or lifecycle changes.
- Use live acceptance when it adds confidence beyond deterministic tests,
  especially for setup, reload, entity, or lifecycle work.
- Treat live acceptance as potentially state-changing. Inspect the target first
  and prefer read-only checks when sufficient.

## Current direction

The product goals and architecture invariants above define current direction.
If roadmap or milestone documents are added later, read them before starting
milestone work and keep them focused on future direction.

## Security and repository hygiene

- Never commit credentials, private URLs, local paths, container identifiers, or
  acceptance output.
- Sanitize logs, fixtures, screenshots, issues, and pull requests.
- Keep GitHub Actions pinned to immutable commits and let Dependabot maintain them.
- Preserve unrelated user changes and do not rewrite shared history.
