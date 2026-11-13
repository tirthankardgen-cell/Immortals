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
