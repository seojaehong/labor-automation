[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string]$CasePath,

    [string]$OutputPath = "",

    [switch]$IncludeDocxPreview,

    [int]$DocxPreviewChars = 1200
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Read-OrDefault {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Path,
        [Parameter(Mandatory = $true)]
        [string]$DefaultValue
    )

    if (Test-Path -LiteralPath $Path) {
        return Get-Content -LiteralPath $Path -Raw
    }
    return $DefaultValue
}

function Get-RelativePathText {
    param(
        [Parameter(Mandatory = $true)]
        [string]$BasePath,
        [Parameter(Mandatory = $true)]
        [string]$TargetPath
    )

    $base = (Resolve-Path -LiteralPath $BasePath).Path.TrimEnd("\")
    $target = (Resolve-Path -LiteralPath $TargetPath).Path
    $baseUri = [System.Uri]($base + "\")
    $targetUri = [System.Uri]$target
    return [System.Uri]::UnescapeDataString($baseUri.MakeRelativeUri($targetUri).ToString()).Replace("/", "\")
}

function Get-DocxPreviewText {
    param(
        [Parameter(Mandatory = $true)]
        [string]$DocxPath,
        [Parameter(Mandatory = $true)]
        [int]$MaxChars
    )

    Add-Type -AssemblyName System.IO.Compression.FileSystem
    $archive = $null
    try {
        $archive = [System.IO.Compression.ZipFile]::OpenRead($DocxPath)
        $entry = $archive.GetEntry("word/document.xml")
        if ($null -eq $entry) {
            return ""
        }

        $stream = $entry.Open()
        $reader = New-Object System.IO.StreamReader($stream)
        $xml = $reader.ReadToEnd()
        $reader.Dispose()
        $stream.Dispose()

        $text = $xml -replace "</w:p>", "`n" -replace "</w:tr>", "`n" -replace "<[^>]+>", " "
        $text = [System.Net.WebUtility]::HtmlDecode($text)
        $text = ($text -replace "\s+", " ").Trim()

        if ($text.Length -gt $MaxChars) {
            return $text.Substring(0, $MaxChars) + " ..."
        }
        return $text
    } catch {
        return ""
    } finally {
        if ($null -ne $archive) {
            $archive.Dispose()
        }
    }
}

if (-not (Test-Path -LiteralPath $CasePath)) {
    throw "CasePath not found: $CasePath"
}

$caseRoot = (Resolve-Path -LiteralPath $CasePath).Path
if ([string]::IsNullOrWhiteSpace($OutputPath)) {
    $OutputPath = Join-Path $caseRoot "05_drafts\agent-brief.md"
}

$metaPath = Join-Path $caseRoot "00_admin\case-meta.yaml"
$factsPath = Join-Path $caseRoot "01_intake\facts.md"
$questionsPath = Join-Path $caseRoot "02_research\questions.md"
$authorityPath = Join-Path $caseRoot "04_authority_notes\authority-notes.md"
$exportsPath = Join-Path $caseRoot "03_platform_exports"

$metaText = Read-OrDefault -Path $metaPath -DefaultValue "case_id: unknown"
$factsText = Read-OrDefault -Path $factsPath -DefaultValue "# Facts`n`n(no facts yet)"
$questionsText = Read-OrDefault -Path $questionsPath -DefaultValue "# Research Questions`n`n1. (none yet)"
$authorityText = Read-OrDefault -Path $authorityPath -DefaultValue "# Authority Notes`n`n(no authority notes yet)"

$files = @()
if (Test-Path -LiteralPath $exportsPath) {
    $files = @(Get-ChildItem -LiteralPath $exportsPath -File -Recurse | Sort-Object LastWriteTime -Descending)
}

$builder = New-Object System.Text.StringBuilder
$generatedAt = (Get-Date).ToString("yyyy-MM-dd HH:mm:ss zzz")

[void]$builder.AppendLine("# Agent Packet")
[void]$builder.AppendLine()
[void]$builder.AppendLine("Generated at: $generatedAt")
[void]$builder.AppendLine("Case path: $caseRoot")
[void]$builder.AppendLine()

[void]$builder.AppendLine("## 1) Case Metadata")
[void]$builder.AppendLine('```yaml')
[void]$builder.AppendLine($metaText.Trim())
[void]$builder.AppendLine('```')
[void]$builder.AppendLine()

[void]$builder.AppendLine("## 2) Facts")
[void]$builder.AppendLine($factsText.Trim())
[void]$builder.AppendLine()

[void]$builder.AppendLine("## 3) Research Questions")
[void]$builder.AppendLine($questionsText.Trim())
[void]$builder.AppendLine()

[void]$builder.AppendLine("## 4) Authority Notes")
[void]$builder.AppendLine($authorityText.Trim())
[void]$builder.AppendLine()

[void]$builder.AppendLine("## 5) Imported File Manifest")
[void]$builder.AppendLine("| file | modified | size_kb |")
[void]$builder.AppendLine("|---|---:|---:|")
if ($files.Count -eq 0) {
    [void]$builder.AppendLine("| (none) | - | - |")
} else {
    foreach ($file in $files) {
        $rel = Get-RelativePathText -BasePath $caseRoot -TargetPath $file.FullName
        $modified = $file.LastWriteTime.ToString("yyyy-MM-dd HH:mm")
        $sizeKb = [Math]::Round($file.Length / 1KB, 1)
        [void]$builder.AppendLine("| $rel | $modified | $sizeKb |")
    }
}
[void]$builder.AppendLine()

if ($IncludeDocxPreview) {
    $docxFiles = @($files | Where-Object { $_.Extension.ToLowerInvariant() -eq ".docx" } | Select-Object -First 3)
    [void]$builder.AppendLine("## 6) DOCX Preview (Top 3 recent)")
    if ($docxFiles.Count -eq 0) {
        [void]$builder.AppendLine('- No `.docx` files found.')
    } else {
        foreach ($docxFile in $docxFiles) {
            $relPath = Get-RelativePathText -BasePath $caseRoot -TargetPath $docxFile.FullName
            $preview = Get-DocxPreviewText -DocxPath $docxFile.FullName -MaxChars $DocxPreviewChars
            if ([string]::IsNullOrWhiteSpace($preview)) {
                $preview = "(preview unavailable)"
            }
            [void]$builder.AppendLine()
            [void]$builder.AppendLine("### $relPath")
            [void]$builder.AppendLine($preview)
        }
    }
    [void]$builder.AppendLine()
}

[void]$builder.AppendLine("## 7) Drafting Instructions For AI")
[void]$builder.AppendLine("- Use only facts and authorities from this packet.")
[void]$builder.AppendLine('- If evidence is missing, mark it as `[확인필요]`.')
[void]$builder.AppendLine('- Link each legal assertion to at least one item from `Authority Notes`.')
[void]$builder.AppendLine("- Output sections in this order: Issue, Rule, Application, Conclusion, Relief.")
[void]$builder.AppendLine("- Keep a short risk section with best/worst-case outcomes.")

$outputDir = Split-Path -Parent $OutputPath
if (-not (Test-Path -LiteralPath $outputDir)) {
    New-Item -ItemType Directory -Path $outputDir -Force | Out-Null
}

$builder.ToString() | Set-Content -LiteralPath $OutputPath -Encoding UTF8
Write-Host "Agent packet generated: $OutputPath"
