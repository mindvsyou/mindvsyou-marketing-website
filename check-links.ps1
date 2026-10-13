# Checks the mindvsyou.io marketing site.
#   ./check-links.ps1          live pages from sitemap.xml + local file checks
#   ./check-links.ps1 -Local   local file checks only (works offline / before pushing)
# Read-only: sends GET requests to mindvsyou.io and changes nothing. Exits 1 if anything fails.

param([switch]$Local, [int]$TimeoutSec = 10)

$root = $PSScriptRoot
Set-Location $root
$site = 'https://mindvsyou.io'
$failures = 0
$noSitemap = @('googleff08a779fb1c9da0.html', 'forgot-login.html')
$noGtag = @('forgot-login.html', 'googleff08a779fb1c9da0.html')

function Fail($msg) { Write-Host "  FAIL  $msg" -ForegroundColor Red; $script:failures++ }
function Ok($msg) { Write-Host "  ok    $msg" -ForegroundColor Green }

$pages = Get-ChildItem -Path $root -Filter *.html -File

# 1. Live pages from the sitemap
if (-not $Local) {
    Write-Host "`n[1] Live pages (sitemap.xml)"
    [xml]$sm = Get-Content "$root\sitemap.xml" -Raw
    $urls = @($sm.urlset.url | ForEach-Object { $_.loc })
    foreach ($u in $urls) {
        $sw = [Diagnostics.Stopwatch]::StartNew()
        try {
            $r = Invoke-WebRequest $u -UseBasicParsing -TimeoutSec $TimeoutSec -ErrorAction Stop
            $sw.Stop()
            if ($r.StatusCode -eq 200) { Ok ("{0}  {1}ms" -f $u, $sw.ElapsedMilliseconds) }
            else { Fail "$u returned $($r.StatusCode)" }
        } catch {
            $code = $_.Exception.Response.StatusCode.value__
            if ($code) { Fail "$u returned $code" } else { Fail "$u no response (timeout/DNS/connection)" }
        }
    }
    if ($failures -eq $urls.Count -and $urls.Count -gt 0) {
        Write-Host "  Every page failed: the server or DNS is likely down, not individual pages." -ForegroundColor Yellow
    }
}

# 2. Internal links and assets
Write-Host "`n[2] Internal links and assets"
$before = $failures
foreach ($p in $pages) {
    $html = Get-Content $p.FullName -Raw
    $refs = [regex]::Matches($html, '(?:href|src)\s*=\s*"([^"]+)"') | ForEach-Object { $_.Groups[1].Value }
    foreach ($ref in ($refs | Sort-Object -Unique)) {
        if ($ref -match '^(mailto:|tel:|javascript:|data:|#)') { continue }
        $path = $ref
        if ($path -match '^https?://(www\.)?mindvsyou\.io(/.*)?$') { $path = $Matches[2] }
        elseif ($path -match '^(https?:)?//') { continue }
        $path = ($path -split '[#?]')[0]
        if ($path -eq '' -or $path -eq '/') { $path = 'index.html' }
        $path = $path.TrimStart('/')
        if (-not (Test-Path (Join-Path $root $path))) { Fail "$($p.Name): broken reference '$ref'" }
    }
}
if ($failures -eq $before) { Ok "all internal links and assets exist" }

# 3. Sitemap coverage
Write-Host "`n[3] Sitemap coverage"
$before = $failures
[xml]$sm = Get-Content "$root\sitemap.xml" -Raw
$mapped = @($sm.urlset.url | ForEach-Object { ([uri]$_.loc).AbsolutePath.TrimStart('/') } | ForEach-Object { if ($_ -eq '') { 'index.html' } else { $_ } })
foreach ($m in $mapped) { if (-not (Test-Path (Join-Path $root $m))) { Fail "sitemap lists '$m' but the file does not exist" } }
foreach ($p in $pages) {
    if ($noSitemap -contains $p.Name -or $p.Name -eq 'mindvsyou-preview.html') { continue }
    if ($mapped -notcontains $p.Name) { Fail "$($p.Name) is not in sitemap.xml" }
}
if ($failures -eq $before) { Ok "sitemap matches the files" }

# 4. Page basics
Write-Host "`n[4] Page basics (title, nav/footer, gtag)"
$before = $failures
foreach ($p in $pages) {
    if ($p.Name -eq 'googleff08a779fb1c9da0.html') { continue }
    $html = Get-Content $p.FullName -Raw
    if ($html -notmatch '(?is)<title>\s*\S') { Fail "$($p.Name): missing <title>" }
    if ($html -notmatch '(?i)<nav') { Fail "$($p.Name): no <nav>" }
    if ($html -notmatch '(?i)<footer') { Fail "$($p.Name): no <footer>" }
    $hasGtag = $html -match 'G-JM406K6TT0'
    if ($noGtag -contains $p.Name) { if ($hasGtag) { Fail "$($p.Name): has gtag but must not (student details page)" } }
    elseif (-not $hasGtag) { Fail "$($p.Name): missing gtag snippet" }
}
if ($failures -eq $before) { Ok "all pages have title, nav, footer and correct gtag" }

Write-Host ""
if ($failures -gt 0) { Write-Host "$failures problem(s) found." -ForegroundColor Red; exit 1 }
Write-Host "All checks passed." -ForegroundColor Green
