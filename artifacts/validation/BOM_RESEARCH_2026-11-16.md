# Prototype BOM research and workbook validation

**Date:** 16 November 2026. **Target:** local Excel deliverable and project specifications.

Deliverable: [Immortals prototype BOM](../../docs/hardware/bom/history/Immortals_Prototype_BOM_2026-11-16.xlsx).

## Completed local checks

- Chrome supplier research is captured in `artifacts/browser/bom-2026-11-16`. Robu was blocked by CAPTCHA/Cloudflare. Indian alternatives include ElectronicsComp, FlyRobo, Robocraze and Sunrom.
- Workbook contains four sheets and 53 BOM rows: Summary, BOM, Power and Design notes. Five owner-confirmed items have zero purchase quantity. Two magnetic mating sets are represented by one observed two-pair pack. Buck quantity is one main BEC plus two auxiliary bucks. One double-sided green board is included.
- 36 product-price matches are recorded in `artifacts/bom-2026-11-16/price-audit.json`. The Amazon pogo price has search-page evidence only. Its direct listing, stock and GST remain unconfirmed. Sunrom BP GST is also unconfirmed.
- Artifact Tool recalculation and independent quantity/price/GST arithmetic agree. Known-GST baseline is INR 16,825.19. Observed BP/pogo prices add INR 5,255.00, giving INR 22,080.19 before unresolved taxes, shipping and unpriced items. Main-power candidates are separate: INR 3,909.82 with 3S BMS or INR 3,947.00 with 4S BMS. BMS purchase is conditional on the existing pack's protection.
- Editable input checks covered doubling the scale target to 16 hours, updating the linked capacity recommendation, setting a microphone purchase quantity to zero, restoring all original inputs, preserving zero owned-item purchases and preserving unavailable fabrication quotes.
- Scale estimate: 1.16889 W average, 8-hour target, 3.6 V cell, 85% conversion, 80% usable capacity and 25% reserve. Required capacity is 4774.88 mAh, rounded to 5000 mAh. Reserve-adjusted estimated runtime is 8.38 hours.
- Tablet estimate: requested 3000 mAh at 3.7 V and estimated 6.0997 W load. Estimated runtime is 1.24 hours. This is not measured performance.
- Every worksheet was rendered and inspected. Supplier-link text was adjusted to prevent clipping. Saved XLSX XML contains the expected table, frozen panes, input validation and 37 HYPERLINK formulas. Saved formula caches match calculated summary outputs and contain zero error cells. Native Microsoft Excel recalculation was not separately tested.

## Evidence boundary

**BOM research and local workbook validation: Done and verified for this provisional deliverable.**

Main battery chemistry/cell count/capacity and solar watts/Vmp/Voc remain unknown. The owner expressly authorizes generalized choices until the label is available. Eleven assemblies/design gaps remain unpriced. Out-of-stock items and substitutions need procurement follow-up. These checks do not establish hardware assembly, Pi compatibility, measured runtime, patient safety, medical validation, cloud acceptance or field readiness.

Document/path validation uses `python -B tools/project/check_workspace.py`. The check is local workspace evidence only.

**Navigation follow-up — 17 November 2026:** the workbook moved into the central
BOM history without changing its bytes. This summary is now tracked; detailed
captures remain local. The original 16 November results apply to that preserved
workbook and do not validate the later purchase documents.
