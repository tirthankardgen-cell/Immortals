# Live Zigbee upgrade - 11 November 2026

The laptop keeps `D:\PROJECTS\Immortals\Sender` and
`D:\PROJECTS\Immortals\Receiver`. Each synchronizes only to its respective Pi.
Sender deploys to `/home/pi/Desktop/Immortals_Monitor`; receiver deploys to
`/home/pi/Desktop/Immortals_Receiver`. Existing Pi paths and startup entries stay
valid. Login information stays in laptop-only `.work/PI_ACCESS.md`.

## Sender versions requested by the owner

| Folder inside Sender | Purpose | Automatic startup |
|---|---|---|
| `versions/01_sensor_only` | Actual old code recovered from the pre-Zigbee backup; sensor acquisition and local dashboard, no forwarding backend | No |
| `versions/02_latest_zigbee` | Release copy of the current live Zigbee sender | Root `main.py` is the active identical copy |
| `versions/03_next_upgrade` | Independent runnable starting copy for the next UI/features phase | No |

Only one sender version may own the sensors/radio at a time. Each version's
`project.md` gives its Pi launch command. Linux environments are kept only on
the Pi. The prior slow Zigbee sender is separately preserved in laptop
`.work/pi-backup/pre-stream-sender`, including its old 9600-baud configuration.
Do not launch it against the upgraded radio without restoring matching settings.

## Changes that remove the delay

- Both radio UART settings are verified as BD=7 (115200 baud); both applications
  now match. PAN/channel/API mode and firmware are retained. The owner does not
  need XCTU, an app setting change, or a firmware upgrade.
- The old implementation sent the entire eight-second history in every message,
  at 9600 baud, starting batches at least five seconds apart. Previously measured
  full snapshots took 15-19 seconds; user observed 20-50 seconds including display.
- The new worker immediately takes current values, retains every scalar field,
  status/null/age and quality marker, and sends only new waveform points.
  It aims for a 200 ms start interval; actual start rate is constrained by RF
  acknowledgements and payload size. There is no accumulated outbound queue.
- A compact v2 envelope removes repeated metadata and measurement labels.
  ECG and pulse are processed using the existing filters and quality checks.
- RF payloads are capped at 84 bytes. Actual high-baud tests delivered these
  reliably. A 200-byte API transmit caused serial timeouts/parser stalls with
  these older radios/adapters even though NP reported 255. NP is not a guarantee
  of reliable high-speed UART buffering. Software does not require new wiring.
- The receiver appends samples into an eight-second graph history, accepts only
  complete CRC-checked messages, clears old history across restart/large gaps,
  and expires forwarding after three seconds. A lost batch creates a gap;
  missing heartbeats are never generated. History is capped and source ages
  remain visible. DHT readings retain their longer seven-second validity.
- Disk persistence runs once per second outside RF reception. Browser polling
  is 100 ms after each completed request. UI styling changes remain for later.

## Measurements and limits

The first successful live run measured 531-590 ms capture-to-receiver delivery.
After compact field coding, 68 hardware batches gave 423 ms median, 497 ms p95,
and 398-583 ms range with zero rejected frames/expired assemblies. This run had
live ECG and all sensor groups; no finger was present, so optical bpm/SpO2 were
correctly null and the pulse graph was empty. Further final evidence is recorded
in the laptop `.work/` validation files.

The owner then placed a finger for the final test. All 69 recorded packets had
an optical heart rate (74.5-85.8 bpm); available SpO2 estimates were 98.7-99.8%.
Both traces arrived (198 pulse points and 985 ECG points in the final eight-second
history). For these 69 packets, capture-to-receiver delivery was 434-562 ms with
465 ms median. The receiver had zero invalid/duplicate frames, expired assemblies,
rejected snapshots or reconnects in this release run. A longer earlier run had an
isolated RF delay near two seconds, so 465 ms is a measured typical result, not
a guaranteed worst-case bound under interference.

The native sender button was tested OFF: forwarding stopped, sampling continued,
and receiver/API/browser cleared numbers and both graphs after the three-second
expiry. ON recovery was then checked with the same processes. The browser showed
83 bpm / estimated SpO2 99.8% with a live pulse trace and no console errors during
the finger test. Receiver service remains enabled at boot. Final source manifests
cover all three version folders and are SHA-256 verified against the correct Pi.

These are application capture-to-receiver times measured with synchronized Pi
UTC clocks, not single-byte radio airtime. Browser display adds its request and
100 ms refresh interval. MAX30102 heart-rate/SpO2 computation still needs an
initial stable acquisition window (approximately eight seconds), and DHT22 has
its physical sampling interval. No transport change can make a sensor produce
a new valid measurement sooner. ECG candidate rates remain explicitly unreliable
when the input is noisy; the upgrade does not change clinical signal quality.

## Synchronizing laptop source with the correct Pi

Install `paramiko` in the laptop Python if needed: `python -m pip install paramiko`.
From `D:\PROJECTS\Immortals`, run:

```powershell
python Sender/sync.py --push
python Receiver/sync.py --push
python Sender/sync.py
python Receiver/sync.py
```

The first two copy source; the last two verify SHA-256 hashes without writing.
Credentials come from `PI_SSH_PASSWORD` or a hidden password prompt. SSH host
keys are pinned to the previously verified devices. Logs, live readings, saved
settings, lock files, and platform-specific virtual environments are excluded.
Source writes use temporary files and atomic rename; no remote files are deleted.
`Sender/sync.py --push` refreshes version 02 from the active root source;
version 01 and the independent version 03 are preserved.

For continuous one-way synchronization while editing, run the relevant command
in a laptop terminal and leave it open:

```powershell
python Sender/sync.py --watch
python Receiver/sync.py --watch
```

Stop with Ctrl+C. A disconnect stops this watcher visibly; rerun after reconnect.
No hidden two-way sync service is installed, and edits do not restart running
apps. Restart the intended app after reviewing/testing synchronized changes.
The existing sender desktop startup starts root `main.py` with Zigbee initially
OFF. The receiver boot service starts its root `main.py` and listens automatically.

## Next stage

Complete source organization, synchronization and verified live transport first.
Then work on the UI and other features in `03_next_upgrade` after the owner's
next instructions. The current stable release remains the active Pi version.
