param([switch]$Elevated)
$ErrorActionPreference = "Stop"
function Test-Admin {
  $identity = [Security.Principal.WindowsIdentity]::GetCurrent()
  $principal = [Security.Principal.WindowsPrincipal]::new($identity)
  return $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
}
if (-not $Elevated -and -not (Test-Admin)) {
  $args = @("-NoProfile","-ExecutionPolicy","Bypass","-File",$PSCommandPath,"-Elevated")
  try {
    $p = Start-Process -FilePath "powershell.exe" -Verb RunAs -ArgumentList $args -Wait -PassThru
    exit $p.ExitCode
  } catch {
    Write-Error "Administrator approval was cancelled or unavailable. $($_.Exception.Message)"
    exit 2
  }
}
$obsRoot = Join-Path $env:ProgramFiles "obs-studio"
$obsExe = Join-Path $obsRoot "bin/64bit/obs64.exe"
if (-not (Test-Path $obsExe)) {
  $winget = Get-Command winget.exe -ErrorAction SilentlyContinue
  if (-not $winget) { throw "Windows Package Manager (winget) is unavailable. Install OBS Studio manually once, then retry setup." }
  & $winget.Source install --id OBSProject.OBSStudio --exact --silent --accept-package-agreements --accept-source-agreements --disable-interactivity
  if ($LASTEXITCODE -ne 0 -and -not (Test-Path $obsExe)) { throw "OBS Studio installation failed (winget exit $LASTEXITCODE)." }
}
if (-not (Test-Path $obsExe)) { throw "OBS Studio was not found after installation." }
$installer = Join-Path $obsRoot "data/obs-plugins/win-dshow/virtualcam-install.bat"
if (Test-Path $installer) {
  & $installer
  if ($LASTEXITCODE -ne 0) { throw "Virtual camera driver registration failed (exit $LASTEXITCODE)." }
}
Write-Output "OBS Virtual Camera components are installed. Close OBS if it opened, then restart ScreenFilter. The app will verify that the virtual camera device can be opened when you start the camera."
