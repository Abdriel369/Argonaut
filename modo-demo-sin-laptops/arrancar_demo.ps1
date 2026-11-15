<#
.SYNOPSIS
    Arranca la demo de Médico de estación en Windows.
.DESCRIPTION
    Ejecuta el script multiplataforma arrancar_demo.py con el interprete de Python del sistema.
#>

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$Runner = Join-Path $ScriptDir "arrancar_demo.py"

if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
    Write-Error "No se encontro 'python' en el PATH. Asegurate de tener Python instalado y accesible."
    exit 1
}

python $Runner

