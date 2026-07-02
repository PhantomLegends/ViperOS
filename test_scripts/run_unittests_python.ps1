#!/usr/bin/env pwsh

param(
    [string]$Subfolder
)

$ErrorActionPreference = 'Stop'
$UnrecoverableErrorExitCode = 69

function Write-StepBanner {
    param(
        [int]$StepNumber,
        [string]$Title
    )

    Write-Host ""
    Write-Host ("===== [{0}/7] {1} =====" -f $StepNumber, $Title)
}

function Write-CommandLine {
    param(
        [string]$CommandText
    )

    Write-Host ("+ {0}" -f $CommandText)
}

function Write-FailureContext {
    param(
        [int]$ExitCode
    )

    Write-Host ("Command failed with exit code {0}." -f $ExitCode)
    Write-Host ("Working directory: {0}" -f (Get-Location).Path)
    Write-Host ("PATH={0}" -f $env:PATH)
    Write-Host ("PYTHONPATH={0}" -f $env:PYTHONPATH)
    Write-Host ("VIRTUAL_ENV={0}" -f $env:VIRTUAL_ENV)
}

if ([string]::IsNullOrWhiteSpace($Subfolder) -or $args.Count -gt 0) {
    Write-Host "Error: No subfolder name provided."
    Write-Host "Usage: $($MyInvocation.MyCommand.Name) <subfolder_name>"
    exit 1
}

$InvocationRoot = (Get-Location).Path
$SourceFolder = Join-Path $InvocationRoot $Subfolder
$WorkingFolder = Join-Path $InvocationRoot (Join-Path '.tmp' ("python_{0}" -f $Subfolder))
$VenvFolder = Join-Path $WorkingFolder '.venv'
$VenvScriptsFolder = Join-Path $VenvFolder 'Scripts'
$VenvPython = Join-Path $VenvScriptsFolder 'python.exe'

Write-StepBanner 1 "Toolchain check"

function Find-WorkingPython {
    $Candidates = [System.Collections.Generic.List[string]]::new()

    if (-not [string]::IsNullOrWhiteSpace($env:APPDATA)) {
        $UvPythonRoot = Join-Path $env:APPDATA 'uv\python'
        if (Test-Path -LiteralPath $UvPythonRoot -PathType Container) {
            Get-ChildItem -Path (Join-Path $UvPythonRoot 'cpython-3.12*-windows-*\python.exe') `
                -File -ErrorAction SilentlyContinue |
                Sort-Object FullName -Descending |
                ForEach-Object { $Candidates.Add($_.FullName) }
        }
    }

    if (-not [string]::IsNullOrWhiteSpace($env:LOCALAPPDATA)) {
        $Candidates.Add((Join-Path $env:LOCALAPPDATA 'Programs\Python\Python312\python.exe'))
    }

    $UvCommand = Get-Command uv -ErrorAction SilentlyContinue
    if ($UvCommand) {
        $env:UV_CACHE_DIR = Join-Path $InvocationRoot '.tmp\uv-cache'
        $ManagedPython = (& $UvCommand.Source python find 3.12 2>$null | Select-Object -First 1)
        if ($LASTEXITCODE -eq 0 -and (Test-Path -LiteralPath $ManagedPython -PathType Leaf)) {
            $Candidates.Add($ManagedPython)
        }
    }

    foreach ($Name in @('python', 'python3')) {
        $Command = Get-Command $Name -ErrorAction SilentlyContinue
        if (-not $Command -or $Command.Source -match 'WindowsApps') {
            continue
        }

        $Candidates.Add($Command.Source)
    }

    $Launchers = [System.Collections.Generic.List[string]]::new()
    $PyCommand = Get-Command py -ErrorAction SilentlyContinue
    if ($PyCommand) {
        $Launchers.Add($PyCommand.Source)
    }
    if (-not [string]::IsNullOrWhiteSpace($env:LOCALAPPDATA)) {
        $Launchers.Add((Join-Path $env:LOCALAPPDATA 'Programs\Python\Launcher\py.exe'))
    }
    foreach ($Launcher in ($Launchers | Select-Object -Unique)) {
        if (-not (Test-Path -LiteralPath $Launcher -PathType Leaf)) {
            continue
        }
        $PreviousPreference = $ErrorActionPreference
        $ErrorActionPreference = 'Continue'
        $ResolvedPython = (& $Launcher -3.12 -c 'import sys; print(sys.executable)' 2>$null | Select-Object -First 1)
        $LauncherExitCode = $LASTEXITCODE
        $ErrorActionPreference = $PreviousPreference
        if ($LauncherExitCode -eq 0 -and -not [string]::IsNullOrWhiteSpace($ResolvedPython)) {
            $Candidates.Add($ResolvedPython)
        }
    }

    foreach ($Candidate in ($Candidates | Select-Object -Unique)) {
        if (-not (Test-Path -LiteralPath $Candidate -PathType Leaf)) {
            continue
        }
        $PreviousPreference = $ErrorActionPreference
        $ErrorActionPreference = 'Continue'
        & $Candidate --version *> $null
        $ExitCode = $LASTEXITCODE
        $ErrorActionPreference = $PreviousPreference
        if ($ExitCode -eq 0) {
            return $Candidate
        }
    }

    return $null
}

$PythonExecutable = Find-WorkingPython
if (-not $PythonExecutable) {
    Write-Host "Error: Python interpreter not found. Please install Python."
    exit $UnrecoverableErrorExitCode
}

Write-Host ("Python command: {0}" -f $PythonExecutable)
Write-CommandLine ("`"{0}`" --version" -f $PythonExecutable)
& $PythonExecutable --version 2>&1 | ForEach-Object {
    Write-Host $_
}

Write-StepBanner 2 "Argument validation"

if (-not (Test-Path -LiteralPath $SourceFolder -PathType Container)) {
    Write-Host ("Error: Source build folder '{0}' does not exist." -f $SourceFolder)
    exit 2
}

Write-Host ("Source folder: {0}" -f (Resolve-Path -LiteralPath $SourceFolder).Path)
Write-Host ("Requested subfolder: {0}" -f $Subfolder)

Write-StepBanner 3 "Working directory setup"

Write-Host ("Working folder: {0}" -f $WorkingFolder)

if (Test-Path -LiteralPath $WorkingFolder) {
    Write-Host "Cleaning existing working folder."
    Get-ChildItem -LiteralPath $WorkingFolder -Force | Remove-Item -Recurse -Force
} else {
    Write-Host "Creating working folder."
    New-Item -ItemType Directory -Path $WorkingFolder -Force | Out-Null
}

Write-StepBanner 4 "Copy the build"

Write-Host ("Copying from {0}" -f (Resolve-Path -LiteralPath $SourceFolder).Path)
Write-Host ("Copy target: {0}" -f $WorkingFolder)
Write-CommandLine ("Copy-Item -Path `"{0}\*`" -Destination `"{1}`" -Recurse -Force" -f $SourceFolder, $WorkingFolder)
Copy-Item -Path (Join-Path $SourceFolder '*') -Destination $WorkingFolder -Recurse -Force

Write-StepBanner 5 "Enter the working directory"

try {
    Set-Location -LiteralPath $WorkingFolder
} catch {
    Write-Host ("Error: Could not enter working folder '{0}'." -f $WorkingFolder)
    exit 2
}

Write-Host ("Current working directory: {0}" -f (Get-Location).Path)

Write-StepBanner 6 "Install dependencies"

Write-Host ("Creating isolated virtual environment at {0}" -f $VenvFolder)
Write-CommandLine ("`"{0}`" -m venv `".venv`"" -f $PythonExecutable)
& $PythonExecutable -m venv .venv
if ($LASTEXITCODE -ne 0) {
    Write-FailureContext $LASTEXITCODE
    exit $LASTEXITCODE
}

Write-Host ("Installing dependencies from {0}" -f (Join-Path (Get-Location).Path 'requirements.txt'))
Write-CommandLine ("`"{0}`" -m pip install -r requirements.txt bcrypt==4.0.1" -f $VenvPython)
& $VenvPython -m pip install -r requirements.txt 'bcrypt==4.0.1'
if ($LASTEXITCODE -ne 0) {
    Write-FailureContext $LASTEXITCODE
    exit $LASTEXITCODE
}

Write-StepBanner 7 "Run the tests"

Write-Host ("Running tests with {0}" -f $VenvPython)
Write-CommandLine ("`"{0}`" -m pytest" -f $VenvPython)
& $VenvPython -m pytest
$TestExitCode = $LASTEXITCODE

if ($TestExitCode -ne 0) {
    Write-FailureContext $TestExitCode
    Write-Host ("Summary: `"{0}`" exited with code {1} in {2}" -f "$VenvPython -m pytest", $TestExitCode, (Get-Location).Path)
    exit $TestExitCode
}

Write-Host ("Summary: `"{0}`" exited with code 0 in {1}" -f "$VenvPython -m pytest", (Get-Location).Path)
exit 0
