# Immortals project guidance

## Main project plan

Read [IMMORTALS_MASTER_PROJECT_DOCUMENT_v2.md](docs/planning/IMMORTALS_MASTER_PROJECT_DOCUMENT_v2.md)
before planning or changing project work. The user designated this document as
the main plan for the whole project on 13 November 2026.

Apply current user instructions first, then the master plan's main sections.
Use [implementation status](docs/planning/IMPLEMENTATION_STATUS.md), component
documentation, and recorded validation to understand the implementation.
The goal requirements, two-phase upgrade notes, website copy, and master
appendices are supporting or historical material. Follow explicitly dated
superseding updates; earlier stage restrictions do not override later scope.
Record implementation gaps against the master instead of silently changing its
requirements or marking unverified work complete.

## Architecture and implementation

- Sender operation is offline-first. Gateway Firebase credentials and cloud
  uploads belong to the receiver gateway.
- Keep acquisition, touchscreen interaction, radio transport, cloud upload,
  and inference independent, with bounded work and persistent recovery.
- Preserve patient ID, monitoring session, submission/event identity, original
  capture times, nulls, quality labels, waveform gaps, and idempotent retries.
- Keep optical heart rate separate from ECG-derived/candidate rate. Retain the
  master plan's measurement labels and validation requirements.
- The current speech tester uses IndicConformer for Hindi/Bengali. The master
  targets Bengali/Hindi/English and an integrated patient workflow; the local
  tester's existence does not complete that workstream.
- Preserve existing releases and platform-specific runtime environments.

## File placement

Use the [project structure guide](docs/development/PROJECT_STRUCTURE.md).
Keep the established component roots `Sender`, `Receiver`, `Sender_v2`,
`Receiver_v2`, `Website`, and `Speech_Test_Phase3`; the master documents their
source and deployment locations. Keep `Website/.git` and its standalone
deployment root intact. Component launchers, tests, configs, and sync scripts
stay with their component.

Place shared project documents, the master plan and BOMs in `docs`, reusable project tools in
`tools/project`, captured evidence in `artifacts`, and historical work in
`archive`. `.work/PI_ACCESS.md`, `.work/backups`, and `.work/cache` are private
laptop material. Preserve historical evidence and original sources when
reorganizing. Store a move record for any later structural change.

## Mandatory development log

Read [development.md](docs/development/development.md) before starting work.
Every agent and contributor must append a dated entry for every repository change
before committing or handing work back. This includes code, documents, BOMs,
configuration, tests, file moves, deletions and deployment/synchronization work.

Each entry must include date, time and timezone (Asia/Calcutta, UTC+05:30), author,
changed paths, what changed, why the change was needed, why that decision was
chosen, validation commands/targets/results/evidence, known gaps, and a rollback
or recovery reference. Record failed checks and their resolution. Use actual
timestamps and results; never invent past development history or Pi validation.
Append corrections and follow-ups instead of rewriting prior entries. Add the
log in the same commit as the change. Never include credentials or patient data.
For work in the standalone website checkout, follow its own AGENTS.md log rule;
record cross-repository work in this central log as well.

## Verification and status

Run `python -B tools/project/check_workspace.py` after document/path changes.
Use `tools/project/run_checks.ps1` for local regression checks, or the affected
component's documented checks for a scoped change. Existing source manifests
describe deployment snapshots; changing those hashes requires an actual
source synchronization, rather than relabelling local edits as Pi-verified.

Use the master's status categories: Done and verified, Implemented but not fully
verified, In progress, or Not started / planned. Record the test, target, date,
and evidence before marking a feature verified. Local checks do not establish
current Pi, cloud, clinical, or field acceptance.

`Website/AGENTS.md` adds the installed Next.js-specific guidance for that component.
