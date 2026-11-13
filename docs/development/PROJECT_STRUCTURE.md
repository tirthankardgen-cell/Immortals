# Project structure and development guide

The [master project plan](../../IMMORTALS_MASTER_PROJECT_DOCUMENT_v2.md) governs
the project. Folder conventions below preserve its established source roots
and deployment boundaries.

```text
Immortals/
├── IMMORTALS_MASTER_PROJECT_DOCUMENT_v2.md  main project plan
├── README.md                              project entry point
├── AGENTS.md                              project-wide working guidance
├── GOAL_REQUIREMENTS.md                    requirements navigation note
├── PROJECT_UPGRADE_PLAN.md                 implementation-plan navigation note
├── Sender_v2/                             current sender application
├── Receiver_v2/                           current receiver gateway
├── Website/                               standalone website Git repository
├── Speech_Test_Phase3/                     standalone offline speech tester
├── Sender/                                preserved sender baseline/versions
├── Receiver/                              preserved receiver baseline/versions
├── docs/
│   ├── planning/                          requirements, implementation notes/status
│   ├── architecture/                      supplied architecture images
│   ├── hardware/                          original wiring document
│   └── development/                       structure and organization report
├── tools/project/                         reusable local checks
├── artifacts/                             local evidence, browser captures, logs
├── archive/                               historical sessions/snapshots/references
└── .work/                                 private access note, backups, caches
```

## Component and deployment boundaries

| Local component | Documented deployment | Role |
|---|---|---|
| `Sender_v2/` | `/home/pi/Desktop/Immortals_Monitor_v2` | Offline patient touchscreen and Zigbee sender |
| `Receiver_v2/` | `/home/pi/Desktop/Immortals_Receiver_v2` | Receiver gateway and Firebase uploader |
| `Speech_Test_Phase3/` | `/home/pi/Desktop/Immortals_Speech_Test_Phase3` | Standalone local speech tester |
| `Sender/` | `/home/pi/Desktop/Immortals_Monitor` | Preserved sensor/Zigbee release |
| `Receiver/` | `/home/pi/Desktop/Immortals_Receiver` | Preserved receiver release |
| `Website/` | Its own Git repository/Vercel root | Cloud patient dashboard |

Component `main.py`, launchers, service files, configs, requirements, tests,
documentation and `sync.py` remain beside their application. Use each component's
documented environment; Pi environments and website dependencies are retained.
The receiver v2 service is `immortals-receiver-v2.service`. Source synchronization
is available from [sender v2 sync](../../Sender_v2/sync.py) and
[gateway v2 sync](../../Receiver_v2/sync.py).

## Preserved releases

- `Sender/versions/01_sensor_only/`: original sensor-only snapshot.
- `Sender/versions/02_latest_zigbee/`: sensor/Zigbee release snapshot.
- `Sender/versions/03_next_upgrade/`: independent upgrade-ready snapshot.
- `Receiver/versions/01_live_zigbee/`: receiver release snapshot.
- Component `reference/` folders retain original supplied sources.

These are dated baselines. Active patient development belongs in the v2
components; future integration follows the [master/status mapping](../planning/IMPLEMENTATION_STATUS.md).

## Placing new files

| File type | Location |
|---|---|
| Application code, app tests/config/docs | Corresponding component |
| Cross-component specification or status | `docs/planning/` |
| Architecture drawings and diagrams | `docs/architecture/` |
| Wiring, hardware references | `docs/hardware/` |
| Development/structure guidance | `docs/development/` |
| Reusable workspace checks | `tools/project/` |
| Screenshots and browser evidence | `artifacts/screenshots/`, `artifacts/browser/` |
| Captured validation and logs | `artifacts/validation/`, `artifacts/logs/` |
| Historical one-off scripts and session notes | `archive/work-sessions/` |
| Previous source snapshots / reference downloads | `archive/source-snapshots/`, `archive/references/` |
| Private access, Pi backups, download/model cache | `.work/PI_ACCESS.md`, `.work/backups/`, `.work/cache/` |

Private local material and generated evidence are excluded by the root
`.gitignore`. `Website/.gitignore` continues to govern its separate repository.
Keep runtime patient databases/results and gateway credentials on their intended
devices and outside source synchronization.

## Local verification

From the project root:

```powershell
python -B tools/project/check_workspace.py
./tools/project/run_checks.ps1
```

The runner launches each Python suite in its own component process, avoiding
cross-component `main` import collisions. It covers sender tests, receiver
tests, the v2 cross-role suite in `Sender_v2/tests`, and both model-free speech
suites. The sender baseline imports Linux-only `fcntl`; on Windows the runner
reports that suite as skipped, with its Linux/Pi environment requirement. It then
runs the website's `npm run check` using its existing portable
Node runtime when present. Hardware/model inference and deployment use the
component guides and the master acceptance plan.

The pinned local romanizer can be installed into a private test-only cache:

```powershell
python -m pip install --target .work/cache/test-dependencies uroman==1.3.1.1
./tools/project/run_checks.ps1 -Only speech
```

The runner uses this cache for speech tests and restores the calling environment
afterward. `-Only` can select `workspace`, `sender`, `receiver`, `patient`,
`speech`, or `website` for a focused recheck.

To verify the recorded 13 November organization snapshot explicitly:

```powershell
python -B tools/project/check_workspace.py --record archive/organization/2026-11-13/manifest.json
```

The historical record checks file preservation against that date's baseline.
Later intentional feature changes can differ from that snapshot; routine
structure/link checks use the command without `--record`.
