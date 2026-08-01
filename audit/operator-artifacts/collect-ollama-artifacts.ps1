# collect-ollama-artifacts.ps1 — the OR-04 §8 park-list probes, one command.
# (audit/VERIFICATION-REPORT-ollama-lifecycle.md §8; see README.md in this folder.)
#
# READ-ONLY and LOOPBACK-ONLY by design: this script never starts, stops, installs, or kills
# anything, and it deliberately NEVER invokes `ollama list` or `ollama run` — either would
# respawn/spawn a server and poison probes 2/3/5 (the audit's explicit DON'T). The only network
# calls are GET/POST to http://127.0.0.1:11434 (the local Ollama API). The keep_alive:0 POST in
# probe 3 is the audit's own override probe: it asks the ALREADY-RUNNING server to release an
# ALREADY-LOADED model — it loads nothing and answers no prompt.
#
# Precondition for probes 2/3: run this right after asking the AI one question, while a model
# is still loaded. Everything is written into this script's folder.

$ErrorActionPreference = "Continue"
$here = if ($PSScriptRoot) { $PSScriptRoot } else { (Get-Location).Path }
$api = "http://127.0.0.1:11434"
$log = Join-Path $here "00-collection-log.txt"

function Log([string]$msg) {
    $line = "{0}  {1}" -f (Get-Date -Format "yyyy-MM-dd HH:mm:ss"), $msg
    $line | Tee-Object -FilePath $log -Append
}

"" | Set-Content $log
Log "collect-ollama-artifacts starting in $here"
Log "PowerShell $($PSVersionTable.PSVersion); loopback target $api"

# ---- Probe 1 (F-16): where is the ollama binary ------------------------------------------
Log "probe 1: where.exe ollama"
$p1 = Join-Path $here "01-where-ollama.txt"
"== where.exe ollama ==" | Set-Content $p1
try { where.exe ollama 2>&1 | Add-Content $p1 } catch { "where.exe failed: $_" | Add-Content $p1 }
"" | Add-Content $p1
"== (Get-Command ollama).Source ==" | Add-Content $p1
try {
    $cmd = Get-Command ollama -ErrorAction SilentlyContinue
    if ($cmd) { $cmd.Source | Add-Content $p1 } else { "ollama not on PATH" | Add-Content $p1 }
} catch { "Get-Command failed: $_" | Add-Content $p1 }
"" | Add-Content $p1
"== OLLAMA_* environment (values the server inherits; no schedule content) ==" | Add-Content $p1
Get-ChildItem Env: | Where-Object { $_.Name -like "OLLAMA*" } |
    ForEach-Object { "{0}={1}" -f $_.Name, $_.Value } | Add-Content $p1
Log "probe 1 written to 01-where-ollama.txt"

# ---- Probe 2 (F-12): raw /api/ps while a model is loaded ---------------------------------
Log "probe 2: GET $api/api/ps (raw JSON)"
$p2 = Join-Path $here "02-api-ps.json"
$psBefore = $null
try {
    $resp = Invoke-WebRequest -Uri "$api/api/ps" -UseBasicParsing -TimeoutSec 10
    $resp.Content | Set-Content $p2
    $psBefore = $resp.Content | ConvertFrom-Json
    Log "probe 2 written to 02-api-ps.json"
} catch {
    "REQUEST FAILED: $_" | Set-Content $p2
    Log "probe 2 FAILED (is the Ollama server up? run right after an Ask-the-AI question)"
}

# ---- Probe 3 (F-13/F-15): does per-request keep_alive:0 override OLLAMA_KEEP_ALIVE=-1 ----
Log "probe 3: keep_alive:0 override sequence"
$p3 = Join-Path $here "03-keepalive-override.txt"
"OLLAMA_KEEP_ALIVE currently: $($env:OLLAMA_KEEP_ALIVE)" | Set-Content $p3
if ($psBefore -and $psBefore.models -and $psBefore.models.Count -gt 0) {
    $model = $psBefore.models[0].name
    "target model (first loaded): $model" | Add-Content $p3
    "" | Add-Content $p3
    "== /api/ps BEFORE ($(Get-Date -Format o)) ==" | Add-Content $p3
    ($psBefore | ConvertTo-Json -Depth 8) | Add-Content $p3
    "" | Add-Content $p3
    "== POST /api/generate {model, keep_alive:0} ($(Get-Date -Format o)) ==" | Add-Content $p3
    try {
        $body = @{ model = $model; keep_alive = 0 } | ConvertTo-Json
        $gen = Invoke-WebRequest -Uri "$api/api/generate" -Method Post -Body $body `
            -ContentType "application/json" -UseBasicParsing -TimeoutSec 30
        $gen.Content | Add-Content $p3
    } catch { "generate POST failed: $_" | Add-Content $p3 }
    "" | Add-Content $p3
    "waiting 10 seconds..." | Add-Content $p3
    Start-Sleep -Seconds 10
    "== /api/ps AFTER ($(Get-Date -Format o)) ==" | Add-Content $p3
    try {
        (Invoke-WebRequest -Uri "$api/api/ps" -UseBasicParsing -TimeoutSec 10).Content |
            Add-Content $p3
    } catch { "second /api/ps failed: $_" | Add-Content $p3 }
    Log "probe 3 written to 03-keepalive-override.txt"
} else {
    "NO MODEL LOADED — re-run this script right after an Ask-the-AI question." | Add-Content $p3
    Log "probe 3 SKIPPED (no loaded model in /api/ps)"
}

# ---- Probe 4 (F-18): the manifest naming the audited blob --------------------------------
Log "probe 4: manifest search"
$p4dir = Join-Path $here "04-manifest"
New-Item -ItemType Directory -Path $p4dir -Force | Out-Null
$shaFragment = "4824460d29f2058aaf6e1118a63a7a197a09bed509f0e7d4e2efb1ee273b447d"
$roots = @("C:\Tool\Ollama\models\manifests",
           (Join-Path $env:USERPROFILE ".ollama\models\manifests"))
$found = 0
foreach ($root in $roots) {
    if (-not (Test-Path $root)) { Log "probe 4: $root not present, skipping"; continue }
    Get-ChildItem -Path $root -Recurse -File -ErrorAction SilentlyContinue | ForEach-Object {
        if (Select-String -Path $_.FullName -Pattern $shaFragment -Quiet -ErrorAction SilentlyContinue) {
            $rel = $_.FullName -replace "[:\\/]", "_"
            Copy-Item $_.FullName (Join-Path $p4dir $rel)
            $found++
            Log "probe 4: matched $($_.FullName)"
        }
    }
}
if ($found -eq 0) {
    "no manifest under $($roots -join ' | ') references $shaFragment" |
        Set-Content (Join-Path $p4dir "NO-MATCH.txt")
    Log "probe 4: no matching manifest found"
}

# ---- Probe 5 (F-7/F-17): runner PPID signature + instance count --------------------------
Log "probe 5: llama-server.exe process/parent survey"
$p5 = Join-Path $here "05-runner-ppid.txt"
"== Win32_Process llama-server.exe ($(Get-Date -Format o)) ==" | Set-Content $p5
try {
    $runners = @(Get-CimInstance Win32_Process -Filter "Name='llama-server.exe'" -ErrorAction Stop)
    "instance count: $($runners.Count)" | Add-Content $p5
    $runners | Select-Object ProcessId, ParentProcessId, CommandLine |
        Format-List | Out-String | Add-Content $p5
    foreach ($ppid in ($runners | Select-Object -ExpandProperty ParentProcessId -Unique)) {
        "== Get-Process -Id $ppid (the parent; 'not found' = the dangling-PPID signature) ==" |
            Add-Content $p5
        try {
            Get-Process -Id $ppid -ErrorAction Stop | Format-List Id, ProcessName, Path |
                Out-String | Add-Content $p5
        } catch { "parent $ppid not found: $_" | Add-Content $p5 }
    }
} catch {
    "CIM query failed (or no llama-server.exe running): $_" | Add-Content $p5
}
Log "probe 5 written to 05-runner-ppid.txt"

Log "collection complete — review the files in $here, then commit them via the GitHub web UI."
