# Workspace maintenance tools

Run these from the Immortals project root. Python 3.11+ and the installed
component test dependencies are used. Website checks use its existing Node
26 portable runtime when available. The sender baseline requires Linux/Pi
`fcntl`; the runner explicitly reports it as skipped on Windows.

| Tool | Purpose |
|---|---|
| `check_workspace.py` | Verify component entry points and local documentation links; optionally verify a dated organization manifest by SHA-256 |
| `run_checks.ps1` | Run workspace navigation, independent Python test suites and the website's existing lint/type/test/build command |

```powershell
python -B tools/project/check_workspace.py
./tools/project/run_checks.ps1
```

Optional recorded-snapshot validation:

```powershell
python -B tools/project/check_workspace.py --record archive/organization/2026-11-13/manifest.json --report artifacts/validation/organization/2026-11-13/preservation.json
./tools/project/run_checks.ps1 -ReportPath artifacts/validation/organization/2026-11-13/checks.json
```

These are local verification tools. Follow the component guides for hardware
operation and source synchronization. Archived deployment/repair helpers retain
their earlier working-directory assumptions. See the
[project structure guide](../../docs/development/PROJECT_STRUCTURE.md) and
[organization report](../../docs/development/ORGANIZATION_REPORT.md).

If the pinned romanizer is absent from the selected Python environment, install
it into the private test cache and run the speech checks:

```powershell
python -m pip install --target .work/cache/test-dependencies uroman==1.3.1.1
./tools/project/run_checks.ps1 -Only speech
```

`-Only` accepts `workspace`, `sender`, `receiver`, `patient`, `speech`, and
`website`. A report records the checks actually selected, including any explicit
platform skip. The speech cache applies only to its test process; existing Pi
runtime environments and application requirements remain component-local.
