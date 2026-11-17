# Immortals development log

This is the project's append-only development and decision history. All agents
must read it before work and update it in the same commit as every change.
Repository changes before this log existed remain in Git and dated validation
reports. They have not been reconstructed as invented timestamped entries.

## Entry format

```text
Date: YYYY-MM-DD
Time: HH:MM:SS +05:30 (Asia/Calcutta)
Author:
Changed paths:
What changed:
Why the change was needed:
Why this decision was made:
Validation: command, target, result, dated evidence
Known gaps / risks:
Rollback / recovery:
```

Use actual times and specific decisions. Include document edits, BOM updates,
renames, deletions, configuration, tests and deployments. Preserve earlier
entries and append corrections. Never include secrets or patient information.

## 2026-11-17 — Documentation organization and mandatory logging

- **Date:** 2026-11-17.
- **Time:** 21:11:51 +05:30 (Asia/Calcutta), initial consolidation.
- **Author:** Codex, at the project owner's request.
- **Changed paths:** root README/AGENTS; `docs/README.md`; planning master and
  status links; hardware index/BOM folders; development structure, log and
  organization record; `tools/project/check_workspace.py`; standalone website
  README/AGENTS and development log. Exact moves are recorded in
  [the move manifest](organization/2026-11-17-moves.json).
- **What changed:** moved the latest master into `docs/planning`, grouped three
  distinct BOM workbooks and the supplied print checklist under
  `docs/hardware/bom`, removed two root navigation-only duplicates, repaired
  active references, and added one documentation hub. Added this log and
  mandatory append-only logging rules for all agents, including the independent
  website repository. Retained earlier workbooks as explicitly dated history.
- **Why the change was needed:** important project documents and purchasing
  workbooks were scattered across the root and generated-output directories.
  The owner needs an auditable record to investigate future bugs and decisions.
- **Why this decision was made:** one documentation hub and stable filenames
  make current files discoverable. Comparing contents, rather than relying on
  similar names, avoids deleting unique supplier research, formulas or safety
  notes. Runtime manuals and release snapshots remain component-local because
  they are shipped with the corresponding deployment. They are indexed centrally.
- **Source differences:** the supplied 17 November print checklist adds automatic
  BP inflation parts and a priced-item total of INR 11,408.40, with unpriced items
  excluded. The latest editable spreadsheet was saved earlier on 17 November,
  retains the earlier manual-pneumatic BP alternatives, and reports INR 10,535.48.
  These are different deliverables, not byte-identical copies. Both originals
  are preserved and their roles are explained in the BOM index. No workbook or
  PDF content was altered during organization. Earlier 16 November validation
  remains attached to its original costing; it does not verify the later files.
- **Pre-existing work preserved:** retained the owner's uncommitted 16 November
  design/milestone changes in the master, status index and hardware notes, and
  existing website documentation edits. No runtime implementation or patient
  data was changed. Source manifests remain dated deployment snapshots.
- **Validation:** pending final structure/preservation checks and publication;
  actual results and push receipts will be appended below before completion.
- **Known gaps / risks:** the print checklist and editable workbook have different
  BP procurement scopes. Reconcile selections before purchase. Hardware/Pi/cloud,
  clinical acceptance and source synchronization are outside this document work.
- **Rollback / recovery:** Git history, the committed move manifest, preserved
  dated workbooks, and private originals in
  `.work/backups/document-organization/2026-11-17/`. Original SHA-256 hashes were
  verified immediately after all five moves. Undo changes through Git and the
  manifest; keep the log history.

## 2026-11-17 — Completion audit and publication preparation

- **Date/time:** 2026-11-17, 21:38:41 +05:30 (Asia/Calcutta).
- **Author:** Codex, continuing the owner's interrupted organization task.
- **Changed paths:** `.gitignore`; `archive/README.md`; `artifacts/README.md`;
  `artifacts/validation/BOM_RESEARCH_2026-11-16.md`;
  `artifacts/validation/PURCHASE_BOM_2026-11-16.md`;
  `docs/development/PROJECT_STRUCTURE.md`, `ORGANIZATION_REPORT_2026-11-17.md`,
  `organization/2026-11-17-moves.json`, and this log;
  `tools/project/check_workspace.py`; `Website/docs/development.md`.
  Earlier pending paths are listed in the preceding consolidation entry.
  Generated reports/logs are in `artifacts/validation` and `artifacts/logs`;
  original validation-document backups are private in `.work`.
- **What changed:** finished the pending consolidation, repaired remaining
  archive/historical evidence links, moved the last generated inspection into
  `artifacts/validation/bom/2026-11-16/`, and recorded its hash in the six-move
  manifest. Corrected retained duplicate groups and recorded navigation backups.
  Tracked only archive/evidence indexes and two dated BOM validation summaries;
  other captures remain ignored. Added generated `outputs/` to `.gitignore`.
- **Why needed:** the earlier chat left uncommitted organization work, pending
  validation/logging and no publication. Old links and ignored indexes prevented
  the complete documentation from being usable through GitHub.
- **Decision:** finish the existing structure, keep component/release roots and
  distinct historical BOM content, preserve original source bytes, and repair
  navigation without rewriting dated results. Allowlist public summaries rather
  than raw capture folders. Runtime sources, manifests and environments remain intact.
- **Validation:** `python -B tools/project/check_workspace.py --report
  artifacts/validation/document-organization-2026-11-17-workspace.json` passed:
  six components, 24 documents, 170 local links, zero errors, Windows laptop,
  17 November 2026. SHA-256 audit passed for all four BOM deliverables, the
  moved inspection and original wiring DOCX; all three XLSX ZIP integrity checks
  passed. Removed v2 manuals exactly match the retained README hashes. The
  preserved master differs only by repaired links and the organization/log note.
  Evidence: `artifacts/validation/document-organization-2026-11-17-preservation.json`.
- **Regression validation:** `./tools/project/run_checks.ps1 -ReportPath
  artifacts/validation/document-organization-2026-11-17-checks.json` exited 0.
  Receiver: 22 tests; patient v2: 15; model-free speech: 21; website: 13;
  all 71 runnable tests passed. Website ESLint, TypeScript and production build
  passed. Output: `artifacts/logs/document-organization-2026-11-17-checks.log`.
  Sender baseline was explicitly skipped on Windows because it requires Linux/Pi
  `fcntl`. Root and website `git diff --check` passed. Both remotes were fetched;
  both main branches initially had zero divergence from `origin/main`.
- **Failed checks/resolution:** initial workspace check failed on the archive's
  old master link; corrected and the final check passed. Execution policy rejected
  a combined evidence-move/empty-directory-cleanup command before execution;
  the move-only retry succeeded with identical SHA-256. Empty generated folders
  remain harmless. An initial read used the wrong nested website-log path;
  corrected to `Website/docs/development.md`. A Python log-append command failed
  with a quoting SyntaxError before writing; appended the entries using a patch.
- **Known gaps:** latest print/editable purchase files differ in BP scope and
  total; neither was silently altered. Local checks do not establish Pi/cloud,
  clinical or field acceptance. Raw captures and backups remain laptop-local.
- **Rollback/recovery:** committed move/removal manifest, preserved workbooks,
  `.work/backups/document-organization/2026-11-17/originals/`, root pre-change
  `a72a932`, website pre-change `2b87ccb`; revert organization commits through Git
  and use the manifest for local evidence moves, keeping append-only log history.
- **Publication:** owner explicitly requested full GitHub main sync. Publish the
  standalone website documentation first, update its root Git reference, then
  publish the complete project. Actual commit/push receipts follow below.

## 2026-11-17 — Resumed audit and complete-clone preparation

- **Date/time:** 2026-11-17, 22:34:50 +05:30 (Asia/Calcutta).
- **Author:** Codex, continuing the owner's request to finish the interrupted
  organization and publish both main branches.
- **Changed paths:** `.gitmodules`; `README.md`; `docs/README.md`;
  `docs/planning/IMPLEMENTATION_STATUS.md`;
  `docs/development/PROJECT_STRUCTURE.md`, `ORGANIZATION_REPORT.md`,
  `ORGANIZATION_REPORT_2026-11-17.md`, and this log;
  `tools/project/check_workspace.py`; the pending `Website` Git reference.
  The preceding entries cover the existing consolidation, BOM moves and website
  documentation commit. New audit receipts remain in `artifacts/validation`.
- **What changed:** retained the completed consolidation rather than repeating
  moves or rewriting source documents. Added the missing website submodule URL
  mapping and complete-clone instructions. Central website links now target its
  standalone GitHub repository. Labelled eight excluded historical evidence
  links as local paths and corrected the consolidation report's move count to
  six. The workspace check now requires `.gitmodules`.
- **Why needed:** live inspection found root main still at `a72a932` with the
  organization uncommitted, and website main one commit ahead at `f58db5c`.
  `git submodule status` failed because the tracked `Website` Git reference had
  no `.gitmodules` mapping. Locally present ignored evidence also hid broken
  published links. These gaps prevented a complete, usable GitHub checkout.
- **Decision:** keep the six component roots and independent website deployment
  intact, register the existing website reference, and verify its pinned commit
  through a fresh recursive clone after publication. Preserve source bytes,
  dated costing differences, backups and historical validation rather than
  deleting useful research or publishing raw captures.
- **Validation:** `./tools/project/run_checks.ps1 -Only workspace -ReportPath
  artifacts/validation/document-organization-2026-11-17-resumed-checks.json`
  passed on this Windows laptop at 22:33:25: six components, 24 documents,
  156 local links, zero errors. The fresh hash/removal/ZIP/publication audit
  passed at 22:34:49: 11 preservation/recovery checks, three intact XLSX files,
  six intentional duplicate groups, no unpublished local link targets and no
  runtime-source changes. The preserved master has exactly the previously
  verified navigation edits. Evidence:
  `artifacts/validation/document-organization-2026-11-17-resumed-preservation-final.json`.
  Root and website `git diff --check` passed. Both origins were fetched and
  root main had zero divergence; website main was ahead one, behind zero.
  `git submodule init -- Website` successfully registered the existing mapping.
- **Regression evidence reviewed:** the earlier 17 November full runner report
  and log show all 71 runnable tests passed, plus website lint, TypeScript and
  production build. Sender baseline was explicitly skipped on Windows because
  of Linux/Pi `fcntl`. Runtime sources are unchanged, so this continuation used
  the affected workspace check instead of repeating the completed suites.
- **Failed checks/resolution:** the missing-submodule-mapping failure was fixed
  with `.gitmodules` and initialization. One multi-file patch failed on an
  incorrect context before writing; checked that no files changed and reapplied
  the corrected patch. The initial fresh preservation audit compared three-line
  diff context with the earlier receipt's two-line context; matching `n=2`
  verified identical edits. The failed receipt is retained as
  `artifacts/validation/document-organization-2026-11-17-resumed-preservation.json`.
- **Known gaps:** the later print checklist and editable workbook retain different
  BP scopes/totals, clearly labelled in the BOM index. Local document checks do
  not establish Pi, cloud, clinical or field acceptance. Fresh-clone and actual
  main publication receipts will be appended after their execution.
- **Rollback/recovery:** root pre-change `a72a932`, website pre-change `2b87ccb`,
  the committed move/removal manifest and private originals in
  `.work/backups/document-organization/2026-11-17/`. Revert the organization
  commits and restore individual originals using the manifest; preserve this
  append-only history. The website remains its own repository.

## 2026-11-17 — Binary document handling and website publication

- **Date/time:** 2026-11-17, 22:38:23 +05:30 (Asia/Calcutta).
- **Author:** Codex, completing the owner's authorized main publication.
- **Changed paths:** `.gitattributes`; `docs/development/PROJECT_STRUCTURE.md`;
  this log; staged BOM documents and the `Website` Git reference. Source document
  bytes remain unchanged.
- **What changed:** marked PDF and Office document formats as binary, overriding
  the laptop's global PDF text-diff behavior. Re-staged the supplied documents
  under this repository policy and documented the root attributes file.
  Published the existing website documentation commit `f58db5c` to GitHub main.
- **Why needed:** the staged whitespace check interpreted the ASCII PDF as text
  and reported its valid trailing spaces. PDF offsets and original source bytes
  must survive staging and Windows checkouts. The earlier website commit had
  remained unpublished despite the owner's request.
- **Decision:** use Git's binary attributes to disable text normalization and
  text diff/merge for these formats, preserving the original deliverables and
  applying meaningful whitespace checks to editable source documents.
- **Validation:** the initial `git diff --cached --check` failed on PDF whitespace.
  Before and after the attribute change, all four staged BOM blobs matched their
  manifest SHA-256 hashes. After `git add --renormalize --` on the document paths,
  `git check-attr text diff merge --` reported all three attributes unset for
  PDF/XLSX, and `git diff --cached --check` passed. Dated byte audit:
  `artifacts/validation/document-organization-2026-11-17-staged-documents.json`.
  Website `git push origin main` succeeded: `2b87ccb..f58db5c`, `main -> main`.
  `git ls-remote --heads origin main` independently returned
  `f58db5cf7124211bbfd3413740aff2b71e6a7807`; its working tree is clean and
  local main matches `origin/main`.
- **Known gaps:** complete-project main publication and fresh-clone verification
  follow this entry. Existing BOM scope differences and hardware acceptance
  boundaries remain as documented above.
- **Rollback/recovery:** revert the organization/attributes commit in the parent
  and website documentation commit in its independent repository, preserving
  subsequent work and log history. Original document hashes and private backups
  remain the recovery references listed in the move manifest.
