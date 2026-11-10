param(
  [Parameter(Mandatory = $true)][string]$BuiltExe,
  [Parameter(Mandatory = $true)][string]$DownloadEndpoint,
  [Parameter(Mandatory = $true)][string]$ExpectedAssetUrl
)

$ErrorActionPreference = "Stop"
if (!(Test-Path -LiteralPath $BuiltExe -PathType Leaf)) {
  throw "Built EXE not found: $BuiltExe"
}

$source = Get-Item -LiteralPath $BuiltExe
$sourceHash = (Get-FileHash -LiteralPath $BuiltExe -Algorithm SHA256).Hash
Write-Host "Built EXE: $($source.Length) bytes; SHA-256 $sourceHash"

# Wait briefly for the Vercel deployment triggered by the main-branch push.
$redirect = $null
for ($attempt = 1; $attempt -le 18; $attempt++) {
  $handler = [System.Net.Http.HttpClientHandler]::new()
  $handler.AllowAutoRedirect = $false
  $client = [System.Net.Http.HttpClient]::new($handler)
  try {
    $response = $client.GetAsync(
      $DownloadEndpoint,
      [System.Net.Http.HttpCompletionOption]::ResponseHeadersRead
    ).GetAwaiter().GetResult()
    try {
      if ([int]$response.StatusCode -eq 302 -and $response.Headers.Location) {
        $redirect = [uri]::new([uri]$DownloadEndpoint, $response.Headers.Location)
        break
      }
      Write-Host "Attempt $attempt: endpoint returned HTTP $([int]$response.StatusCode); waiting for deployment."
    } finally {
      $response.Dispose()
    }
  } catch {
    Write-Host "Attempt $attempt: endpoint not ready yet: $($_.Exception.Message)"
  } finally {
    $client.Dispose()
  }
  Start-Sleep -Seconds 10
}

if (!$redirect) {
  throw "The live download endpoint did not return an HTTP 302 redirect within 3 minutes."
}
if ($redirect.AbsoluteUri -ne $ExpectedAssetUrl) {
  throw "Unexpected redirect target: $($redirect.AbsoluteUri)"
}
Write-Host "PASS: $DownloadEndpoint redirects to the expected latest EXE asset."

# Follow the published GitHub Release redirect and download the actual bytes.
$downloadPath = Join-Path $env:RUNNER_TEMP "screenfilter-integration-download.exe"
$downloadHandler = [System.Net.Http.HttpClientHandler]::new()
$downloadHandler.AllowAutoRedirect = $true
$downloadClient = [System.Net.Http.HttpClient]::new($downloadHandler)
$downloadClient.Timeout = [TimeSpan]::FromMinutes(10)
try {
  $downloadResponse = $downloadClient.GetAsync(
    $redirect,
    [System.Net.Http.HttpCompletionOption]::ResponseHeadersRead
  ).GetAwaiter().GetResult()
  try {
    if (!$downloadResponse.IsSuccessStatusCode) {
      throw "Published EXE download returned HTTP $([int]$downloadResponse.StatusCode)."
    }
    $finalUri = $downloadResponse.RequestMessage.RequestUri
    if ($finalUri.Scheme -ne "https") {
      throw "Final EXE download did not use HTTPS: $finalUri"
    }
    $inputStream = $downloadResponse.Content.ReadAsStreamAsync().GetAwaiter().GetResult()
    $outputStream = [System.IO.File]::Create($downloadPath)
    try {
      $inputStream.CopyTo($outputStream)
    } finally {
      $outputStream.Dispose()
      $inputStream.Dispose()
    }
  } finally {
    $downloadResponse.Dispose()
  }
} finally {
  $downloadClient.Dispose()
}

$downloaded = Get-Item -LiteralPath $downloadPath
$downloadHash = (Get-FileHash -LiteralPath $downloadPath -Algorithm SHA256).Hash
if ($downloaded.Length -ne $source.Length) {
  throw "Downloaded EXE size mismatch: expected $($source.Length), got $($downloaded.Length)."
}
if ($downloadHash -ne $sourceHash) {
  throw "Downloaded EXE SHA-256 mismatch: expected $sourceHash, got $downloadHash."
}
$signature = [System.IO.File]::ReadAllBytes($downloadPath)
if ($signature.Length -lt 2 -or $signature[0] -ne 0x4D -or $signature[1] -ne 0x5A) {
  throw "Downloaded file does not have a Windows PE MZ signature."
}
Write-Host "PASS: live endpoint redirected, published EXE downloaded, and bytes match the CI-built EXE."
Write-Host "Downloaded $($downloaded.Length) bytes; SHA-256 $downloadHash."
