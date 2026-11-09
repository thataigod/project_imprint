param(
    [string]$Python = ""
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot

if (-not $Python) {
    $candidates = @(
        (Join-Path $root ".venv312\Scripts\python.exe"),
        (Join-Path $root ".venv\Scripts\python.exe")
    )
    foreach ($candidate in $candidates) {
        if (-not (Test-Path -LiteralPath $candidate)) {
            continue
        }
        & $candidate -c "import PyInstaller" 2>$null
        if ($LASTEXITCODE -eq 0) {
            $Python = $candidate
            break
        }
    }
}

if (-not $Python) {
    throw "No Python 3.12 environment found. Create .venv312 or pass -Python <path>."
}

if (Test-Path -LiteralPath $Python) {
    $pythonExe = (Resolve-Path -LiteralPath $Python).Path
} else {
    $command = Get-Command $Python -ErrorAction SilentlyContinue
    if (-not $command) {
        throw "Python executable not found: $Python"
    }
    $pythonExe = $command.Source
}

Write-Host "Building Imprint with $pythonExe"
& $pythonExe -m PyInstaller `
    (Join-Path $root "packaging\imprint.spec") `
    --noconfirm `
    --clean `
    --distpath (Join-Path $root "dist") `
    --workpath (Join-Path $root "build\pyinstaller")

if ($LASTEXITCODE -ne 0) {
    throw "PyInstaller failed with exit code $LASTEXITCODE."
}

$exe = Join-Path $root "dist\Imprint\Imprint.exe"
if (-not (Test-Path -LiteralPath $exe)) {
    throw "Build finished but $exe is missing."
}

Write-Host "Built $exe"
