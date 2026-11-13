# Immortals Sender v2 — remote health checkups

Updated 12 November 2026. This is the new sender release. The original `Sender`
folder and the deployed `/home/pi/Desktop/Immortals_Monitor` remain preserved.

Immortals is intended for health checkups in remote places. The touch-only sender
collects readings near the patient without an internet connection. Zigbee carries
patient records to a separate gateway. Only the gateway has Firebase access.

## Operator flow

**ECG available: ON/OFF** is on the main and monitoring screens. Turn it OFF
when ECG/electrodes are unavailable or failing. ECG is then marked skipped and
does not block automatic stable recording of the other sensors, the recording
popup, or sending to the gateway. Turn it ON to require ECG again. The setting
is saved on the sender and retained after restart; saved recordings do not change.

1. Choose Patient or Add Patient. Search by name or the full patient ID using the
   built-in keyboard. Registration requires name, whole-number age 0–130, and sex.
2. Confirm the patient. A new monitoring session starts. Check the sensor values
   and both graphs; the initial optical collection window takes about 8 seconds.
3. Recording happens **automatically** after all required readings and both
   waveforms are ready and stable for three seconds. Optical quality must be at
   least 70%; qualified ECG quality/rate at least 50% is required. Heart rate,
   SpO2, surface/ambient temperature, room temperature/humidity, pressure and
   board temperature must be fresh. Poor contact keeps acquisition running.
   **Record Available** can explicitly capture a labelled partial check.
4. A **Data recorded successfully** popup shows that fixed recording. Tap
   **Send to Gateway** to release it for transmission. Recording alone does not send.
5. The same popup shows sending and saved by gateway from acknowledgements.
   **Record Again** discards an unsent draft and restarts the same patient's
   check. Already sent records stay saved; New Check starts another check.
   Done returns to the main screen.
6. If the gateway cannot be reached, the popup confirms that the record is saved on
   this device and will sync automatically when the gateway returns. After 4.5
   seconds it closes and returns to the main screen. Background retries continue.

Use Review Saved Record to reopen an unsent or pending capture. A recorded draft
needs an explicit Send action; captures already released for sending retry
automatically. Changing patient never reassigns earlier records.
**Sync All Saved Data** releases prior drafts and retries pending/rejected records.
Every record retains its patient ID, monitoring session and original capture.
The main screen separates patient actions, gateway/device status and saved-data
controls. Popups have rounded surfaces, soft shadows and a blurred/dimmed
backdrop, verified on the actual display. Headings are slightly bolder.

Missing or poor-quality readings remain unavailable, with their original labels.
Check finger/electrode contact before recording. The software does not manufacture
values for missing sensors. Infrared temperature is a surface measurement; SpO2
is an uncalibrated estimate; qualified and provisional ECG rates remain separate.

## Patient ID nomenclature

Example: **IMM-20261112-408DF0F0-00001**

- `IMM`: Immortals project prefix.
- `20261112`: registration date in India time (`Asia/Kolkata`).
- `408DF0F0`: last eight hexadecimal digits of the configured sender radio address.
- `00001`: daily device counter, saved in SQLite and continued after restart.

This exact string is `patient_id`, `patient_code`, the searchable sender ID, the
Firestore patient document key, and the website patient ID. A separate
`patient_uuid` retains a globally unique internal identity. Names need not be
unique. Existing codes received from the gateway are also checked before a new
code is allocated. This release supports the one configured sender/gateway pair.

## Communication and persistence

```text
Touch sender + sensors (no internet / no Firebase credentials)
       ⇅ Zigbee: patient list, submissions, acknowledgements/status
Gateway Pi with internet ⇄ Firebase Firestore ⇄ website
```

`patient_data.sqlite3` is device-local runtime data. It contains the patient cache,
ID counters, recorded drafts, immutable outgoing captures, and saved receipts.
Pending storage is bounded to 500 records / 32 MiB; up to 50 completed receipts
are retained. A full buffer is reported and records are not silently discarded.
The sender's UI, sensor workers, disk snapshots, and Zigbee worker remain separate.

Zigbee v3 keeps the existing 115200 baud and 84-byte RF cap. Larger recordings
are compressed, fragmented, CRC checked, and reconstructed within a 60-second
assembly window. Sending a whole waveform recording takes longer than a compact
live batch. Gateway acceptance means a durable local commit; Firebase completion
is a separate status. Retries retain the same submission ID and capture time.

## Files and deployment

Laptop: `D:\PROJECTS\Immortals\Sender_v2`

Pi: `/home/pi/Desktop/Immortals_Monitor_v2`

Start: `/home/pi/Desktop/Immortals_Monitor_v2/.venv/bin/python /home/pi/Desktop/Immortals_Monitor_v2/main.py`

It opens automatically when the sender Pi boots into its desktop. If the window
does not open, tap **Immortals Patient Monitor v2.desktop** on the desktop, or run:

```sh
python3 /home/pi/Desktop/Immortals_Monitor_v2/main.py
```

Tap **Close** at the top right of the main, patient-selection, registration,
confirmation or monitoring screen to exit the app. Ctrl+Q and Alt+F4 also exit.
The window closes immediately while existing cleanup stops the workers and
releases the hardware lock. Saved records remain on the device. Popups keep
their existing Main Screen controls and do not show an app-close button.
Use the desktop launcher to reopen the monitor after closing it.

The file to open in Thonny or run manually is `main.py` in this v2 folder. It
automatically selects the existing Pi virtual environment.

The v2 desktop/autostart entry is `immortals-monitor-v2.desktop`. The earlier entry
is retained as `immortals-monitor.desktop.disabled`. The Pi `.venv` links to the
existing sender environment; environments and runtime databases stay on that Pi.
Both releases use the same hardware-owner lock and must not run together.

- `main.py`: preserved sensor processing and main vitals dashboard.
- `patient_ui.py`: rounded touch controls, keyboard, patient screens and delivery popup.
- `patient_sender.py`: session context, recording, outbox and bidirectional radio worker.
- `patient_common.py`: shared v3 schema, framing and SQLite storage.
- `zigbee_config.json`: existing serial/radio configuration.
- `sync.py`: source-only synchronization and SHA-256 verification.

Firebase libraries, credentials and cloud calls are not used by this application.
Its patient list comes from the gateway over Zigbee and is cached for offline use.
