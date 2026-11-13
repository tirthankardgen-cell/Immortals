# Immortals

Portable, offline-first health screening and patient monitoring on Raspberry Pi 5.

Start with the [master project plan](IMMORTALS_MASTER_PROJECT_DOCUMENT_v2.md).
It is the main plan for the whole project: scope, architecture, hardware direction,
December 2026 target, and acceptance criteria. The [implementation status index](docs/planning/IMPLEMENTATION_STATUS.md)
connects that plan to the current components and their recorded evidence.

## Architecture

**Sensors → sender/local patient record → Zigbee → receiver gateway → Firebase → website.**

The sender operates offline. The gateway owns Firebase uploads. Patient identity,
monitoring sessions, original capture times, durable queues, and independent
acquisition/UI/transport workers are shared requirements across the project.
Offline speech, document capture, VLM processing, and Qwen summaries extend this
same patient workflow under the master plan.

## Components

| Folder | Purpose | Start here |
|---|---|---|
| `Sender_v2/` | Current patient touchscreen, sensor acquisition, recordings, Zigbee outbox | [Sender guide](Sender_v2/README.md) |
| `Receiver_v2/` | Current Zigbee gateway, durable storage, Firebase upload worker | [Gateway guide](Receiver_v2/README.md) |
| `Website/` | Patient dashboard; independent Git repository and Vercel application | [Website guide](Website/README.md) |
| `Speech_Test_Phase3/` | Standalone Hindi/Bengali offline speech and speaker tester | [Speech guide](Speech_Test_Phase3/README.md) |
| `Sender/` | Preserved sensor/Zigbee baseline, original references, three sender versions | [Sender baseline](Sender/project.md) |
| `Receiver/` | Preserved receiver baseline, original references, release snapshot | [Receiver baseline](Receiver/project.md) |

These component folder names and their Pi deployment paths follow the master
plan. Their launchers, environments, and source synchronization remain component-local.

## Project resources

| Location | Contents |
|---|---|
| [Documentation index](docs/README.md) | Planning references, architecture images, original wiring guide, development guidance |
| [Project structure](docs/development/PROJECT_STRUCTURE.md) | Folder map, file placement rules, legacy versions, validation commands |
| `tools/project/` | Workspace verification and local regression-check runner |
| [Artifacts index](artifacts/README.md) | Local screenshots, browser captures, logs, validation evidence |
| [Archive index](archive/README.md) | Historical scripts, source snapshots, references, organization records |
| `.work/` | Private Pi access note, device backups, reusable download/model caches |

`GOAL_REQUIREMENTS.md` and `PROJECT_UPGRADE_PLAN.md` at the root are navigation
notes for their relocated source documents. Supporting plans and historical
snapshots are interpreted through the master plan.

## Local checks

From this project folder:

```powershell
python -B tools/project/check_workspace.py
./tools/project/run_checks.ps1
```

The runner checks workspace links, receiver tests, the v2 cross-role contract,
model-free speech tests, and the website's lint/type/test/build checks. Sender
baseline tests run on Linux and are explicitly reported as skipped on Windows.
Pi hardware and full field acceptance use the component guides and the master
plan's acceptance lists.

For website development:

```powershell
./Website/scripts/with-node.ps1 npm run dev
```

The [organization report](docs/development/ORGANIZATION_REPORT.md) records the
13 November 2026 folder changes, preservation checks, and local test results.
