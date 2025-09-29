param(
  [Parameter(Mandatory=$false)][string]$Message = "Checkpoint",
  [Parameter(Mandatory=$true)][string]$Tag
)

function Fail($msg){ Write-Error $msg; exit 1 }

# Ensure we're in repo root
$repoRoot = Split-Path -Parent $MyInvocation.MyCommand.Path | Split-Path -Parent
Set-Location $repoRoot

# Basic git checks
if (-not (Get-Command git -ErrorAction SilentlyContinue)) { Fail "git is not installed or not on PATH." }

$branchRaw = git rev-parse --abbrev-ref HEAD 2>$null
if (-not $branchRaw) { Fail "Not a git repository or git not available." }
$branch = $branchRaw.Trim()

# Ensure no unmerged/rebase in progress
$statusDir = Join-Path (git rev-parse --git-common-dir) "rebase-apply"
if (Test-Path $statusDir) { Fail "Rebase or patch apply in progress. Resolve before checkpointing." }

# Check for staged/unstaged changes
$dirtyRaw = git status --porcelain 2>$null
$dirty = $dirtyRaw ? $dirtyRaw.Trim() : ""
if ($dirty -ne "") {
  Write-Host "Committing working changes..." -ForegroundColor Yellow
  git add -A | Out-Null
  git commit -m $Message | Out-Null
} else {
  Write-Host "Working tree clean; creating tag from latest commit." -ForegroundColor Yellow
}

# Create annotated tag
$existingTagRaw = git tag -l $Tag 2>$null
if ($existingTagRaw -and $existingTagRaw.Trim() -ne "") { Fail "Tag '$Tag' already exists. Choose a new tag name." }

git tag -a $Tag -m $Message

Write-Host "Checkpoint created: $Tag" -ForegroundColor Green
Write-Host "Restore examples:" -ForegroundColor Cyan
Write-Host "  git checkout $Tag  # detached HEAD"
Write-Host "  git switch -c restore/$(($Tag -replace 'ckpt/','')) $Tag"
