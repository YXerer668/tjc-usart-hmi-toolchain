param(
    [string]$Output = "camera_usb_cam.jpg",
    [string]$Device = "USB Cam",
    [string]$PixelFormat = "yuyv422",
    [int]$Width = 2560,
    [int]$Height = 1440,
    [int]$Framerate = 30,
    [double]$WarmupSeconds = 1.0
)

$ErrorActionPreference = "Stop"

$outputPath = [System.IO.Path]::GetFullPath($Output)
$outputDir = [System.IO.Path]::GetDirectoryName($outputPath)
if ($outputDir -and -not (Test-Path -LiteralPath $outputDir)) {
    New-Item -ItemType Directory -Force -Path $outputDir | Out-Null
}

$videoSize = "${Width}x${Height}"
$ffmpegArgs = @(
    "-hide_banner",
    "-y",
    "-f", "dshow",
    "-pixel_format", $PixelFormat,
    "-video_size", $videoSize,
    "-framerate", "$Framerate",
    "-i", "video=$Device"
)

if ($WarmupSeconds -gt 0) {
    $ffmpegArgs += @("-ss", "$WarmupSeconds")
}

$ffmpegArgs += @(
    "-frames:v", "1",
    "-update", "1",
    $outputPath
)

& ffmpeg @ffmpegArgs

if (-not (Test-Path -LiteralPath $outputPath)) {
    throw "Capture failed: $outputPath was not created"
}

Get-Item -LiteralPath $outputPath | Select-Object FullName,Length,LastWriteTime
