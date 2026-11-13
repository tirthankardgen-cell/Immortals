# Immortals Receiver v2 — Zigbee/Firebase gateway

Updated 12 November 2026. Laptop: `D:\PROJECTS\Immortals\Receiver_v2`.
Pi: `/home/pi/Desktop/Immortals_Receiver_v2`.
The original `Receiver` folder and `/home/pi/Desktop/Immortals_Receiver` remain
preserved. The enabled service is `immortals-receiver-v2.service`; the old service
is retained but disabled.

## Purpose and architecture

The system supports health checkups in remote places. The sender near the patient
does not need internet. It records vitals and sends patient-associated captures
over Zigbee. **Only this gateway connects to Firebase**, using its internet link.
The website reads those records from Firebase, without a direct
connection to either Pi.

The receiver continues to understand the earlier v1/v2 live sensor protocol and
adds v3 patient-list requests, recorded submissions, durable acknowledgements,
and submission status. Patient records are synchronized to the sender over
bidirectional Zigbee; no Firebase credential or cloud connection is on the sender.

## Gateway responsibilities

- Validate source radio, CRC, patient ID, monitoring session, capture time, sensor
  groups and waveforms. A name alone never identifies a patient.
- Save complete submissions to `gateway_data.sqlite3` before acknowledging them.
- Upload through an independent worker, with bounded requests and retry backoff
  from 2 to 60 seconds. Internet failures do not block radio reception or the UI.
- Keep original patient association, units, null/quality labels and capture time.
- Use the submission UUID as the Firestore reading key, so retrying is idempotent.
- Update latest data atomically only when its capture is at least as new as the
  saved latest capture. Old offline uploads do not become fresh measurements.
- Synchronize a local cloud patient cache. Radio list pages contain ten patients;
  the sender can use its cache during gateway/cloud outages.

The queue allows 500 pending records / 32 MiB and retains up to 50 completed
receipts. If storage is full, reject explicitly and expose an unsaved count;
the sender retains its local capture. Reception and uploads use separate workers.

## Patient IDs and Firestore

`IMM-YYYYMMDD-DEVICE8-COUNTER` is the exact displayed and stored `patient_id`.
For example, `IMM-20261112-408DF0F0-00001` has this database structure:

```text
patients/IMM-20261112-408DF0F0-00001
    patient_id = IMM-20261112-408DF0F0-00001
    patient_code = IMM-20261112-408DF0F0-00001
    patient_uuid, name, age, sex, created_at, age_recorded_at
    monitoring/latest
    readings/{submission_uuid}
    sessions/{monitoring_session_uuid}
```

Every capture carries the same patient ID and a separate monitoring-session UUID,
device ID, transport session/sequence and original capture time. Existing v2
records initially stored under UUID patient keys were reconciled to the matching
display ID, with their history retained and a reconciliation backup saved.

Project: `immortals-3`. Firebase service account: `immortals-gateway` with
`roles/datastore.user`. Credentials exist only under `/home/pi/.config/immortals`
on the gateway, outside both source folders and website assets (directory mode
0700, files 0600). `firebase.json` holds the project ID, credential path, timeout,
and buffer limits. Never copy credential contents into this repository.

## Dashboard and startup

LAN dashboard: `http://immortals-recv.local:8080`.
`/api/readings` exposes radio/cloud state and the last recorded capture.
`/api/patients` lists the cached profiles. The API is read-only.

Live cards expire; the separately labelled recorded-capture section preserves
the last submitted values. Restart restores saved capture context while keeping
it stale. Firebase status and pending/rejected/unsaved counts remain visible.

Start/service:

```sh
sudo systemctl status immortals-receiver-v2.service
sudo systemctl restart immortals-receiver-v2.service
```

The gateway starts automatically at power-on, even when the internet is
temporarily unavailable. If it is stopped, use
`sudo systemctl start immortals-receiver-v2.service`. The manual application file
is `/home/pi/Desktop/Immortals_Receiver_v2/main.py`; it can also be started with
`python3 /home/pi/Desktop/Immortals_Receiver_v2/main.py` after stopping the service.

The v2 `.venv` reuses the existing receiver environment, with `firebase-admin`
installed. The hardware-owner lock is shared with the preserved original release.
`sync.py` copies only source files and verifies hashes; databases, runtime logs,
environments and credentials remain device-local.

The sender's recording popup distinguishes **recorded locally**, **sending**,
**saved on gateway**, and **saved in Firebase**. Failure to reach this gateway
returns the operator to the sender main screen after confirming local storage;
the original record is retried automatically. The sender automatically records
stable complete readings, supports Record Again before sending and Sync All
Saved Data to release earlier drafts. The sender displays gateway status only.
