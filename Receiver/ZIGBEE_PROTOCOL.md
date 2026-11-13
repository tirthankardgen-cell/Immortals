# Immortals live Zigbee protocol

Current release: 11 November 2026. Sender and receiver each keep a matching copy.
See `UPGRADE_NOTES.md` for deployment, version folders, synchronization and measured
latency. Historical full-snapshot transport is retained only as a backup.

## Hardware and timing

- Sender `0013A200408DF0F0`; receiver `0013A200408DF0CE`.
- USB path `/dev/serial/by-id/usb-Silicon_Labs_CP2102_USB_to_UART_Bridge_Controller_0001-if00-port0`.
- Both radio UART settings BD=7 and both Pi applications use 115200 baud, 8N1.
  API mode 1, PAN `0x0C001BEE`, channel `0x16`, AI=0. Firmware is retained.
- RF uses acknowledged addressed transmission between these two radios. Their
  RF link carries sensor data; Wi-Fi is only for SSH and the browser connection.
- The radio reports NP=255, but the verified default RF payload is 84 bytes.
  At high UART speed, 200-byte sends stalled these radios/adapters. Do not
  increase the packet limit based solely on NP. Current wiring needs no change.
- The worker targets a 200 ms interval between starts, but acknowledgement and
  byte throughput set actual cadence. Batches start with the latest state,
  never with a queued old snapshot. Waveforms include at most the latest 500 ms
  and only samples newer than the previous successful capture.
- ON/OFF is controlled by the existing sender button. Default startup is OFF.
  OFF cancels remaining fragments and releases the port when a bounded operation
  returns. A packet already sent cannot be recalled. Sampling/display continue.
  No application-level receiver acknowledgement exists: sender success counters
  confirm radio delivery only. Receiver counters/HTTP verify actual decoding.
- Connection/retry work stays in its own thread. Send/serial timeouts are two
  seconds; failed batches are abandoned and connection is retried after five
  seconds. Opening the SDK performs several bounded operations.

## RF header - 20 bytes

Network byte order `struct.Struct('!2sBBIIHHI')`:

| Offset | Bytes | Meaning |
|---|---|---|
| 0 | 2 | `IM` magic |
| 2 | 1 | Version 2 for compact live data; version 1 for legacy JSON snapshots |
| 3 | 1 | Flags=1: zlib-compressed UTF-8 JSON |
| 4 | 4 | Random per-process session ID |
| 8 | 4 | Sequence, unsigned modulo 2^32 |
| 12 | 2 | Zero-based fragment index |
| 14 | 2 | Total fragment count |
| 16 | 4 | CRC32 of the entire compressed message |
| 20 | remainder | Compressed-message slice |

With the 84-byte cap each fragment carries at most 64 compressed data bytes.
SDK API framing surrounds this RF payload; do not append serial newlines or
decode a fragment as UTF-8 text. Fragments are sent synchronously with successful
transmit status required for each; memory and queued work remain bounded.

## Version 2 compact envelope

The compressed JSON contains a four-item array:

```text
[timestamp, ecg_enabled, sensor_groups, waveform_groups]
```

`timestamp` is the original ISO-8601 UTC capture time; `ecg_enabled` is boolean.
Sensor order is fixed: pulse, ecg, bmp, mlx, dht. Every sensor group is
`[status, age_seconds, values]`. All actual scalar values, status strings, nulls
and ages are preserved. Known measurement dictionary keys are shortened to
`#0` through `#18` and expanded back on the receiver:

| Index | Field | Index | Field |
|---|---|---|---|
| 0 | heart_rate_bpm | 10 | voltage_max_v |
| 1 | spo2_percent | 11 | rail_percent |
| 2 | perfusion_percent | 12 | candidate_bpm |
| 3 | quality_percent | 13 | max_sample_gap_ms |
| 4 | spo2_status | 14 | temperature_c |
| 5 | sample_count | 15 | pressure_hpa |
| 6 | fifo_overflows | 16 | ambient_c |
| 7 | sample_rate_hz | 17 | object_c |
| 8 | voltage_v | 18 | humidity_percent |
| 9 | voltage_min_v | | |

Unknown descriptive field names remain unchanged. The receiver accepts legacy
descriptive keys inside v2 but rejects duplicate expanded keys and invalid compact
indices. Engineering units are restored from the fixed schema; they are not sent
repeatedly. The protocol version and this field table must change together if
field order changes in a future incompatible release.

Waveform order is pulse, ecg. Each waveform is
`[status, clear, time_offset_ms, values]`. Time offsets are relative to capture,
rounded to milliseconds. Samples are rounded to two decimal places. Pulse uses
the existing detrended IR graph; ECG uses the existing 50 Hz notch and 0.5-35 Hz
filter, in millivolts at the ADC, resampled at 125 Hz. Sensor analysis still uses
the full local analysis window, independent of the transmitted batch length.

`clear=true` means the waveform is unavailable/disabled/interrupted and its arrays
must be empty. It immediately clears receiver history. `clear=false` appends
samples; empty arrays can mean no new samples and do not clear earlier history.
The receiver restores schema_version=1, message_type=sensor_snapshot, radio/header
identity, units, and waveform_mode=append for its existing dashboard API.

## Receiver reconstruction and freshness

Only the configured source address is accepted. The receiver bounds compressed
messages to 64 KiB, decompressed JSON to 256 KiB, fragments to 2048 and pending
assemblies to four. It accepts reordered/identical duplicate fragments, rejects
conflicting metadata/duplicates and checks CRC, decompression and all measurement
types before publication. Version is checked across all fragments. Incomplete
assemblies expire after two seconds. Partial values are never displayed.

The receiver rejects old/duplicate sequences, retired sender sessions, backwards
capture time and already stale captures. UTC clocks must be synchronized. Both
Pis currently report NTPSynchronized=yes. Times more than five seconds in the
future are rejected; capture-age calculations are never made negative.

Live waveform points are indexed by absolute capture UTC plus sample offset,
deduplicated, sorted and pruned to eight seconds (maximum 1500 points per trace).
New session, a clear marker, ECG disable or a gap over 800 ms clears old history.
The browser lifts the pen across remaining sample gaps instead of connecting
missing segments. There is no fabricated/interpolated heartbeat. Slow or lost
batches may drop old points beyond the 500 ms sender cap; this is a live display,
not a lossless diagnostic recorder.

Forwarding expires after three seconds using receiver monotonic time plus original
capture age. Sensor age also includes transport time. Scalar validity is three
seconds, except DHT's seven seconds. Stopped/stale data clears values and graphs.
The receiver ignores old disk readings on boot and waits for actual RF data.
Disk persistence runs once per second outside the RF worker; the browser refreshes
100 ms after each response. Network/render time adds to radio delivery latency.

Version 1 remains supported for reconstructed full JSON snapshots with the original
sensor_snapshot schema and complete wave arrays. To use the archived old sender,
its UART settings must match the current modules and fresh captures must arrive
within the configured expiry. It is not the active release.

## Verification

Sender: `cd /home/pi/Desktop/Immortals_Monitor && PYTHONPATH=. .venv/bin/python -m unittest discover -s tests -v`.
Receiver: `cd /home/pi/Desktop/Immortals_Receiver && PYTHONPATH=. .venv/bin/python -m unittest discover -s tests -v`.
32 sender and 22 receiver checks pass in their respective Pi runtimes. Live RF,
browser display, real finger readings, ON/OFF freshness and source hashes are
verified separately. `receiver.delivery_latency_ms` reports the rolling last
256 capture-to-receiver delivery samples with min/median/p95/max; `last_delivery_ms`
reports the most recent sample. These are application latency measurements,
not physical sensor acquisition time or browser paint time.
