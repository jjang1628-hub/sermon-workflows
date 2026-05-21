param(
    [string]$LogosUri = "",
    [string]$Output = "",
    [string]$Passage = "",      # 예: "john-3"  → 파일명에 포함
    [string]$SourceKind = "",   # 예: "passage-guide", "commentary", "bible-text"
    [int]$WaitSeconds = 8,
    [switch]$Force
)

$ErrorActionPreference = "Stop"

function Get-DefaultOutputPath {
    $stamp = Get-Date -Format "yyyyMMdd-HHmmss"
    $dir = Join-Path (Get-Location) "tmp\logos-capture\raw"
    New-Item -ItemType Directory -Force -Path $dir | Out-Null

    if ($Passage -and $SourceKind) {
        $safePsg  = $Passage   -replace '[^a-zA-Z0-9가-힣\-]', '-' -replace '-+', '-'
        $safeKind = $SourceKind -replace '[^a-zA-Z0-9\-]', '-'     -replace '-+', '-'
        return Join-Path $dir "$safePsg-$safeKind-$stamp.md"
    }
    return Join-Path $dir "logos-capture-$stamp.md"
}

function Add-NativeMethods {
    if ("NativeMethods" -as [type]) {
        return
    }

    Add-Type @"
using System;
using System.Runtime.InteropServices;

public static class NativeMethods {
    [DllImport("user32.dll")]
    public static extern bool SetForegroundWindow(IntPtr hWnd);

    [DllImport("user32.dll")]
    public static extern bool ShowWindowAsync(IntPtr hWnd, int nCmdShow);
}
"@
}

function Focus-LogosWindow {
    Add-NativeMethods

    $process = Get-Process |
        Where-Object {
            $_.MainWindowHandle -ne 0 -and
            ($_.ProcessName -like "*Logos*" -or $_.MainWindowTitle -like "*Logos*")
        } |
        Sort-Object StartTime -Descending |
        Select-Object -First 1

    if (-not $process) {
        throw "Logos 창을 찾지 못했습니다. Logos를 먼저 실행한 뒤 다시 시도해 주세요."
    }

    [NativeMethods]::ShowWindowAsync($process.MainWindowHandle, 9) | Out-Null
    Start-Sleep -Milliseconds 300
    [NativeMethods]::SetForegroundWindow($process.MainWindowHandle) | Out-Null
    Start-Sleep -Milliseconds 700

    return $process
}

function Capture-ActiveText {
    Add-Type -AssemblyName System.Windows.Forms

    $previousClipboard = $null
    try {
        $previousClipboard = Get-Clipboard -Raw -ErrorAction SilentlyContinue
    } catch {
        $previousClipboard = $null
    }

    Set-Clipboard -Value ""
    [System.Windows.Forms.SendKeys]::SendWait("^a")
    Start-Sleep -Milliseconds 400
    [System.Windows.Forms.SendKeys]::SendWait("^c")
    Start-Sleep -Milliseconds 900

    $captured = Get-Clipboard -Raw -ErrorAction SilentlyContinue

    if ($null -ne $previousClipboard) {
        Set-Clipboard -Value $previousClipboard
    }

    return $captured
}

if (-not $Output) {
    $Output = Get-DefaultOutputPath
}

$outputPath = [System.IO.Path]::GetFullPath($Output)
$outputDir = Split-Path -Parent $outputPath

if ((Test-Path $outputPath) -and -not $Force) {
    throw "출력 파일이 이미 있습니다. 덮어쓰려면 -Force를 사용하세요: $outputPath"
}

if ($LogosUri) {
    Write-Host "Logos URI 실행: $LogosUri"
    Start-Process $LogosUri
    Start-Sleep -Seconds $WaitSeconds
}

$logosProcess = Focus-LogosWindow
Write-Host "Logos 창 포커스: $($logosProcess.MainWindowTitle)"

$capturedText = Capture-ActiveText

if ([string]::IsNullOrWhiteSpace($capturedText)) {
    throw "캡처된 텍스트가 없습니다. Logos에서 복사 가능한 본문/자료 패널을 클릭한 뒤 다시 실행해 주세요."
}

New-Item -ItemType Directory -Force -Path $outputDir | Out-Null

$header = @"
# Logos 캡처 원문

- 캡처 일시: $(Get-Date -Format "yyyy-MM-dd HH:mm:ss")
- Logos URI: $LogosUri
- 주의: 자동 캡처 원문입니다. 설교 자료로 사용하기 전에 반드시 직접 검토하세요.

## 캡처 내용

"@

Set-Content -Path $outputPath -Value ($header + $capturedText) -Encoding UTF8

Write-Host "캡처 저장 완료: $outputPath"
Write-Host "글자 수: $($capturedText.Length)"
