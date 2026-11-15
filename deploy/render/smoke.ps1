# Smoke test de la demo integrada (backend + orquestador en un solo proceso).
# Uso: powershell -ExecutionPolicy Bypass -File deploy/render/smoke.ps1 -Base http://127.0.0.1:8111

param(
  [string]$Base = "http://127.0.0.1:8111"
)

$ErrorActionPreference = "Stop"
$fallos = 0

function Probar([string]$nombre, [scriptblock]$accion) {
  try {
    $resultado = & $accion
    Write-Host "OK    $nombre -> $resultado"
  } catch {
    $script:fallos++
    Write-Host "FALLA $nombre -> $($_.Exception.Message)" -ForegroundColor Red
  }
}

function Get-Json([string]$ruta) {
  return Invoke-RestMethod -Uri "$Base$ruta" -Method Get -TimeoutSec 20
}

function Post-Json([string]$ruta, $cuerpo) {
  $json = if ($null -eq $cuerpo) { "{}" } else { $cuerpo | ConvertTo-Json -Depth 12 }
  return Invoke-RestMethod -Uri "$Base$ruta" -Method Post -Body $json `
    -ContentType "application/json" -TimeoutSec 30
}

Probar "1. pagina principal y assets locales" {
  $r = Invoke-WebRequest -Uri "$Base/" -UseBasicParsing -TimeoutSec 20
  if ($r.StatusCode -ne 200) { throw "HTTP $($r.StatusCode)" }
  if ($r.Content -notmatch "Station Doctor") { throw "sin titulo" }
  $js = Invoke-WebRequest -Uri "$Base/js/app.js" -UseBasicParsing -TimeoutSec 20
  $css = Invoke-WebRequest -Uri "$Base/css/estilos.css" -UseBasicParsing -TimeoutSec 20
  if ($js.StatusCode -ne 200 -or $css.StatusCode -ne 200) { throw "assets no servidos" }
  "HTML $($r.RawContentLength) B, app.js $($js.RawContentLength) B, estilos.css $($css.RawContentLength) B"
}

Probar "2. seis astronautas" {
  $t = Get-Json "/api/tripulacion"
  if ($t.astronautas.Count -ne 6) { throw "esperaba 6, hay $($t.astronautas.Count)" }
  ($t.astronautas | ForEach-Object { $_.id }) -join ","
}

Probar "3. dia de mision (del 1 al 4)" {
  $inicio = Post-Json "/api/demo/reiniciar" $null
  if ($inicio.dia_actual -ne 1) { throw "dia inicial $($inicio.dia_actual)" }
  $e = Post-Json "/api/demo/dia" @{ dia = 4 }
  if ($e.dia_actual -ne 4) { throw "dia_actual=$($e.dia_actual)" }
  "dia 1 -> 4, nivel $($e.resultado.nivel_global), modo $($e.resultado.modo)"
}

Probar "4. respuestas guardadas en uso" {
  $r = Get-Json "/api/red"
  if (-not $r.respuestas_guardadas) { throw "respuestas_guardadas=false" }
  $e = Get-Json "/api/estado"
  $miembros = @($e.resultado.junta | Where-Object { $_.estado -eq "respondio" })
  if ($miembros.Count -lt 1) { throw "ningun especialista respondio" }
  "$($miembros.Count) especialistas respondieron ($(($miembros | ForEach-Object { $_.especialista }) -join ', ')); origen=$($e.resultado.origen)"
}

Probar "5. alertas y protocolos" {
  $e = Get-Json "/api/estado"
  if ($e.resultado.alertas.Count -lt 1) { throw "sin alertas en el dia 4" }
  $a = $e.resultado.alertas[0]
  $p = $e.resultado.protocolos.($a.protocolo_id)
  if (-not $p) { throw "protocolo $($a.protocolo_id) ausente" }
  $paso = $p.pasos[0]
  $marcado = Post-Json "/api/protocolo/paso" @{ alerta_id = $a.id; paso_id = $paso.id; hecho = $true }
  if (-not $marcado.pasos_hechos.($a.id)) { throw "el paso no quedo marcado" }
  "$($e.resultado.alertas.Count) alertas; nivel $($e.resultado.nivel_global); protocolo $($p.id) con $($p.pasos.Count) pasos; paso $($paso.id) marcado"
}

Probar "6. evento solar" {
  $e = Post-Json "/api/demo/evento-solar" @{ activo = $true }
  $modo = $e.resultado.modo
  Post-Json "/api/demo/evento-solar" @{ activo = $false } | Out-Null
  "evento solar activado y desactivado; modo $modo"
}

Probar "7. detalle de tripulacion" {
  $d = Get-Json "/api/tripulacion/AST-03?dia=4"
  if (-not $d.astronauta.id) { throw "detalle incompleto" }
  "$($d.astronauta.id) preparacion=$($d.preparacion.preparacion_pct) estado=$($d.preparacion.estado)"
}

Probar "8. sensor defectuoso" {
  $e = Post-Json "/api/demo/sensor-defectuoso" @{ activo = $true; tipo = "imposible" }
  $aviso = $e.resultado.sensores_sospechosos[0]
  if (-not $aviso) { throw "sin aviso de sensor" }
  Post-Json "/api/demo/sensor-defectuoso" @{ activo = $false } | Out-Null
  "$($aviso.indicador) = $($aviso.valor_leido) ($($aviso.motivo)): $($aviso.aviso)"
}

Probar "9. modo degradado (caida simulada de la Laptop 2)" {
  $e = Post-Json "/api/demo/caida-laptop2" @{ activa = $true }
  if ($e.resultado.modo -ne "degradado") { throw "modo=$($e.resultado.modo)" }
  $noDisp = ($e.resultado.especialistas_no_disponibles -join ",")
  $vuelta = Post-Json "/api/demo/caida-laptop2" @{ activa = $false }
  if ($vuelta.resultado.modo -ne "completo") { throw "no volvio a completo: $($vuelta.resultado.modo)" }
  "degradado con $noDisp y vuelta a completo al reparar la red"
}

Probar "10. reloj web" {
  $w = Invoke-WebRequest -Uri "$Base/reloj/" -UseBasicParsing -TimeoutSec 20
  if ($w.StatusCode -ne 200) { throw "HTTP $($w.StatusCode)" }
  $estado = Get-Json "/api/reloj/estado?astronauta_id=AST-01"
  $js = Invoke-WebRequest -Uri "$Base/reloj/reloj.js" -UseBasicParsing -TimeoutSec 20
  "HTML $($w.RawContentLength) B, reloj.js $($js.RawContentLength) B, nivel $($estado.nivel_global), alertas $($estado.alertas.Count), campos $($estado.campos.Count)"
}

Probar "11. lectura del reloj idempotente" {
  $lectura = @{
    lectura_id    = [guid]::NewGuid().ToString()
    astronauta_id = "AST-01"
    capturado_en  = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ")
    origen        = "reloj-simulado"
    indicadores   = @{ sueno_h = 6.9; animo = 4; estres = 36; fc_reposo = 63; hrv = 51; spo2 = 98; temperatura = 36.6 }
  }
  $r1 = Post-Json "/api/reloj/lectura" $lectura
  $r2 = Post-Json "/api/reloj/lectura" $lectura
  if (-not $r1.aceptado -or -not $r2.repetida) { throw "idempotencia rota" }
  "aceptada=$($r1.aceptado), repetida=$($r2.repetida), nivel $($r1.nivel_global)"
}

Probar "12. reiniciar demo" {
  $e = Post-Json "/api/demo/reiniciar" $null
  $t = Get-Json "/api/tripulacion"
  if ($e.dia_actual -ne 1 -or $t.astronautas.Count -ne 6) { throw "estado tras reiniciar incorrecto" }
  "dia $($e.dia_actual), $($t.astronautas.Count) astronautas"
}

Probar "13. exportar CSV y salud" {
  $csv = Invoke-WebRequest -Uri "$Base/api/exportar.csv" -UseBasicParsing -TimeoutSec 20
  $salud = Get-Json "/salud"
  if ($salud.estado -ne "ok") { throw "salud=$($salud.estado)" }
  "CSV $($csv.RawContentLength) B, salud=$($salud.estado)"
}

if ($fallos -gt 0) {
  Write-Host "`n$fallos prueba(s) fallaron." -ForegroundColor Red
  exit 1
}
Write-Host "`nTodas las pruebas de humo pasaron." -ForegroundColor Green
