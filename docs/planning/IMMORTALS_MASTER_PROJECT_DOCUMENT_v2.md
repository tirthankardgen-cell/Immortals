# IMMORTALS — Integrated Offline Health Screening & Patient Monitoring System

**Master project document**  
**Document date:** 12 November 2026  
**Purpose:** Consolidated project brief, system architecture, hardware baseline, software/data flow, current deployment status, upgrade roadmap, and source requirements.  
**Project name:** Immortals  
**Primary deployment context:** Portable health camps in rural/remote areas with unreliable or no mains power and no internet at the point of care.

> **Status note:** This document combines the project owner's description with the supplied `GOAL_REQUIREMENTS.md`, `PROJECT_UPGRADE_PLAN.md`, and Raspberry Pi 5 sensor wiring guide. It distinguishes implemented/reported baseline from proposed or not-yet-verified features. It is a project specification, not evidence that every sensor is medically validated or every end-to-end acceptance test has passed.

> **Superseding owner update — 16 November 2026:** The physical prototype is a toolbox/suitcase with a lid-mounted solar panel, a detachable Pi Zero 2 W touchscreen control unit, and a detachable ESP32 Bluetooth weight/height station stored below the case. The Pi 5 remains inside the suitcase and owns main processing and local model inference. Section 3.4 and the updated Section 4.1 govern this arrangement. Earlier descriptions of a single fixed touchscreen or a separately purchased Bluetooth scale are historical alternatives. This update specifies the intended prototype, not completed hardware integration or field acceptance.

> **15 December milestone clarification — owner update, 16 November 2026:** The required deliverable is a working hardware/software proof of concept by **15 December 2026**. Assemble the electronics on green double-sided prototyping/VeroBoard and use a cardboard/rough mock-up to show the eventual suitcase arrangement if useful. A fabricated enclosure, finished case and field-ready product are not required for this milestone. Section 3.5 governs the demonstration and low-cost purchase list. Final product requirements remain the later target.

## 0. Executive status snapshot — 12 November 2026

This section records the current implementation status as described by the project owner and the supplied project files. “Reported working” means the project has been described as implemented; it does not imply that every clinical, hardware, recovery, or field acceptance test has passed.

### 0.1 What is already implemented or reported working

| Area | Current status | Notes / evidence boundary |
|---|---|---|
| Raspberry Pi 5 sensor acquisition and local display | **Implemented baseline; individual sensor quality and full acceptance still require verification** | The supplied wiring guide documents the currently connected sensor set and pin mapping. The project requirements describe a running sensor dashboard and real waveform display. |
| Currently documented sensor modules | **Connected/documented legacy set; sensor-retention review in progress** | AD8232 ECG module through ADS1115 ADC; MH-ET LIVE MAX30102 for optical pulse/estimated SpO₂; BMP180 for ambient pressure/temperature; DHT22 for room temperature/humidity; HW-691 / MLX90614 infrared surface temperature. The wiring guide records what has been connected, not the final production sensor list. DHT22 and BMP180 are candidates for removal because general environmental readings are not central to the health-screening goal. See Section 4 and Appendix C for historical wiring details. |
| Local patient measurement recording | **Reported working** | Sensor measurements can be recorded on the sender device. The patient-recording v2 workflow adds fixed patient-associated snapshots and persistent pending records; full v2 acceptance should be tracked separately from the earlier sensor-only baseline. |
| Zigbee sender-to-gateway link | **Implemented/reported working** | Sender can transmit recorded sensor data over Zigbee to the separate gateway. The existing codebase includes Zigbee communication and status controls. RF reception, latency, reconnection, queue recovery and all v2 message types must still be acceptance-tested as a complete release. |
| Receiver/gateway Raspberry Pi | **Implemented/reported working** | The gateway receives sender data and is the designated device that connects to Firebase. Sender remains offline-first and must not hold Firebase credentials. |
| Firebase database integration | **Implemented/reported working** | The gateway saves received patient-associated data to Firebase. Current documented database is Cloud Firestore in Firebase project `immortals-3`; private gateway credentials remain on the gateway. |
| Website/dashboard | **Deployed and reported working** | The website fetches patient information from Firebase and provides patient directory/details, readings and available waveform/status views. The supplied upgrade plan records a Vercel production deployment at `https://immortals-dashboard.vercel.app`. |
| Sender → Zigbee → gateway → Firebase → website data path | **Core path reported working** | The project owner confirms that sensor records can be recorded locally, sent to the gateway over Zigbee, stored in the database, and displayed by the website. Formal end-to-end tests must continue to cover patient association, retries, stale data and outage recovery. |
| Patient IDs, local cache, recording popup and v2 workflow | **Specified; full acceptance status not established by the supplied summary** | The v2 documents define `IMM-YYYYMMDD-DEVICE8-COUNTER`, patient selection/registration, fixed recordings, explicit Send to Gateway, Record Again, Sync All Saved Data and gateway/cloud acknowledgements. Do not mark every item complete until verified on the actual devices. |
| Local-language conversation transcripts | **Not yet integrated into the complete data path** | Offline transcription in Bengali, Hindi and English is a target. Transcript delivery over Zigbee/internet-to-gateway, storage in Firebase and display on the website remain work to complete and verify. |
| Camera-based medical document capture and VLM analysis | **Planned / not yet demonstrated as an integrated feature** | Capture prior reports/prescriptions, preserve originals, describe/extract visible information locally and flag uncertainty. |
| Offline Qwen multimodal summary and suggestions | **Planned / model and performance validation pending** | Combine transcripts, document/VLM results, measured vitals and relevant patient context; generate a short source-linked summary and cautious general suggestions. The exact Qwen variant/quantization must be benchmarked on the target Pi 5. |
| Additional hardware: Bluetooth scale, LiDAR height, BP monitor, GPS, camera, microphone, battery and rugged IP-rated enclosure | **Some components are planned; integration and validation remain** | The supplied wiring guide does not document these as part of the current wired sensor set. Exact models, interfaces, calibration, battery runtime, isolation and ingress-protection testing remain to be closed. |

### 0.2 Current architecture that is already in place

```mermaid
flowchart LR
    Sensors[Currently connected sensors] --> Sender[Sender Raspberry Pi 5]
    Sender --> Local[Local readings / recording]
    Local --> Zigbee[Zigbee link]
    Zigbee --> Gateway[Receiver Raspberry Pi gateway]
    Gateway --> Firebase[Firebase / Cloud Firestore]
    Firebase --> Website[Immortals website dashboard]
```

The project owner reports that this core sensor-data path is already operational. The remaining work is not to rebuild that foundation from scratch; it is to harden and verify it, complete patient-linked v2 behavior, and add the speech, document-understanding and offline-summary pipeline plus the planned hardware integrations.

### 0.3 Work remaining to reach the December 2026 target

1. **Stabilize the existing core:** verify all currently connected sensor readings, quality labels, ECG waveform/rate separation, local persistence, Zigbee delivery, gateway durability, Firebase writes and dashboard freshness under real device conditions.
2. **Finish patient-based v2 acceptance:** verify Choose/Add Patient, persistent IDs, patient/session binding, fixed recordings, acknowledgement states, retries, duplicate prevention and restart recovery on sender and gateway.
3. **Complete multilingual offline transcription:** benchmark real Bengali, Hindi and English speech on the Raspberry Pi 5; choose and package the model; preserve timestamps and conservative speaker labels; test noisy and mixed-language conversations.
4. **Implement transcript synchronization:** persist transcripts locally, transfer them to the gateway with acknowledgements/retry/deduplication, store them in Firebase, and expose them in the correct patient's website view.
5. **Implement camera/document workflow:** capture prior reports and prescriptions, retain original images, associate them with the patient/session, and handle poor-quality or unreadable images safely.
6. **Integrate an offline VLM:** extract or describe visible document content with uncertainty markers; measure RAM, latency, thermal behavior and reliability on the target hardware.
7. **Integrate offline Qwen:** combine source-linked transcripts, VLM output, vitals and known patient context into a concise summary and general next-step suggestions. Test factual grounding, uncertainty and non-fabrication.
8. **Resolve image and transcript transport:** Zigbee is suitable for constrained text/control/sensor messages, but full-resolution images may exceed practical bandwidth. Decide and test chunking, compression, deferred upload or a separately authenticated network path to the gateway without granting the sender direct Firebase access.
9. **Integrate remaining peripherals and enclosure:** Bluetooth weighing scale, LiDAR-based height method, BP device, GPS, camera/microphone, power/battery, thermal management and IP-rated enclosure as feasible within the deadline.
10. **Complete end-to-end field simulation:** test no-internet operation, gateway loss, radio loss, power/restart recovery, stale-data labeling, patient isolation, privacy/consent, clinical review and operator usability.

### 0.4 Delivery planning and completion reporting

**Target: complete the agreed project scope by December 2026.** As of 12 November 2026, the core sensor → local recording → Zigbee → gateway → Firebase → website path is reported as already working. The expanded AI workflow and several proposed hardware integrations are not yet complete. No single percentage is assigned because the project has distinct hardware, software, data, safety and field-validation workstreams; a percentage without weighted, test-backed acceptance criteria would be misleading.

Track each work item with one of four statuses: **Done and verified**, **Implemented but not fully verified**, **In progress**, or **Not started / planned**. Only move an item to “Done and verified” after it passes its defined acceptance test on the intended hardware and the result is recorded. December readiness means the agreed end-to-end workflow passes offline field simulation, not merely that individual scripts or models run once.

## 1. Project vision

Immortals is intended to be a compact, portable, rugged, all-in-one health-screening and patient-monitoring system. It is designed for health camps and other field settings where there may be no internet, unreliable electricity, and no doctor physically present at every measurement station. A trained nurse, health worker, or other appropriately trained operator should be able to follow a guided touchscreen workflow to register or select a patient, collect measurements, save a patient-associated record, and synchronize it later.

The device is an aid for collecting and presenting measurements. It must not be described as replacing a qualified clinician, diagnosing a disease, or making autonomous clinical decisions. Readings must retain their units, timestamps, source, signal-quality information, and unavailable/invalid state. The system must never fabricate a vital sign when a sensor is disconnected or its signal is unusable.

### Core design goals

- **Portable and rugged:** a compact enclosure suitable for repeated field use; impact resistance and environmental sealing/IP rating are design targets that require mechanical and ingress-protection testing.
- **Offline-first:** patient registration/cache, measurement acquisition, local recording, and the operator interface work without internet access.
- **Simple operation:** touch-first UI, patient name/ID search, virtual keyboard, clear measurement states, and explicit recording/synchronization feedback.
- **Patient-linked data:** each measurement belongs to a stable patient ID and a distinct monitoring session.
- **Store-and-forward connectivity:** Zigbee transfers records to a nearby gateway; if it is out of range, records remain queued locally and can be sent when the link returns. The field team may also carry the sender back into a place with internet/gateway access, depending on the deployed topology.
- **Gateway-mediated cloud access:** the sender has no Firebase credentials or direct Firebase connection. Only the receiver/gateway connects to Firebase when it has internet.
- **Reliable recovery:** retries, durable outboxes, application acknowledgements, duplicate prevention, and preservation of original capture times.
- **Expandable, multimodal platform:** a patient website/dashboard is available; offline local-language conversation transcription, medical-document/image understanding, and on-device multimodal summarization are part of the expanded target.

## 2. Field-use scenario and operator workflow

1. Carry the sender device to a health camp or field location. The sender can operate without internet.
2. Power on the system and open the patient workflow on the touchscreen.
3. **Choose Patient** to search/select an existing patient by name or ID, or **Add Patient** to register a new patient. Similar names must be distinguishable by ID.
4. Confirm the patient's displayed identity and start a monitoring session. No patient-specific recording may start before a valid patient/session context exists.
5. Collect the available measurements. The system continues sensor acquisition and shows signal/quality states while readings stabilize.
6. The v2 target flow waits for all required readings to be stable for three seconds, then creates a fixed local recording. Missing or poor-quality signals remain marked as unavailable/poor; they must not be filled with invented values.
7. Show a **Data recorded successfully** popup with the saved record and its transfer status. The operator can choose **Send to Gateway**, **Record Again** (discarding the unsent draft and restarting for the same patient), or use **Sync All Saved Data** to release earlier unsent records.
8. If the gateway is reachable, the sender transmits the patient record and available waveform snapshots over Zigbee. Gateway acceptance means the record is durably stored at the gateway; it is distinct from Firebase upload completion.
9. The gateway independently uploads validated records to Firebase when internet is available. Acknowledgements/status return to the sender over Zigbee where applicable.
10. If the gateway is unavailable, the sender confirms that the record is saved locally and will synchronize when the gateway returns. The operator can return to the main screen and continue other checks; radio/cloud retries must not block acquisition or the display.
11. The website reads synchronized patient records and displays patient profiles, measurements, waveforms, history, monitoring status, and—when implemented—conversation transcripts and document/image summaries.

## 3. System architecture

### 3.1 Main data path

```mermaid
flowchart LR
    Operator[Trained health worker] --> UI[Sender patient UI; detachable touchscreen target]
    UI --> Patient[Patient selection / registration]
    Patient --> Sensors[Sensor acquisition and quality checks]
    Sensors --> Local[Local fixed record + persistent outbox]
    Local --> SenderPi[Sender Raspberry Pi 5]
    SenderPi <-->|Bidirectional Zigbee: records, patient lists, controls, acknowledgements| Gateway[Receiver Raspberry Pi / gateway]
    Gateway --> Durable[Gateway local storage / upload outbox]
    Durable -->|Internet when available| Firebase[Firebase Cloud Firestore]
    Firebase --> Website[Immortals patient website / dashboard]
    Website --> Viewer[Authorized or currently public viewer]
```

### 3.2 Responsibilities by component

| Component | Primary responsibility | Connectivity expectation |
|---|---|---|
| Sender device / Raspberry Pi 5 | Touchscreen workflow, patient cache, sensor acquisition, local display, fixed patient-associated recordings, persistent pending queue, Zigbee sender | Must work offline; no Firebase credentials/direct Firebase access |
| Sensors and peripheral devices | Capture the specific measurement assigned to each sensor/device | Local wired bus or supported short-range wireless link |
| Zigbee link | Transfer records and control messages between sender and gateway, with application-level acknowledgement and retry | Local radio range; must not block sensing/display |
| Receiver/gateway Raspberry Pi | Receive/reassemble/validate messages, maintain durable local queue, manage cloud uploads, report status | Zigbee to sender; internet for Firebase when available |
| Firebase Cloud Firestore | Store patient profiles, latest submitted snapshot, reading history, sessions, and future transcripts | Reached by gateway; website uses configured web application access |
| Website/dashboard | Patient directory, patient details, measurements, graphs/waveforms, history, status, future transcript view | Internet connection required for current cloud-backed data |
| Optional Phase 2 speech pipeline | Capture external microphone audio, perform offline transcription and speaker diarization, queue transcript events | Local inference on sender; no cloud speech API required |

The sender's physical UI allocation is superseded by the 16 November 2026 module design in Section 3.4. The sender Pi 5 retains patient/session authority, local persistence, radio scheduling and inference. The receiver gateway remains a separate role.

### 3.3 Connectivity and synchronization behavior

- **Sender offline, gateway reachable by Zigbee:** record is sent to the gateway without internet at the sender.
- **Sender and gateway temporarily separated:** record stays in the sender's persistent outbox. It is retried when the gateway becomes reachable.
- **Gateway has Zigbee but no internet:** gateway durably queues records locally and uploads them later.
- **Internet returns:** gateway uploads pending records with bounded timeouts and backoff; retries use stable IDs to avoid duplicate history.
- **Patient-list synchronization:** gateway-mediated, bidirectional Zigbee exchanges provide the sender with available patient profiles and return registration/control acknowledgements. A patient not in the local cache must be resolved or explicitly registered before a session starts.
- **Stale-data handling:** original capture time is authoritative. Upload time must never make an old record appear live or allow delayed data to overwrite a newer latest reading.
- **Transport vs application success:** radio delivery alone is not proof that the gateway accepted a complete record. Use versioned messages, validation, and application acknowledgements.

### 3.4 Suitcase and detachable modules — owner update, 16 November 2026

The owner has specified a toolbox/suitcase enclosure with two closing clips, fitted storage slots and a detachable lower module. The solar panel mounts on the inside of the lid and must face daylight when deployed. The main case contains the Pi 5, main battery and power distribution, charging inlet/external AC inlet arrangement, GPS, Zigbee and remaining directly connected sensors. Provide dedicated storage and strain relief for the BP cuff, tubing/pipe connector and retractable sensor leads.

| Physical module | Hardware and responsibility | Local connection |
|---|---|---|
| Main suitcase | Existing Raspberry Pi 5. Owns the patient/session records, sensor aggregation, offline speech/VLM/LLM processing and persistent sender outboxes. GPS, Zigbee and other retained wired sensors connect here. Main battery and charging/power distribution remain in the case. | Hosts the local link to the control unit and the scale. Zigbee still links to the separate receiver gateway. |
| Detachable control unit | Raspberry Pi Zero 2 W accessory, its own flat 3000 mAh battery, touchscreen, autofocus camera, two INMP441 microphones, selected infrared temperature sensor and red aiming laser. Captures images/audio/temperature, displays the patient app and accepts notes/operator input. Does not host the main AI models. | Bluetooth carries lightweight readings, notes, control and status. Local Wi-Fi carries images and microphone audio to Pi 5 and large responses. Both links may be used as needed. Reconnect without changing the captured patient's identity. |
| Detachable weight/height station | Four load cells with an appropriate bridge/ADC, ESP32, its own battery, Bluetooth weight delivery and a telescopic height-measuring stand with the selected ToF LiDAR and a repeatable fixture. Stored in the detachable lower section, then placed on the ground for measurement. | ESP32 transmits weight, height, quality/status and capture timestamps to the Pi 5 over Bluetooth or BLE. The control display shows the result. |

The requested **weight scale** and **Bluetooth-enabled weight scale** are one integrated station, not two separate scales. The owner specifies **eight hours** between charges for this station and **two magnetic pogo-pin connector sets** for detachable charging docks. Purchase quantities must distinguish a complete mating set from a single connector half. Dock connectors must be keyed for polarity and rated for the actual charging current. Do not assume the pogo pins carry HDMI, camera CSI or the main Pi 5 power rail.

Keep touchscreen interaction, acquisition, audio/image transfer, inference and Zigbee transport independent and bounded. A slow local Wi-Fi link or inference job must not stop the main sender's acquisition or the ESP32 measurement loop. The Pi Zero retains unsent captures/notes with patient ID, session ID, event identity, original capture times and quality/gap information. Reconnection uses idempotent requests and acknowledgements. The Pi 5 owns patient registration and reconciles detached/offline drafts before they are finalized. Direct sender or Pi Zero Firebase access remains prohibited. Define authenticated local pairing and patient/session transfer before field use.

The existing sender touchscreen implementation and current deployment paths remain preserved. Extending its app to a detachable client, creating ESP32 firmware, audio/image transport and reconnect behavior are **Not started / planned** against this new target until dated implementation evidence establishes otherwise. Housing, docking, telescopic geometry, battery runtime and combined physical acceptance are **In progress** at specification/BOM research level. No Pi, cloud, clinical, ingress or field acceptance is established by this document update.

Power planning must separate three battery domains. The owner already has the Pi 5, Zigbee module, nominal 12 V solar panel, main drone battery and Waveshare 7-inch touchscreen. Reuse these and exclude them from new-purchase totals. The touchscreen belongs in the detachable Pi Zero 2 W control unit. Confirm its exact HDMI/USB-touch connections and current draw during integration. Add one green double-sided prototyping/VeroBoard to the purchase list. “Two-layer” describes copper on both sides, not two boards.

The owner cannot confirm the main battery label yet and authorizes a generalized BOM now. The orange drone pack is described as roughly 14 V, either 3S or 4S, and possibly 1500, 5000 or 5200 mAh. These are unconfirmed alternatives, not measured specifications. A conventional **3S lithium-ion/polymer pack is 11.1 V nominal and 12.6 V fully charged**. Conventional **4S is 14.8 V nominal and 16.8 V full**. List mutually exclusive 3S/4S protection choices and a configurable balance-charger candidate. Final chemistry, charge voltage/current, connector and BMS selection must wait for the label. A BMS provides protection/balancing and does not replace a lithium CC/CV charger. The nominal 12 V panel's watts, Vmp and Voc are unknown. A buck-only solar controller requires enough panel voltage above the selected charge voltage, particularly for 4S. Do not use a single-cell CN3791 charger for this pack. Any necessary solar boost/input conditioning remains a separately identified design gap.

The ECG front end needs a quiet supply and an electrically safe patient-connected design. A separate battery or isolated DC/DC converter alone is insufficient if ADC, I²C, ground, USB, charging or other wiring reconnects it to the main system. Specify the complete isolated power and signal barrier or a fully isolated battery-powered wireless front end before human-connected validation. Retain the Section 9 safety requirements.

See [dated prototype architecture and BOM research notes](../hardware/PROTOTYPE_ARCHITECTURE_2026-11-16.md) for allocations, assumptions and unresolved purchase decisions.

The [provisional Excel BOM dated 16 November 2026](../hardware/bom/history/Immortals_Prototype_BOM_2026-11-16.xlsx) includes Indian supplier links, prices/GST/stock observations, owned-item exclusions, separate main-battery alternatives and editable runtime calculations. The eight-hour scale baseline recommends a protected 1S 5000 mAh assembly. The requested 3000 mAh tablet battery has approximately 1.24 hours estimated runtime with the reused seven-inch display. Main battery/panel labels and measured loads must be confirmed before finalizing power hardware. Local workbook research/validation is **Done and verified** with [dated evidence](../../artifacts/validation/BOM_RESEARCH_2026-11-16.md); hardware integration remains **Not started / planned**.

### 3.5 Low-cost proof of concept due 15 December 2026

The milestone must demonstrate that the proposed electronics and software work together. It is not satisfied by a case mock-up or disconnected sensor displays alone. Preserve the Pi 5 main processor, Pi Zero 2 W capture/UI accessory and ESP32 weight/height roles from Section 3.4. Demonstrate touchscreen operation, sensor capture, Bluetooth lightweight/weight/height messages, Wi-Fi image/audio delivery and Pi 5 processing with the original patient/session/capture identity intact. Integration remains **Not started / planned** until implemented and tested on the target devices. Keep the earlier deployment evidence separate.

Use inexpensive, common modules first and seek parts in Kolkata's Chandni Market or Robu.in. Local stock and quotations must be checked with sellers; online listings do not establish Chandni availability. The fresh BOM contains purchase-only electronics, with harder-to-source items in a separate section. Exclude the owned Pi 5, Zigbee, solar panel, main battery and touchscreen. Do not add fabricated case/enclosure parts, duplicate replacements or a separately purchased Bluetooth scale.

Budget candidates include a basic GY-906 MLX90614 instead of the expensive narrow-FOV DCI grade, a VL53L0X short-range ToF module instead of TF-Luna, NEO-6M GPS instead of NEO-M8N and common LM2596 ancillary bucks. These are procurement candidates, not tested substitutions. Use a fixed height reference with a short head-to-sensor distance within the ToF module's usable range. Retain infrared **surface-temperature** labeling, no-fix GPS behavior and measurement quality/calibration requirements. Keep a suitably rated main Pi 5 supply; a cheap small buck is not evidence of adequate Pi 5 power.

**Camera and costing clarification — owner update, 16 November 2026:** Keep both a basic fixed-focus OV5647 5MP camera and the autofocus Camera Module 3 in the purchase costing, including sold-out listings. The owner will compare prices in Kolkata's Chandni Market and on Robu before final selection. Sold-out status does not exclude a component from the costing submitted to the principal. Both cameras require the Pi Zero-specific CSI cable. Count one selected camera in the budget; retain autofocus as the final-product target. This is a costing deliverable for the 15 December proof of concept, not a purchase order or evidence of assembled hardware.

The current [purchase-only Excel costing](../hardware/bom/history/Immortals_Purchase_Only_BOM_Dec15_2026-11-16.xlsx) supersedes the earlier broad procurement workbook for this milestone. It contains 35 priced component/alternative rows on one worksheet, with common modules, specialty/stock-limited components, BP alternatives and both camera choices. The default basic-camera/module-BP total is **INR 10,593.50** including the listed GST and provisional main-power allowance, excluding delivery and unresolved integration parts. Selecting the digital-BP donor gives **INR 10,836.50**. Autofocus adds **INR 2,952.00**. Only one BP route and one camera are counted. The owned Pi 5, Zigbee, solar panel, main battery and touchscreen, fabricated enclosure and duplicate replacements are excluded. Online prices are reference quotes for local comparison, not confirmed Chandni prices.

The lower-cost scale power estimate is **0.91789 W** using conservative ESP32, VL53L0X, HX711 and bridge assumptions. Eight hours requires approximately **3750 mAh** including 85% conversion efficiency, 80% usable capacity and 25% reserve; round the minimum to 4000 mAh. Retain the listed **1S 5000 mAh** cell for additional margin, with an estimated reserve-adjusted runtime of 10.67 hours. This updated estimate replaces the earlier TF-Luna load assumption for the low-cost prototype. Current draw, capacity, cutoff and peak behavior still need assembled-device measurements. Main BMS/charger/solar choices remain provisional until the battery and panel labels are known. See [purchase-costing validation](../../artifacts/validation/PURCHASE_BOM_2026-11-16.md).

The owner requires **automatic BP data transfer**, with two possible routes. Prefer a suitable cuff-pressure module if available and build the pressure acquisition/pneumatic arrangement. The low-cost HX710B 0–40 kPa module is a bench candidate; pressure sensing alone does not calculate validated systolic/diastolic BP. Provide the cuff/tubing, inflation/controlled deflation, calibrated pressure conversion and oscillometric processing needed by the selected method. If this route is unavailable, use a normal digital BP machine as a donor and inspect its internal signal/data interface. A consumer BP machine is not assumed to expose UART. Decode the actual protocol/display/pressure path and verify voltages before connection to 3.3 V Pi GPIO. Do not purchase both routes as required parts or report automatic BP integration complete before it works.

Cardboard illustrates layout and use only. It is not a load-bearing patient scale frame. Demonstrate weighing with suitable bench loads until a rigid platform, overload stops and calibration support the intended human load. ECG power and signal isolation requirements remain in force for human-connected use. Demonstration software must preserve unavailable/unreliable readings rather than inventing vitals.

## 4. Hardware and measurement scope

### 4.1 Main device

- **Compute:** Raspberry Pi 5 inside the sender suitcase for main processing and all local AI models. Pi Zero 2 W is a detachable capture/UI accessory, not a replacement for Pi 5.
- **Operator display:** reuse the owner's Waveshare 7-inch touchscreen in the detachable Pi Zero 2 W control unit. Verify its exact model, resolution, HDMI/USB-touch connections and measured battery load. Reusing the display does not establish compatibility or runtime of the new tablet arrangement.
- **Field enclosure:** toolbox/suitcase with two clips, inside-lid solar panel, fitted sensor/cuff/tubing storage and detachable lower weight/height station. Ruggedness/IP rating, structural loads, cable routing and thermal behavior require assembled-device testing.
- **Wireless data link:** Zigbee between sender and receiver/gateway.
- **Patient scale:** one custom Bluetooth-enabled station with four load cells and an ESP32, stored in the detachable lower section and placed on the ground. Bridge/ADC, platform capacity, calibration, units and reconnection require selection/verification.
- **Height:** telescopic stand integrated with the weight station and a ToF LiDAR fixture. Choose and document the geometry, reference plane, stand locking, orientation and patient positioning. The earlier handheld ground-ranging arrangement is a historical candidate. A distance value alone is not a validated height result.
- **Peripheral allocation:** autofocus camera, two INMP441 microphones, selected infrared temperature sensor, red laser and touchscreen reside in the Pi Zero control unit. GPS, Zigbee and remaining retained sensors connect to Pi 5 in the main case. BP needs a dedicated cuff/pump/measurement device and a supported data interface. Model selection, electrical interfaces and clinical acceptance remain open.

### 4.2 Current connected sensors versus the intended final sensor set

The supplied wiring guide is a record of the **currently documented/connected prototype**, not a commitment to retain every module in the final device. The owner has clarified that the final product should prioritize clinically relevant patient measurements and the AI-assisted encounter workflow. Most general environmental sensing is unnecessary for the intended field use and should be removed unless a clear clinical, safety, or device-health use case justifies keeping it.

| Measurement / output | Documented component | Current interface / interpretation |
|---|---|---|
| Optical heart rate | MH-ET LIVE MAX30102 | I²C; calculated from optical samples, quality checked |
| Estimated SpO₂ | MAX30102 | I²C; estimate from red/infrared optical samples; not a diagnostic-grade result by default |
| ECG waveform | AD8232 + ADS1115 ADC | AD8232 analogue output enters ADS1115 A0; ADS1115 shares I²C with Pi |
| ECG-derived rate | Derived from ECG waveform | Must be displayed separately from MAX30102 optical heart rate; candidate rate marked unreliable when quality checks fail |
| Infrared surface temperature | HW-691 / MLX90614 | I²C; label clearly as infrared surface measurement; do not imply it is a validated core body temperature |
| Room temperature and relative humidity | DHT22 | Digital GPIO4 (physical pin 7); **candidate for removal** because room humidity/temperature are not core patient measurements |
| Ambient pressure and sensor temperature | BMP180 | I²C; **candidate for removal** because barometric pressure is environmental data, not blood pressure |
| Weight | Proposed Bluetooth scale | Planned integration; no scale pin mapping in supplied wiring guide |
| Height | Proposed time-of-flight LiDAR arrangement | Planned integration; geometry and validation still required |
| Blood pressure (systolic/diastolic) | Device not yet specified in supplied wiring guide | Planned requirement; exact device and data integration are open items |
| GPS location | Module/device not specified | Planned requirement; exact hardware and privacy/consent behavior are open items |
| Camera | Module/device not specified | Planned requirement; purpose, storage, consent and interface need specification |
| Microphone / speech | External microphone planned for Phase 2 | Offline speech pipeline planned; exact microphone to be selected/tested |

**Sensor-retention decision and design direction:**

- **Prioritize and retain in the core clinical design:** MAX30102 for optical pulse/estimated SpO₂; AD8232 + ADS1115 for ECG waveform (subject to safe electrical isolation and validation); and MLX90614 as a provisional infrared surface-temperature input until the owner confirms the final temperature-sensor choice.
- **Plan to remove unless a specific need is demonstrated:** DHT22 room humidity/temperature and BMP180 ambient pressure/temperature. These are general environmental readings and are not required for the primary patient screening workflow. Their wiring and software references remain in this document as historical prototype documentation until removal is implemented and verified.
- **Add/integrate for the intended all-in-one device:** a Bluetooth weighing scale for weight; a validated time-of-flight LiDAR arrangement for height; a dedicated blood-pressure device; GPS; camera for medical-document capture; and microphone for local-language conversation capture/transcription. Exact models and interfaces still need selection and validation.
- **Keep environmental sensing only selectively:** retain a small number of environmental/device-health measurements only where they materially support safe operation or interpretation. Do not keep sensors merely because they were present in the prototype.
- **Firmware/UI/data cleanup:** after hardware decisions are confirmed, remove unneeded sensor polling, environmental cards, dependencies, and fields from the active UI/data contract, while retaining versioned historical records and clear compatibility handling. Never relabel ambient pressure as blood pressure.

**Terminology:** In the current software baseline, “heart rate” from MAX30102 and any rate calculated from ECG are separate fields. BMP180 pressure is ambient atmospheric pressure. Blood pressure is a separate clinical measurement and requires a dedicated supported BP device. All calculated/estimated values must include source and quality status.

### 4.3 Raspberry Pi 5 pin map (documented baseline)

| Pi physical pin | Signal | Connection / use |
|---:|---|---|
| 1 | 3.3 V | Sensor breakout power, only where board supply requirements allow |
| 3 | GPIO2 / SDA | Shared I²C data for ADS1115, MAX30102, BMP180, MLX90614 |
| 5 | GPIO3 / SCL | Shared I²C clock for ADS1115, MAX30102, BMP180, MLX90614 |
| 6 | GND | Common ground |
| 7 | GPIO4 | DHT22 DATA |
| 11 | GPIO17 | AD8232 LO+ (optional lead-off signal) |
| 13 | GPIO27 | AD8232 LO− (optional lead-off signal) |
| 15 | GPIO22 | MAX30102 INT (optional; basic polling does not require it) |

Typical I²C addresses: ADS1115 `0x48` (ADDR tied to GND), MAX30102 `0x57`, BMP180 `0x77`, MLX90614 `0x5A`. These are typical module addresses, not guarantees for every breakout/clone.

Detailed module-to-module wiring is transcribed in Appendix C.

## 5. Sender software and user interface

### 5.1 Main screen

- Patient Information header at the top, showing the active patient's name and stable ID; clearly marked placeholders may be used only before registration UI is integrated.
- Main and largest area for Patient Vitals, including optical heart rate, estimated SpO₂, infrared surface temperature, ECG waveform, and separately labelled ECG-derived rate.
- Historical prototype UI: compact environmental cards displayed room temperature, humidity, ambient pressure, and board temperature where available. **Final UI direction:** remove cards and polling for environmental sensors that are dropped from the final bill of materials; reserve the display area for clinically relevant measurements, patient context, signal quality, and AI workflow status. Keep only explicitly approved environmental/device-health indicators.
- Live numeric values, units, signal-quality labels, null/unavailable state, and live graphs/waveforms.
- A native rounded/capsule Zigbee ON/OFF push-toggle at the far right. ON controls forwarding only; OFF stops forwarding but must not stop local acquisition or display. Radio backend behavior is part of the sender/gateway integration stage; UI-only and integrated versions must be distinguished.
- Full-screen operation and controls must be tested on the real touchscreen/display, including touch and mouse input where supported.

### 5.2 Patient workflow

**Existing patient:** Choose Patient → search by name or ID → select the exact patient → confirm ID/name/age/sex → begin a new monitoring session.

**New patient:** Add Patient → enter name, age and sex → validate → create and persist unique ID → show confirmation → begin a monitoring session.

The current v2 naming convention is `IMM-YYYYMMDD-DEVICE8-COUNTER`, with India-local date, configured sender radio suffix, and a persistent daily counter. Example: `IMM-20261112-408DF0F0-00001`. The exact same `patient_id` is shown in the UI, attached to readings, used as the Firestore patient document key, and shown on the website. A separate UUID may be retained internally as `patient_uuid`; session and submission IDs are distinct UUIDs. Website-created IDs use registrar `57454201` with the same date/counter shape. Counter allocation must be atomic and IDs must not be reused after patient deletion.

Patient name is not a unique key. Patients with identical names remain distinct. Patient ID, monitoring session ID, device ID, capture timestamp, and submission/event ID must travel with each record. When the operator changes patient, end the old session and create a new one; queued readings keep the patient/session association stamped at capture time.

### 5.3 Recording and retry UX

- Required readings must remain stable for three seconds before the v2 flow auto-records a complete stable snapshot.
- Save all sensor groups, values, units, status/null fields, quality labels, capture times, and available waveform samples as a fixed local record.
- Display **Data recorded successfully** and show local saved status, gateway sending/sent/accepted state, and cloud-upload state in the same popup.
- **Send to Gateway** releases the saved draft to Zigbee.
- **Record Again** discards the unsent draft and restarts measurement for the same patient.
- **Sync All Saved Data** releases earlier unsent recordings.
- Gateway unavailable: explicitly state that the record is saved locally and will sync when the gateway returns; close the popup and return to the main screen without blocking subsequent checks.
- Retry work must be asynchronous/non-blocking. Preserve the original capture timestamp and patient association during retries.
- Use rounded controls, rounded popup corners, shadows/blur and bolder headings as the UI direction, while preserving clear contrast and readability.

### 5.4 Sensor processing requirements

- Repair and verify DHT22 acquisition.
- Calculate meaningful optical heart rate and estimated SpO₂ from MAX30102 samples; never show invented values when there are no usable samples.
- Keep top-left/main optical heart rate exclusively from MAX30102.
- Display ECG waveform after filtering and calculate an ECG-derived rate separately. If quality checks fail but candidate peaks exist, label the rate explicitly tentative/unreliable; if there are no peaks, do not invent a value.
- Preserve sensor quality/status labels, null values, and stale/fresh distinction.
- Keep acquisition, display and radio/cloud work independent so network delay cannot freeze the UI or stop sampling.

## 6. Zigbee transport and gateway

### 6.1 Sender

- Keep the sensor-only legacy source, latest verified Zigbee release, and independent upgrade-ready version; do not overwrite the only known-good version.
- Sender acquisition/display must remain independent of radio and receiver failure.
- Transmit patient-associated sensor measurements and waveform snapshots when forwarding is enabled and the record has been released for sending under the v2 workflow.
- Support patient registration, patient-list requests/responses, session events, record submission, and application acknowledgements with versioned message types.
- Maintain persistent pending records and retry state. Keep source copies synchronized between laptop and Pi; verify hashes. Virtual environments are platform-specific and should not be copied as if portable.
- The reported previous live path had 20–50 second delays; a millisecond-scale path is a target to measure, not an assumed result. Record actual baud rates, measured latency, packet-size limits, and acquisition limits after testing.

### 6.2 Receiver/gateway

- Runs on a separate Raspberry Pi, not on the sender.
- Receives/reassembles and validates Zigbee packets, checks patient/session context, deduplicates retries, and stores complete records durably before acknowledging gateway acceptance.
- Maintains a persistent bounded upload queue. The documented current defaults are a 10-second request timeout, 500 pending records, and 32 MiB outbox limit; confirm these against the deployed version before relying on them.
- Firebase upload is an independent worker with bounded timeouts and exponential/backoff-style retries. Cloud failure must not block Zigbee reception or the local gateway dashboard.
- Preserve measurement values, units, source identity, original capture times, null values, quality/status labels, and waveform data.
- Old queued records must not overwrite newer latest snapshots. Upload time is not capture time.
- Report pending count, upload errors, last successful upload and storage-limit conditions. Do not silently lose records.

### 6.3 Acknowledgement semantics

1. **Radio delivery:** a radio packet reached the peer; this alone does not prove the whole record was stored.
2. **Gateway acceptance:** a complete, validated record is durably saved in the gateway's local store/outbox.
3. **Cloud completion:** Firebase upload succeeded and is confirmed separately.

Stable submission IDs and idempotent handling are required so retries do not duplicate patient histories. Patient registrations must be reconciled before dependent readings are published; hold readings when context is unresolved.

## 7. Firebase data model and website

### 7.1 Current services

- Firebase project: `immortals-3`.
- Database: Cloud Firestore Native, `asia-south1`.
- Website: Next.js, deployed on Vercel at <https://immortals-dashboard.vercel.app>.
- Repository: <https://github.com/tirthankardgen-cell/Immortals-dashboard>, branch `main`.
- Gateway Admin SDK credentials remain on the gateway Pi, outside source-control folders and sender folders.
- Website Firebase web configuration is deployed through environment variables. Do not place private service-account JSON, private keys, or CLI OAuth tokens in source control.

### 7.2 Collections and records

```text
patients/{patient_id}
    patient_id, patient_code, patient_uuid
    name, age, sex
    created_at, age_recorded_at, optional updated_at/device_id

patients/{patient_id}/monitoring/latest
    patient_id, monitoring_session_id, device_id
    session_id, sequence, captured_at, received_at, uploaded_at
    sensors, waveforms, quality/status

patients/{patient_id}/readings/{submission_uuid}
    immutable patient-associated measurement snapshot/history

patients/{patient_id}/sessions/{monitoring_session_uuid}
    patient_id, monitoring_session_id, device_id
    started_at, ended_at, recording_mode

patients/{patient_id}/transcripts/{transcript_id}  # Phase 2
    patient/session/device IDs, capture times, language
    segments, transcription_model, diarization_model

registration_counters/{IMM-YYYYMMDD-57454201}
    value, patient_id
```

Store the same v2 `patient_id` consistently across sender, gateway, Firestore, and website. Use separate monitoring-session IDs and submission IDs. Store original measurement time and gateway receipt/upload times independently. Missing sensor measurements stay `null` with status/quality metadata rather than being replaced by zero or a plausible-looking estimate.

### 7.3 Website features

- Patient directory with name/ID search.
- Filters for age group (0–17, 18–35, 36–59, 60+, age not entered), sex/gender field, measurement status, and sorting/list/grid view.
- Patient detail page with name, ID, entered profile details, vital cards, units, capture timestamp, quality labels, available pulse/ECG graphs, and history.
- Live refresh as records arrive, with explicit Connected/Connecting/Cached/Offline/Unavailable connection state.
- Freshness recalculated as time passes; stale data remains visibly stale even if it is uploaded later.
- A reserved Transcripts view for Phase 2 with chronological, speaker-labelled segments.
- Registration and confirmed patient deletion are currently reported to work without sign-in under temporary public-access rules. Browser profile edits and sensor-record creation/updates are denied by Firestore rules.

### 7.4 Current access posture — important

As of 12 November 2026, the supplied upgrade plan says patient documents and subcollections are publicly readable without sign-in, website registration is public subject to validation and an atomic counter, and confirmed deletion is public. This is a temporary posture explicitly recorded in the supplied source. Patient health data is sensitive: before real-world deployment, review the access model, obtain appropriate authorization/consent, restrict access to authenticated authorized users, audit deletion, and test security rules. Do not treat public access as a production-healthcare security recommendation. The owner should explicitly approve any change to this posture.

The public website can create a patient using registrar `57454201`; sender-created IDs use the sender's eight-hex radio suffix. A deleted ID is not reused. The current site has a patient directory/detail interface and a reserved transcripts section. The supplied plan reports that no patient profiles were present at the time of its update; use preview/fictitious records only when clearly labelled as such.

## 8. Phase 2 — offline speech transcription and speaker differentiation

Phase 2 extends the same patient/session architecture to audio. It is planned, not yet fully accepted as complete.

- Capture audio from an external microphone on the sender Pi during an active patient session.
- Buffer audio locally with timestamps; run voice activity detection (VAD) and speaker processing on-device.
- **Transcription runtime/model:** `whisper.cpp` with the Whisper **base** model in a compatible local format.
- **VAD / speaker embeddings / diarization candidate:** Sherpa-ONNX with compatible local models.
- Process offline; no cloud speech API is required for recognition.
- Align text, timestamps, and speaker labels. Use labels such as `Speaker 1`/`Speaker 2` unless a speaker's identity has been enrolled and verified or manually confirmed. Do not infer that every voice belongs to the patient.
- Send finalized transcript text/metadata over Zigbee with patient ID, session ID, device ID, stable transcript/event ID, language where available, segment timestamps, speaker IDs, and uncertainty/quality markers.
- Do not send raw microphone audio over Zigbee in the current plan.
- Chunk long transcript events within validated size limits; use acknowledgement, retry, deduplication and persistent pending-event storage.
- Give vitals priority in the shared radio scheduler and ensure speech processing cannot block sensor acquisition, UI responsiveness, or vitals delivery.
- Website Transcripts view displays original capture time and chronological speaker-labelled text; delayed upload must not change the event's original time.
- Benchmark model/runtime compatibility, language accuracy, CPU/RAM use, thermal behavior, backlog and latency on the deployed Pi. Do not assume real-time performance until measured.

### Phase 2 acceptance checks

- Microphone captures usable audio on the sender.
- Whisper base transcribes locally with internet disabled.
- Sherpa-ONNX VAD/speaker models run locally and differentiate at least two speakers with aligned timestamps.
- Silence, noise, overlap, and uncertain identity do not create invented text or unsupported speaker names.
- Patient/session association survives patient changes, delayed inference, radio outages and cloud outages.
- Real transcripts travel through Zigbee, reach Firebase, and appear in the correct patient's Transcripts view.
- Chunking, validation, deduplication, acknowledgements, retry, restart recovery, storage limits, and access rules are verified.
- Sensors, UI, freshness, and vitals delivery remain functional during sustained inference and transcript radio traffic.

## 9. Safety, quality and validation

- **Not a certified medical device:** the supplied wiring guide explicitly states that the modules are not certified medical devices. Do not use the system as a substitute for clinical assessment or a validated medical instrument.
- **ECG electrical safety:** do not attach electrodes to a person while the setup has an unsafe electrical path through mains-powered instruments, USB-connected equipment, or other connected hardware. The wiring guide calls for a battery-powered, appropriately isolated arrangement. The current project notes say a clean body-connected ECG result remains unverified because an appropriate battery/isolated arrangement was unavailable; software/setup work may continue, but live human ECG validation must wait for safe isolation.
- **Never fake readings:** disconnected inputs, absent peaks, poor optical contact, sensor errors and stale data must be shown as unavailable/unreliable, not as invented values.
- **Signal interpretation:** MAX30102 SpO₂ is an estimate. MLX90614 reports infrared surface temperature. ECG-derived rate is separate from optical heart rate and can be tentative. BMP180 measures ambient pressure, not blood pressure.
- **Electrical:** use 3.3 V logic on Pi SDA/SCL; do not allow 5 V I²C pull-ups. Check the exact breakout's supply range and board revision. Raspberry Pi 5 has no built-in analog input; AD8232 OUTPUT must enter ADS1115 A0.
- **Mechanical/IP:** an IP rating cannot be claimed from design intent alone. Validate the assembled enclosure, seams, buttons, ports, cable entries, thermal behavior and cleaning procedure against the target ingress rating.
- **Patient privacy:** camera/audio/location collection must have a defined purpose, consent/notice, retention policy and access control before field deployment.
- **Data integrity:** preserve nulls, quality labels, capture timestamps, patient/session IDs and waveform gap markers. A late upload must not overwrite newer latest readings.
- **Operational testing:** test finger placement/removal, lead-off behavior, sensor disconnects, stale clearing, Zigbee OFF/ON, radio loss, gateway restart, internet loss/return, local queue recovery, browser freshness, and startup after power cycle.

## 10. Current reported status and known gaps

### Reported as implemented/deployed in supplied documents (verify against live hardware before sign-off)

- Sensor dashboard baseline on Raspberry Pi 5 with MAX30102, ECG/ADS1115, MLX90614, DHT22 and BMP180.
- Separate sender and receiver/gateway architecture with Zigbee protocol and browser dashboard.
- Sender UI layout with patient header, main vitals area/waveforms, environmental cards, and Zigbee capsule control.
- Website deployed to Vercel with patient list/detail pages, filters, registration, deletion, status/freshness display and reserved transcript view.
- Firestore rules and website build/test checks described in the supplied upgrade plan.
- Patient ID format, patient/session association model, persistent queues, acknowledgements, and v2 recording flow are specified.

### Sensor scope change — owner decision (12 November 2026)

The current wiring guide includes DHT22 and BMP180, but these are prototype/environmental modules rather than required final patient measurements. The intended final device should remove most nonessential environmental sensing, with DHT22 and BMP180 specifically marked as removal candidates. Retain only selected environmental/device-health inputs with a documented purpose. Prioritize the clinical sensor set and planned additions: ECG, optical heart rate/estimated SpO₂, selected temperature measurement, Bluetooth weight, LiDAR-based height, dedicated blood pressure, GPS, camera and microphone. This is a scope decision; physical removal, code cleanup and regression testing are still outstanding.

### Not fully verified / outstanding

- Complete end-to-end v2 patient selection → sensor capture → local fixed record → Zigbee gateway acceptance → Firebase → website workflow.
- Real-world hardware acceptance checks for all sensor values and waveforms, including stable/poor/missing signal handling.
- A clean body-connected ECG result with appropriate electrical isolation; this is explicitly unverified and must not be tested unsafely.
- Dedicated blood-pressure device integration.
- Bluetooth scale pairing and data integration.
- Validated LiDAR height-measurement geometry and repeatability.
- GPS, camera and microphone hardware selection/integration beyond the specified future speech path.
- Rugged enclosure design and verified IP rating.
- Phase 2 offline transcription and speaker differentiation on the actual sender Pi.
- Review and hardening of the currently temporary public patient-data access model before use with real patient information.

## 11. Source organization and deployment references

The supplied goal file specifies preserving prior versions and keeping the runnable sender project on the sender Pi under `/home/pi/Desktop/Immortals_Monitor` for the earlier sensor-monitor stage. Later v2 notes specify separate v2 deployment folders:

- Laptop: `Sender_v2` and `Receiver_v2` inside the existing project parent folder.
- Sender Pi v2: `/home/pi/Desktop/Immortals_Monitor_v2`.
- Receiver Pi v2: `/home/pi/Desktop/Immortals_Receiver_v2`.
- Gateway Firebase configuration: `/home/pi/.config/immortals/firebase.json` (private runtime configuration; not a source file).
- Laptop-only access notes were requested under `.work/PI_ACCESS.md`; keep credentials out of public project documentation and source control.
- Keep original versions and backups. Retain the legacy sensor-only source, the latest verified Zigbee release, and an independent next-upgrade copy.
- Synchronize source copies between laptop and the corresponding Pi and verify hashes. Do not copy platform-specific virtual environments between systems.
- The source documents refer to `Sender/project.md`, `Receiver/project.md`, `Receiver/UPGRADE_NOTES.md`, `Receiver/ZIGBEE_PROTOCOL.md`, `Sender/UI_UPDATE_NOTES.md`, `Sender_v2/README.md`, `Receiver_v2/README.md`, and `Sender_v2/ZIGBEE_PROTOCOL.md` as detailed implementation references. These files were not among the three source documents consolidated here, so their contents are not independently reproduced unless present in the supplied upgrade plan.

## 12. Implementation roadmap

### Stage A — reliable sensor monitor

- Verify Pi connectivity and each I²C address.
- Validate MAX30102 heart-rate and SpO₂ estimates with real finger placement and signal quality; remove DHT22/BMP180 from the active build if the planned sensor-retention decision is confirmed.
- Keep the filtered ECG waveform visible and ECG-derived rate separate; defer unsafe human-connected testing until isolation is appropriate.
- Deliver a self-contained `main.py` entry point and autostart in the Pi desktop session.
- Preserve original source and Zigbee code, keep the project in its agreed folder, and synchronize/hash-check laptop and Pi copies.

### Stage B — patient-based sender v2

- Add touch-first Choose Patient/Add Patient and patient cache.
- Implement stable patient ID allocation and monitoring-session context.
- Implement stable-reading detection, fixed local recording, successful-recording popup, Send to Gateway, Record Again and Sync All Saved Data.
- Keep all acquisition/display workers independent of radio/cloud workers.

### Stage C — gateway and cloud synchronization

- Extend the Zigbee protocol for patient list, registration, session events, sensor snapshots/waveforms and acknowledgements.
- Validate and persist complete records on gateway before acknowledging acceptance.
- Add independent Firebase upload worker, bounded queue, retry/backoff and duplicate protection.
- Confirm website patient profiles, readings, waveforms, stale/fresh status and deletion/access rules.

### Stage D — physical product integration

- Select and integrate Bluetooth scale, height LiDAR, dedicated blood-pressure device, GPS, camera, microphone, battery/power arrangement, display and enclosure.
- Validate measurement methods, repeatability, ergonomics, thermal management, serviceability, ingress protection and field cleaning.
- Define battery capacity/runtime and charging only after the actual hardware load is known.

### Stage E — offline speech Phase 2

- Select/test microphone; benchmark a Pi 5-compatible local-language transcription model for Bengali, Hindi and English. whisper.cpp/Whisper base and Sherpa-ONNX remain documented candidates, but the chosen model must pass real-language tests on the actual Pi 5 before being locked.
- Verify offline multilingual transcription and speaker diarization with real field noise and all sensors active.
- Add transcript event transport, gateway storage, Firebase schema and website transcript UI.

### Stage F — offline multimodal case understanding

- Capture patient/family/health-worker conversations during the active patient session, with appropriate notice/consent and patient/session context.
- Transcribe speech locally in the language spoken; retain transcript text, timestamps, language/quality markers, and conservative speaker labels.
- Let the operator photograph or capture relevant prior reports, prescriptions, lab results, or other patient-provided documents. Store the original image locally and associate it with the patient/session; avoid silently treating an image as verified clinical evidence.
- Run an offline vision-language model (VLM) to describe visible document/image contents and extract readable text/measurements where supported. Preserve the source image and flag uncertain/illegible content for human review.
- Combine the transcript, VLM output, recorded vitals, available patient context, and provenance metadata as inputs to an offline Qwen model selected and benchmarked for Raspberry Pi 5 resource limits.
- Produce a concise, clearly labelled case summary: what was reported, what the supplied images/documents appear to contain, what measurements were captured, what information is missing/uncertain, and general next-step suggestions for review by a qualified health professional.
- Treat all model output as decision-support information, not a diagnosis, prescription, or replacement for a clinician. Include uncertainty and escalation language for concerning findings; do not invent facts or infer unreadable report values.
- Persist transcripts, image references, VLM descriptions, generated summaries, model/version metadata and capture timestamps locally. Synchronize patient-linked records through the gateway over Zigbee; a separately designed network route to the gateway may be used where available. The sender must not gain direct Firebase credentials. Large original images may require a separately tested transfer path, compression, chunking, or deferred upload because Zigbee bandwidth is limited.
- Display the summary and its source evidence to the operator, with a way to review the original transcript/image and correct obvious capture or transcription errors before finalizing where feasible.

## 13. Acceptance checklist

### Field workflow and patient records
- [ ] Device boots and operates without internet at the sender.
- [ ] Touch-only patient selection, ID search and virtual keyboard work on the actual display.
- [ ] New patient requires validated name, age and sex; ID persists across restart and is never reused.
- [ ] Duplicate names remain distinct; every recording is bound to the correct patient and monitoring session.
- [ ] Stable complete readings trigger recording only after the specified stability period; poor/missing inputs are retained as null/status values.
- [ ] Record Again cancels the unsent draft; Sync All Saved Data queues older saved records.
- [ ] Popup distinguishes local save, gateway acceptance and cloud completion.

### Sensors and display
- [ ] All expected sensors are detected and values/units are correct.
- [ ] MAX30102 optical heart rate and estimated SpO₂ are plausible only when signal quality supports them.
- [ ] ECG waveform is real and filtered; ECG rate is separate and marked tentative/unreliable when appropriate.
- [ ] Final sensor inventory is approved; DHT22 and BMP180 are removed from the active build unless a documented use case justifies retention; MLX90614 retention is explicitly confirmed.
- [ ] Active UI and data schema contain only retained sensor groups, with backward compatibility for historical records from the prototype.
- [ ] No disconnected sensor produces a fabricated value; stale values are visibly stale.
- [ ] 1024 × 600 / 7-inch touchscreen layout, fullscreen controls, native buttons and startup are verified on the actual Pi.

### Wireless, gateway and cloud
- [ ] Zigbee ON forwards permitted records; OFF stops forwarding but does not stop acquisition/display.
- [ ] Sender radio loss does not block sensing or UI; unsent records persist.
- [ ] Receiver validates and durably stores complete records before gateway acknowledgement.
- [ ] Gateway internet loss does not block Zigbee reception; upload recovers automatically.
- [ ] Retries do not duplicate history or overwrite newer latest values.
- [ ] Patient list and application acknowledgements synchronize bidirectionally.
- [ ] Source copies and hashes match intended releases; startup and recovery are verified.
- [ ] Measured radio/processing latency and packet constraints are documented, not assumed.

### Website, security and Phase 2
- [ ] Website patient directory, detail pages, filters, waveforms, history and freshness states work.
- [ ] Security rules are reviewed before real patient data is exposed; access, consent, retention and deletion behavior are documented.
- [ ] LiDAR height, Bluetooth weight and BP integrations are tested against appropriate references before clinical claims.
- [ ] Camera/GPS/microphone behavior has a defined purpose and consent/privacy handling.
- [ ] Phase 2 runs fully offline, differentiates speakers conservatively, and does not impair vitals acquisition/transport.

## 14. Expanded Phase 2 — local-language conversation, document understanding and offline health-summary assistance

### 14.1 Purpose

During a health-camp visit, relevant conversation may occur between the patient, a family member, a nurse, a health worker, a doctor, or another health expert. The system is intended to capture and transcribe that conversation locally in the language actually spoken, including the project's initial target languages: **Bengali, Hindi and English**. It must be designed for offline operation; no cloud speech API should be required for the local capture, transcription, image analysis, or summary-generation path.

The operator may also use the integrated camera to capture previous medical reports, prescriptions, laboratory results, or other patient-provided documents. The goal is to combine these sources with the current visit's measured vitals to create a concise, traceable summary that helps a trained operator and qualified health professional understand the collected information.

### 14.2 Target multimodal pipeline

```mermaid
flowchart TD
    Session[Confirmed patient + monitoring session] --> Audio[Microphone: patient, family and health-worker conversation]
    Session --> Camera[Camera: prior reports, prescriptions and test results]
    Session --> Vitals[Measured vitals + sensor quality/status]
    Audio --> STT[Offline local-language speech-to-text]
    STT --> Transcript[Timestamped transcript + cautious speaker labels]
    Camera --> ImageStore[Original image stored locally and linked to patient/session]
    ImageStore --> VLM[Offline vision-language model: describe image and readable content]
    Transcript --> Context[Multimodal case context]
    VLM --> Context
    Vitals --> Context
    Context --> Qwen[Offline Qwen model, selected and benchmarked for Pi 5]
    Qwen --> Summary[Concise summary + cautious general next-step suggestions + uncertainty flags]
    Transcript --> LocalStore[Encrypted/restricted local patient record and persistent outbox]
    ImageStore --> LocalStore
    VLM --> LocalStore
    Vitals --> LocalStore
    Summary --> LocalStore
    LocalStore --> Gateway[Gateway via Zigbee; optional separately configured route to gateway]
    Gateway --> Firebase[Gateway uploads to Firebase when internet is available]
    Firebase --> Website[Patient page: vitals, transcript, document summary and status]
```

### 14.3 Processing responsibilities

1. **Audio capture and transcription:** capture audio only for the active patient session and transcribe it on the sender using an offline model. Select a model based on measured Bengali, Hindi and English accuracy, memory use, latency, licensing and sustained operation on Raspberry Pi 5. Existing project notes mention whisper.cpp with Whisper base and Sherpa-ONNX for voice activity detection/speaker embeddings as candidates; these are not proof that the selected stack meets multilingual requirements. Benchmark with natural speech, local accents, background noise, code-switching and multiple speakers.
2. **Speaker differentiation:** use session-scoped labels such as `Speaker 1` and `Speaker 2` unless identity has been confirmed. Do not automatically infer that a speaker is the patient or a doctor. Mark overlapping, unclear or low-confidence speech as uncertain.
3. **Camera and prior records:** capture a document image only with the operator's action and appropriate permission. Keep original images, capture time, patient ID and session ID. A VLM may describe the page and extract visible text, but must distinguish visible evidence from interpretation and flag blur, glare, cropping, low confidence or unreadable text.
4. **Vision-language model (VLM):** process captured report images locally where practical. Its output should describe what is visibly present and provide extracted text/fields with confidence or uncertainty markers when supported. It must not convert a visual impression into a confirmed diagnosis.
5. **Offline Qwen model:** pass the available transcript, VLM-produced description/extracted text, current measured vitals, units, timestamps, signal-quality states, and relevant patient context to a locally runnable Qwen model. The exact Qwen model/quantization is an open engineering choice until tested for RAM, CPU, thermal performance, response time and output quality on the actual Pi 5.
6. **Generated summary:** produce a short structured result with (a) reported concerns and history, (b) what the captured documents visibly state, (c) the current measured vitals and their quality, (d) missing/contradictory/uncertain information, and (e) cautious general suggestions for follow-up or clinician review. Every statement should be traceable to a transcript segment, image/document extraction or measured value where possible.
7. **Local persistence and sync:** save the transcript, image reference/original image, VLM output, summary, model identifiers, capture timestamps, patient ID and monitoring-session ID. Maintain a durable outbox and retry/acknowledgement handling. The receiver/gateway remains the only Firebase client under the current architecture.

### 14.4 Safety, privacy and reliability requirements

- Obtain appropriate consent/notice before recording conversations or photographing reports; provide a clear recording indicator and a way to stop capture.
- Collect only data relevant to the patient's care, restrict access, document retention/deletion policy, and protect locally stored health information and credentials.
- Never fabricate a transcript, document value, vital sign, speaker identity, or clinical fact. Missing values remain missing; poor-quality sensor values retain their quality label.
- Model-generated suggestions are **informational decision support only**. They must not be presented as a diagnosis, prescription, or proof that a person is healthy. A qualified clinician must assess clinical decisions; urgent or potentially dangerous findings require a clearly defined escalation policy approved by the project’s clinical adviser.
- Include model name/version, prompt/schema version where appropriate, and source references in stored outputs so results can be audited and reproduced.
- Validate that speech/VLM/Qwen processing cannot freeze sensor acquisition, touchscreen response, local recording or Zigbee delivery. Use bounded queues, independent workers, explicit backlog/error states and thermal/resource monitoring.
- Avoid sending raw audio by Zigbee unless separately justified and tested; the initial design sends transcript text and metadata. Image transfer is a separate bandwidth/size decision: Zigbee payload limits must be measured before attempting full-resolution image transfer. Where needed, queue images for a suitable gateway route while still syncing text/metadata over Zigbee.
- A network connection from the sender, if added later, must still route records to the gateway under a defined authenticated protocol; it does not grant the sender direct Firebase access under the current architecture.

### 14.5 Data and website additions

The patient/session record should be able to reference:

- `transcripts/{transcript_id}`: transcript segments, language, session-scoped speaker labels, capture start/end times, transcription model/version and quality/uncertainty markers.
- `documents/{document_id}` or an equivalent approved storage record: image/storage reference, capture time, document type if known, extraction text, VLM description, confidence/legibility status and model/version.
- `summaries/{summary_id}` or an equivalent approved record: summary text, general suggestions, source transcript/document/reading references, generation time, Qwen model/version, uncertainty flags and review status.

These are proposed logical records, not a claim that the current Firestore schema or website already implements them. The final schema must decide whether image binaries live in Firebase Storage or another approved object store; Firestore should hold metadata and references rather than unbounded image blobs. Access rules must cover transcripts, image references, summaries and originals consistently with patient records. The website's existing Transcripts option can be extended; document/image review and summaries require new UI work.

### 14.6 December 2026 delivery target

**Target completion: December 2026.** This is the project's intended deadline, not a claim that all hardware, models, clinical validation or acceptance tests are already complete. Prioritize a working, testable end-to-end vertical slice and record what remains unverified.

Suggested milestone sequence:

1. **Milestone 1 — freeze scope and interfaces:** confirm supported languages, sensor list, image/document workflow, patient/session schema, transfer rules, and model evaluation criteria.
2. **Milestone 2 — reliable core device:** complete patient selection/registration, sensor readings, local records, Zigbee sender/gateway acknowledgements, offline outboxes and recovery.
3. **Milestone 3 — multilingual speech:** benchmark and select the local transcription model; verify Bengali, Hindi and English with representative speakers/noise and store patient-linked transcripts.
4. **Milestone 4 — camera and VLM:** capture reports locally, preserve originals, and verify readable-text extraction and uncertainty handling on representative document images.
5. **Milestone 5 — Qwen summary:** run the chosen quantized offline Qwen model on the Pi 5; produce evidence-linked summaries and general suggestions, with clear uncertainty and no fabricated facts.
6. **Milestone 6 — complete sync and website:** transmit/queue transcripts and metadata, decide/test the image-transfer path, upload through the gateway to Firebase, and expose patient-linked transcripts/document summaries on the website.
7. **Milestone 7 — field acceptance:** run a full offline health-camp simulation; test power/network loss, restart recovery, queue limits, privacy/consent, multilingual speech, document readability, thermal limits and all sensor-quality states. Obtain clinical review of safety wording before any real-world deployment.

### 14.7 Acceptance checklist for the expanded pipeline

- [ ] Bengali, Hindi and English speech are tested locally with internet disabled; performance limitations are documented by language and noise condition.
- [ ] Transcripts are linked to the correct patient and session, include timestamps, and use conservative speaker labels.
- [ ] Recording consent/notice, recording indicator and stop controls are present.
- [ ] Camera captures are associated with the correct patient/session and original images are retained without silent replacement.
- [ ] The VLM distinguishes extracted visible content from interpretation and flags unreadable/uncertain documents.
- [ ] The offline Qwen model runs on the target Pi 5 with measured RAM, CPU, latency and thermal behavior.
- [ ] Generated summaries cite or reference their transcript/document/vital sources and retain uncertainty/missing-data information.
- [ ] The model does not fabricate measurements, report values, speech, identities or diagnoses in the defined test set.
- [ ] Transcripts, document metadata, VLM results and summaries persist locally and recover after restart.
- [ ] Gateway delivery, acknowledgements, deduplication and cloud upload work under network/radio interruption.
- [ ] A tested transport plan exists for image files; large images do not block vital-sign transport.
- [ ] The website presents patient-linked transcripts and summaries with capture times, source references and stale/pending/error states.
- [ ] Clinical, privacy, security and field-use limitations are reviewed before deployment with real patients.

## 15. Open decisions

1. Custom ESP32 Bluetooth scale protocol, four-load-cell bridge/ADC, safe platform capacity and unit/calibration handling, under the 16 November 2026 owner design.
2. Exact LiDAR model and telescopic-stand fixture/reference method, including stand locks, platform reference and repeatable patient geometry.
3. Exact blood-pressure monitor and interface (Bluetooth, USB, serial or other supported data protocol).
4. GPS module/source with realistic indoor reception limits, autofocus camera and Pi Zero CSI cable, two INMP441 stereo capture/driver arrangement, touchscreen model and intended use/storage rules.
5. Three battery domains, main 3S versus 4S decision, charging/power-path architecture, dock connector ratings, complete ECG isolation and measured runtime. Scale target is eight hours. Main-case and tablet runtime targets remain to be agreed.
6. Target IP rating and test method; enclosure materials, seals, ports, strap/handle and cleaning requirements.
7. Required record fields, waveform sampling/downsampling policy, cloud update frequency, retention and queue-size limits.
8. Final patient-data access policy and authentication/authorization model before real health data is used.
9. Supported languages and measured accuracy targets for offline speech (the project currently names Bengali, Hindi and English as desired languages in project discussion; exact model selection/performance remains to be validated on Pi 5).
10. Whether weight/height/BP/GPS/camera are part of the first field release or staged after the current documented sensor baseline.

---

> **Document consolidation — 17 November 2026:** This current master was moved
> into `docs/planning` without changing its requirements. Shared documents are
> indexed in [the documentation hub](../README.md). The
> [BOM index](../hardware/bom/README.md) identifies the latest supplied editable
> workbook, the later automatic-inflation print checklist, and the earlier
> verified costing files. Those deliverables differ; earlier totals remain dated
> history. All changes must be recorded in
> [development.md](../development/development.md).

# Appendices — supplied source documents

The following appendices preserve the full text of the two supplied Markdown source files so the consolidated document retains their dated requirements, acceptance criteria, deployment notes, schema details and configuration references. Where earlier notes conflict with later updates, use the dated/superseding notes and the main status distinctions above; do not treat an earlier stage restriction as current if a later section explicitly supersedes it.


## Appendix A — Original `GOAL_REQUIREMENTS.md`

```markdown
# Pi desktop sensor monitor

User requirements, including follow-up instructions:

## Patient-recording v2 stage — 12 November 2026

- Preserve existing versions. Create `Sender_v2` and `Receiver_v2` inside the
  current laptop parent folder and separate v2 folders on the correct Pis.
- Design for health checkups in remote places: sender has no internet/Firebase
  connection; only the gateway has Firebase access. Bidirectional Zigbee carries
  patient lists, recordings and application acknowledgements.
- Touch-only Choose/Add Patient flow with proper name/ID search and a virtual
  keyboard. Automatically allocate a persistent `IMM-YYYYMMDD-DEVICE8-COUNTER`
  patient ID; use that same ID in Firebase and on the website.
- Check vitals, then Record Vitals. Save a fixed record of all sensor groups and
  available waveforms, then show a successful-recording popup with Send to Gateway.
- Keep sending/sent/cloud status inside the same popup. If gateway delivery fails,
  confirm that the record is saved on the device and will sync when the gateway
  returns, then close and return to the main screen. Retry without blocking checks.
- Give the UI rounded controls and a modern appearance; verify fullscreen controls
  on the real display. Preserve unavailable readings and original quality labels.
- Update project docs with this purpose, architecture, naming, flow and recovery.
- Latest flow: auto-record stable complete readings; Record Again discards the
  unsent draft and restarts that patient; Sync All Saved Data releases earlier
  recordings. Rounded popup corners/shadows/blur and bolder headings are required.
- Sender shows gateway status; only the gateway has a Firebase connection.

- Read the local old code and wiring guide and the updated `/home/pi/Downloads/pi5_sensor_monitor.py`.
- Repair DHT22 and compute meaningful heart rate (bpm) and estimated blood oxygen saturation (SpO2 percent) from MAX30102 samples.
- Display all sensors on the connected 1024 x 600 HDMI display using a dashboard with numbers, meters and live graphs.
- Deliver one self-contained Python entry point named `main.py`; running it starts the entire monitor.
- Start the monitor automatically in the Pi desktop session.
- Keep the runnable project only at `/home/pi/Desktop/Immortals_Monitor`.
- Preserve all Zigbee code and put it inside that project folder. Zigbee transmission integration is a later task.
- Preserve `pi5_sensor_monitor.py` and remove unneeded old project files after a verified backup.
- Ask the user for a finger placement test when ready.
- Latest update: the user has now connected the body pads and ECG module. Enable and verify the live ECG waveform after confirming Pi connectivity; the earlier deferral for missing pads is superseded. Do not manufacture a heartbeat from disconnected input.
- Include one `project.md` with components, pin mapping, environment setup, current architecture, and the planned sender Pi / Zigbee / receiver Pi / laptop architecture.
- Keep matching project source copies on the laptop and Pi and verify their hashes. Virtual environments remain platform-specific.
- Keep top-left heart rate exclusively from MAX30102; show ECG-derived bpm separately in the lower ECG panel.
- Latest scope limit: the user has no battery/isolated power arrangement and asks to finish everything possible with the current adapter-powered setup. A clean body-connected ECG result remains unverified and is deferred; do not require an unavailable battery to finish the authorized software/setup work.
- Latest display correction: keep ECG enabled and display its calculated bpm separately for comparison with MAX30102. Show a tentative detected-peak rate with an explicit unreliable marker when quality checks fail; do not represent it as a validated heart rate or invent a value when no peaks exist. Keep the actual filtered waveform visible and document that battery/isolated testing comes later.
- Add one touchscreen Zigbee ON/OFF button (push toggle, not slider). Only the UI is implemented now. Document future ON forwarding sensor data while the local screen continues, and OFF stopping forwarding without stopping acquisition/display. No Zigbee backend or sending is authorized in this stage.
- Give the Zigbee button a modern capsule shape and matching rounded cards. Verify that clicks change both ON/OFF text and colour and check for UI bugs on the Pi display.
- Remove the ECG footer control and place the Zigbee capsule at the far right. User confirmed the final native button works with both Pi mouse and touchscreen.

The active goal includes these additions. The goal-status API supports status changes only; this file records the expanded acceptance criteria.

## Zigbee sender stage - 11 November 2026 (supersedes UI-only restriction above)

- Connect to the current sender Pi over SSH, inspect deployed project and old working senders.
- Integrate Zigbee into the self-contained sensor monitor and send all displayed sensor measurements and waveform snapshots.
- Wire the existing ON/OFF capsule to the backend; preserve independent sensor acquisition and local display during radio delays or failures.
- Keep the old sender sources and synchronize the delivered project source with the laptop.
- Document SSH credentials in a laptop-local access note as explicitly requested by the owner (`.work/PI_ACCESS.md`).
- The owner confirmed the receiver is off/unavailable and requested completion of sender testing only.
- Prepare the new receiver on the laptop only after the owner provides the old receiver code. It belongs on another Pi, not this sender Pi; it is outside this stage.

## Receiver integration stage - supersedes the earlier receiver deferral

- Owner supplied SSH `pi@immortals-recv.local` and authorized updating its receiver code and end-to-end testing.
- Record receiver SSH credentials and connection information in the laptop access document.
- Inspect and preserve original receiver code, deploy the compatible receiver to that Pi, and keep its source on the laptop.
- Verify actual RF reception of all sensor values and waveforms, browser display, finger placement/removal, sender OFF/ON, freshness, recovery and startup.
- Receiver runs on the separate Pi only. Sender acquisition and display must remain independent of radio and receiver failures.

## Live transport and source organization stage - 11 November 2026

- Keep laptop source in Sender and Receiver, synchronized/hash-verified to the respective Pi 5 projects.
- Reduce the reported 20-50 second delay to a measured millisecond-scale live path, preserving acquisition/display independence.
- Retain three sender versions: actual old sensor-only source, latest verified Zigbee release, and an independent runnable copy ready for the next UI/features upgrade.
- Document version purpose, active startup, synchronization, baud settings, timing changes, actual hardware measurements and sensor acquisition limits.
- Inspect/change and verify radio baud settings through the Pis; the owner should not need XCTU or a firmware change.
- Verify real finger data and both waveforms, ON/OFF, stale clearing, recovery and browser display. The owner placed a finger and authorized removal after the completed capture.
- UI/features redesign is the next stage. Only refresh/freshness behavior is part of this stage.

## Sender screen UI stage — 11 November 2026

- Update laptop Sender source and deploy the matching code to the sender Pi.
- Show Patient Information, Patient Vitals, and Environmental Data on its screen.
- Latest layout direction: patient information is a top header; vitals use the
  main and largest area; environmental data uses small cards along the right edge.
- Use clearly marked placeholder patient name and ID until registration exists.
- Put measured MLX90614 surface/body temperature in vitals, alongside optical
  heart rate, estimated SpO2, and the pulse/ECG displays.
- Keep room temperature, relative humidity, air pressure, and board temperature
  in the compact environmental section.
- Preserve independent sensing/forwarding/display, real null/quality handling,
  and working native screen controls; verify the deployed display and source sync.
```


## Appendix B — Original `PROJECT_UPGRADE_PLAN.md`

```markdown
# Immortals — Two-Phase Project Upgrade Plan

**Temporary access update — 12 November 2026:** Patient documents and their
subcollections are publicly readable without sign-in at the owner's request.
New patient registration is also available without sign-in, using the sender v2
ID format with website registrar `57454201` and an atomic daily counter. Existing
profiles cannot be edited by browser clients; sensor creation/edits and access-list
reads remain blocked. A confirmed Delete patient action removes the profile and
its cloud monitoring records, history, sessions, and transcripts. Authentication
is optional until private access is restored.

**Website layout and sharing update:** The desktop workspace fits one viewport,
with height-aware directory pagination and left navigation for registration and
patient sections. Page titles, descriptions, and a branded 1200×630 sharing image
support WhatsApp and other Open Graph/Twitter previews.

**Date:** 12 November 2026  
**Status:** Website deployed to Vercel. Patient viewing, registration, and confirmed
deletion are temporarily public without sign-in. Sender/gateway v2 implementation
is documented below; complete hardware acceptance checks and Phase 2 speech
processing remain outstanding.

## Project objective

### Sender/gateway v2 update — 12 November 2026

The device is intended for health checkups in remote places. The sender works
without internet and has no Firebase access. It sends patient records over
Zigbee to a separate gateway; only the gateway connects to Firebase using its
internet link. Patient-list synchronization and upload acknowledgements return
to the sender over Zigbee. The website reads the resulting Firebase records.

The confirmed v2 flow replaces automatic live forwarding for this release:
**Choose/Add Patient → confirm → check vitals → automatically record stable complete
readings → “Data recorded successfully” popup → Send to Gateway**. The popup stays open for sending,
gateway acceptance and Firebase completion. Recording saves all sensor groups,
units/status/null values and available waveforms as a fixed local draft. Only
Send releases it to the radio. If the gateway is unavailable, show that the
record is saved on the device and will synchronize automatically, then close
the popup and return to the main screen. Checkups and acquisition continue
independently of radio/cloud failures. Touch screens use a virtual keyboard,
patient-name/ID search and rounded controls.
All required readings must remain stable for three seconds before auto-recording;
poor/missing signals keep acquisition running. Record Again cancels an unsent
draft and restarts that patient. Sync All Saved Data releases prior unsent
recordings. The final main screen has organized controls/status, bolder headings,
soft shadows and rounded popups over a blurred background.

The exact same **IMM-YYYYMMDD-DEVICE8-COUNTER** `patient_id` is displayed on the
sender, carried in readings, used as the Firestore patient document key and
shown on the website; for example `IMM-20261112-408DF0F0-00001`. The date is India
time; DEVICE8 is the configured sender's radio suffix; the daily counter survives
restart. A separate `patient_uuid` remains available internally. This supersedes
the earlier proposal to use UUIDs as the primary/displayed patient ID. Duplicate
names remain distinct. Submission and monitoring-session IDs are separate UUIDs.

The laptop parent folder is unchanged. New releases are in `Sender_v2` and
`Receiver_v2`; deployed folders are `/home/pi/Desktop/Immortals_Monitor_v2` and
`/home/pi/Desktop/Immortals_Receiver_v2`. Original versions are preserved. See
[sender v2](Sender_v2/README.md), [gateway v2](Receiver_v2/README.md), and
[patient protocol](Sender_v2/ZIGBEE_PROTOCOL.md).

Persistent outboxes retain patient association and original capture times.
Gateway acceptance means durable local storage; Firebase completion is a
separate acknowledgement. Uploads run independently with bounded timeouts and
backoff. Retry IDs prevent duplicate histories and delayed records cannot
replace newer latest readings. Saved values remain labelled as recordings;
upload time does not make an old reading live. Phase 2 speech remains future work.

Upgrade Immortals into a patient-based vitals and speech monitoring platform.
The first Raspberry Pi is the sender and sensor device. The second Raspberry Pi
is the receiving gateway. Both phases use the path **sender Pi → Zigbee → receiver
Pi/gateway → Firebase → website/dashboard**.

**Phase 1** adds the sender UI flow for choosing an existing patient or creating
a new patient with name, age, and sex before scanning vitals. Patient-associated
readings are saved in Firebase. The website lists patients, and clicking a name
opens that patient's profile, details, vitals, and monitoring status.

**Phase 2** adds an external microphone to the sender Pi, offline transcription
using **whisper.cpp with the Whisper base model**, and local speaker differentiation
using **Sherpa-ONNX**. Speaker-labelled transcripts follow the same Zigbee and
Firebase path and appear as a selectable option on the patient's website page.

## Two-phase roadmap

| Phase | Target | Scope status | Completion condition |
|---|---|---|---|
| **Phase 1 — Patient UI, Firebase gateway, and website** | Select/create a patient on the sender, scan vitals, deliver patient-associated readings through Zigbee to Firebase, and display patient lists and details on the website. | Defined; all patient-selection and creation UI changes belong to Phase 1. | The patient-to-vitals-to-website flow passes the Phase 1 acceptance checks. |
| **Phase 2 — Offline speech and speaker differentiation** | Capture external-microphone audio on the sender, transcribe with whisper.cpp base, differentiate speakers with Sherpa-ONNX, and deliver labelled transcripts through Zigbee and Firebase to the website. | Defined; model packaging and performance need hardware validation. | The offline speech-to-patient-transcript flow passes the Phase 2 acceptance checks. |

The phases in this document define the full upgrade scope. The website portion
has been delivered; the existing sensor and live Zigbee releases remain the
starting point for the remaining sender and gateway work.

## Existing project baseline

The current source and release notes describe:

- **Sender Pi:** sensor acquisition, local touchscreen dashboard, and Zigbee
  transmission controlled by the existing ON/OFF button.
- **Receiver Pi:** Zigbee reception, packet validation, live readings, and a
  local browser dashboard.
- **Current measurements:** MAX30102 optical heart rate and estimated SpO2;
  ECG waveform and separately labelled ECG rates; MLX90614 surface and ambient
  temperature; DHT22 room temperature and humidity; BMP180 temperature and pressure.
- **Current transport:** a live Zigbee protocol with independent acquisition,
  radio, and display workers, plus explicit freshness and signal-quality handling.

See [Sender project](Sender/project.md), [Receiver project](Receiver/project.md),
[current release notes](Receiver/UPGRADE_NOTES.md), and
[current Zigbee protocol](Receiver/ZIGBEE_PROTOCOL.md) for the existing implementation.

## Phase 1 — Patient UI, Firebase gateway, and website

**Website delivery — 12 November 2026:** The standalone project is in `Website`
and is published at <https://immortals-dashboard.vercel.app> from
<https://github.com/tirthankardgen-cell/Immortals-dashboard>. It includes patient
lists, patient details, prominent vitals/waveforms, compact environmental cards,
history, and a reserved Transcripts view. Firebase Authentication and restricted
Firestore reads are configured; all browser writes are denied. The final build,
seven measurement-model tests, six rule tests, and authorized production reads
passed. The database currently has no patient profiles. Fictional records are
available only in the explicitly labelled `?view=preview` workspace. This does
not complete sender patient registration or the receiving gateway's uploads.

**Current UI increment — 11 November 2026:** The sender screen now has a patient
information header, a large vitals area with both waveforms, and compact
environmental cards along the right edge. It uses Demo Patient / DEMO-001
placeholders. The MLX90614 surface measurement appears under patient vitals as
body temperature, explicitly labelled infrared surface. This deployed layout
increment precedes the patient-selection/registration and Firebase work below.
See [sender UI release notes](Sender/UI_UPDATE_NOTES.md) for verification.

### 1. Target architecture

```mermaid
flowchart TD
    Start[Sender Pi: first screen] --> Choice{Choose patient or add patient}
    Choice -->|Existing patient| Existing[Select patient and verify patient ID]
    Choice -->|New patient| Form[Add patient: name, age, sex]
    Form --> Create[Create and persist unique patient ID]
    Existing --> Session[Confirm patient and start monitoring session]
    Create --> Session
    Session --> Vitals[Scan vitals on sender Pi]
    Vitals --> Local[Sender local dashboard]
    Vitals -->|Readings with patient and session IDs| Zigbee[Zigbee wireless link]
    Create -->|Patient registration event| Zigbee
    Session -->|Patient session event| Zigbee
    Zigbee --> Gateway[Second Pi: receiving gateway]
    Gateway --> Upload[Independent Firebase upload worker]
    Upload --> Database[Firebase database]
    Database --> List[Website: patient list]
    List -->|Click patient name| Detail[Patient details, vitals, and monitoring status]
```

The second Pi needs an internet connection to reach Firebase. Sensor data still
travels between the Pis over Zigbee. The website reads the cloud database, so a
remote viewer does not need a direct connection to the receiver's local network.

**Selected services:** Cloud Firestore for patient profiles and readings,
Firebase Authentication for website access, and Vercel for the Next.js website.
The Firebase web configuration is set in Vercel's production, preview, and
development environments. Gateway Admin SDK credentials stay on the second Pi.

### 2. Sender patient UI flow

The first screen on the sender must offer **Choose Patient** and **Add Patient**.
A patient monitoring session and its vitals recording/transmission start only
after a valid patient has been selected or created and confirmed. Phase 2 audio
capture follows the same gate. Patient-list and other control exchanges can run
before selection.

**Existing patient flow:**

1. Open **Choose Patient** and select a registered patient, using the specific
   patient ID to distinguish records with similar or identical names.
2. Display the patient's ID, name, age, and sex for confirmation.
3. Continue to the vitals dashboard and begin a monitoring session for that ID.

**New patient flow:**

1. Open **Add Patient** when the patient is not already registered.
2. Enter the required fields: **name, age, and sex**. Validate the form before saving.
3. Create a stable, unique patient ID and persist the patient record on the sender.
4. Display the created patient and ID, then continue to the vitals dashboard.
5. Send the patient registration, session context, and vitals over Zigbee to the
   gateway. The gateway saves them under that patient ID in Firebase.

The monitoring screen must always show the active patient's name and ID. A
**Change Patient / End Session** action ends the current association and returns
to the patient selector. Background sensor workers can continue operating, but
unassigned samples must not be saved as another patient's measurements.

The sender keeps a persistent local patient cache. Synchronize the available
patient list and registration results through a bidirectional Zigbee control
exchange with the gateway, which accesses Firebase. This avoids requiring a
direct Firebase connection on the sender. An uncached patient ID must be resolved
or the patient explicitly registered before starting that patient's session.
During a gateway/cloud outage, known cached patients and locally created patients
can be used with a clearly displayed pending-sync state.

### 3. Receiving gateway responsibilities

The receiver will extend its existing application to:

1. Receive and reconstruct Zigbee packets, extending the current validated
   protocol for patient registration, patient-list requests, and session events.
2. Validate the explicit patient and monitoring-session context carried by the
   sender, and reconcile patient registrations before publishing their readings.
3. Preserve measurement values, units, capture times, source identity, null values,
   signal-quality labels, and available pulse/ECG waveform data.
4. Save the patient-associated readings to Firebase through a separate worker.
5. Track cloud connection, pending uploads, failures, and the last successful upload.

Cloud operations must remain independent of Zigbee reception and the local
dashboard. Use bounded timeouts, retries with backoff, and a bounded persistent
upload buffer for temporary internet outages. Define the buffer limit and expose
unsaved-data counts if that limit is reached.

Use versioned message types and application acknowledgements for registration
and control exchanges; radio delivery alone does not confirm that a patient record
has been accepted. Hold dependent readings if their registration/context has not
yet been validated, and retry registration idempotently.

Buffered records retain their original patient association, monitoring session,
and capture time. Uploading an old reading after reconnection must not replace a
newer latest reading or make old data appear live.

### 4. Unique patient IDs and monitoring sessions

- Every patient receives a stable, globally unique `patient_id`. Use a UUID-based
  ID that can be generated offline; a shorter display code can be added separately.
- Patient names are display fields; the database uses the ID as the record key.
  Two patients with the same name must remain separate.
- The sender's Phase 1 UI creates/selects the patient and binds the active sender
  device to a separate `monitoring_session_id` before scanning begins.
- Every reading carries `patient_id`, `monitoring_session_id`, device ID, and
  capture time. The Zigbee radio address and transport session identify hardware
  and delivery; neither replaces the patient ID or monitoring-session ID.
- When a patient changes, end the previous monitoring session and begin a new one.
  Stamp the context at capture time and keep it immutable for queued readings.
  Late packets must not be assigned using only the device's current patient.
- Ambiguous or unassigned data must be held separately until its association is
  resolved; a patient name alone is never sufficient for assignment.

The current receiver accepts one configured sender. Phase 1 can list multiple
registered patients and show their stored details, while live monitoring follows
the active device assignment. Simultaneous reception from multiple sender Pis
requires additional requirements and implementation.

### 5. Proposed Firebase data structure

```text
patients/{patient_id}
    patient_id
    name
    age
    age_recorded_at
    sex
    profile_details
    created_at
    updated_at

patients/{patient_id}/monitoring/latest
    patient_id
    monitoring_session_id
    device_id
    session_id
    sequence
    captured_at
    received_at
    uploaded_at
    sensors
    waveforms

patients/{patient_id}/readings/{reading_id}
    timestamped patient-associated measurement record

patients/{patient_id}/sessions/{monitoring_session_id}
    device_id
    patient_id
    started_at
    ended_at

patients/{patient_id}/transcripts/{transcript_id}    # Phase 2
    patient_id
    monitoring_session_id
    device_id
    started_at
    ended_at
    received_at
    uploaded_at
    language
    segments
    transcription_model
    diarization_model
```

The required Phase 1 registration fields are **name, age, and sex**, alongside
the generated patient ID. Contact information, ward/bed, admission details, and
assigned clinician are optional future profile fields. Record when age was entered
so a saved age is not presented as a newly calculated value years later.

`sensors` preserves each sensor's values, units, status, source age, and quality
information. `waveforms` preserves available pulse and ECG samples with their time
information and clear/gap markers. Missing measurements stay null.

Use a repeatable reading key based on device, monitoring session, transport
session, sequence, and capture time so upload retries do not create duplicate
records. Keep the latest reading separate from history so the website can load
a patient quickly. Define cloud
update frequency, historical sampling, waveform storage, and retention before
implementation; cloud writes should not run synchronously for every RF fragment.

### 6. Website pages and behavior

| Page or workflow | Required behavior |
|---|---|
| Sign-in | Optional during temporary public access; retain authentication for future private access. |
| Patient registration visibility | Display patients created on the sender once the gateway synchronizes their profiles into Firebase. |
| Patient list | Show all registered patients without sign-in, including patient name, unique ID, monitoring status, and last measurement time. |
| New patient | Save a validated name/age/sex profile with the sender v2 ID format and an atomic website registration counter. |
| Delete patient | Confirm the selected patient's name/ID, then delete its profile and cloud monitoring, reading, session, and transcript documents. |
| Patient detail | Open when a patient name is clicked; show that patient's name, ID, entered profile details, vitals, and available waveforms. |
| Live updates | Refresh the selected patient's readings as new data reaches Firebase. |
| Unavailable or stale data | Clearly show missing, outdated, or offline readings and the time of the last measurement. |
| Transcripts option | Reserve a visible patient-page option/tab for Phase 2 speech transcripts; show an empty state until transcript data is available. |

The patient detail page will include optical heart rate, estimated SpO2,
temperature readings with their sensor/source labels, room humidity, pressure,
and available pulse/ECG graphs. Qualified ECG heart rate and provisional ECG
candidate rate must remain separate; unreliable estimates retain their label.

Freshness must be recalculated as time passes, even when Firebase sends no new
update. A stopped sender or disconnected gateway must cause the website to mark
the last reading stale. Upload time is not measurement time, and an internet
connection must not hide the age of the original sensor data.

### 7. Access and configuration

Keep Firebase gateway credentials on the receiver Pi, outside website assets and
source-control files. Current rules allow public patient reads, validated website
registration, and patient deletion. Authentication is optional for now; restore
authorized patient access when private mode is requested. The gateway writes validated sender
registrations, session records, and measurements. Any additional website profile
editing must follow the same patient-ID and session rules.

### 8. Implementation sequence

1. Select the Firebase project, database, access roles, upload frequency, and
   retention policies.
2. Build the sender's Choose Patient / Add Patient first screen, name-age-sex form,
   unique-ID creation, patient cache, and monitoring-session flow.
3. Extend sender and receiver together for patient-context messages, registration,
   list synchronization, and application acknowledgements while preserving vitals.
4. Add the independent Firebase upload worker to the receiver.
5. Build the website patient list, detail page, and reserved transcripts option.
6. Verify patient-specific storage, duplicate prevention, buffering, patient
   changes, and recovery with real Zigbee data.
7. Deploy the verified Phase 1 UI and gateway/website update to their respective
   devices and hosting environment.

### 9. Phase 1 acceptance criteria

- [ ] The sender starts with Choose Patient / Add Patient before patient scanning.
- [ ] Selecting an existing patient by its specific ID opens monitoring for that
      patient after confirmation.
- [ ] Add Patient requires name, age, and sex; successful creation persists a
      unique ID and allows that patient's vitals session to start.
- [ ] The monitoring screen shows the active patient; ending/changing patient
      creates a new session without misassigning pending or late readings.
- [ ] Sender patient-list/cache synchronization, pending registrations, and
      control acknowledgements work through the gateway.
- [ ] The second Pi receives real sensor data over the existing Zigbee link.
- [ ] Each registered patient has a unique ID and a separately stored profile.
- [ ] Measurements are saved under the patient assigned to the source device.
- [ ] Patients with identical names remain distinct; reassignment does not move
      old records or pending uploads to another patient.
- [ ] The website lists patients and clicking a name opens the correct profile.
- [ ] The patient page includes the reserved transcripts option for Phase 2.
- [ ] The detail page shows entered patient details, vitals, units, timestamps,
      signal-quality labels, and available pulse/ECG graphs.
- [ ] New readings update the website; missing and stale readings are displayed
      correctly, including when the sender is OFF or the gateway loses internet.
- [ ] Internet loss does not block reception, sender acquisition, or local display;
      buffered uploads recover within the defined storage policy.
- [ ] Upload retries do not duplicate records or overwrite newer latest data.
- [ ] Receiver restart restores the cloud worker and pending uploads without
      presenting saved old readings as live.
- [ ] Temporary public reads, validated registration, and deletion work without
      sign-in; browser measurement/profile edits and access-list operations are denied.

**Phase 1 deliverable:** A sender UI that selects or creates a patient before
scanning vitals, plus delivery through Zigbee to the receiver gateway and Firebase,
and a website with patient lists, individual profiles, and patient-specific vitals.

## Phase 2 — Offline speech and speaker differentiation

### 1. Target and selected software

Connect an external microphone to the **sender Pi**, capture speech during an
active patient monitoring session, transcribe it locally, and differentiate the
speakers. Deliver the resulting speaker-labelled text to the receiver gateway over
Zigbee, save it in Firebase under the same patient ID and monitoring-session ID,
and make it available through the website's **Transcripts** option.

| Component | Planned choice | Responsibility |
|---|---|---|
| External microphone | Pi-compatible external microphone; exact device to be selected/tested. | Capture speech on the sender Pi. |
| Offline transcription runtime | **whisper.cpp** on sender ARM64 Linux. | Run transcription locally without a cloud speech API. |
| Transcription model | **Whisper base** model in whisper.cpp-compatible format. | Convert captured speech to text. |
| Local speech/speaker toolkit | **Sherpa-ONNX** with compatible VAD and speaker models. | Detect voice activity, produce speaker embeddings, and support offline diarization. |
| Speaker association | Diarization/clustering and timestamp alignment on the sender. | Attach speaker labels to transcript segments. |
| Delivery | Existing Zigbee link, extended for transcript events. | Carry patient-associated transcript text and metadata to the gateway. |
| Storage and viewing | Firebase and the patient's website Transcripts option. | Save and fetch speaker-labelled transcript records. |

Sherpa-ONNX is the selected candidate for local VAD, speaker embeddings, and
diarization on ARM64/Raspberry Pi. Select and verify the actual models, runtime
build, dependencies, and performance on the deployed sender before release.
The requested transcription choice is whisper.cpp **base**; model quantization,
language settings, and worker sizing are implementation choices to benchmark.

### 2. Offline audio and transcript flow

```mermaid
flowchart TD
    Patient[Active patient and monitoring session on sender] --> Mic[External microphone capture]
    Mic --> Buffer[Timestamped local audio buffer]
    Buffer --> VAD[Sherpa-ONNX voice activity detection]
    VAD --> Speech[Detected speech segments]
    Speech --> Whisper[whisper.cpp: Whisper base transcription]
    Speech --> Speakers[Sherpa-ONNX speaker embeddings and diarization]
    Whisper --> Align[Align transcript text, times, and speaker labels]
    Speakers --> Align
    Align --> Events[Transcript events with patient and session IDs]
    Events --> Zigbee[Zigbee transfer alongside vitals]
    Zigbee --> Gateway[Receiver Pi: validate and reconstruct]
    Gateway --> Upload[Independent Firebase upload worker]
    Upload --> Firebase[Patient transcript records in Firebase]
    Firebase --> Web[Website: patient Transcripts option]
```

Capture and process all detected speech in the active session, rather than only
commands or a selected speaker. Normalize microphone input to the format required
by the selected models, typically mono 16 kHz PCM. Keep sample timing so transcript
and speaker segments can be aligned and attributed to the original session.

VAD, transcription, and speaker processing run locally; Firebase connectivity
is needed for eventual cloud upload, not for recognition. Use separate bounded
workers/processes and queues so model inference does not block sensor acquisition,
the sender UI, or Zigbee delivery. Benchmark sustained capture, CPU, RAM, storage,
and thermal behavior with sensors active; do not assume real-time inference on
the Pi. Make processing backlog, microphone failures, and any dropped audio visible.

At End Session / Change Patient, finalize or explicitly mark unfinished speech
segments. Audio captured under the previous patient retains that context even if
inference finishes after another patient's session begins.

### 3. Speaker differentiation and identification

- Diarization answers **which speaker spoke when**, using labels such as
  `Speaker 1` and `Speaker 2` within the monitoring session.
- Sherpa-ONNX speaker embeddings support comparison/clustering of voices. Align
  the resulting speaker intervals with whisper.cpp transcript timestamps.
- A patient's record owns the monitoring session; this does not mean every voice
  in that session belongs to the patient. Other people may also speak.
- Identifying a speaker by a real name or role requires enrolled voice samples
  and a verified matching policy, or a confirmed manual label mapping. Until then,
  show session-scoped anonymous labels and mark uncertain/overlapping speech as
  unknown or ambiguous instead of assigning a name without evidence.
- Verify differentiation with at least two speakers, pauses, noise, and overlapping
  speech. Cross-session recognition must not be assumed from session labels alone.

### 4. Zigbee delivery and Firebase transcript records

Extend the wire contract with a versioned transcript message type, coordinated
across sender and receiver. The current compact sensor-only envelope cannot be
treated as though it already carries patient metadata or transcript text.

Each finalized transcript event must include:

- `patient_id`, `monitoring_session_id`, and `device_id` stamped at audio capture.
- A stable `transcript_id`/event ID for deduplication and retry.
- Original segment start/end timestamps and language information when available.
- Text segments with speaker labels and any available uncertainty/quality markers.
- Transcription and speaker-model identifiers for traceability.

The `segments` field in `patients/{patient_id}/transcripts/{transcript_id}` stores
items such as `{start_ms, end_ms, speaker_id, text}` relative to the event start.
The gateway adds receipt/upload timestamps while preserving original audio times.
The website orders records by audio capture time, not by delayed upload time.

Transmit text and speaker/timestamp metadata over Zigbee. Raw microphone audio
is not part of the planned Zigbee payload. Chunk long transcripts into bounded
messages with validation/reassembly limits; use application acknowledgements,
retry, and persistent pending-event storage so temporary link failures do not
silently lose finalized transcripts. Report failures and storage-limit losses.

Share the radio through one scheduler/owner. Give current vitals priority while
allocating bounded capacity for transcript and control traffic so neither is
starved. Preserve the current verified packet-size constraints until new hardware
tests justify a change. Measure vitals latency while transcript traffic is active.
Respect the existing Zigbee ON/OFF control: OFF stops forwarding without stopping
local sensor operation or speech processing, and finalized transcript events stay
pending for later transmission within the defined storage limit.

The gateway accepts only complete validated events, saves them to the correct
patient/session, and deduplicates retries. Cloud upload remains a separate worker
with persistent buffering and recovery, as in Phase 1.

### 5. Website Transcripts option

On a selected patient's detail page, the **Transcripts** option will fetch that
patient's Firebase transcript records and show:

- Monitoring session and original capture date/time.
- Speaker-labelled text in chronological order.
- Named speakers only where a confirmed mapping exists; otherwise anonymous labels.
- Available processing/uncertainty status, plus an empty state when no speech has
  been saved and a clear pending/error state when reported by the pipeline.

Users can return to the patient's vitals without changing the selected patient.
Apply the same patient-access rules to transcripts as to profiles
and sensor readings.

### 6. Implementation and deployment sequence

1. Start from the verified Phase 1 sender/gateway/data contract. Use the independent
   `Sender/versions/03_next_upgrade` workspace for sender upgrade development and
   refresh its baseline to Phase 1 before adding speech features. The patient UI
   changes themselves are delivered in Phase 1.
2. Connect and verify the external microphone on the sender Pi.
3. Build/install whisper.cpp and download/install the Whisper base model locally;
   verify transcription with internet access disabled.
4. Install the selected Sherpa-ONNX ARM64 runtime and compatible VAD/speaker models;
   verify speaker differentiation and timestamp alignment offline.
5. Integrate patient-session audio capture, independent workers, bounded buffers,
   and finalized transcript events.
6. Extend sender/receiver Zigbee handling together, then add Firebase transcript
   storage and the website Transcripts view.
7. Run the Phase 2 acceptance checks with real speech and active sensors. Record
   model versions, latency, resource use, gaps, and recovery evidence.
8. Push/deploy the verified Phase 2 sender, gateway, and website changes to their
   respective targets, retaining backups and the verified Phase 1 release.

### 7. Phase 2 acceptance criteria

- [ ] The sender Pi captures usable audio from the external microphone.
- [ ] whisper.cpp runs the installed **Whisper base** model locally and transcribes
      speech while internet access is disabled.
- [ ] Sherpa-ONNX runs the selected VAD/speaker models locally on sender ARM64 and
      differentiates at least two speakers with aligned transcript labels.
- [ ] Silence, noise, overlap, and uncertain identity are handled without invented
      speech or unsupported named-speaker claims; observed limitations are recorded.
- [ ] Captured audio and resulting text retain the correct patient/session across
      patient changes, delayed inference, link outages, and queued uploads.
- [ ] Real speaker-labelled transcripts traverse Zigbee to the receiver gateway,
      are stored under the correct patient in Firebase, and appear on the website.
- [ ] Selecting the patient's Transcripts option fetches chronological text with
      speaker labels and capture timestamps; empty/pending/error states work.
- [ ] Long transcript chunking, complete-event validation, deduplication,
      acknowledgements, retry, restart, and cloud recovery are verified.
- [ ] Sensor acquisition, UI responsiveness, freshness, and vitals delivery remain
      functional during sustained speech inference and transcript radio traffic;
      measured latency and resource limits are documented.
- [ ] Microphone disconnect, model errors, backlog, and storage limits are reported
      without blocking the vitals system or silently reassigning data.
- [ ] Transcript access follows the same public/private mode as patient vitals,
      with browser transcript creation and edits denied.
- [ ] The verified Phase 2 update is deployed to the intended sender, receiver,
      and website, with backups and model/configuration versions recorded.

**Phase 2 deliverable:** External-microphone speech captured and transcribed on
the sender Pi using offline whisper.cpp base, differentiated with Sherpa-ONNX,
delivered as patient/session-linked text over Zigbee to the gateway and Firebase,
and accessible from the patient's website Transcripts option alongside vitals.

## Current Firebase and website deployment reference — 12 November 2026

### Projects and credential references

| Setting | Current value |
|---|---|
| Firebase project | `immortals-3` |
| Firestore database | `projects/immortals-3/databases/(default)` |
| Database type and region | Firestore Native, `asia-south1` |
| Firebase CLI deployment account | `tirthankar.dgen@gmail.com` |
| Gateway service account | `immortals-gateway`, role `roles/datastore.user` |
| Gateway runtime configuration | `/home/pi/.config/immortals/firebase.json` |
| Gateway Admin SDK credential | The private JSON file named by `credential_path` in that configuration; alternatively `GOOGLE_APPLICATION_CREDENTIALS` or Application Default Credentials |
| Gateway credential permissions | Directory `0700`, credential files `0600`, outside the sender/receiver source folders |
| Website environment | Laptop `Website/.env.local`; matching `NEXT_PUBLIC_*` variables configured in Vercel |
| GitHub repository and branch | https://github.com/tirthankardgen-cell/Immortals-dashboard, `main` |
| Vercel project and scope | `immortals-dashboard`, `tirthankar-s` |
| Production website | https://immortals-dashboard.vercel.app |
| Current patient access | Public viewing, validated creation, and confirmed cloud deletion; sign-in optional |

Firebase console: https://console.firebase.google.com/project/immortals-3/overview.
Service-account management:
https://console.firebase.google.com/project/immortals-3/settings/serviceaccounts/adminsdk.

The following is the **public Firebase web application configuration** used by
the dashboard. Its API key identifies the browser app; access is controlled by
Firestore rules. Gateway private-key JSON and CLI OAuth tokens stay in their
credential stores; this reference records the accounts and locations.

```dotenv
NEXT_PUBLIC_FIREBASE_API_KEY=AIzaSyAprY7F6j48OH2q1jdwgKlr-WwHioKt9jw
NEXT_PUBLIC_FIREBASE_AUTH_DOMAIN=immortals-3.firebaseapp.com
NEXT_PUBLIC_FIREBASE_PROJECT_ID=immortals-3
NEXT_PUBLIC_FIREBASE_STORAGE_BUCKET=immortals-3.firebasestorage.app
NEXT_PUBLIC_FIREBASE_MESSAGING_SENDER_ID=515749825593
NEXT_PUBLIC_FIREBASE_APP_ID=1:515749825593:web:1b55995c75735beca511e8
NEXT_PUBLIC_FIREBASE_MEASUREMENT_ID=G-WJH0J7G1ZB
# Optional: enable browser analytics only after your deployment setup.
NEXT_PUBLIC_ENABLE_ANALYTICS=false
```

The receiver reads `project_id`, `credential_path`, and
`request_timeout_seconds` from its private configuration. The current code's
defaults are a 10-second request timeout, 500 pending records, and a 32 MiB
outbox limit. The sender does not receive Firebase credentials. Receiver
Admin SDK writes use the gateway service account and bypass browser rules.

### Implemented Firestore collections

| Document path | Contents and behavior |
|---|---|
| `patients/{patient_id}` | Name, age, sex, `patient_id`, identical `patient_code`, `patient_uuid`, `created_at`, and `age_recorded_at`. Gateway-created profiles may additionally contain `updated_at` and `device_id`. |
| `patients/{patient_id}/monitoring/latest` | Latest submitted snapshot, including patient/session/device identity, original capture time, receive/upload times, sensors, quality/status, and waveforms. |
| `patients/{patient_id}/readings/{submission_uuid}` | Saved snapshot history. The receiver uses the submission/request UUID as the document key for repeatable retries. |
| `patients/{patient_id}/sessions/{monitoring_session_uuid}` | `patient_id`, `monitoring_session_id`, `device_id`, `started_at`, and `recording_mode: submitted_snapshot`. |
| `patients/{patient_id}/transcripts/{transcript_id}` | Reserved Phase 2 patient/session-linked speech records and speaker-labelled segments; the website already supports display. |
| `registration_counters/{IMM-YYYYMMDD-57454201}` | Website daily counter: `value` (integer) and `patient_id` (most recently assigned ID). |
| `dashboard_access/{email}` | Optional private-access entries retained for future use; browser reads/writes are currently denied and public viewing does not consult them. |

Website registrations use `IMM-YYYYMMDD-57454201-NNNNN`, with the India date,
a sequence padded to at least five digits, and a UUID stored separately.
The sender uses its eight-hex radio registrar (for example `408DF0F0`) in the
same format. A Firestore transaction creates the website profile and advances
its counter together. Existing browser profiles cannot be edited. The counter
survives patient deletion, so a deleted patient ID is not allocated again.

Deleting a patient clears its cloud `monitoring`, `readings`, `sessions`,
and `transcripts` documents in batches, then removes the profile. It does not
change other patients or remove the sender/gateway's local cache/outbox; a
later gateway upload can recreate a patient that is still stored on a Pi.


### Public dashboard UI and patient search filters

The public dashboard no longer shows Preview or Sign in controls in its header,
empty states, or error panels. Its Firebase connection indicator appears in the
header on every page, showing Connected, Connecting, Cached, Offline, or
Unavailable as appropriate. The previous directory connection-status card has
been removed.

The directory combines patient name/ID search with these filters:

- **Age group:** all ages, 0–17, 18–35, 36–59, 60+, or age not entered.
- **Gender:** all genders, Female, Male, Other, Prefer not to say, or not entered.
  This filter reads the sender-compatible `sex` profile field.
- **Measurements:** all patients, measured, or not measured. Measured means a
  saved latest snapshot exists, including an older/paused recorded capture.
  Not measured means the gateway's latest document is confirmed absent.
- **Sort and display:** name/newest order, list/grid views, and one Reset action
  for the search text and all filters.

Measurement filtering checks every matching name/age/gender candidate before
pagination; it does not stop at the patients visible on the current page.
Unknown responses show a checking state, and failed reads show an error/retry
state instead of being classified as not measured.

Patient record controls have their own spacing beneath the header. The recorded
capture timestamp is in the patient header, keeping more space for the vital
cards and waveforms. Plots adapt to the available height while reserving space
for quality labels and units, so waveform captions do not overlap the lower note.
Directory pagination measures both the toolbar and footer. Compact grid cards
keep the name, ID, demographic line, and record controls inside their boundaries.

Browser checks covered patient vitals plus directory list/grid layouts at
1280×600, 1024×600, 900×520, and 1440×800, with responsive mobile width checked at
390 pixels. Combined age/gender/measurement filters, reset behavior, the header
connection label, and the absence of Preview/Sign in controls passed.

### Deployed Firestore rules

The source is `Website/firestore.rules` in the parent workspace and
`firestore.rules` at the website repository root. The deployed release is
`projects/immortals-3/releases/cloud.firestore`; its verified ruleset is
`projects/immortals-3/rulesets/4b8fd81e-ea6b-4cf6-b51c-7395eee944af`.

Rules source SHA-256: `85fb735d39e78219d92560f627278f8c2983a50c1ad269349241f8b310386a60`.

Public reads and deletes apply only to the patient tree. Browser profile
creation must meet the exact sender-compatible fields and atomic counter
checks. Browser measurement creation/updates, profile updates, access-list
operations, and unrelated collections remain denied.

```text
rules_version = '2';
service cloud.firestore {
  match /databases/{database}/documents {
    function webPrefix(prefix) {
      return prefix.matches('IMM-[0-9]{8}-57454201');
    }
    function validProfile(data, patientId) {
      return patientId.matches('IMM-[0-9]{8}-57454201-([0-9]{5}|[1-9][0-9]{5,8})')
        && data.keys().hasAll(['patient_id', 'patient_code', 'patient_uuid', 'name', 'age', 'sex', 'created_at', 'age_recorded_at'])
        && data.keys().hasOnly(['patient_id', 'patient_code', 'patient_uuid', 'name', 'age', 'sex', 'created_at', 'age_recorded_at'])
        && data.patient_id == patientId && data.patient_code == patientId
        && data.patient_uuid is string
        && data.patient_uuid.matches('[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}')
        && data.name is string && data.name.size() >= 1 && data.name.size() <= 80
        && data.name.matches('[^\\x00-\\x1F]{1,80}') && data.name.matches('.*[^ ].*')
        && data.age is int && data.age >= 0 && data.age <= 130
        && data.sex in ['Female', 'Male', 'Other', 'Prefer not to say']
        && data.created_at is string
        && data.created_at.matches('[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}[.][0-9]{3}Z')
        && data.age_recorded_at == data.created_at;
    }
    function registrationCounterMatches(patientId) {
      let parts = patientId.split('-');
      let prefix = parts[0] + '-' + parts[1] + '-' + parts[2];
      let counter = /databases/$(database)/documents/registration_counters/$(prefix);
      return getAfter(counter).data.patient_id == patientId
        && getAfter(counter).data.value == int(parts[3])
        && ((!exists(counter) && getAfter(counter).data.value == 1)
          || (exists(counter) && getAfter(counter).data.value == get(counter).data.value + 1));
    }
    function validCounter(data, prefix) {
      let patient = /databases/$(database)/documents/patients/$(data.patient_id);
      return webPrefix(prefix)
        && data.keys().hasAll(['value', 'patient_id']) && data.keys().hasOnly(['value', 'patient_id'])
        && data.value is int && data.value >= 1 && data.value <= 999999999
        && data.patient_id is string && data.patient_id.matches(prefix + '-([0-9]{5}|[1-9][0-9]{5,8})')
        && int(data.patient_id.split('-')[3]) == data.value
        && !exists(patient) && validProfile(getAfter(patient).data, data.patient_id);
    }
    // Temporary public viewing, requested by the owner. Sign-in is not required.
    match /patients/{patientId} {
      allow read: if true;
      allow create: if validProfile(request.resource.data, patientId) && registrationCounterMatches(patientId);
      allow update: if false;
      allow delete: if true;
      match /{record=**} {
        allow read: if true;
        allow create, update: if false;
        allow delete: if true;
      }
    }
    // A new profile and the next website counter must be committed together.
    match /registration_counters/{prefix} {
      allow get: if webPrefix(prefix);
      allow list, delete: if false;
      allow create: if validCounter(request.resource.data, prefix) && request.resource.data.value == 1;
      allow update: if validCounter(request.resource.data, prefix) && request.resource.data.value == resource.data.value + 1;
    }
    // Access entries and measurements are managed by the gateway/Admin SDK.
    // Patient deletion is public for now; measurement creation/edits remain blocked.
    match /{document=**} { allow read, write: if false; }
  }
}
```

The earlier private rules are retained locally at
`Website/.deployment-backups/firestore-rules-private-20261112.rules`.
Use them as a reference when private access is restored; include any registration
and deletion behavior required at that time.

### Deployment and verification

From the `Website` directory, deploy rules separately from the Vercel website:

```powershell
npx firebase-tools@15.35.0 deploy --only firestore:rules --project immortals-3 --account tirthankar.dgen@gmail.com --non-interactive
```

Push website changes to GitHub `main`; the linked Vercel project builds and
publishes that commit to the production domain. Firebase rules are a separate
deployment and must be checked against the release listed above.

Validation completed for this update: 11 model/profile tests and 9 Firestore
emulator tests passed, including simultaneous registration, public access,
atomic counters, rejected edits, and deletion isolation. Lint, type checking,
and the production build passed. A real browser created a temporary patient
without sign-in, verified its Sender_v2-style ID, deleted it, and confirmed
Firestore returned 404. Desktop viewport checks passed at 1280×600 and
1440×800; mobile width was checked at 390 pixels. The 1200×630 sharing image,
page metadata, icons, and manifest were also checked.

**Initial production deployment receipt:** GitHub `main` contains commit
`6e8ac3895b5d4580cb03ba4024e66326600b996c`. Vercel deployment
`dpl_Fx23QGNqdFR4pCTEDdcAwfZKRFAX` is READY and serves that same commit at
https://immortals-dashboard.vercel.app. Live anonymous registration and confirmed
deletion passed; the temporary test patient was removed. Production page titles,
descriptions, canonical URLs, Open Graph/Twitter tags, the 1200×630 preview image,
icons, and manifest passed verification. Firebase's released rules source matched
`Website/firestore.rules`, and an unauthenticated patient read returned HTTP 200.

**Latest UI deployment receipt:** GitHub `main` and Vercel production now use
`360fc4b53ee201d48599f16b19d0464ada020ae6`. Vercel deployment
`dpl_HvmX1kCmxNEVh74arwviLgHNzJdD` is READY at the same production domain.
This update fixes the record/grid text overlaps, removes public Preview/Sign in
controls, moves Firebase status to the header, and adds the combined directory
filters described above. Lint, type checking, model/profile tests, the production
build, and responsive browser checks passed. The live public header, filters,
Connected/Offline states, mobile navigation, and registration route passed with
zero browser errors. Firebase rules were unchanged by this UI update and their
released source was verified again against `Website/firestore.rules`.
```

# Appendix C — Raspberry Pi 5 sensor wiring guide (transcribed from supplied DOCX)

RASPBERRY PI 5
SENSOR WIRING GUIDE

Complete pin mapping for AD8232 ECG, ADS1115, MH-ET LIVE MAX30102, BMP180, DHT22 and HW-691 MLX90614

1. System overview

The ADS1115 converts the AD8232 ECG module’s analog OUTPUT into digital readings. The ADS1115, MAX30102, BMP180 and MLX90614 share the Raspberry Pi 5 I²C bus. The DHT22 uses a separate digital GPIO pin.

2. Raspberry Pi 5 physical pins used

3. AD8232 ECG module → ADS1115 ADC

4. ADS1115 ADC → Raspberry Pi 5

5. MH-ET LIVE MAX30102 → Raspberry Pi 5

For the board orientation in the supplied photo, the top row is labelled GND, RD, IRD, INT from left to right; the bottom row is VIN, SDA, SCL, GND from left to right.

6. BMP180 pressure / temperature sensor → Raspberry Pi 5

7. DHT22 temperature / humidity sensor → Raspberry Pi 5

Bare 4-pin DHT22, grille facing you and pins pointing down: the usual order is VCC, DATA, NC, GND. A bare sensor typically needs a 4.7–10 kΩ pull-up resistor between DATA and 3.3 V. A 3-pin breakout may already include this resistor; check the board.

8. HW-691 MLX90614 infrared temperature sensor → Raspberry Pi 5

9. Shared I²C addresses (typical)

These are typical addresses, not a guarantee for every clone or board configuration. The I²C addresses listed do not conflict with one another.

10. Bring-up / verification

With power disconnected, wire the modules and inspect for shorts or reversed connections.

Enable I²C with: sudo raspi-config → Interface Options → I2C.

Install the scanner: sudo apt update && sudo apt install -y i2c-tools.

Scan the bus: sudo i2cdetect -y 1.

Expected typical addresses: 48 (ADS1115), 57 (MAX30102), 77 (BMP180), 5a (MLX90614).

If a device is missing, check power, SDA/SCL orientation, ground, pull-ups, and board-specific voltage requirements before running code.

11. Safety and electrical notes

The Raspberry Pi 5 has no built-in analog input; AD8232 OUTPUT must go to ADS1115 A0, not a Pi GPIO.

Use 3.3 V logic on Pi SDA/SCL. Do not allow I²C pull-ups to drive the Pi GPIO lines to 5 V.

Do not assume all breakout boards support the same supply voltage. Check the exact module documentation, especially for VIN and any 1V8/3V3 selection pads.

For ECG measurements on a person, use a battery-powered, appropriately isolated arrangement. Do not attach electrodes to a person while the setup has an unsafe electrical path through mains-powered instruments, USB-connected equipment, or other connected hardware. These modules are not certified medical devices.

Reference wiring guide based on the module labels and photos supplied. Verify each board revision before applying power.

### Wiring table 1

| Physical pin | Pi signal | Use |
| --- | --- | --- |
| 1 | 3.3 V | Power for sensor breakout boards, subject to each board’s voltage requirements |
| 3 | GPIO2 / SDA | Shared I²C data: ADS1115, MAX30102, BMP180, MLX90614 |
| 5 | GPIO3 / SCL | Shared I²C clock: ADS1115, MAX30102, BMP180, MLX90614 |
| 6 | GND | Common ground for all modules; ADS1115 ADDR may also connect here |
| 7 | GPIO4 | DHT22 DATA |
| 11 | GPIO17 | AD8232 LO+ (optional lead-off signal) |
| 13 | GPIO27 | AD8232 LO− (optional lead-off signal) |
| 15 | GPIO22 | MAX30102 INT (optional; not required for basic polling) |

### Wiring table 2

| AD8232 pin | Connect to | Notes |
| --- | --- | --- |
| 3.3V | Pi physical pin 1 / common 3.3 V rail | Power the ECG breakout at 3.3 V. |
| GND | Pi physical pin 6 / common GND | All grounds must be common. |
| OUTPUT | ADS1115 A0 | Analog ECG signal; do not connect directly to a Pi GPIO. |
| LO+ | Pi physical pin 11 / GPIO17 (optional) | Lead-off detection output. |
| LO− | Pi physical pin 13 / GPIO27 (optional) | Lead-off detection output. |
| SDN | 3.3 V | Keeps the AD8232 enabled on common breakout designs; verify your board revision. |
| RA, LA, RL | Compatible 3-electrode cable | Follow the electrode/cable labels; these are not Pi GPIO pins. |

### Wiring table 3

| ADS1115 pin | Connect to | Notes |
| --- | --- | --- |
| VDD | 3.3 V / physical pin 1 | Use 3.3 V for Pi-compatible I²C logic. |
| GND | GND / physical pin 6 | Common ground. |
| SDA | GPIO2 / physical pin 3 | Shared I²C data. |
| SCL | GPIO3 / physical pin 5 | Shared I²C clock. |
| ADDR | GND / physical pin 6 | Selects address 0x48 on the usual ADS1115 breakout. |
| A0 | AD8232 OUTPUT | ECG analog input. |
| A1, A2, A3 | Leave unconnected | Spare ADC inputs. |
| ALERT | Leave unconnected | Optional alert/ready output. |

### Wiring table 4

| MAX30102 pin | Connect to | Notes |
| --- | --- | --- |
| VIN (bottom row) | 3.3 V / physical pin 1 | Confirm the exact breakout’s supply range and logic pull-ups. |
| GND (bottom row) | GND / physical pin 6 | Common ground. |
| SDA | GPIO2 / physical pin 3 | Shared I²C data. |
| SCL | GPIO3 / physical pin 5 | Shared I²C clock. |
| INT | GPIO22 / physical pin 15 (optional) | Interrupt line; omit for basic polling. |
| RD, IRD | Leave unconnected | LED driver-related labels on this board, not Pi data pins. |
| GND (top row) | Optional additional common GND | If used, connect to the same ground rail. |

### Wiring table 5

| BMP180 pin | Connect to | Physical pin |
| --- | --- | --- |
| VCC | 3.3 V | 1 |
| GND | GND | 6 |
| SDA | GPIO2 / SDA | 3 |
| SCL | GPIO3 / SCL | 5 |

### Wiring table 6

| DHT22 pin | Connect to | Physical pin |
| --- | --- | --- |
| VCC / + | 3.3 V | 1 |
| DATA / OUT | GPIO4 | 7 |
| GND / − | GND | 6 |
| NC (bare 4-pin sensor only) | Leave unconnected | — |

### Wiring table 7

| HW-691 pin label | Connect to | Physical pin |
| --- | --- | --- |
| VIN | 3.3 V (verify the exact board’s supported range) | 1 |
| GND | GND | 6 |
| SCL | GPIO3 / SCL | 5 |
| SDA | GPIO2 / SDA | 3 |

### Wiring table 8

| Device | Typical 7-bit address | Interface |
| --- | --- | --- |
| ADS1115 | 0x48 (ADDR tied to GND) | I²C; analog input A0 receives AD8232 OUTPUT |
| MAX30102 | 0x57 | I²C |
| BMP180 | 0x77 | I²C |
| MLX90614 / HW-691 | 0x5A | I²C |
| DHT22 | Not applicable | Single-wire digital GPIO |
| AD8232 | Not applicable | Analog output into ADS1115 |

