# Folder organization — 13 November 2026

The user designated [IMMORTALS_MASTER_PROJECT_DOCUMENT_v2.md](../planning/IMMORTALS_MASTER_PROJECT_DOCUMENT_v2.md)
as the main project plan. The master and its supplied appendices were read before
applying these structural changes. The original master document remains at the
root, with its content and 12 November date preserved.

## Changes

- Added the root project index, documentation index, project working guidance,
  structure guide, and master-to-implementation status map.
- Grouped the two supplied architecture images in `docs/architecture` and the
  original wiring DOCX in `docs/hardware`.
- Moved supporting requirements and implementation notes to `docs/planning`.
  Root navigation notes retain the familiar document paths and point to the
  main master plan and the relocated sources.
- Grouped screenshots, browser captures, logs, and raw work-session validation
  under `artifacts`. The speech tester's synchronized `validation_indic` tree
  remains with its component.
- Grouped historical helpers/commands/notes in `archive/work-sessions/2026-11`,
  earlier source snapshots in `archive/source-snapshots`, downloaded reference
  code in `archive/references`, and prior bytecode in `archive/generated`.
- Grouped device backups under `.work/backups/pi` and staged models/packages
  under `.work/cache`. `.work/PI_ACCESS.md` retains its requested private path.
- Added reusable structure/link verification and a local regression-check runner.
  The website README and bundled implementation snapshot now refer to the main
  project plan and current resource locations.

All six component roots, their release snapshots, Pi paths, application code,
launchers, configs and deployment/source manifests retain their existing layout.
The website keeps its independent Git repository, dependencies, tool runtime,
environment and deployment state. Folder organization performed no remote
deployment, hardware reconfiguration or cloud data operation.

## Preservation and traceability

The move record contains **151 operations covering 484 files (794.59 MiB)**.
Files were relocated with native PowerShell moves after validating absolute
workspace bounds. Original documents edited for navigation were backed up.

Local records, excluded from Git:

- Move manifest, `archive/organization/2026-11-13/manifest.json`: old/new paths,
  original SHA-256 hashes, protected files, and documented navigation edits.
- Original inventory, `archive/organization/2026-11-13/baseline.json`:
  pre-organization file sizes and hashes, excluding dependency/build/tool internals.
- Original documents, `archive/organization/2026-11-13/originals/`:
  source copies before link/navigation edits.
- Applied move script, `archive/organization/2026-11-13/organize.ps1`:
  the bounded one-time relocation procedure.

Historical component reports and raw JSON retain their original dates, path
strings and test observations. Consult the move manifest when following those
old evidence paths. Archived one-off scripts retain their original working
directory assumptions; current source synchronization uses the component
`sync.py` tools. To restore an individual original file, locate its source/target
entry and use the preserved destination or document backup.

## Verification results

| Check | Result |
|---|---|
| Master and existing protected files | 276 files match their original SHA-256 hashes, including the master, application sources/configs/manifests, retained component evidence, and private access note |
| Relocated material | All 484 moved files are accounted for; original versions of documents adjusted for navigation remain backed up |
| Workspace navigation | All checked local document links and six component entry points resolve |
| Receiver baseline | 22 tests passed |
| Patient v2 cross-role contract | 15 tests passed |
| Model-free speech | 21 tests passed with the pinned local romanizer |
| Website | 13 tests, lint, type checking and production build passed |
| Linux sender baseline | Explicitly skipped on this Windows laptop; requires `fcntl` and the documented Linux/Pi sender environment |

**71 local tests passed.** Results distinguish the platform-specific sender skip
from successful laptop checks. Application code and deployment source manifests
were preserved; these checks concern local organization and regression coverage.

The initial laptop run exposed the sender's Linux import requirement and an
absent global romanizer. The check runner now records the platform requirement
and uses an isolated `.work/cache/test-dependencies` cache containing the pinned
`uroman==1.3.1.1` and its regex dependency. The speech follow-up passed without
changing the speech application or the Pi runtime.

Local receipt paths, relative to the project root:

- Final local check results: `artifacts/validation/organization/2026-11-13/checks.json`.
- File/link preservation results: `artifacts/validation/organization/2026-11-13/preservation.json`.
- Initial check log: `artifacts/logs/organization/2026-11-13/local-checks.log`.
- Targeted follow-up log: `artifacts/logs/organization/2026-11-13/followup-checks.log`.

These files retain both the setup findings and their resolution. The 17 November
navigation update labels excluded evidence as local paths so the published report
does not link to files absent from GitHub. The historical results remain unchanged.

## Project scope recorded

The status index distinguishes the implemented patient/sensor/gateway/website
baseline from incomplete field acceptance and planned work. The installed
Hindi/Bengali speech tester is recorded separately from the master's
Bengali/Hindi/English patient-linked speech target. Camera/VLM/Qwen integration,
remaining peripherals, final sensor inventory and field acceptance continue to
follow the master plan. No project completion percentage is assigned.
