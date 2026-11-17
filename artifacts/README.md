# Local evidence and generated artifacts

This folder groups captured project evidence. This index and the two dated BOM
validation summaries below are tracked so GitHub documentation can cite them.
Other captures remain excluded by the root `.gitignore`. Keep dates, original
capture times, and patient/session provenance when adding new evidence.

- [16 November BOM research validation](validation/BOM_RESEARCH_2026-11-16.md)
- [16 November purchase-costing validation](validation/PURCHASE_BOM_2026-11-16.md)

| Folder | Contents |
|---|---|
| `screenshots/pi/` | Earlier sender and patient-v2 UI captures; gateway captures in its `playwright/` subfolder |
| `screenshots/diagnostics/` | ECG, radio, UI and speech diagnostic captures from the earlier work directory |
| `screenshots/website/playwright/` | Website desktop/mobile/browser QA captures |
| `browser/root-session/` | Earlier root Playwright YAML and console logs |
| `browser/website-session/` | Earlier website Playwright YAML and console logs |
| `validation/work-sessions/2026-11/` | Original local sensor/radio/patient/speech verification JSON |
| `validation/speech/fixtures/` | Retained reference WAVs and their metadata |
| `logs/website/` | Captured website/emulator logs |

The current speech tester's `validation_indic/` tree remains in
`Speech_Test_Phase3` with its synchronized component evidence.
New organization/check results are stored under `validation/organization/` and
`logs/organization/`.

Use the [organization report](../docs/development/ORGANIZATION_REPORT.md) and
move manifest to locate evidence mentioned by its former `output/` or `.work/`
path. Existing evidence keeps its original content and date.
