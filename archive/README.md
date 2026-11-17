# Historical project material

This local archive preserves previous work. This navigation index is tracked;
archived contents are excluded by the root `.gitignore`. Active components remain
at the project root; the
[master project plan](../docs/planning/IMMORTALS_MASTER_PROJECT_DOCUMENT_v2.md)
is in the shared documentation hub.

| Folder | Purpose |
|---|---|
| `work-sessions/2026-11/scripts/` | Original one-off audit/deployment/repair/helper scripts |
| `work-sessions/2026-11/commands/` | Original command payloads and console text |
| `work-sessions/2026-11/notes/` | Original work-state and protocol notes |
| `source-snapshots/close-button-before/` | Sender UI sources before the Close control update |
| `source-snapshots/whisper-before-indic/` | Speech tester sources before the IndicConformer update |
| `references/` | Downloaded Indic/romanization/Whisper reference code |
| `generated/` | Preserved bytecode from the old work and component folders |
| `organization/2026-11-13/` | File inventory, bounded move script, manifest, original document backups |

Historical scripts retain their original paths and import/working-directory
assumptions. They record earlier operations; use the component guides and
component `sync.py` for current supported source synchronization. The
[organization report](../docs/development/ORGANIZATION_REPORT.md) explains how
to trace an original path to its preserved file.

Device backup archives remain private under `.work/backups/pi`; staged model
and package downloads remain under `.work/cache`. Sensor/Zigbee release
snapshots stay within `Sender/versions` and `Receiver/versions` as specified by
the master plan.
