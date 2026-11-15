# ============================================================================
# Arranca TODO en esta máquina sin Docker (Windows / PowerShell).
# Los mismos siete servicios que scripts/arrancar_local.sh, en 127.0.0.1.
#
#   .\scripts\arrancar_local.ps1            arranca y deja los logs en .tmp\astro-medico
#   .\scripts\arrancar_local.ps1 parar      detiene todo
#
# Si Windows bloquea el script por la directiva de ejecución:
#   powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\arrancar_local.ps1
#
# No requiere bash. Usa el Python del .venv si existe; si no, el de PATH.
# ============================================================================

param([string]$Accion = "start")

$ErrorActionPreference = "Stop"
$Raiz = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$Logs = Join-Path $Raiz ".tmp\astro-medico"
$Pids = Join-Path $Logs "pids.txt"
$Python = if (Test-Path (Join-Path $Raiz ".venv\Scripts\python.exe")) {
    Join-Path $Raiz ".venv\Scripts\python.exe"
} else { "python" }

New-Item -ItemType Directory -Force -Path $Logs | Out-Null

function Parar {
    if (Test-Path $Pids) {
        Get-Content $Pids | ForEach-Object {
            if ($_ -match '^\d+$') { & cmd.exe /c "taskkill /PID $_ /T /F >nul 2>&1" | Out-Null }
        }
        Remove-Item $Pids -Force -ErrorAction SilentlyContinue
    }
}

if ($Accion -eq "parar") {
    Parar
    Write-Output "Servicios detenidos."
    exit 0
}

Parar
Start-Sleep -Seconds 1   # deja liberar los puertos

function Lanzar {
    param(
        [string]$Nombre,
        [string]$Carpeta,
        [string]$Rutas,
        [string]$Objetivo,
        [int]$Puerto,
        [string]$Extra = "",
        [hashtable]$Variables = @{}
    )
    $partes = @("set `"PYTHONPATH=$Rutas`"")
    foreach ($clave in $Variables.Keys) {
        $partes += "set `"$clave=$($Variables[$clave])`""
    }
    $partes += "`"$Python`" -m uvicorn $Objetivo $Extra --host 127.0.0.1 --port $Puerto >> `"$Logs\$Nombre.log`" 2>&1"
    $comando = $partes -join " && "
    $proceso = Start-Process -FilePath "cmd.exe" -ArgumentList "/c", $comando `
        -WorkingDirectory $Carpeta -WindowStyle Hidden -PassThru
    Add-Content -Path $Pids -Value $proceso.Id
    Write-Output ("  {0,-14} http://127.0.0.1:{1}" -f $Nombre, $Puerto)
}

$L1 = Join-Path $Raiz "laptop1-backend-frontend"
$L2 = Join-Path $Raiz "laptop2-modelos"
$L3 = Join-Path $Raiz "laptop3-orquestador"
$Datos = Join-Path $L2 "datos-sinteticos"

Write-Output "Arrancando los siete servicios (logs en $Logs):"

# Laptop 2: tres modelos + gateway
Lanzar "modelo-sueno" (Join-Path $L2 "modelos\sueno") `
    "$Raiz;$Datos;$(Join-Path $L2 'modelos\sueno')" "api_sueno:app" 8210
Lanzar "modelo-fatiga" (Join-Path $L2 "modelos\fatiga-bienestar") `
    "$Raiz;$Datos;$(Join-Path $L2 'modelos\fatiga-bienestar')" "api_fatiga:app" 8220
Lanzar "modelo-cardio" (Join-Path $L2 "modelos\cardiovascular") `
    "$Raiz;$Datos;$(Join-Path $L2 'modelos\cardiovascular')" "api_cardio:app" 8230
Lanzar "gateway" $L2 "$Raiz;$L2" "gateway.principal:crear_app" 8200 "--factory"

# Laptop 3: modelo solar + orquestador
Lanzar "modelo-solar" (Join-Path $L3 "modelos\riesgo-solar") `
    "$Raiz;$(Join-Path $L3 'modelos\riesgo-solar')" "api_solar:app" 8310
Lanzar "orquestador" $L3 "$Raiz;$L3" "orquestador.principal:crear_app" 8300 "--factory" `
    @{ URL_GATEWAY = "http://127.0.0.1:8200"; URL_MODELO_SOLAR = "http://127.0.0.1:8310" }

# Laptop 1: backend + frontend
$RutaBd = if ($env:RUTA_BD) { $env:RUTA_BD } else { Join-Path $Logs "astro_medico.db" }
Lanzar "backend" $L1 "$Raiz;$L1;$L3" "backend.principal:crear_app" 8100 "--factory" `
    @{ URL_ORQUESTADOR = "http://127.0.0.1:8300"; RUTA_BD = $RutaBd }

Write-Output ""
Write-Output "Interfaz:  http://127.0.0.1:8100/"
Write-Output "Reloj:     http://127.0.0.1:8100/reloj/"
Write-Output "Para parar: .\scripts\arrancar_local.ps1 parar"
