$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$ProjectRoot = Split-Path -Parent $PSScriptRoot
$BuildEnvironment = Join-Path $ProjectRoot ".venv-build"
$Python = Join-Path $BuildEnvironment "Scripts\python.exe"
Set-Location $ProjectRoot

function Invoke-Checked {
    param(
        [Parameter(Mandatory = $true)][string]$Command,
        [Parameter(ValueFromRemainingArguments = $true)][string[]]$Arguments
    )

    # Windows PowerShell 5.1 converts any native stderr output into a
    # NativeCommandError when the global preference is Stop. Let the program
    # finish and use its real process exit code instead.
    $PreviousErrorActionPreference = $ErrorActionPreference
    try {
        $ErrorActionPreference = "Continue"
        & $Command @Arguments
        $ExitCode = $LASTEXITCODE
    }
    finally {
        $ErrorActionPreference = $PreviousErrorActionPreference
    }

    if ($ExitCode -ne 0) {
        throw "Command failed with exit code $ExitCode`: $Command $($Arguments -join ' ')"
    }
}

function Test-BuildEnvironment {
    if (-not (Test-Path $Python)) {
        return $false
    }
    try {
        $Process = Start-Process -FilePath $Python `
            -ArgumentList @("-m", "pip", "--version") `
            -Wait -PassThru -WindowStyle Hidden
        return $Process.ExitCode -eq 0
    }
    catch {
        return $false
    }
}

function Test-PythonSelector {
    param([Parameter(Mandatory = $true)][string]$Selector)

    try {
        $Process = Start-Process -FilePath "py.exe" `
            -ArgumentList @($Selector, "--version") `
            -Wait -PassThru -WindowStyle Hidden
        return $Process.ExitCode -eq 0
    }
    catch {
        return $false
    }
}

function Get-PythonSelector {
    if (-not (Get-Command py.exe -ErrorAction SilentlyContinue)) {
        return $null
    }

    if (Test-PythonSelector "-3.12") {
        return "-3.12"
    }

    if (Test-PythonSelector "-3.13") {
        return "-3.13"
    }

    return $null
}

function Install-PythonRuntime {
    $Winget = Get-Command winget.exe -ErrorAction SilentlyContinue
    if (-not $Winget) {
        throw "Python 3.12 or 3.13 is missing and Windows Package Manager is unavailable. Install 64-bit Python 3.12 from https://www.python.org/downloads/windows/ and select 'Install launcher for all users'."
    }

    Write-Host "Python 3.12 is not installed. Installing it through Windows Package Manager..." -ForegroundColor Yellow
    Invoke-Checked -Command $Winget.Source -Arguments @(
        "install", "--id", "Python.Python.3.12", "--exact", "--silent",
        "--accept-package-agreements", "--accept-source-agreements"
    )
}

function Find-InnoCompiler {
    $Command = Get-Command ISCC.exe -ErrorAction SilentlyContinue
    $Candidates = @(
        @(
            $(if ($Command) { $Command.Source }),
            "${env:ProgramFiles}\Inno Setup 7\ISCC.exe",
            "${env:ProgramFiles(x86)}\Inno Setup 7\ISCC.exe",
            "${env:LOCALAPPDATA}\Programs\Inno Setup 7\ISCC.exe",
            "${env:ProgramFiles}\Inno Setup 6\ISCC.exe",
            "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe",
            "${env:LOCALAPPDATA}\Programs\Inno Setup 6\ISCC.exe"
        ) | Where-Object { $_ -and (Test-Path $_) }
    )

    if ($Candidates) {
        return $Candidates[0]
    }
    return $null
}

Write-Host "prxmpt 1.0.9 Windows update builder" -ForegroundColor Cyan
Write-Host "Project: $ProjectRoot"
Write-Host ""

if (-not (Test-BuildEnvironment)) {
    if (Test-Path $BuildEnvironment) {
        Write-Host "The previous build environment is incomplete. Replacing it..." -ForegroundColor Yellow
        Remove-Item -LiteralPath $BuildEnvironment -Recurse -Force
    }

    $PythonSelector = Get-PythonSelector
    if (-not $PythonSelector) {
        Install-PythonRuntime
        $PythonSelector = Get-PythonSelector
    }

    if (-not $PythonSelector) {
        throw "Python was installed, but the Python Launcher has not refreshed yet. Close this window and run BUILD_INSTALLER.bat again."
    }

    Write-Host "Creating a clean Python build environment using $PythonSelector..."
    Invoke-Checked -Command "py.exe" -Arguments @($PythonSelector, "-m", "venv", $BuildEnvironment)
}

Write-Host "Repairing and updating packaging tools..."
Invoke-Checked -Command $Python -Arguments @("-m", "ensurepip", "--upgrade")
Invoke-Checked -Command $Python -Arguments @("-m", "pip", "install", "--upgrade", "pip", "setuptools", "wheel")

Write-Host "Installing prxmpt build dependencies..."
Invoke-Checked -Command $Python -Arguments @("-m", "pip", "install", "-e", ".[dev]")

Write-Host "Running automated tests..."
Invoke-Checked -Command $Python -Arguments @("-m", "pytest")

Write-Host "Preparing the bundled tiny.en speech model..."
Invoke-Checked -Command $Python -Arguments @(
    "scripts\fetch_tiny_model.py", "--output", "build\models\faster-whisper-tiny.en"
)

Write-Host "Building the standalone application..."
Invoke-Checked -Command $Python -Arguments @("-m", "PyInstaller", "--noconfirm", "--clean", "build\clearcue.spec")

$InnoCompiler = Find-InnoCompiler
if (-not $InnoCompiler) {
    $Winget = Get-Command winget.exe -ErrorAction SilentlyContinue
    if (-not $Winget) {
        throw "Inno Setup is missing and Windows Package Manager is unavailable. Install Inno Setup from https://jrsoftware.org/isdl.php and run this builder again."
    }

    Write-Host "Installing Inno Setup through Windows Package Manager..." -ForegroundColor Yellow
    Invoke-Checked -Command $Winget.Source -Arguments @(
        "install", "--id", "JRSoftware.InnoSetup", "--exact", "--silent",
        "--accept-package-agreements", "--accept-source-agreements"
    )
    $InnoCompiler = Find-InnoCompiler
}

if (-not $InnoCompiler) {
    throw "Inno Setup was installed but ISCC.exe could not be located. Restart Windows, then run BUILD_INSTALLER.bat again."
}

Write-Host "Creating prxmptUpdate_1.0.9.exe..."
Invoke-Checked -Command $InnoCompiler -Arguments @("installer\prxmpt.iss")

$Installer = Join-Path $ProjectRoot "installer\output\prxmptUpdate_1.0.9.exe"
if (-not (Test-Path $Installer)) {
    throw "The installer compiler finished but prxmptUpdate_1.0.9.exe was not created."
}

Write-Host ""
Write-Host "SUCCESS" -ForegroundColor Green
Write-Host "Installer created at:" -ForegroundColor Green
Write-Host $Installer -ForegroundColor White
Write-Host ""
if ($env:GITHUB_ACTIONS -ne "true") {
    Start-Process explorer.exe -ArgumentList "/select,`"$Installer`""
}
