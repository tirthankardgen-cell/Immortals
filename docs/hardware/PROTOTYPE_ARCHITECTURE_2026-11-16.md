# Suitcase prototype architecture and BOM research

**Owner design update:** 16 November 2026. The [master plan](../planning/IMMORTALS_MASTER_PROJECT_DOCUMENT_v2.md), Sections 3.4 and 4.1, governs this prototype.

The main enclosure is a toolbox/suitcase with two closing clips. Its lid holds the solar panel. Its main tray holds the Pi 5, battery/power distribution and fitted storage for the BP cuff, tube connectors and retractable sensor leads. A detachable touchscreen unit and a detachable lower weight/height station have independent batteries.

## Allocation

| Assembly | Components | Work |
|---|---|---|
| Suitcase | Pi 5, main battery, solar/mains charging, GPS, Zigbee and remaining retained wired sensors | Patient/session authority, offline speech/VLM/LLM inference, acquisition aggregation and persistent sender transport |
| Detachable control unit | Pi Zero 2 W, flat 3000 mAh cell, touchscreen, basic fixed-focus or autofocus camera, two INMP441 microphones, IR temperature sensor, red laser | Operator app/notes, image/audio/temperature capture, local display and temporary capture recovery |
| Lower station | Four load cells, HX711 or selected bridge ADC, ESP32, ToF LiDAR, telescopic height stand and separate battery | Weight/height acquisition, quality/calibration, Bluetooth delivery and eight-hour runtime target |

There is one integrated Bluetooth scale. The result displays on the control unit. Two magnetic pogo-pin sets are requested for charging docks. A set means both mating connector halves. An HDMI FPC extension is a matched cable assembly, not a camera CSI extension. Pi Zero uses mini HDMI; Pi 5 uses micro HDMI. Final adapter choices must match the actual display and cable series.

Reuse the owner's Pi 5, Zigbee module, nominal 12 V solar panel, main drone battery and Waveshare 7-inch touchscreen. They have zero purchase quantity in the BOM. The 7-inch display goes in the detachable control unit. Add one green double-sided 7 × 9 cm prototyping/VeroBoard. This candidate has individual pads, so confirm the desired stripboard versus pad-board pattern before ordering.

The owner confirms that ESP32 sends weight and height to Pi 5 over Bluetooth or BLE. Pi Zero sends lightweight readings, notes, control and status using Bluetooth, and images/audio using local Wi-Fi. Both links may be used as required. Define transport roles, pairing/authentication, patient binding, reconnect and bounded queues before implementation. The Pi 5 keeps the original offline-first sender role. Only the separate receiver gateway uploads to Firebase.

## Power and measurement decisions

- The main orange drone battery label is unconfirmed. The owner authorizes generalized 3S/4S choices and 1500/5000/5200 mAh runtime examples until the label is available. Conventional 3S lithium is 11.1 V nominal/12.6 V full. Conventional 4S is 14.8 V nominal/16.8 V full. Do not treat any scenario as the owned pack's measured specification. Keep 3S and 4S BMS choices mutually exclusive. A configurable mains balance charger is a candidate, with settings and current selected only after the chemistry/cell count and connector are known.
- Keep the scale's eight-hour load calculation separate from the Pi Zero and Pi 5 load calculations. Capacities are estimates until input current, converters, battery capacity and cutoff are measured.
- Main Pi 5 supply needs adequate regulated 5 V current, startup/transient allowance, fuse/cable ratings and thermal checks. Do not treat a generic “5 A” buck listing as a verified continuous Pi 5 supply.
- Main battery charging requires a lithium CC/CV charger and compatible protection. Solar selection requires panel watts/Vmp/Voc, lithium charge voltage/current and reverse-current behavior. A lead-acid controller or single-cell CN3791 solar board cannot be substituted for 3S/4S. The CN3722 candidate is buck based, so a nominal 12 V panel may need an additional boost stage, especially for 4S. That stage remains unpriced until panel/load specifications are known.
- The Pi Zero 3000 mAh pouch must have documented discharge capability for the touchscreen/camera/audio load. A high output-current claim on a boost converter does not prove the battery can support it. Charging with the system active requires a tested power path. Simple TP4056 arrangements should charge with the downstream load disconnected unless load sharing is engineered.
- Four nominal 50 kg half-bridge cells do not automatically establish a safe 200 kg human platform. Specify frame stiffness, corner overload, mechanical stops, fastening, reference weights and usable calibrated capacity.
- LiDAR height requires a selected fixture and reference plane on the telescopic stand. Preserve invalid readings rather than calculating plausible height from a poor return.
- MLX90614 is a provisional infrared **surface-temperature** input. Medical-grade/body-temperature claims require exact sensor grade, optical geometry, calibration and clinical/reference validation.
- Indoor GPS fix is conditional on visibility and building attenuation. Provide antenna placement near a window/outdoors or a last-known-fix workflow with age/quality shown. Guaranteed indoor positioning is a different system requirement.
- ECG noise reduction and patient isolation are separate. Select the complete power and signal isolation arrangement. A shared I²C/ADC/ground path defeats a separate supply's isolation. Bench tests may proceed without a person. Human-connected use remains subject to the master safety requirements.

## Procurement evidence and status

For the **15 December 2026 proof of concept**, the owner requires a component costing for the principal. Use green double-sided prototyping board and a rough/cardboard layout mock-up. A fabricated enclosure is later work. The current [purchase-only Excel costing](bom/history/Immortals_Purchase_Only_BOM_Dec15_2026-11-16.xlsx) lists only new purchases and retains sold-out components for comparison in Chandni Market/Robu. It supersedes the earlier broad workbook for milestone purchasing.

Both camera options remain: **OV5647 5MP fixed focus, INR 293 including GST**, and **Camera Module 3 autofocus, INR 3245 including GST** (sold out at the observed supplier). Select one camera in the total. Keep the separate Pi Zero CSI cable for either choice. The earlier autofocus requirement remains the later product target; the cheaper camera is an explicit prototype alternative.

Automatic BP transfer remains required. The preferred bench candidate is the HX710B 0–40 kPa pressure/ADC module (**INR 113**) plus cuff/bladder/hand-bulb set (**INR 443**). Manual inflation is compatible with automatic electronic pressure capture, but pressure calibration, controlled deflation and oscillometric systolic/diastolic processing remain to be implemented. The alternative digital donor machine costs **INR 799**. Its internal wires do not establish a supported serial interface; inspect/decode the actual signals and check voltage levels before Pi connection. Count one route, with pneumatic fittings/level conversion priced only after the interface is specified.

The base costing is **INR 10,593.50** with basic camera/module BP, or **INR 10,836.50** with basic camera/digital donor. Autofocus adds **INR 2952**. These totals include known GST and provisional main-power parts; shipping and unspecified integration parts are excluded. The lower-cost choices include VL53L0X, basic GY-906, NEO-6M and common ancillary buck modules. The selected eight-hour scale supply remains 1S 5000 mAh. At the revised estimated 0.91789 W load, the reserve-inclusive minimum is 3749.55 mAh, rounded to 4000 mAh; the selected 5000 mAh gives approximately 10.67 hours with reserve. The calculation is editable in the same worksheet.

**Current purchase-costing research and local workbook validation: Done and verified**, 16 November 2026, with [recorded evidence](../../artifacts/validation/PURCHASE_BOM_2026-11-16.md). Main battery/panel specifications and complete ECG power/signal isolation remain open. Device integration remains **Not started / planned**; these are costing and document checks only.

The Excel BOM is a dated supplier-price research deliverable. It must preserve requested quantities, price/tax basis, stock observations, direct Indian supplier URLs and design decisions still needed. Shipping, optional alternatives, reused Pi 5/sensors and custom mechanical fabrication must be identified separately. Search-result prices are discovery evidence; final selections should use product-page observations where accessible.

The earlier [broad provisional Excel BOM](bom/history/Immortals_Prototype_BOM_2026-11-16.xlsx) is preserved as research history. It contains 53 rows, four sheets, supplier links, stock/tax observations, owned-item exclusions, alternatives and editable battery calculations. Its TF-Luna scale estimate is superseded by the VL53L0X calculation above for the low-cost milestone. The requested 3000 mAh tablet battery gives approximately 1.24 hours under the estimated seven-inch-screen load. Actual runtime requires assembled-device measurements.

**Provisional BOM research and local workbook validation: Done and verified** on 16 November 2026, as recorded in the [validation evidence](../../artifacts/validation/BOM_RESEARCH_2026-11-16.md). Physical design remains **In progress**. Hardware/client/ESP32 integration against this layout is **Not started / planned**. Main battery/panel labels, missing fabrication prices and complete ECG isolation remain open. This local research does not establish deployed Pi compatibility, sensor calibration, medical safety, cloud acceptance or field readiness.

## Document organization update — 17 November 2026

BOM source files are consolidated in the [BOM index](bom/README.md). The
16 November amounts and local validation above describe the preserved historical
workbooks. The later editable workbook and automatic-inflation print checklist
have different scopes/totals and are separately identified there. Organization
does not establish new procurement, hardware or Pi acceptance.
