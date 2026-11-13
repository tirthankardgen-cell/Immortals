# Implementation status against the master plan

**Index date:** 13 November 2026. **Main plan:**
[IMMORTALS_MASTER_PROJECT_DOCUMENT_v2.md](../../IMMORTALS_MASTER_PROJECT_DOCUMENT_v2.md),
dated 12 November 2026. **Delivery target:** December 2026, as specified there.

This index maps the master to the inspected local workspace and dated component
reports. Those reports describe prior device/deployment checks. The folder
organization performed on 13 November does not re-certify live hardware or cloud
state. Local checks for the organization are recorded separately in the
[organization report](../development/ORGANIZATION_REPORT.md).

## Workstreams

| Master workstream | Current implementation / evidence | Status against full master acceptance | Remaining work |
|---|---|---|---|
| Stage A: reliable sensor monitor | [Sender v2](../../Sender_v2/README.md), [preserved sensor/Zigbee baseline](../../Sender/project.md), [sender validation](../../Sender_v2/VALIDATION.md) | Implemented but not fully verified | Complete real sensor/signal acceptance, safe ECG verification, retained sensor inventory, touchscreen/startup and sustained operation |
| Stage B: patient workflow and local recordings | [Sender v2](../../Sender_v2/README.md), [patient contract tests](../../Sender_v2/tests/test_patient_flow.py), [patient wire protocol](../../Sender_v2/ZIGBEE_PROTOCOL.md) | Implemented but not fully verified | Complete field acceptance for patient choice/registration, stable recording, immutable context, outages, queue limits, restart and operator usability |
| Stage C: gateway, radio and cloud | [Gateway v2](../../Receiver_v2/README.md), [gateway validation](../../Receiver_v2/VALIDATION.md) | Implemented but not fully verified | Complete combined radio/internet/power-loss and restart checks, acknowledgement semantics, patient isolation, durable recovery and measured latency |
| Stage C: website and patient views | [Website](../../Website/README.md), its local tests and dated deployment notes | Implemented but not fully verified | Complete integrated patient-to-website acceptance and the master plan's release access review; future document/summary views remain separate work |
| Stage D: physical product integration | [Hardware references](../hardware/README.md), master Sections 4 and 15 | In progress | USB microphone is documented/tested; Bluetooth scale, validated LiDAR height, dedicated BP, GPS/camera, battery/isolation, enclosure and IP testing remain open/planned |
| Stage E: standalone speech testing | [Speech tester](../../Speech_Test_Phase3/README.md), [Pi validation report](../../Speech_Test_Phase3/VALIDATION.md) | Implemented but not fully verified | Real live speakers, overlap/noise, sustained sensor/radio/thermal checks and English coverage required by the full plan |
| Stage E: patient-linked speech synchronization | Master Sections 8, 12, 13 and 14; website has a transcript view | Not started / planned | Patient/session audio capture, transcript outbox/transport, gateway persistence, Firebase delivery and end-to-end patient transcript acceptance |
| Stage F: documents, offline VLM and Qwen summaries | Master Section 14 | Not started / planned | Camera workflow, original image retention, local model benchmarks, source-linked summaries, durable records, image transport and patient review UI |
| Field release acceptance | Master Sections 13 and 14.7 | Implemented but not fully verified | Full offline camp simulation and the combined hardware/software/data/field checks across the agreed scope |

## Decisions and implementation differences

- **Speech languages and model:** the master targets Bengali, Hindi and English.
  Its expanded sections require model selection by actual Pi benchmarks. The
  standalone tester currently uses IndicConformer INT8 and Sherpa-ONNX for Hindi
  and Bengali, with native/Roman display. It is local testing evidence, not an
  integrated multilingual patient release. Whisper references remain dated
  candidates/earlier plans; the organization keeps the installed tester intact.
- **Sensor retention:** the master prioritizes patient measurements and marks
  DHT22/BMP180 as removal candidates. The current code retains those prototype
  groups. Final inventory, physical removal, schema compatibility and regression
  testing remain an implementation work item. MLX90614 retention is provisional.
- **Peripheral choices:** weight, height geometry, BP device, GPS/camera,
  power/isolation and enclosure decisions remain in master Section 15. The local
  speech reports identify a tested external USB microphone.
- **Data and connectivity:** patient IDs use `IMM-YYYYMMDD-DEVICE8-COUNTER`;
  sessions and submissions use separate identities. Gateway acceptance follows
  durable storage and is separate from cloud completion. The gateway owns
  Firebase credentials and upload operations.
- **Access:** temporary public website behavior is recorded in the master and
  component notes. The organization adds no access-policy change; follow the
  master's release review and current owner instructions for later work.

## Keeping this index current

Use the master's four status categories and attach dated evidence before moving
an item to **Done and verified**. Distinguish model-free local tests, reference
audio benchmarks, actual Pi checks, cloud checks, and full field acceptance.
Update this index when implementation changes; keep the master as the main plan
and retain dated historical documents and original validation evidence.
