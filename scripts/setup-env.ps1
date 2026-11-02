# Create .venv, install requirements.lock, and install the pinned desktop extra.
# Usage, from any directory: pwsh -File scripts/setup-env.ps1 [-Python python-exe]
param(
    [string] $Python = ""
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$Root = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$VenvDir = Join-Path $Root ".venv"
$VenvPython = Join-Path $VenvDir "Scripts\python.exe"

function Test-SupportedPython {
    param(
        [Parameter(Mandatory = $true)][string] $Executable,
        [string[]] $Prefix = @()
    )
    # Probe failures write "runtime not found" and must not abort the search.
    $PSNativeCommandUseErrorActionPreference = $false
    $null = & $Executable @Prefix -c "import sys; raise SystemExit(0 if (3, 11) <= sys.version_info[:2] < (3, 14) else 1)" 2>&1
    return ($LASTEXITCODE -eq 0)
}

# Prefer 3.12: that is the interpreter recorded with the locked CAD stack.
# A generic List avoids PowerShell flattening nested arrays.
$candidates = [System.Collections.Generic.List[object]]::new()
$candidates.Add(@("py", "-3.12"))
$candidates.Add(@("py", "-3.13"))
$candidates.Add(@("py", "-3.11"))
$candidates.Add(@("python"))
$candidates.Add(@("python3"))

if (-not (Test-Path -LiteralPath $VenvPython)) {
    $launcher = $null
    if ($Python) {
        if (-not (Test-SupportedPython -Executable $Python)) {
            throw "Python at '$Python' is not 3.11, 3.12, or 3.13."
        }
        $launcher = @($Python)
    } else {
        foreach ($candidate in $candidates) {
            $executable = [string]$candidate[0]
            $prefix = @()
            if ($candidate.Count -gt 1) {
                $prefix = @($candidate[1..($candidate.Count - 1)])
            }
            if (-not (Get-Command $executable -ErrorAction SilentlyContinue)) {
                continue
            }
            if (Test-SupportedPython -Executable $executable -Prefix $prefix) {
                $launcher = @($executable) + $prefix
                break
            }
        }
    }
    if (-not $launcher) {
        throw "Python 3.11, 3.12, or 3.13 was not found. Install one, or pass -Python."
    }
    Write-Host "Creating .venv with $($launcher -join ' ')"
    & $launcher[0] @($launcher | Select-Object -Skip 1) -m venv $VenvDir
    if ($LASTEXITCODE -ne 0) {
        exit $LASTEXITCODE
    }
}

if (-not (Test-SupportedPython -Executable $VenvPython)) {
    throw ".venv exists but its Python is outside 3.11-3.13. Remove .venv and run this script again."
}

$pyproject = Get-Content -LiteralPath (Join-Path $Root "pyproject.toml") -Raw
$match = [regex]::Match($pyproject, '(?m)^gui = \["(PySide6==[^"]+)"\]')
if (-not $match.Success) {
    throw "Could not read the gui extra pin from pyproject.toml."
}
$guiPin = $match.Groups[1].Value

function Invoke-VenvPip {
    param([Parameter(Mandatory = $true)][string[]] $PipArgs)
    & $VenvPython -m pip @PipArgs
    if ($LASTEXITCODE -ne 0) {
        exit $LASTEXITCODE
    }
}

Write-Host "Installing pinned dependencies from requirements.lock"
Invoke-VenvPip @("install", "--upgrade", "pip")
Invoke-VenvPip @("install", "--upgrade", "-r", (Join-Path $Root "requirements.lock"))
Write-Host "Installing parametric-deco without re-resolving locked dependencies"
Invoke-VenvPip @("install", "--upgrade", "--no-deps", "-e", $Root)
Write-Host "Installing desktop extra $guiPin"
Invoke-VenvPip @("install", "--upgrade", $guiPin)
Write-Host "Environment ready: $VenvPython"
Write-Host "Open the editor with: .\scripts\run-gui.ps1"
