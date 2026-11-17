# Document consolidation — 17 November 2026

The owner requested one organized documentation hub, retention of the most
updated documents, duplicate removal, a mandatory development log, and publication
to GitHub main. This follows the current master and keeps all component roots,
platform environments, application code and original release snapshots intact.

## Current layout

- Shared documents, including the current master, live under `docs/`.
- Purchase spreadsheets/PDF live in `docs/hardware/bom/`; distinct superseded
  workbooks live in its dated `history/` folder, preserving unique formulas,
  supplier evidence and original verification sources.
- Root README and AGENTS remain discovery/agent entry points. Runtime manuals
  remain with the components that deploy them. The standalone Website keeps
  its own Git root and documentation. All are linked from `docs/README.md`.
- The central change log is `docs/development/development.md`. Website also has
  `Website/docs/development.md` so its agents can log work in a standalone clone.
  Website work in this workspace must also be entered in the central log.

## Duplicate and version decisions

Removed four redundant documents: the root GOAL_REQUIREMENTS and PROJECT_UPGRADE_PLAN
navigation-only notes, and identical Sender_v2/Receiver_v2 `project.md` manuals.
The original requirements/plans remain in `docs/planning`; each v2 README is the
canonical operational guide. Originals are backed up privately and in Git history.

The latest supplied editable purchase workbook was saved on 17 November and
differs from the 16 November version. The later print checklist has automatic
BP inflation and additional partly unpriced parts. These are not duplicates.
The BOM index labels each source's date, purpose, scope and total. No workbook,
PDF or wiring DOCX bytes were edited or re-exported.

Matching protocol/upgrade manuals in sender, gateway and preserved release
snapshots are intentional deployment documentation. Keep them with the sources
that ship to each device. The historical website snapshot has different dated
content and must remain usable in its separate repository. These files are
indexed rather than deleted indiscriminately. Original master appendices and
historical evidence remain intact.

## Move and recovery record

The committed [manifest](organization/2026-11-17-moves.json) records six exact
moves, old/new paths, original SHA-256 hashes and four removals with canonical
destinations. A private pre-change inventory and original-document backups are
in `.work/backups/document-organization/2026-11-17/`. Git and the manifest provide
the recovery trail. Earlier organization reports retain their dates and results;
only active navigation links were repaired.

The generated workbook inspection was relocated from `outputs/` to
`artifacts/validation/bom/2026-11-16/`. Its original SHA-256 is also in the
manifest. The archive/evidence indexes and two dated BOM validation summaries
are now tracked for GitHub navigation; raw captures and private backups remain
excluded. Their deliverable links point to the preserved historical workbooks.

The source SHA manifests still describe their recorded deployment snapshots.
Removing local duplicate manuals is not a Pi source synchronization or a reason
to relabel those snapshots. No hardware/cloud/clinical acceptance was claimed.

## Verification and publication

The root `.gitmodules` now maps the existing `Website/` Git reference to its
independent GitHub repository. A complete clone can retrieve the pinned website
commit without changing its standalone deployment root. Website links in the
central indexes point to that repository, and excluded historical evidence is
identified by local paths. Publication checks cover a fresh recursive clone.

Actual checks and GitHub push receipts are recorded in
[development.md](development.md). Local navigation and file-preservation checks
cover this document organization. They do not establish hardware/field readiness.
