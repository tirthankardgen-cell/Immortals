# Patient protocol v3

The fixed 20-byte header is `>2sBBIIHHI`: `IM`, version 3, compression flag 1,
32-bit transport session, 32-bit sequence, fragment index/count, and compressed
CRC32. Payloads remain at most 84 bytes at 115200 UART baud. Compressed messages
are limited to 64 KiB and decoded JSON to 256 KiB; four incomplete assemblies and
a 60-second assembly timeout bound receiver memory.

Every JSON event contains `schema_version:3`, `message_type`, `sender_id`,
`session_id` matching the header, `sequence`, and a UUID `request_id`.

| Type | Direction | Content |
|---|---|---|
| `patient_list_request` | Sender → gateway | Local-cache page offset |
| `patient_list_page` | Gateway → sender | At most ten validated profiles; next offset and more flag |
| `patient_submit` | Sender → gateway | Immutable patient profile, monitoring-session UUID, started_at, complete recorded reading |
| `submission_ack` | Gateway → sender | pending/uploaded/rejected, with request ID matching submission |
| `submission_status_request` | Sender → gateway | Persisted submission receipt lookup |
| `submission_status` | Gateway → sender | pending/uploaded/rejected/unknown |

Profiles use the same `IMM-YYYYMMDD-DEVICE8-COUNTER` patient ID shown to the
operator and used in Firestore. A separate UUID is saved internally. The nested
reading preserves the established sensor schema, all groups/units/statuses,
available full waveforms, explicit patient/session/device IDs, capture time,
and `recording_mode:submitted_snapshot`.

Recording creates a local draft. Only Send to Gateway releases it to the outbox.
Duplicate RF/application deliveries remain safe: v3 reassembly allows a repeated
message to be processed so a lost ACK can be regenerated, while durable stores
reject a submission ID reused with changed contents. Cloud history keys use the
submission UUID. Patient lists/status do not transmit unsubmitted sensor data.

The gateway acknowledges only after durable local storage. A pending ACK does
not mean Firebase upload completed; an uploaded status does. No cloud call runs
in either radio worker. The sender polls incomplete cloud receipts and retries
unacknowledged submissions with their original IDs and values.
