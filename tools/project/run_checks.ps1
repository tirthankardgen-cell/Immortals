param(
    [string]$ReportPath = '',
    [ValidateSet('workspace', 'sender', 'receiver', 'patient', 'speech', 'website')]
    [string[]]$Only = @()
)

$ErrorActionPreference = 'Stop'
$projectRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..\..')).ProviderPath
$pythonPath = (Get-Command python -ErrorAction Stop).Source
$checkResults = [Collections.Generic.List[object]]::new()
$checkOriginalPath = $env:Path
$checkPreviousBytecode = $env:PYTHONDONTWRITEBYTECODE
$checkPreviousUtf8 = $env:PYTHONUTF8
$checkPreviousPythonPath = $env:PYTHONPATH
$env:PYTHONDONTWRITEBYTECODE = '1'
$env:PYTHONUTF8 = '1'

function Should-RunCheck([string]$Key) {
    return ($Only.Count -eq 0 -or $Key -in $Only)
}

function Invoke-ProjectCheck([string]$Name, [string]$Directory, [scriptblock]$Command, [string]$Key) {
    if (-not (Should-RunCheck $Key)) { return }
    Write-Output "Running $Name"
    $timer = [Diagnostics.Stopwatch]::StartNew()
    $code = 1
    Push-Location -LiteralPath $Directory
    try {
        & $Command
        $code = $LASTEXITCODE
    }
    catch { Write-Output $_.Exception.Message }
    finally { Pop-Location; $timer.Stop() }
    $checkResults.Add([pscustomobject]@{
        name = $Name
        status = $(if ($code -eq 0) { 'passed' } else { 'failed' })
        passed = ($code -eq 0)
        skipped = $false
        exit_code = $code
        seconds = [Math]::Round($timer.Elapsed.TotalSeconds, 2)
    })
}

try {
    Invoke-ProjectCheck 'Workspace navigation' $projectRoot {
        & $pythonPath -B (Join-Path $PSScriptRoot 'check_workspace.py')
    } 'workspace'
    if (Should-RunCheck 'sender') {
        if ([Environment]::OSVersion.Platform -eq [PlatformID]::Win32NT) {
            $reason = 'Requires Linux/Pi fcntl and the documented sender environment.'
            Write-Output "Sender baseline tests: skipped on Windows. $reason"
            $checkResults.Add([pscustomobject]@{
                name = 'Sender baseline tests'; status = 'skipped'; passed = $null
                skipped = $true; exit_code = $null; seconds = 0; reason = $reason
            })
        }
        else {
            Invoke-ProjectCheck 'Sender baseline tests' (Join-Path $projectRoot 'Sender') {
                & $pythonPath -B -m unittest discover -s tests -p 'test_*.py' -v
            } 'sender'
        }
    }
    Invoke-ProjectCheck 'Receiver baseline tests' (Join-Path $projectRoot 'Receiver') {
        & $pythonPath -B -m unittest discover -s tests -p 'test_*.py' -v
    } 'receiver'
    Invoke-ProjectCheck 'Patient v2 cross-role tests' (Join-Path $projectRoot 'Sender_v2') {
        & $pythonPath -B -m unittest discover -s tests -p 'test_*.py' -v
    } 'patient'
    $speechDependencies = Join-Path $projectRoot '.work\cache\test-dependencies'
    if (Should-RunCheck 'speech') {
        if (Test-Path -LiteralPath (Join-Path $speechDependencies 'uroman\__init__.py')) {
            $env:PYTHONPATH = $speechDependencies
            if ($checkPreviousPythonPath) {
                $env:PYTHONPATH += [IO.Path]::PathSeparator + $checkPreviousPythonPath
            }
        }
    }
    Invoke-ProjectCheck 'Speech model-free tests' (Join-Path $projectRoot 'Speech_Test_Phase3') {
        & $pythonPath -B -m unittest discover -s . -p 'test_*.py' -v
    } 'speech'
    $env:PYTHONPATH = $checkPreviousPythonPath
    $nodeRuntime = Join-Path $projectRoot 'Website\.tools\node-v26.13.1-win-x64'
    if (Test-Path -LiteralPath (Join-Path $nodeRuntime 'node.exe')) {
        $env:Path = "$nodeRuntime;$checkOriginalPath"
    }
    Invoke-ProjectCheck 'Website lint, types, tests and build' (Join-Path $projectRoot 'Website') {
        & npm.cmd run check
    } 'website'
}
finally {
    $env:Path = $checkOriginalPath
    $env:PYTHONDONTWRITEBYTECODE = $checkPreviousBytecode
    $env:PYTHONUTF8 = $checkPreviousUtf8
    $env:PYTHONPATH = $checkPreviousPythonPath
}

$failed = @($checkResults | Where-Object { -not $_.skipped -and -not $_.passed })
$skipped = @($checkResults | Where-Object { $_.skipped })
if ($ReportPath) {
    $resultPath = [IO.Path]::GetFullPath((Join-Path $projectRoot $ReportPath))
    $rootPrefix = $projectRoot.TrimEnd('\') + '\'
    if (-not $resultPath.StartsWith($rootPrefix, [StringComparison]::OrdinalIgnoreCase)) {
        throw 'Report path must be inside the workspace.'
    }
    New-Item -ItemType Directory -Path (Split-Path -Parent $resultPath) -Force | Out-Null
    @{ passed = ($failed.Count -eq 0); skipped_checks = $skipped.Count; selected_checks = $Only; checks = @($checkResults.ToArray()) } |
        ConvertTo-Json -Depth 5 | Set-Content -LiteralPath $resultPath -Encoding utf8
}
$checkResults | Format-Table name,status,passed,seconds -AutoSize
if ($failed.Count) { exit 1 }
exit 0
