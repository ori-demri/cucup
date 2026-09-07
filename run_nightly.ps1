# ==============================================================================
# Nightly Job Runner (Sleep-Proof & Auto-Reporting)
# ==============================================================================
[CmdletBinding()]
param (
    [string]$Retailers = "all",
    [int]$Concurrency = 5,
    [double]$RateLimit = 6.0,
    [string]$Proxies = $null
)

Write-Host "`n[*] Preventing Windows sleep mode for overnight batch execution..." -ForegroundColor Cyan
$Signature = '[DllImport("kernel32.dll")] public static extern uint SetThreadExecutionState(uint esFlags);'
$PowerUtil = Add-Type -MemberDefinition $Signature -Name SleepUtil -Namespace SystemPower -PassThru
# ES_CONTINUOUS (0x80000000) | ES_SYSTEM_REQUIRED (0x00000001)
$null = $PowerUtil::SetThreadExecutionState(0x80000001)

try {
    $cmdArgs = @("run", "python", "main.py", "nightly", "--resume", "--retailers", $Retailers, "--concurrency", "$Concurrency", "--rate-limit", "$RateLimit")
    if ($Proxies) {
        $cmdArgs += @("--proxies", $Proxies)
    }

    Write-Host "[*] Executing: uv $($cmdArgs -join ' ')" -ForegroundColor Green
    & uv $cmdArgs
}
finally {
    # Restore normal Windows sleep settings
    Write-Host "`n[*] Restoring standard system power policies..." -ForegroundColor Cyan
    $null = $PowerUtil::SetThreadExecutionState(0x80000000)

    # Pop the latest report
    $latestReport = Get-ChildItem -Path "reports\*.md" -ErrorAction SilentlyContinue | 
                    Sort-Object LastWriteTime -Descending | 
                    Select-Object -First 1

    if ($latestReport) {
        Write-Host "[+] Opening executive report: $($latestReport.FullName)" -ForegroundColor Yellow
        Start-Process $latestReport.FullName
    }
}
