# Sender patient-monitor UI update — 11 November 2026

## Delivered screen layout

The 1024 × 600 sender screen gives vitals the largest area, with patient
information in a header and environmental readings in compact cards at the right.

| Section | Placement | Contents |
|---|---|---|
| Patient Information | Full-width header below the application title. | Demo Patient, DEMO-001, age/sex placeholders, and a visible PLACEHOLDER badge. |
| Patient Vitals | Main area below the header. | MAX30102 heart rate, estimated SpO2, infrared body-surface temperature, pulse waveform, and ECG waveform/rate. |
| Environmental Data | Small cards along the right edge. | DHT22 room temperature and relative humidity; BMP180 air pressure and board/sensor temperature. |

The body-temperature card displays the existing MLX90614 `object_c` value in
Celsius and explicitly labels it as an infrared surface measurement. The existing
sensor driver already calculates Celsius from the raw reading. Missing heart rate
or SpO2 remains `--`; provisional ECG rates retain their `~` and UNRELIABLE labels.

The patient name and ID are display placeholders. Patient registration, patient
selection, Firebase, and transcription remain the planned work described in the
root `PROJECT_UPGRADE_PLAN.md`.

## Source and runtime

The changes are confined to `Dashboard` in `main.py`. Sensor acquisition,
processing, source freshness, Zigbee payloads, worker scheduling, and startup are
identical to the pre-update code by AST comparison.

The laptop source is `D:\PROJECTS\Immortals\Sender`; the sender Pi runs
`/home/pi/Desktop/Immortals_Monitor/main.py` through the existing desktop startup.
`versions/02_latest_zigbee/main.py` is refreshed from the active root by `sync.py`.
The sensor-only version and independent `03_next_upgrade` baseline are retained.

## Verification

- All 32 existing sender tests passed in the deployed Pi virtual environment.
- Actual display captures were inspected at 1024 × 600 and in the 960 × 520
  windowed layout; all three sections and the waveform/status areas fit.
- Real screen-coordinate mouse events toggled the native Zigbee button in both
  layouts and restored full-screen placement to `(0, 0)`.
- During the interaction check, optical acquisition advanced by 301 samples,
  with zero FIFO overflows. ECG and environmental readings continued updating.
- The temporary ON period increased radio-acknowledged snapshots from 17 to 27,
  with zero sender failures. Zigbee was restored to its initial OFF state.

Evidence on the laptop: `output/sender-ui-final.png`,
`output/sender-ui-windowed.png`, and `.work/sender-ui-validation.json`.

## Backup

Pre-update sources and saved settings are archived on the sender at:
`/home/pi/.local/share/immortals-backups/sender-patient-ui-20261111-165901/before-ui.tar.gz`.
The laptop copy is `.work/pi-backup/before-patient-ui/before-ui.tar.gz`.
SHA-256: `441a1a68d82996ba28dcb4842aef354116dc738c76956e5da1142b717836b37b`.
