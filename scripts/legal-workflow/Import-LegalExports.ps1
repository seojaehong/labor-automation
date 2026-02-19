[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string]$CasePath,

    [string]$SourcePath = (Join-Path $env:USERPROFILE "Downloads"),

    [int]$SinceHours = 12,

    [string[]]$Extensions = @("doc", "docx", "hwp", "hwpx", "pdf", "txt", "md"),

    [ValidateSet("auto", "lbox", "superlawyer", "bigcase", "other")]
    [string]$Platform = "auto",

    [switch]$Move
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Get-NormalizedExtensionSet {
    param([string[]]$InputExtensions)
    return $InputExtensions |
        ForEach-Object { $_.Trim().TrimStart(".").ToLowerInvariant() } |
        Where-Object { -not [string]::IsNullOrWhiteSpace($_) } |
        Select-Object -Unique
}

function Get-PlatformName {
    param(
        [string]$FileName,
        [string]$RequestedPlatform
    )

    if ($RequestedPlatform -ne "auto") {
        return $RequestedPlatform
    }

    $name = $FileName.ToLowerInvariant()
    if ($name -match "lbox|엘박스") {
        return "lbox"
    }
    if ($name -match "superlawyer|슈퍼로이어") {
        return "superlawyer"
    }
    if ($name -match "bigcase|빅케이스") {
        return "bigcase"
    }
    return "other"
}

function Get-SafeBaseName {
    param([string]$BaseName)
    $clean = $BaseName -replace '[\\/:*?"<>|]+', "-" -replace "\s+", "_" -replace "_{2,}", "_"
    $clean = $clean.Trim("._-")
    if ([string]::IsNullOrWhiteSpace($clean)) {
        return "file"
    }
    return $clean
}

if (-not (Test-Path -LiteralPath $CasePath)) {
    throw "CasePath not found: $CasePath"
}
if (-not (Test-Path -LiteralPath $SourcePath)) {
    throw "SourcePath not found: $SourcePath"
}

$extensionSet = Get-NormalizedExtensionSet -InputExtensions $Extensions
$cutoff = (Get-Date).AddHours(-1 * [Math]::Abs($SinceHours))
$caseRoot = (Resolve-Path -LiteralPath $CasePath).Path

$files = Get-ChildItem -LiteralPath $SourcePath -File |
    Where-Object {
        ($_.Extension.TrimStart(".").ToLowerInvariant() -in $extensionSet) -and
        ($_.LastWriteTime -ge $cutoff)
    } |
    Sort-Object LastWriteTime

if ($files.Count -eq 0) {
    Write-Host "No matching files found in '$SourcePath' since $($cutoff.ToString("yyyy-MM-dd HH:mm:ss"))."
    return
}

$records = New-Object System.Collections.Generic.List[object]

foreach ($file in $files) {
    $platformName = Get-PlatformName -FileName $file.Name -RequestedPlatform $Platform
    $destinationDir = Join-Path $caseRoot ("03_platform_exports\" + $platformName)
    New-Item -ItemType Directory -Path $destinationDir -Force | Out-Null

    $stamp = $file.LastWriteTime.ToString("yyyyMMdd_HHmmss")
    $safeBase = Get-SafeBaseName -BaseName ([System.IO.Path]::GetFileNameWithoutExtension($file.Name))
    $ext = $file.Extension.ToLowerInvariant()
    $destinationName = "{0}_{1}_{2}{3}" -f $stamp, $platformName, $safeBase, $ext
    $destinationPath = Join-Path $destinationDir $destinationName

    $counter = 1
    while (Test-Path -LiteralPath $destinationPath) {
        $destinationName = "{0}_{1}_{2}_{3}{4}" -f $stamp, $platformName, $safeBase, $counter, $ext
        $destinationPath = Join-Path $destinationDir $destinationName
        $counter++
    }

    if ($Move) {
        Move-Item -LiteralPath $file.FullName -Destination $destinationPath
        $operation = "move"
    } else {
        Copy-Item -LiteralPath $file.FullName -Destination $destinationPath
        $operation = "copy"
    }

    $destItem = Get-Item -LiteralPath $destinationPath
    $hash = (Get-FileHash -LiteralPath $destinationPath -Algorithm SHA256).Hash

    $records.Add([PSCustomObject]@{
        imported_at_utc       = (Get-Date).ToUniversalTime().ToString("o")
        source_file           = $file.FullName
        destination_file      = $destinationPath
        platform              = $platformName
        size_bytes            = $destItem.Length
        sha256                = $hash
        source_last_write_utc = $file.LastWriteTime.ToUniversalTime().ToString("o")
        operation             = $operation
    }) | Out-Null
}

$logPath = Join-Path $caseRoot "07_audit\import-log.csv"
if (Test-Path -LiteralPath $logPath) {
    $records | Export-Csv -LiteralPath $logPath -NoTypeInformation -Append -Encoding UTF8
} else {
    $records | Export-Csv -LiteralPath $logPath -NoTypeInformation -Encoding UTF8
}

$grouped = $records | Group-Object platform | Sort-Object Count -Descending
Write-Host "Imported files: $($records.Count)"
foreach ($group in $grouped) {
    Write-Host ("- {0}: {1}" -f $group.Name, $group.Count)
}
Write-Host "Audit log updated: $logPath"
