#requires -version 5.1
[CmdletBinding()]
param(
    [ValidateSet('Local','Tunnel','TunnelBackend')]
    [string]$Mode = 'Local',
    [switch]$ForceReinstallDependencies,
    [switch]$NoBrowser
)

$ErrorActionPreference = 'Stop'
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
try { [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12 } catch { }

function Write-Step([string]$Text) { Write-Host $Text -ForegroundColor Cyan }
function Write-Ok([string]$Text) { Write-Host $Text -ForegroundColor Green }
function Write-Warn([string]$Text) { Write-Host $Text -ForegroundColor Yellow }
function Write-Fail([string]$Text) { Write-Host $Text -ForegroundColor Red }

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$Root = Split-Path -Parent $ScriptDir
$Root = (Resolve-Path $Root).Path
$BackendDir = Join-Path $Root 'backend'
$FrontendDir = Join-Path $Root 'frontend'
$DataDir = Join-Path $Root 'data'
$RuntimeDir = Join-Path $Root '.runtime_windows'
$Port = 5000
$LocalBase = "http://127.0.0.1:$Port"
$LocalFrontend = "$LocalBase/frontend/index.html"
$HealthUrl = "$LocalBase/api/health"
$TunnelMode = $Mode -in @('Tunnel','TunnelBackend')

Write-Host '============================================================'
Write-Host ' PRIMERA INFANCIA 2.7.0 - INICIO ROBUSTO WINDOWS'
Write-Host " Modo: $Mode"
Write-Host '============================================================'
Write-Host ''

if (-not (Test-Path (Join-Path $BackendDir 'app.py'))) {
    throw "No existe backend\app.py en $BackendDir. Ejecuta el BAT que está en la raíz del proyecto."
}
if (-not (Test-Path (Join-Path $FrontendDir 'index.html'))) {
    throw "No existe frontend\index.html en $FrontendDir."
}
New-Item -ItemType Directory -Force -Path $DataDir,$RuntimeDir,(Join-Path $DataDir 'logs'),(Join-Path $DataDir 'backups'),(Join-Path $DataDir 'uploads'),(Join-Path $DataDir 'archivos_actualizados'),(Join-Path $DataDir 'templates_originales'),(Join-Path $DataDir 'storage'),(Join-Path $DataDir 'documentos_institucionales'),(Join-Path $DataDir 'cuentas_cobro_plantillas') | Out-Null

function Get-ProjectInstanceId([string]$ProjectRoot) {
    $normalized = [IO.Path]::GetFullPath($ProjectRoot).TrimEnd([char[]]'\/').ToLowerInvariant()
    $sha = [Security.Cryptography.SHA256]::Create()
    try {
        $bytes = [Text.Encoding]::UTF8.GetBytes($normalized)
        return ([BitConverter]::ToString($sha.ComputeHash($bytes))).Replace('-','').Substring(0,16).ToLowerInvariant()
    } finally { $sha.Dispose() }
}
$ProjectInstanceId = Get-ProjectInstanceId $Root
Set-Content -Path (Join-Path $RuntimeDir 'project_instance_id.txt') -Encoding ASCII -Value $ProjectInstanceId
Write-Host "Proyecto: $Root"
Write-Host "Instancia: $ProjectInstanceId"
Write-Host ''

function Resolve-PythonCommand {
    $existingVenvPython = Join-Path $BackendDir '.venv\Scripts\python.exe'
    if (Test-Path $existingVenvPython) {
        try {
            $versionOutput = & $existingVenvPython --version 2>&1
            $versionExitCode = $LASTEXITCODE
            $version = $versionOutput | Select-Object -First 1
            if ($versionExitCode -eq 0 -and $version -match 'Python 3\.(11|12)\.') {
                return [PSCustomObject]@{ File=$existingVenvPython; Prefix=@(); Label='Python del entorno virtual existente'; Version=[string]$version }
            }
        } catch { }
    }

    $candidates = [System.Collections.Generic.List[object]]::new()
    $pyLauncher = Join-Path $env:WINDIR 'py.exe'
    if (Test-Path $pyLauncher) {
        $candidates.Add([PSCustomObject]@{ File=$pyLauncher; Prefix=@('-3.12'); Label='Python 3.12 (py launcher)' })
        $candidates.Add([PSCustomObject]@{ File=$pyLauncher; Prefix=@('-3.11'); Label='Python 3.11 (py launcher)' })
    }
    foreach ($minor in @('312','311')) {
        $directPython = Join-Path $env:LOCALAPPDATA "Programs\Python\Python$minor\python.exe"
        if (Test-Path $directPython) {
            $candidates.Add([PSCustomObject]@{ File=$directPython; Prefix=@(); Label="Python $($minor.Insert(1,'.'))" })
        }
    }
    $candidates.Add([PSCustomObject]@{ File='python.exe'; Prefix=@(); Label='Python en PATH' })

    foreach ($candidate in $candidates) {
        try {
            $candidateFile = [string]$candidate.File
            $arguments = @($candidate.Prefix) + @('--version')
            $versionOutput = & $candidateFile @arguments 2>&1
            $versionExitCode = $LASTEXITCODE
            $version = $versionOutput | Select-Object -First 1
            if ($versionExitCode -eq 0 -and $version -match 'Python 3\.(11|12)\.') {
                return [PSCustomObject]@{ File=$candidateFile; Prefix=$candidate.Prefix; Label=$candidate.Label; Version=[string]$version }
            }
        } catch { }
    }
    return $null
}

Write-Step '[1/8] Detectando Python 3.11 o 3.12...'
$Python = Resolve-PythonCommand
if (-not $Python) { throw 'No se encontró Python 3.11 o 3.12. Instálalo y marca Add Python to PATH.' }
Write-Ok "Usando $($Python.Label): $($Python.Version)"

$VenvDir = Join-Path $BackendDir '.venv'
$VenvPython = Join-Path $VenvDir 'Scripts\python.exe'
$Recreate = $false
if (Test-Path $VenvPython) {
    $venvVersion = 'Python 3.12 (entorno existente)'
} else { $Recreate = $true }

Write-Step '[2/8] Preparando entorno virtual...'
if ($Recreate) {
    if (Test-Path $VenvDir) { Remove-Item -Recurse -Force $VenvDir }
    $venvArguments = @($Python.Prefix) + @('-m','venv',$VenvDir)
    $pythonFile = [string]$Python.File
    & $pythonFile @venvArguments
    if ($LASTEXITCODE -ne 0 -or -not (Test-Path $VenvPython)) { throw 'No se pudo crear backend\.venv.' }
    Write-Ok 'Entorno virtual creado.'
} else { Write-Ok "Entorno virtual existente: $venvVersion" }

$Requirements = Join-Path $BackendDir 'requirements-production.txt'
if (-not (Test-Path $Requirements)) { $Requirements = Join-Path $BackendDir 'requirements.txt' }
if (-not (Test-Path $Requirements)) { throw 'No existe requirements-production.txt ni requirements.txt.' }
function Get-Sha256([string]$Path) {
    $sha = [Security.Cryptography.SHA256]::Create()
    $stream = [IO.File]::OpenRead($Path)
    try { return ([BitConverter]::ToString($sha.ComputeHash($stream))).Replace('-','').ToLowerInvariant() }
    finally { $stream.Dispose(); $sha.Dispose() }
}
$ReqHash = Get-Sha256 $Requirements
$ReqHashFile = Join-Path $VenvDir '.requirements.sha256'
$InstalledHash = if (Test-Path $ReqHashFile) { (Get-Content $ReqHashFile -Raw).Trim().ToLowerInvariant() } else { '' }

Write-Step '[3/8] Verificando dependencias...'
if ($ForceReinstallDependencies -or $InstalledHash -ne $ReqHash) {
    & $VenvPython -m pip install --upgrade pip setuptools wheel
    if ($LASTEXITCODE -ne 0) { throw 'Falló la actualización de pip/setuptools/wheel.' }
    & $VenvPython -m pip install --prefer-binary --no-cache-dir -r $Requirements
    if ($LASTEXITCODE -ne 0) { throw 'Falló la instalación de dependencias. Revisa internet, antivirus y data\logs.' }
    Set-Content -Path $ReqHashFile -Encoding ASCII -Value $ReqHash
    Write-Ok 'Dependencias instaladas y verificadas.'
} else { Write-Ok 'Dependencias vigentes; no se reinstalaron.' }

$DbUrlFile = Join-Path $RuntimeDir 'database_url.local.txt'
$DatabaseUrl = [string]$env:DATABASE_URL
if ([string]::IsNullOrWhiteSpace($DatabaseUrl) -and (Test-Path $DbUrlFile)) {
    $DatabaseUrl = (Get-Content $DbUrlFile -Raw).Trim()
}
if ([string]::IsNullOrWhiteSpace($DatabaseUrl)) {
    $EnvFile = Join-Path $Root '.env'
    if (Test-Path $EnvFile) {
        $DbLine = Get-Content $EnvFile | Where-Object { $_ -match '^\s*DATABASE_URL\s*=' } | Select-Object -First 1
        if ($DbLine) { $DatabaseUrl = ($DbLine -split '=',2)[1].Trim() }
    }
}
if ([string]::IsNullOrWhiteSpace($DatabaseUrl)) { throw 'DATABASE_URL PostgreSQL es obligatoria; el inicio con SQLite está deshabilitado.' }
if ($DatabaseUrl.StartsWith('postgres://')) { $DatabaseUrl = 'postgresql+psycopg://' + $DatabaseUrl.Substring(11) }
elseif ($DatabaseUrl.StartsWith('postgresql://')) { $DatabaseUrl = 'postgresql+psycopg://' + $DatabaseUrl.Substring(13) }
if (-not $DatabaseUrl.StartsWith('postgresql+psycopg://')) { throw 'DATABASE_URL debe usar PostgreSQL; SQLite está deshabilitado.' }
$DatabasePath = Join-Path $DataDir 'database.sqlite3'
$DatabaseBackend = 'postgresql'
$SafeDb = ($DatabaseUrl -replace '://([^:@/]+):([^@/]+)@','://$1:***@')
Write-Host "Base seleccionada: $DatabaseBackend ($SafeDb)"

# Variables de aplicación. El proceso backend hereda este entorno; no se escriben secretos en el script hijo.
$env:APP_ENV = 'development'
$env:FLASK_ENV = 'development'
$env:APP_VERSION = '2.7.2-document-center'
$env:SERVER_MODE = if ($TunnelMode) { 'TUNEL_ONLINE' } else { 'LOCAL' }
$env:PUBLIC_TUNNEL_MODE = if ($TunnelMode) { 'true' } else { 'false' }
$env:PROJECT_INSTANCE_ID = $ProjectInstanceId
$env:FLASK_HOST = '127.0.0.1'
$env:FLASK_PORT = [string]$Port
$env:PORT = [string]$Port
$env:LIAM_AVATAR_3D_ENABLED = if ($TunnelMode) { 'false' } else { 'true' }
$env:FRONTEND_PORT = [string]$Port
$env:DATA_DIR = $DataDir
$env:DATABASE_PATH = $DatabasePath
$env:DATABASE_URL = $DatabaseUrl
$env:UPLOAD_FOLDER = Join-Path $DataDir 'uploads'
$env:OUTPUT_FOLDER = Join-Path $DataDir 'archivos_actualizados'
$env:TEMPLATES_FOLDER = Join-Path $DataDir 'templates_originales'
$env:LOG_FOLDER = Join-Path $DataDir 'logs'
$env:BACKUPS_FOLDER = Join-Path $DataDir 'backups'
$env:LOCAL_STORAGE_PATH = Join-Path $DataDir 'storage'
$env:DOCUMENTOS_FOLDER = Join-Path $DataDir 'documentos_institucionales'
$env:CUENTAS_COBRO_FOLDER = Join-Path $DataDir 'cuentas_cobro_plantillas'
$env:FRONTEND_ORIGIN = $LocalBase
$env:PUBLIC_APP_URL = $LocalBase
$env:ALLOWED_ORIGINS = if ($TunnelMode) { '' } else { 'http://127.0.0.1:5000,http://localhost:5000' }
$env:FORCE_HTTPS = 'false'
$env:SESSION_COOKIE_SECURE = if ($TunnelMode) { 'true' } else { 'false' }
$env:SESSION_COOKIE_SAMESITE = 'Lax'
$env:TRUSTED_PROXY_COUNT = if ($TunnelMode) { '1' } else { '0' }
$env:SINGLE_TENANT_MODE = 'false'
$env:ALLOW_EXPERIMENTAL_MULTI_TENANT = 'true'
$env:MULTI_TENANT_STRICT = 'true'
$env:TENANT_STORAGE_ISOLATION = 'true'
$env:MULTI_TENANT_SCHEMA_VERSION = '3'
$env:ALLOW_LEGACY_QUERY_TOKENS = 'false'
$env:ALLOW_PASSWORD_RESET_TOKEN_RESPONSE = 'false'
$env:ALLOW_LOCAL_RECOVERY_CODE = if ($TunnelMode) { 'false' } else { 'true' }
$env:ENABLE_POSTGRESQL_RUNTIME = 'true'
$env:LOGIN_DB_RETRY_ATTEMPTS = '4'
$env:LOGIN_DB_BUSY_TIMEOUT_MS = '150'
$env:LOGIN_DB_RETRY_BASE_MS = '50'
$env:LOGIN_DB_RETRY_BUDGET_MS = '1200'
$env:LOGIN_SLOW_THRESHOLD_MS = '1500'
$env:DB_POOL_SIZE = '8'
$env:DB_MAX_OVERFLOW = '12'
$env:DB_POOL_TIMEOUT_SECONDS = '15'
$env:DB_POOL_RECYCLE_SECONDS = '1200'
$env:DB_CONNECT_TIMEOUT_SECONDS = '10'
$env:DB_STATEMENT_TIMEOUT_MS = '120000'
$env:DB_APPLICATION_NAME = 'primera-infancia-2.7.0'
$env:PYTHONUTF8 = '1'
$env:PYTHONIOENCODING = 'utf-8'

# PostgreSQL instalado en Windows no siempre agrega sus herramientas al PATH.
# Backups y restauraciones necesitan localizar pg_dump/pg_restore.
$PostgresBin = 'C:\Program Files\PostgreSQL\18\bin'
if (Test-Path (Join-Path $PostgresBin 'pg_dump.exe')) {
    $env:PATH = "$PostgresBin;$($env:PATH)"
}

function Ensure-Secret([string]$Name) {
    $file = Join-Path $RuntimeDir "$Name.txt"
    if (-not (Test-Path $file)) {
        $value = & $VenvPython -c "import secrets; print(secrets.token_urlsafe(64))"
        Set-Content -Path $file -Encoding ASCII -Value $value
    }
    return (Get-Content $file -Raw).Trim()
}
$env:SECRET_KEY = Ensure-Secret 'local_secret_key'
$env:JWT_SECRET_KEY = Ensure-Secret 'local_jwt_secret_key'
if ($env:SECRET_KEY -eq $env:JWT_SECRET_KEY) {
    Remove-Item (Join-Path $RuntimeDir 'local_jwt_secret_key.txt') -Force
    $env:JWT_SECRET_KEY = Ensure-Secret 'local_jwt_secret_key'
}
$env:INITIAL_ADMIN_USERNAME = 'admin.local'
$env:INITIAL_ADMIN_EMAIL = 'admin.local@primera-infancia.local'
$env:INITIAL_ADMIN_NAME = 'Administrador Local'
$env:INITIAL_ADMIN_FORCE_PASSWORD_CHANGE = 'true'
$env:INITIAL_FOUNDATION_NAME = 'Entorno local de pruebas'
$BootstrapPassword = & $VenvPython -c "import secrets,string; r=secrets.SystemRandom(); chars=string.ascii_letters+string.digits+'@#_-'; p=[r.choice(string.ascii_uppercase),r.choice(string.ascii_lowercase),r.choice(string.digits),r.choice('@#_-')]+[r.choice(chars) for _ in range(24)]; r.shuffle(p); print(''.join(p))"
$env:INITIAL_ADMIN_PASSWORD = ([string]$BootstrapPassword).Trim()

Write-Step '[4/8] Inicializando y comprobando la base...'
Push-Location $BackendDir
try {
    & $VenvPython init_hosting.py
    if ($LASTEXITCODE -ne 0) { throw "init_hosting.py terminó con código $LASTEXITCODE. Revisa data\logs." }
} finally { Pop-Location }
$Marker = Join-Path $DataDir '.primera_infancia_initialized.json'
$CredentialsFile = Join-Path $RuntimeDir 'CREDENCIALES_INICIALES_LOCAL.txt'
if (Test-Path $Marker) {
    try {
        $markerData = Get-Content $Marker -Raw | ConvertFrom-Json
        if ($markerData.admin_created -eq $true) {
            @(
                'PRIMERA INFANCIA - CREDENCIALES INICIALES LOCALES',
                '=================================================',
                "Usuario: $($env:INITIAL_ADMIN_USERNAME)",
                "Correo:  $($env:INITIAL_ADMIN_EMAIL)",
                "Clave:   $($env:INITIAL_ADMIN_PASSWORD)",
                '',
                'Cambia esta clave en el primer ingreso y elimina este archivo.'
            ) | Set-Content -Path $CredentialsFile -Encoding UTF8
            Write-Warn "Administrador inicial creado. Credenciales: $CredentialsFile"
        } elseif (Test-Path $CredentialsFile) {
            Write-Warn 'La base ya contiene usuarios. El archivo de credenciales iniciales puede ser histórico; usa la clave vigente.'
        }
    } catch { Write-Warn 'No se pudo leer el marcador de inicialización.' }
}

function Get-PortPids([int]$PortNumber) {
    $ids = @()
    try { $ids = @(Get-NetTCPConnection -LocalPort $PortNumber -State Listen -ErrorAction SilentlyContinue | Select-Object -ExpandProperty OwningProcess -Unique) } catch { }
    if (-not $ids) {
        $ids = @(netstat -ano 2>$null | Select-String -Pattern ":$PortNumber\s+.*LISTENING\s+(\d+)$" | ForEach-Object { [int]$_.Matches[0].Groups[1].Value } | Select-Object -Unique)
    }
    return @($ids | Where-Object { $_ -gt 0 })
}
function Get-HealthInfo([int]$Timeout = 3) {
    try { return Invoke-RestMethod -Uri $HealthUrl -TimeoutSec $Timeout } catch { return $null }
}
$ExpectedTunnel = $TunnelMode
$health = Get-HealthInfo
if ($health) {
    $sameInstance = ([string]$health.project_instance_id -eq $ProjectInstanceId)
    $sameMode = ([bool]$health.public_tunnel_mode -eq [bool]$ExpectedTunnel)
    if ($sameInstance -and $sameMode) {
        Write-Ok '[5/8] Esta copia ya está activa.'
        if (-not $NoBrowser -and $Mode -eq 'Local') { Start-Process $LocalFrontend }
        if ($Mode -eq 'Tunnel') { & (Join-Path $ScriptDir 'iniciar_tunel_cloudflare.ps1') }
        exit 0
    }
}
$PortPids = Get-PortPids $Port
if ($PortPids.Count -gt 0) {
    Write-Warn "[5/8] El puerto $Port está ocupado por PID(s): $($PortPids -join ', ')."
    $allowStop = $env:PI_AUTO_STOP_OTHER -eq '1'
    if (-not $allowStop) { $allowStop = (Read-Host '¿Cerrar esos procesos para iniciar esta copia? [S/N]') -match '^[Ss]$' }
    if (-not $allowStop) { throw 'Operación cancelada porque el puerto está ocupado.' }
    foreach ($pidValue in $PortPids) { Stop-Process -Id $pidValue -Force -ErrorAction SilentlyContinue }
    Start-Sleep -Seconds 2
} else { Write-Ok '[5/8] Puerto local disponible.' }

Write-Step '[6/8] Iniciando backend y frontend...'
$RunScript = Join-Path $RuntimeDir 'run_backend.ps1'
$runContent = @"
`$ErrorActionPreference = 'Continue'
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
`$host.UI.RawUI.WindowTitle = 'Primera Infancia - Backend 2.7.0 ($Mode)'
Set-Location -LiteralPath '$($BackendDir.Replace("'","''"))'
Write-Host 'Plataforma: $LocalFrontend' -ForegroundColor Cyan
Write-Host 'Instancia: $ProjectInstanceId' -ForegroundColor DarkGray
Write-Host 'Base: $DatabaseBackend' -ForegroundColor DarkGray
Write-Host 'Logs: $($env:LOG_FOLDER)' -ForegroundColor DarkGray
& '$($VenvPython.Replace("'","''"))' 'app.py'
Write-Host ''
Write-Host 'El backend terminó. Revisa data\logs.' -ForegroundColor Yellow
"@
Set-Content -Path $RunScript -Encoding UTF8 -Value $runContent
$BackendProcess = Start-Process -FilePath 'powershell.exe' -ArgumentList @('-NoLogo','-NoProfile','-ExecutionPolicy','Bypass','-File',"`"$RunScript`"") -WorkingDirectory $Root -PassThru
Set-Content -Path (Join-Path $RuntimeDir 'backend.pid') -Encoding ASCII -Value $BackendProcess.Id

Write-Step '[7/8] Esperando /api/health...'
$ready = $null
for ($i=0; $i -lt 90; $i++) {
    Start-Sleep -Seconds 1
    $candidate = Get-HealthInfo 2
    if ($candidate -and [string]$candidate.status -eq 'ok' -and [string]$candidate.project_instance_id -eq $ProjectInstanceId -and [bool]$candidate.public_tunnel_mode -eq [bool]$ExpectedTunnel) {
        $ready = $candidate; break
    }
    if ($BackendProcess.HasExited) { break }
}
if (-not $ready) { throw "El backend no confirmó la instancia/modo en 90 segundos. Revisa la ventana del backend y $($env:LOG_FOLDER)." }
Write-Ok "Backend listo. Versión=$($ready.version); DB=$($ready.database_backend); latencia DB=$($ready.database_latency_ms) ms."

Write-Step '[8/8] Apertura final...'
if ($Mode -eq 'Tunnel') {
    & (Join-Path $ScriptDir 'iniciar_tunel_cloudflare.ps1')
} elseif ($Mode -eq 'Local') {
    if (-not $NoBrowser) { Start-Process $LocalFrontend }
    Write-Ok "Plataforma local: $LocalFrontend"
} else {
    Write-Ok 'Backend en modo túnel listo para cloudflared.'
}
