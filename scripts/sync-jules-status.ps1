param(
    [switch]$DryRun
)

$ErrorActionPreference = "Stop"

# Use environment variable override to satisfy the strict production default constraint
$basePath = $env:PROJECT_BASE_PATH
if ([string]::IsNullOrWhiteSpace($basePath)) {
    $basePath = "C:\Dev\Projects\"
    $repoRoot = Join-Path $basePath "czar-platform"
} else {
    $repoRoot = $basePath
}

$logDir = Join-Path $repoRoot "artifacts\logs"
$logFile = Join-Path $logDir "jules-sync-2026-05-22.log"

if (-not (Test-Path $logDir)) {
    New-Item -ItemType Directory -Path $logDir -Force | Out-Null
}

function Write-Log {
    param (
        [string]$Message,
        [string]$Repo = "N/A",
        [string]$PrNumber = "N/A",
        [string]$Action = "INFO"
    )
    $timestamp = (Get-Date).ToString("yyyy-MM-dd HH:mm:ss")
    $logEntry = "[$timestamp] [REPO:$Repo] [PR:$PrNumber] [ACTION:$Action] $Message"
    Write-Host $logEntry
    Add-Content -Path $logFile -Value $logEntry
}

$GH_PAT_READ = $env:GH_PAT_READ
$JULES_API_KEY = $env:JULES_API_KEY

if ([string]::IsNullOrWhiteSpace($GH_PAT_READ) -or [string]::IsNullOrWhiteSpace($JULES_API_KEY)) {
    Write-Log -Message "Missing required environment variables: GH_PAT_READ or JULES_API_KEY" -Action "ERROR"
    exit 1
}

$repos = @(
    "czar-platform",
    "ai-router",
    "props-optimizer",
    "media-listing-pipeline",
    "google-trends-monetizer",
    "ebay-arbitrage-scanner",
    "sportsbook-optimizer",
    "new-projects-gumroad"
)

Write-Log -Message "Starting Jules sync across 8 repos" -Action "START"

$runspacePool = [runspacefactory]::CreateRunspacePool(1, 8)
$runspacePool.Open()

$jobs = @()

foreach ($repo in $repos) {
    $scriptBlock = {
        param($repoName, $ghToken)
        $ErrorActionPreference = "Stop"
        $headers = @{
            "Authorization" = "Bearer $ghToken"
            "Accept" = "application/vnd.github.v3+json"
            "User-Agent" = "PowerShell"
        }
        $url = "https://api.github.com/repos/Czar68/$repoName/pulls?state=closed&per_page=30"
        try {
            $response = Invoke-RestMethod -Uri $url -Headers $headers -Method Get
            if ($response) {
                $mergedPrs = @($response) | Where-Object { $_.merged_at -ne $null }
                return @{ Repo = $repoName; PRs = $mergedPrs; Error = $null }
            } else {
                return @{ Repo = $repoName; PRs = @(); Error = $null }
            }
        } catch {
            return @{ Repo = $repoName; PRs = @(); Error = $_.Exception.Message }
        }
    }

    $ps = [powershell]::Create().AddScript($scriptBlock).AddArgument($repo).AddArgument($GH_PAT_READ)
    $ps.RunspacePool = $runspacePool
    $jobs += [PSCustomObject]@{
        PowerShell = $ps
        Handle = $ps.BeginInvoke()
        Repo = $repo
    }
}

$mergedPrResults = @()

foreach ($job in $jobs) {
    $job.Handle.AsyncWaitHandle.WaitOne() | Out-Null
    $result = $job.PowerShell.EndInvoke($job.Handle)
    $job.PowerShell.Dispose()

    if ($result.Error) {
        Write-Log -Message "Error fetching PRs for repo: $($result.Error)" -Repo $job.Repo -Action "ERROR"
    } else {
        $prCount = 0
        if ($result.PRs) { $prCount = $result.PRs.Count }
        Write-Log -Message "Fetched $prCount merged PRs" -Repo $job.Repo
        if ($result.PRs) {
            foreach ($pr in $result.PRs) {
                $mergedPrResults += @{
                    Repo = $job.Repo
                    Number = $pr.number
                    Title = $pr.title
                    Branch = $pr.head.ref
                }
            }
        }
    }
}

$runspacePool.Close()
$runspacePool.Dispose()

# Process each merged PR
$julesHeaders = @{
    "x-goog-api-key" = $JULES_API_KEY
    "Content-Type"   = "application/json"
}

# Fetch Jules sessions outside loop to avoid duplicate network requests
$sessions = @()
try {
    $sessionsResponse = Invoke-RestMethod -Uri "https://jules.googleapis.com/v1alpha/sessions" -Method Get -Headers $julesHeaders
    if ($sessionsResponse.sessions) {
        $sessions = @($sessionsResponse.sessions)
    }
} catch {
    Write-Log -Message "Failed to fetch Jules sessions: $($_.Exception.Message)" -Action "ERROR"
}

foreach ($pr in $mergedPrResults) {
    $repo = $pr.Repo
    $prNumber = $pr.Number
    $prTitle = $pr.Title
    $branchName = $pr.Branch

    $targetSession = $null
    foreach ($session in $sessions) {
        if (($session.title -and $prTitle -and $session.title -match [regex]::Escape($prTitle)) -or ($session.title -and $branchName -and $session.title -match [regex]::Escape($branchName))) {
            $targetSession = $session
            break
        }
    }

    if (-not $targetSession) {
        Write-Log -Message "No matching Jules session found" -Repo $repo -PrNumber $prNumber -Action "SKIP"
        continue
    }

    $sessionId = $targetSession.id
    if (-not $sessionId) {
        $sessionId = $targetSession.name
    }

    $state = $targetSession.state

    if ($state -eq "AWAITING_USER_FEEDBACK" -or $state -eq "NEEDS_REVIEW" -or $state -eq "PENDING") {
        Write-Log -Message "Session $sessionId needs review. Marking as resolved." -Repo $repo -PrNumber $prNumber -Action "RESOLVING"
        try {
            if (-not $DryRun) {
                $resolveUrl = "https://jules.googleapis.com/v1alpha/sessions/$($sessionId):resolve"
                $body = "{}"
                Invoke-RestMethod -Uri $resolveUrl -Method Post -Headers $julesHeaders -Body $body | Out-Null
            }
            Write-Log -Message "Successfully marked session $sessionId as resolved" -Repo $repo -PrNumber $prNumber -Action "RESOLVED"
        } catch {
            if ($_.Exception.Response.StatusCode.value__ -eq 404) {
                Write-Log -Message "Session $sessionId already completed/cancelled (404), skipping resolve" -Repo $repo -PrNumber $prNumber -Action "SKIP"
            } else {
                Write-Log -Message "Failed to resolve session ${sessionId}: $($_.Exception.Message)" -Repo $repo -PrNumber $prNumber -Action "ERROR"
            }
        }
    } else {
        Write-Log -Message "Session $sessionId is in state $state, no action needed" -Repo $repo -PrNumber $prNumber -Action "SKIP"
    }
}

Write-Log -Message "Jules sync completed" -Action "END"
