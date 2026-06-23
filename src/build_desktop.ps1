$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$desktopPath = [Environment]::GetFolderPath("Desktop")
$buildName = "PhotoPrivacyExposer"
$desktopFileName = [char]0x7167 + [char]0x7247 + [char]0x9690 + [char]0x5F62 + [char]0x8DB3 + [char]0x8FF9 + [char]0x66DD + [char]0x5149 + [char]0x5668 + ".exe"

Set-Location $projectRoot

python -m pip install -r desktop_requirements.txt

python -m PyInstaller --noconfirm --onefile --windowed --name $buildName --hidden-import=PIL._tkinter_finder desktop_app.py

$builtExe = Join-Path $projectRoot ("dist\" + $buildName + ".exe")
$targetExe = Join-Path $desktopPath $desktopFileName

if (-not (Test-Path $builtExe)) {
    throw "Build failed"
}

Copy-Item -Path $builtExe -Destination $targetExe -Force
Write-Host ("Desktop app ready: " + $targetExe)
