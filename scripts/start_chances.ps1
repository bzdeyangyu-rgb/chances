param(
    [switch]$NoBrowser,
    [int]$WaitSeconds = 40
)

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot
$PythonExe = Join-Path $ProjectRoot ".venv\Scripts\python.exe"
$RuntimeScript = Join-Path $PSScriptRoot "runtime_chances.py"

if (-not (Test-Path -LiteralPath $PythonExe)) {
    throw "未找到项目虚拟环境：$PythonExe"
}

$arguments = @($RuntimeScript, "start", "--wait-seconds", $WaitSeconds)
if ($NoBrowser) {
    $arguments += "--no-browser"
}

& $PythonExe @arguments
exit $LASTEXITCODE
