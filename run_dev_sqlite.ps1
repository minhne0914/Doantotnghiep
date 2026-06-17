param(
    [string]$LogPath = ''
)

$ErrorActionPreference = 'Continue'

$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $Root

$TraceLog = Join-Path $Root 'logs\run_dev_sqlite.trace.log'
New-Item -ItemType Directory -Force -Path (Split-Path -Parent $TraceLog) | Out-Null
Add-Content -Path $TraceLog -Value "$(Get-Date -Format o) start pid=$PID logPath=$LogPath"

$env:PYTHONPATH = Join-Path $Root '.venv-runtime\Lib\site-packages'
$env:DB_ENGINE = 'django.db.backends.sqlite3'
$env:DB_NAME = Join-Path $Root 'db.sqlite3'
$env:DB_USER = ''
$env:DB_PASSWORD = ''
$env:DB_HOST = ''
$env:DB_PORT = ''
$env:DJANGO_DEBUG = 'True'
$env:DJANGO_ALLOWED_HOSTS = '127.0.0.1,localhost'

$Python = Join-Path $Root '.uv-python\cpython-3.10-windows-x86_64-none\python.exe'
Add-Content -Path $TraceLog -Value "$(Get-Date -Format o) python=$Python exists=$(Test-Path $Python)"
if ($LogPath) {
    $Command = "`"$Python`" manage.py runserver 127.0.0.1:8000 --noreload > `"$LogPath`" 2>&1"
    & "$env:SystemRoot\System32\cmd.exe" /d /c $Command
} else {
    & $Python manage.py runserver 127.0.0.1:8000 --noreload
}
Add-Content -Path $TraceLog -Value "$(Get-Date -Format o) exit code=$LASTEXITCODE"
