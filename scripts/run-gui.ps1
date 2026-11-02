# Open the desktop CAD editor with the project virtualenv.
# Usage, from any directory: pwsh -File scripts/run-gui.ps1 [config.json]
param(
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]] $GuiArgs
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$Root = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$Gui = Join-Path $Root ".venv\Scripts\parametric-deco-gui.exe"
if (-not (Test-Path -LiteralPath $Gui)) {
    [Console]::Error.WriteLine("Desktop editor is not installed. From the repository root, run: .\scripts\setup-env.ps1")
    exit 1
}

if ($null -eq $GuiArgs) {
    $GuiArgs = @()
}
Set-Location -LiteralPath $Root
& $Gui @GuiArgs
exit $LASTEXITCODE
