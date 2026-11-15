# Argonaut · demo en Render (un solo servicio)

Esta carpeta contiene todo lo necesario para publicar **solo la demo funcional** de
Argonaut (Station Doctor) en Render, con **un Web Service**, **un contenedor Docker**
y **un proceso**.

> Prototipo con datos simulados. No es una herramienta de diagnóstico médico.

## Arquitectura

```text
Navegador (HTTPS)
      │
      ▼
┌─────────────────────────────────────────────────────────────┐
│ Un contenedor · un proceso (uvicorn)                        │
│                                                             │
│  FastAPI backend  ──httpx.ASGITransport──▶  orquestador     │
│  (API + frontend)                          (reglas, junta,  │
│       │                                     protocolos,     │
│       └── SQLite /tmp/astro_medico.db       informe)        │
│                                                  │          │
│                                                  ▼          │
│                                    respuestas-guardadas.json│
│                                    (88 respuestas grabadas) │
└─────────────────────────────────────────────────────────────┘
```

- No hay segunda laptop, segundo puerto ni segundo servicio.
- `httpx.ASGITransport` llama al orquestador **en el mismo proceso**, sin red.
- Los especialistas no ejecutan modelos: `ClienteGuardado` devuelve las 88
  respuestas de ejecuciones reales (`modo-demo-sin-laptops/respuestas-guardadas.json`).
- La interfaz muestra siempre el aviso de demo con respuestas guardadas.

## Variables de entorno

| Variable | Valor en Render | Para qué |
|---|---|---|
| `RUTA_BD` | `/tmp/astro_medico.db` | SQLite temporal (se crea sola). |
| `RESPUESTAS_GUARDADAS` | `/app/respuestas-guardadas.json` | Respuestas grabadas de los especialistas. |
| `PORT` | la asigna Render | Puerto en el que escucha uvicorn. |
| `URL_ORQUESTADOR` | `http://orquestador.interno` | Solo URL simbólica: el transporte es en proceso. |

El Dockerfile ya trae valores por defecto para todas. En Render solo hace falta
`RUTA_BD` y `RESPUESTAS_GUARDADAS` (o ninguna, porque están en la imagen).

## Probar en local sin Docker

Desde la raíz del repositorio, con Python 3.12:

```powershell
# Windows (PowerShell)
$env:PYTHONPATH = "$PWD;$PWD\laptop1-backend-frontend;$PWD\laptop3-orquestador"
$env:RUTA_BD = "$PWD\.tmp\render-test\astro_medico.db"
$env:RESPUESTAS_GUARDADAS = "$PWD\modo-demo-sin-laptops\respuestas-guardadas.json"
$env:PORT = "8100"
.\.venv\Scripts\python.exe -m uvicorn app:app --app-dir deploy/render --host 0.0.0.0 --port $env:PORT
```

```bash
# Linux/macOS
export PYTHONPATH="$PWD:$PWD/laptop1-backend-frontend:$PWD/laptop3-orquestador"
export RUTA_BD=/tmp/astro_medico.db
export RESPUESTAS_GUARDADAS="$PWD/modo-demo-sin-laptops/respuestas-guardadas.json"
python -m uvicorn app:app --app-dir deploy/render --host 0.0.0.0 --port 8100
```

Abre <http://127.0.0.1:8100/> (tablero) y <http://127.0.0.1:8100/reloj/> (reloj).

## Probar con Docker (como en Render)

```bash
docker build -f deploy/render/Dockerfile -t argonaut-render:local .
docker run --rm --memory=512m --memory-swap=512m --cpus=0.1 \
  -e PORT=10000 -p 10000:10000 argonaut-render:local
```

Abre <http://127.0.0.1:10000/>. El límite `--memory=512m --cpus=0.1` reproduce el
plan gratuito de Render.

Pruebas de humo automatizadas (13 comprobaciones):

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File deploy/render/smoke.ps1 -Base http://127.0.0.1:10000
```

## Publicar en Render (manual)

El repositorio **no se sube desde aquí**: tú haces el `git push` a tu rama y
conectas GitHub en Render.

### Opción A · Web Service (recomendada)

1. **Sube tu rama a GitHub** (tú, manualmente; este trabajo no hace `git push`).
   Asegúrate de incluir `deploy/render/` y `render.yaml` en el commit.
2. En Render, entra con tu cuenta y autoriza **GitHub** si es la primera vez
   (*Account Settings → GitHub → Connect*). Dale acceso solo a este repositorio.
3. **New + → Web Service** → *Build and deploy from a Git repository* → elige el
   repositorio de Argonaut.
4. Configura:
   - **Name**: `argonaut-station-doctor` (o el que quieras).
   - **Language / Runtime**: `Docker`
   - **Branch**: la rama que subiste.
   - **Root Directory**: vacío (la raíz del repo).
   - **Dockerfile Path**: `deploy/render/Dockerfile`
   - **Docker Build Context Directory**: `.`
   - **Instance Type**: `Free`
   - **Health Check Path**: `/salud`
   - **Auto-Deploy**: `Off` si quieres publicar a mano.
5. **Environment Variables** (opcionales; el Dockerfile ya trae los valores):
   - `RUTA_BD=/tmp/astro_medico.db`
   - `RESPUESTAS_GUARDADAS=/app/respuestas-guardadas.json`
6. **Create Web Service**. Render construye la imagen y arranca
   `uvicorn app:app` en el puerto que le pasa en `PORT`.
7. Cuando el estado sea **Live**, abre la URL `https://<servicio>.onrender.com/`.
   Comprueba también `https://<servicio>.onrender.com/salud` y
   `https://<servicio>.onrender.com/reloj/`.

No configures un *start command*: lo define el `CMD` del Dockerfile. Si Render te
pide un puerto, déjalo vacío: se lee de `PORT`.

### Opción B · Blueprint (`render.yaml`)

En Render: **New + → Blueprint**, conecta el repositorio y confirma. El archivo
[`render.yaml`](../../render.yaml) ya declara imagen, plan gratuito, health check
y variables. Revisa la rama antes de aplicar.

### Comprobar HTTPS

```bash
curl -s https://<servicio>.onrender.com/salud
curl -s https://<servicio>.onrender.com/api/tripulacion | head
```

Debe responder `{"estado":"ok",...}` y la lista de los seis astronautas. El
certificado HTTPS lo gestiona Render; la app no necesita configuración TLS.

## Qué se pierde al reiniciar o suspender

La SQLite vive en `/tmp`, que es **temporal**:

- En el plan gratuito Render suspende el servicio tras 15 minutos sin tráfico.
- Al despertar puede arrancar una instancia nueva, con `/tmp` vacío.
- La base se **reconstruye sola** al arrancar: esquema + los seis astronautas y
  su guion de 7 días (desde los TOML de configuración).

Se pierde, por tanto, el estado de la sesión anterior:

- día de misión seleccionado y astronauta activo;
- alertas/pasos de protocolo marcados y evaluaciones guardadas;
- lecturas del reloj y su idempotencia;
- informes pendientes/enviados y el último enlace con la Tierra;
- evento solar y sensor defectuoso activos.

Las **respuestas de los especialistas** no se pierden: están grabadas en la imagen.
Para conservar el estado entre reinicios habría que añadir un disco persistente de
Render (no es gratuito) o Postgres; no se incluye porque la demo no lo necesita.

## Regenerar las respuestas guardadas

Requiere los modelos reales (no se instalan en la imagen):

```bash
python modo-demo-sin-laptops/grabar_respuestas.py
```

Genera `modo-demo-sin-laptops/respuestas-guardadas.json` (88 respuestas, 112 estados).

## Recursos medidos (contenedor, 512 MB / 0.1 CPU)

| Métrica | Valor |
|---|---|
| RAM en reposo y bajo carga de las 13 pruebas | ~41 MiB (`VmRSS` 57,6 MB) |
| CPU media | < 1 % |
| Imagen | 211 MB |
| Procesos | 1 (uvicorn como PID 1) |
| Arranque hasta `/salud` | ~10 s |
| Apagado ordenado (SIGTERM) | ~1,1 s, exit code 0 |

## Solución de problemas

- **La página carga pero no hay respuestas guardadas**: revisa
  `RESPUESTAS_GUARDADAS` y que el archivo exista dentro de la imagen
  (`docker exec <id> ls -l /app/respuestas-guardadas.json`).
- **Modo degradado permanente**: la demo arrancó sin respuestas guardadas o el
  JSON no coincide con los datos. Los logs muestran
  `respuestas_guardadas=True/False`.
- **Datos raros tras varios días**: pulsa **Restart demo** en la interfaz o
  reinicia el servicio; la base se reconstruye.
- **Cold start lento**: el plan gratuito duerme el servicio; la primera petición
  puede tardar 30–60 s.
