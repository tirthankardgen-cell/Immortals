# v2 delivery verification — 12 November 2026

- Sender and receiver source files are SHA-256 verified against their respective
  Pi v2 folders. Original folders/releases and pre-update archives remain saved.
- The new sender desktop startup and receiver systemd service are running.
- Thirteen cross-role tests pass: durable drafts, automatic complete/stable
  readiness, Record Again cancellation, Sync All patient association, ID counters
  after restart, fragmentation/CRC and replay ACKs, queue capacity, immutable
  captures, cloud outage recovery, stale restart restoration and receipt ordering.
- Two real patient recordings reached the gateway over Zigbee and were uploaded
  to Firestore. The sender received uploaded acknowledgements and has no pending
  or rejected captures at the final check. Patient ID matches the sender,
  Firestore document key and website (`IMM-20261112-408DF0F0-00001`).
- A temporary cloud integration check verified idempotent history, null handling
  and protection of newer latest captures against old uploads. Test cloud records
  were removed afterwards. The earlier pending upload recovered after gateway
  restart without losing the original recording.
- Actual screen captures verify organized controls, corrected fullscreen sizing,
  rounded popup corners, shadow/blur and the final bolder headings. Independent
  sensor acquisition continued with zero FIFO overflows in the final snapshot.
- Complete automatic readiness was checked with controlled sensor fixtures;
  actual missing/unstable finger/electrode signals remain labelled and keep
  automatic recording waiting. Record Available supports an explicit partial check.
- Website checks/build passed and production deployment is ready at
  `https://immortals-dashboard.vercel.app` with saved-capture display semantics.

Evidence: laptop `output/patient-v2-home-final.png`,
`output/patient-v2-rounded-popup-final.png`, `.work/patient-upgrade-backups.json`,
`.work/patient-id-reconciliation.json`, and each role's `source-sha256.json`.

Firebase credentials are on the gateway only. The sender app has no Firebase
library import, credential or internet upload path; gateway statuses arrive over
Zigbee. Runtime databases and platform environments are excluded from source sync.
