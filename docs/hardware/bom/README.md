# BOM and purchase documents

All BOM workbooks and the supplied print checklist live here. Use the dates and
roles below instead of treating every workbook as the same purchase list.

| Document | Role and source date |
|---|---|
| [Purchase print checklist](Immortals_Purchase_BOM_Print.pdf) | Latest supplied purchase checklist, 17 November 2026. Automatic BP inflation parts, selected fixed-focus camera, handwritten update column. INR 11,408.40 for priced items; several BP parts and shipping remain unpriced. |
| [Editable purchase workbook](Immortals_Purchase_BOM.xlsx) | Latest supplied editable workbook, saved 17 November 2026 at 01:54:29 IST, originally `purchase bom.xlsx`. Retains earlier BP/camera alternatives and battery calculations. INR 10,535.48 under its saved selection. |
| [16 November purchase costing](history/Immortals_Purchase_Only_BOM_Dec15_2026-11-16.xlsx) | Superseded purchase costing associated with the recorded 16 November validation, INR 10,593.50 under its original selection. Historical comparison only. |
| [16 November broad research BOM](history/Immortals_Prototype_BOM_2026-11-16.xlsx) | Historical four-sheet supplier research, design notes and power scenarios. Retains unique research that is absent from the purchase-only files. |

The print checklist and spreadsheet differ in BP scope and total. The later
checklist requests automatic inflation; the spreadsheet retains a manual bulb
route. Organization preserves both originals without silently changing prices,
engineering requirements or formulas. Reconcile the chosen purchase configuration
before buying. Earlier verification records apply to their dated source files.

All four files were moved without modifying bytes. Original paths and SHA-256
hashes are in the [move record](../../development/organization/2026-11-17-moves.json).
See the [master plan](../../planning/IMMORTALS_MASTER_PROJECT_DOCUMENT_v2.md),
[hardware decisions](../PROTOTYPE_ARCHITECTURE_2026-11-16.md) and
[development log](../../development/development.md).

Keep one current file per purpose. Put superseded versions with unique content
in `history/` with a date, and link the current file here. Do not use generated
output folders as the long-term home for project purchase documents.
