$repo = Split-Path $PSScriptRoot -Parent
Set-Location $repo
$log = Join-Path $repo "git-push-log.txt"
@(
  "=== git status ==="
  (git status -sb 2>&1 | Out-String)
  "=== git diff stat ==="
  (git diff --stat 2>&1 | Out-String)
  "=== commit ==="
) | Set-Content $log -Encoding UTF8
git add -A 2>&1 | Add-Content $log
git commit -m "Fix auth build, local env docs, and cross-page header nav links" 2>&1 | Add-Content $log
git rev-parse HEAD 2>&1 | Add-Content $log
git push origin main 2>&1 | Add-Content $log
git status -sb 2>&1 | Add-Content $log
