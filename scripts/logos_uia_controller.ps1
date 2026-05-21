param(
    [ValidateSet("OpenUri", "Focus", "Inspect", "Search", "Click", "Capture", "PassageWorkflow", "RunRecipe")]
    [string]$Action = "Inspect",

    [string]$Passage = "",
    [string]$LogosUri = "",
    [string]$TargetName = "",
    [string]$AutomationId = "",
    [string]$Output = "",
    [string]$Recipe = "",
    [string]$PassageSlug = "",
    [string]$SourceKind = "uia-capture",

    [int]$WaitSeconds = 6,
    [int]$InspectDepth = 5,
    [int]$MaxInspectItems = 250,

    [switch]$Force,
    [switch]$DryRun
)

$ErrorActionPreference = "Stop"

Add-Type -AssemblyName UIAutomationClient
Add-Type -AssemblyName UIAutomationTypes
Add-Type -AssemblyName System.Windows.Forms

function Add-NativeMethods {
    if ("LogosNativeMethods" -as [type]) {
        return
    }

    Add-Type @"
using System;
using System.Runtime.InteropServices;

public static class LogosNativeMethods {
    [DllImport("user32.dll")]
    public static extern bool SetForegroundWindow(IntPtr hWnd);

    [DllImport("user32.dll")]
    public static extern bool ShowWindowAsync(IntPtr hWnd, int nCmdShow);

    [DllImport("user32.dll")]
    public static extern bool SetCursorPos(int X, int Y);

    [DllImport("user32.dll")]
    public static extern void mouse_event(uint dwFlags, uint dx, uint dy, uint dwData, UIntPtr dwExtraInfo);
}
"@
}

function Get-LogosProcess {
    $process = Get-Process |
        Where-Object {
            $_.MainWindowHandle -ne 0 -and
            ($_.ProcessName -like "*Logos*" -or $_.MainWindowTitle -like "*Logos*")
        } |
        Sort-Object StartTime -Descending |
        Select-Object -First 1

    if (-not $process) {
        throw "Logos window was not found. Start Logos first or use -Action OpenUri."
    }

    return $process
}

function Focus-LogosWindow {
    Add-NativeMethods
    $process = Get-LogosProcess
    [LogosNativeMethods]::ShowWindowAsync($process.MainWindowHandle, 9) | Out-Null
    Start-Sleep -Milliseconds 300
    [LogosNativeMethods]::SetForegroundWindow($process.MainWindowHandle) | Out-Null
    Start-Sleep -Milliseconds 700
    return $process
}

function Get-LogosRoot {
    $process = Focus-LogosWindow
    $root = [System.Windows.Automation.AutomationElement]::FromHandle($process.MainWindowHandle)
    if (-not $root) {
        throw "Could not get the Logos AutomationElement root."
    }
    return $root
}

function Get-ControlTypeName($controlType) {
    if ($null -eq $controlType) {
        return ""
    }
    return ($controlType.ProgrammaticName -replace "^ControlType\.", "")
}

function Find-AllElements {
    param(
        [System.Windows.Automation.AutomationElement]$Root
    )
    $condition = [System.Windows.Automation.Condition]::TrueCondition
    return $Root.FindAll([System.Windows.Automation.TreeScope]::Descendants, $condition)
}

function Find-ElementByAutomationId {
    param(
        [System.Windows.Automation.AutomationElement]$Root,
        [string]$Id
    )
    if (-not $Id) {
        return $null
    }
    $condition = New-Object System.Windows.Automation.PropertyCondition(
        [System.Windows.Automation.AutomationElement]::AutomationIdProperty,
        $Id
    )
    return $Root.FindFirst([System.Windows.Automation.TreeScope]::Descendants, $condition)
}

function Find-ElementByNameContains {
    param(
        [System.Windows.Automation.AutomationElement]$Root,
        [string]$NamePart
    )
    if (-not $NamePart) {
        return $null
    }

    $all = Find-AllElements -Root $Root
    foreach ($element in $all) {
        $name = $element.Current.Name
        if ($name -and $name -like "*$NamePart*") {
            return $element
        }
    }
    return $null
}

function Find-CommandBox {
    param(
        [System.Windows.Automation.AutomationElement]$Root
    )

    $known = @("OurTextBox", "CommandBox", "SearchTextBox")
    foreach ($id in $known) {
        $element = Find-ElementByAutomationId -Root $Root -Id $id
        if ($element) {
            return $element
        }
    }

    $nameHints = @("Search", "Passage", "Reference", "Command")
    foreach ($hint in $nameHints) {
        $element = Find-ElementByNameContains -Root $Root -NamePart $hint
        if ($element) {
            return $element
        }
    }

    $condition = New-Object System.Windows.Automation.PropertyCondition(
        [System.Windows.Automation.AutomationElement]::ControlTypeProperty,
        [System.Windows.Automation.ControlType]::Edit
    )
    return $Root.FindFirst([System.Windows.Automation.TreeScope]::Descendants, $condition)
}

function Invoke-Element {
    param(
        [System.Windows.Automation.AutomationElement]$Element
    )
    if (-not $Element) {
        throw "No UI element was provided for invocation."
    }

    $invokePattern = $null
    if ($Element.TryGetCurrentPattern([System.Windows.Automation.InvokePattern]::Pattern, [ref]$invokePattern)) {
        if (-not $DryRun) {
            $invokePattern.Invoke()
        }
        return
    }

    if (-not $DryRun) {
        Focus-OrClickElement -Element $Element
        [System.Windows.Forms.SendKeys]::SendWait("{ENTER}")
    }
}

function Focus-OrClickElement {
    param(
        [System.Windows.Automation.AutomationElement]$Element
    )
    if (-not $Element) {
        throw "No UI element was provided."
    }
    if ($DryRun) {
        return
    }

    try {
        $Element.SetFocus()
        Start-Sleep -Milliseconds 200
        return
    } catch {
        # Some Chromium-backed controls expose UIA metadata but reject SetFocus.
    }

    $point = New-Object System.Windows.Point
    if ($Element.TryGetClickablePoint([ref]$point)) {
        Add-NativeMethods
        [LogosNativeMethods]::SetCursorPos([int]$point.X, [int]$point.Y) | Out-Null
        Start-Sleep -Milliseconds 100
        [LogosNativeMethods]::mouse_event(0x0002, 0, 0, 0, [UIntPtr]::Zero)
        [LogosNativeMethods]::mouse_event(0x0004, 0, 0, 0, [UIntPtr]::Zero)
        Start-Sleep -Milliseconds 250
        return
    }

    throw "Could not focus or click the target UI element."
}

function Set-ElementText {
    param(
        [System.Windows.Automation.AutomationElement]$Element,
        [string]$Text
    )
    if (-not $Element) {
        throw "No UI element was provided for text input."
    }

    $valuePattern = $null
    Focus-OrClickElement -Element $Element

    if ($Element.TryGetCurrentPattern([System.Windows.Automation.ValuePattern]::Pattern, [ref]$valuePattern)) {
        if (-not $valuePattern.Current.IsReadOnly) {
            if (-not $DryRun) {
                $valuePattern.SetValue($Text)
            }
            return
        }
    }

    if (-not $DryRun) {
        [System.Windows.Forms.SendKeys]::SendWait("^a")
        Start-Sleep -Milliseconds 100
        [System.Windows.Forms.SendKeys]::SendWait($Text)
    }
}

function Get-DefaultOutputPath {
    $stamp = Get-Date -Format "yyyyMMdd-HHmmss"
    $dir = Join-Path (Get-Location) "tmp\logos-capture\raw"
    New-Item -ItemType Directory -Force -Path $dir | Out-Null

    if ($PassageSlug) {
        $safePassage = $PassageSlug -replace '[^a-zA-Z0-9\-]', '-' -replace '-+', '-'
        $safeKind = $SourceKind -replace '[^a-zA-Z0-9\-]', '-' -replace '-+', '-'
        return Join-Path $dir "$safePassage-$safeKind-$stamp.md"
    }

    return Join-Path $dir "logos-uia-capture-$stamp.md"
}

function Capture-ActiveText {
    $previousClipboard = $null
    try {
        $previousClipboard = Get-Clipboard -Raw -ErrorAction SilentlyContinue
    } catch {
        $previousClipboard = $null
    }

    if (-not $DryRun) {
        Set-Clipboard -Value ""
        [System.Windows.Forms.SendKeys]::SendWait("^a")
        Start-Sleep -Milliseconds 350
        [System.Windows.Forms.SendKeys]::SendWait("^c")
        Start-Sleep -Milliseconds 900
    }

    $captured = Get-Clipboard -Raw -ErrorAction SilentlyContinue

    if ($null -ne $previousClipboard) {
        Set-Clipboard -Value $previousClipboard
    }

    return $captured
}

function Save-Capture {
    param(
        [string]$Text,
        [string]$PathValue
    )

    if (-not $PathValue) {
        $PathValue = Get-DefaultOutputPath
    }

    $outputPath = [System.IO.Path]::GetFullPath($PathValue)
    if ((Test-Path $outputPath) -and -not $Force) {
        throw "Output file already exists. Use -Force to overwrite: $outputPath"
    }

    if ([string]::IsNullOrWhiteSpace($Text)) {
        throw "No text was captured. Click the target Logos panel or run -Action Inspect."
    }

    $outputDir = Split-Path -Parent $outputPath
    New-Item -ItemType Directory -Force -Path $outputDir | Out-Null

    $header = @"
# Logos UI Automation Raw Capture

- CapturedAt: $(Get-Date -Format "yyyy-MM-dd HH:mm:ss")
- Action: $Action
- Passage: $Passage
- Logos URI: $LogosUri
- SourceKind: $SourceKind
- Warning: This is a UI Automation capture. Review it directly before using it for sermon preparation.

## Captured Content

"@

    Set-Content -Path $outputPath -Value ($header + $Text) -Encoding UTF8
    Write-Host "Capture saved: $outputPath"
    Write-Host "Character count: $($Text.Length)"
}

function Test-CaptureText {
    param(
        [string]$Text,
        $Step
    )

    $failures = New-Object System.Collections.Generic.List[string]

    $minChars = 0
    if ($Step.minChars) {
        $minChars = [int]$Step.minChars
    }
    if ($minChars -gt 0 -and $Text.Length -lt $minChars) {
        $failures.Add("Text is shorter than minChars: $($Text.Length) < $minChars")
    }

    if ($Step.mustContain) {
        foreach ($term in @($Step.mustContain)) {
            $needle = [string]$term
            if ($needle -and -not $Text.Contains($needle)) {
                $failures.Add("Missing required text: $needle")
            }
        }
    }

    if ($Step.mustNotContain) {
        foreach ($term in @($Step.mustNotContain)) {
            $needle = [string]$term
            if ($needle -and $Text.Contains($needle)) {
                $failures.Add("Forbidden text found: $needle")
            }
        }
    }

    if ($failures.Count -gt 0) {
        $message = "Capture validation failed:`n- " + ($failures -join "`n- ")
        throw $message
    }

    if ($minChars -gt 0 -or $Step.mustContain -or $Step.mustNotContain) {
        Write-Host "Capture validation passed."
    }
}

function Inspect-Logos {
    param(
        [System.Windows.Automation.AutomationElement]$Root
    )

    $walker = [System.Windows.Automation.TreeWalker]::ControlViewWalker
    $queue = New-Object System.Collections.Queue
    $queue.Enqueue([pscustomobject]@{ Element = $Root; Depth = 0 })
    $count = 0

    while ($queue.Count -gt 0 -and $count -lt $MaxInspectItems) {
        $item = $queue.Dequeue()
        $element = $item.Element
        $depth = [int]$item.Depth
        $indent = "  " * $depth

        $name = $element.Current.Name
        $id = $element.Current.AutomationId
        $type = Get-ControlTypeName $element.Current.ControlType
        $enabled = $element.Current.IsEnabled

        Write-Host "$indent- type='$type' name='$name' id='$id' enabled='$enabled'"
        $count += 1

        if ($depth -ge $InspectDepth) {
            continue
        }

        $child = $walker.GetFirstChild($element)
        while ($child -and $count -lt $MaxInspectItems) {
            $queue.Enqueue([pscustomobject]@{ Element = $child; Depth = $depth + 1 })
            $child = $walker.GetNextSibling($child)
        }
    }

    Write-Host "Inspect items: $count"
}

function Open-LogosUri {
    if (-not $LogosUri) {
        if ($Passage) {
            $encoded = [uri]::EscapeDataString($Passage)
            $LogosUri = "logos4:Bible;ref=$encoded"
        } else {
            $LogosUri = "logos4:"
        }
    }

    Write-Host "Opening Logos URI: $LogosUri"
    if (-not $DryRun) {
        Start-Process $LogosUri
        Start-Sleep -Seconds $WaitSeconds
    }
}

function Search-Passage {
    if (-not $Passage) {
        throw "Specify -Passage."
    }

    $root = Get-LogosRoot
    $box = Find-CommandBox -Root $root
    if (-not $box) {
        throw "Could not find the Logos command/search box. Run -Action Inspect and check AutomationId."
    }

    Write-Host "Input box found: name='$($box.Current.Name)' id='$($box.Current.AutomationId)'"
    Set-ElementText -Element $box -Text $Passage
    if (-not $DryRun) {
        Start-Sleep -Milliseconds 200
        [System.Windows.Forms.SendKeys]::SendWait("{ENTER}")
        Start-Sleep -Seconds $WaitSeconds
    }
}

function Click-Target {
    $root = Get-LogosRoot
    $target = $null

    if ($AutomationId) {
        $target = Find-ElementByAutomationId -Root $root -Id $AutomationId
    }
    if (-not $target -and $TargetName) {
        $target = Find-ElementByNameContains -Root $root -NamePart $TargetName
    }
    if (-not $target) {
        throw "Target UI element was not found. Use -TargetName or -AutomationId after running Inspect."
    }

    Write-Host "Target found: type='$(Get-ControlTypeName $target.Current.ControlType)' name='$($target.Current.Name)' id='$($target.Current.AutomationId)'"
    Invoke-Element -Element $target
    Start-Sleep -Seconds $WaitSeconds
}

function Invoke-Recipe {
    if (-not $Recipe) {
        throw "Specify -Recipe."
    }
    $recipePath = [System.IO.Path]::GetFullPath($Recipe)
    if (-not (Test-Path $recipePath)) {
        throw "Recipe file was not found: $recipePath"
    }

    $data = Get-Content -Raw -Encoding UTF8 -Path $recipePath | ConvertFrom-Json
    if ($data.passage) {
        $script:Passage = [string]$data.passage
    }
    if ($data.passageSlug) {
        $script:PassageSlug = [string]$data.passageSlug
    }
    if (-not $data.steps) {
        throw "Recipe must include a steps array."
    }

    foreach ($step in $data.steps) {
        $stepAction = [string]$step.action
        Write-Host "Recipe step: $stepAction"

        $allowedActions = @("OpenUri", "Focus", "Search", "Click", "Sleep", "Capture", "Inspect")
        if ($allowedActions -notcontains $stepAction) {
            throw "Unsupported recipe step action: $stepAction"
        }
        if ($DryRun) {
            continue
        }

        switch ($stepAction) {
            "OpenUri" {
                if ($step.logosUri) { $script:LogosUri = [string]$step.logosUri }
                if ($step.waitSeconds) { $script:WaitSeconds = [int]$step.waitSeconds }
                Open-LogosUri
                Focus-LogosWindow | Out-Null
            }
            "Focus" {
                Focus-LogosWindow | Out-Null
            }
            "Search" {
                if ($step.passage) { $script:Passage = [string]$step.passage }
                if ($step.waitSeconds) { $script:WaitSeconds = [int]$step.waitSeconds }
                Search-Passage
            }
            "Click" {
                $script:TargetName = ""
                $script:AutomationId = ""
                if ($step.targetName) { $script:TargetName = [string]$step.targetName }
                if ($step.automationId) { $script:AutomationId = [string]$step.automationId }
                if ($step.waitSeconds) { $script:WaitSeconds = [int]$step.waitSeconds }
                Click-Target
            }
            "Sleep" {
                $seconds = 1
                if ($step.seconds) { $seconds = [int]$step.seconds }
                if (-not $DryRun) { Start-Sleep -Seconds $seconds }
            }
            "Capture" {
                if ($step.sourceKind) { $script:SourceKind = [string]$step.sourceKind }
                $stepOutput = ""
                if ($step.output) { $stepOutput = [string]$step.output }
                Focus-LogosWindow | Out-Null
                $text = Capture-ActiveText
                Test-CaptureText -Text $text -Step $step
                Save-Capture -Text $text -PathValue $stepOutput
            }
            "Inspect" {
                if ($step.inspectDepth) { $script:InspectDepth = [int]$step.inspectDepth }
                if ($step.maxInspectItems) { $script:MaxInspectItems = [int]$step.maxInspectItems }
                $root = Get-LogosRoot
                Inspect-Logos -Root $root
            }
        }
    }
}

switch ($Action) {
    "OpenUri" {
        Open-LogosUri
        if (-not $DryRun) {
            Focus-LogosWindow | Out-Null
        }
    }
    "Focus" {
        $process = Focus-LogosWindow
        Write-Host "Logos focused: $($process.MainWindowTitle)"
    }
    "Inspect" {
        $root = Get-LogosRoot
        Inspect-Logos -Root $root
    }
    "Search" {
        Search-Passage
    }
    "Click" {
        Click-Target
    }
    "Capture" {
        if ($DryRun) {
            Write-Host "DryRun: capture skipped."
            return
        }
        Focus-LogosWindow | Out-Null
        $text = Capture-ActiveText
        Save-Capture -Text $text -PathValue $Output
    }
    "PassageWorkflow" {
        if ($DryRun) {
            Write-Host "DryRun: passage workflow skipped."
            return
        }
        Open-LogosUri
        Search-Passage
        $text = Capture-ActiveText
        Save-Capture -Text $text -PathValue $Output
    }
    "RunRecipe" {
        Invoke-Recipe
    }
}
