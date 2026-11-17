# Purchase-only prototype costing validation

**Date:** 16 November 2026. **Target:** local Excel costing for the principal and project specifications. **Milestone:** 15 December 2026 hardware/software proof of concept.

Deliverable: [purchase-only Excel BOM](../../docs/hardware/bom/history/Immortals_Purchase_Only_BOM_Dec15_2026-11-16.xlsx). The previous broad BOM and its evidence remain preserved.

## Scope and source checks

- One worksheet, 35 priced component/alternative rows. Common modules, specialty/stock-limited items, BP routes and both camera choices have separate sections.
- Owner-authorized costing retains sold-out listings for Chandni Market/Robu comparison. Direct Indian supplier URLs, stock observations and tax basis are included. Robu links are lookups/matches; blocked automated access did not establish current Robu prices. Local market stock/quotes are unverified.
- Existing Pi 5, Zigbee, solar panel, main battery and touchscreen are excluded. No fabricated enclosure or separate purchased Bluetooth scale. Two complete magnetic pogo mating pairs, two INMP441 microphones, four load cells, one HX711, three bucks and one green double-sided board are represented.
- Camera pages were rechecked through the existing Chrome/Playwright session: OV5647 fixed-focus INR 293 including GST with Add to Cart shown; Camera Module 3 INR 3245 including GST, sold out. Captures: `artifacts/browser/bom-2026-11-16/camera-fixed-final.json` and `camera-auto-final.json`. Both require the separately listed Zero CSI cable.
- Remaining selected prices match same-session supplier captures through the purchase data builder. ElectronicsComp's quoted prices have 18% GST added; FlyRobo/Robocraze/1mg gross references retain observed prices. The default BP candidate totals INR 556; donor alternative is INR 799. Availability is a procurement follow-up, not a reason to remove the owner's costing alternatives.

## Local calculation checks

- Artifact Tool exported the final XLSX. Quantity/price arithmetic independently agrees for all four selections: basic/module INR 10,593.50; basic/donor INR 10,836.50; autofocus/module INR 13,545.50; autofocus/donor INR 13,788.50.
- Changing BP and camera selectors updates selected quantities and budget; unselected alternatives have zero purchase quantity. All four combinations were checked and the default basic/module selection restored.
- Eight-hour scale assumptions: ESP32 board 5 V/150 mA, VL53L0X allowance 3.3 V/30 mA, HX711 allowance 3.3 V/10 mA, equivalent bridge 1000 ohm at 3.3 V, status overhead 5 V/5 mA; continuous duty. Total output estimate is 0.91789 W and target output energy is 7.34312 Wh.
- At 3.6 V, 85% conversion, 80% usable capacity and 25% reserve, the minimum is 3749.55 mAh, rounded to 4000 mAh. Selected 5000 mAh retains margin and gives 10.67 estimated hours with reserve. A 16-hour input doubles required capacity; the original eight-hour input was restored.
- Final rendered costing and battery calculation were visually inspected. The saved XLSX has one worksheet, four tables, six input validations, frozen identification/header panes and 70 supplier/Robu HYPERLINK formulas. Saved budget is INR 10,593.50, both magnetic-pair and microphone quantities are two, load-cell quantity is four, the unselected autofocus quantity is zero, and no cached error cells were found. Formula scan matched zero errors. Evidence: `artifacts/bom-purchase-only-2026-11-16/export-validation.json`, `validation.json`, `formula-scan.ndjson` and rendered review images. Native Microsoft Excel execution was not separately tested.
- `python -B tools/project/check_workspace.py` passed after project document changes: six components, 20 documents and 107 local links checked, zero errors. This is local workspace evidence only.

## Evidence boundary

**Costing research and local workbook validation: Done and verified.** This is an estimated purchase costing for comparison, not a confirmed stocked order or a complete installed-system quote. Shipping, BP fittings/interface parts, solar input conditioning and full ECG signal isolation remain unpriced until specified. Main battery chemistry/cell count/capacity and panel watts/Vmp/Voc are pending; their main-power allowances are provisional. No hardware purchase, assembly, deployed Pi compatibility, BP result validation, patient safety, measured runtime, cloud or field acceptance is established by these checks. New device integration remains **Not started / planned**.

**Navigation follow-up — 17 November 2026:** the workbook moved into the central
BOM history without changing its bytes. This summary is now tracked; detailed
captures remain local. The original 16 November results apply to that preserved
workbook and do not validate the later purchase documents.
