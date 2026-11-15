# Demo del reloj y de la vista de tripulación · 2–3 minutos

> Todo es simulado. No es una evaluación médica ni una decisión de aptitud.

## Antes de empezar

1. Arranca los servicios (Windows):
   ```powershell
   .\scripts\arrancar_local.ps1
   ```
   Linux/macOS:
   ```bash
   ./scripts/arrancar_local.sh
   ```
2. Abre `http://127.0.0.1:8100/` (o la IP de la Laptop 1 desde el celular).
3. Si quieres el modo demo sin las tres laptops, usa
   `modo-demo-sin-laptops/arrancar_demo.sh local` (Linux/macOS) o el mismo backend
   con `URL_ORQUESTADOR` apuntando al orquestador local.

## Guion

### 1. El tablero del comandante (45 s)

- En la página principal, baja a **Crew**. Se ven los seis astronautas, la
  distribución por nivel, el promedio de preparación, la mejor y la menor.
- Pulsa **With alerts**: quedan los que están en amarillo o peor. Vuelve a **All**.
- Pulsa **Incomplete data**: Hana Sato (AST-05) aparece al final con
  **Not enough data**, nunca con un 0 %.
- Pulsa la fila de **Aisha Ndiaye (AST-03)**. El panel muestra el desglose del
  índice, el riesgo de los modelos aparte, sus indicadores, la tendencia, las
  alertas, la junta y la calidad de los datos. Si la Laptop 3 no responde, dice
  **Local rules only**.
- Cierra el detalle. Abre **How is this calculated?** y lee la fórmula y el límite.

### 2. El reloj del astronauta (60 s)

- Pulsa **Watch** en la navegación (o abre `http://127.0.0.1:8100/reloj/`).
- Pantalla **Today**: nombre, día, nivel, riesgo y **What to do now**.
- Ve a **Measure**. Pulsa **Measure now**: se rellenan pulso, HRV, SpO2 y
  temperatura con una lectura simulada alrededor de la línea base. Corrige un
  valor a mano si quieres. Pulsa **Send**: aparece **Sent.** y el estado se
  refresca con la respuesta compacta.
- Ve a **Alert**: se ve la alerta principal y sus pasos. Marca un paso: se guarda
  en el servidor y aparecerá en el informe del cirujano de vuelo. Pulsa
  **Remind me in 15 min** para ver la cuenta atrás local.
- Ve a **Trend**: tres mini-gráficas y la proyección **If this continues…**.
  Si hay menos de 3 puntos, dice **Not enough data to project**.

### 3. Sin conexión (30 s)

- En **My watch**, activa el modo offline del navegador (DevTools → Network →
  Offline) o apaga el backend.
- Vuelve a **Measure**, pulsa **Measure now** y **Send**: dice **Saved on watch**
  y la lectura queda en la cola.
- Recarga la página: la cola sigue ahí.
- Vuelve a online: el reloj reintenta con backoff (1 s, 2 s, 4 s…) y sincroniza
  una sola vez. En **My watch** puedes **Retry**, **Edit** o **Discard**.
- Si el servidor rechaza un valor (4xx), la lectura pasa a **Needs review** con
  el mensaje exacto; no se reintenta para siempre.

### 4. Reinicio (15 s)

- En la página principal, panel **Demo**, pulsa **Reset**. Vuelve al día 1 con
  los seis astronautas. La historia de AST-01 sigue igual: verde, verde,
  amarillo, naranja, rojo, amarillo, verde.

## Qué mirar si algo falla

- **Degraded**: si la Laptop 3 no responde, la vista Crew sigue con reglas
  locales y el detalle lo indica. Si la Laptop 2 no responde, el detalle muestra
  el modo degradado.
- **Suspicious data**: AST-04 tiene una lectura imposible el día 3; debe verse
  como aviso de equipo y no cambiar su nivel verde.
- **AST-05**: no tiene días 3–7; debe aparecer como **Not enough data**, al final.
- **Consola**: no debe haber 404 ni errores de JavaScript. Todos los recursos son
  locales.
