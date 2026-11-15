// Station Doctor · UI application.
// Asks the backend (Laptop 1) for the state, renders it and sends user actions.
// If something fails, a notice is shown and the screen keeps working with the last data received.

import { esc, icono, NOMBRES_ESPECIALISTA } from "./util.js";
import { ANIMOS, PREGUNTAS_EQUIPO } from "./contenido.js";
import { nombreIndicador, unidadIndicador, traducirError, traducirNombre } from "./i18n.js";
import {
  vistaEstado, vistaTablero, vistaCuerpo, vistaAlertas, vistaJunta, vistaTendencia, vistaInforme,
  zonaPorDefecto,
} from "./vistas.js";

const INTERVALO_ESTADO_MS = 4000;     // syncs phone and laptop
const INTERVALO_RED_MS = 5000;        // healthchecks of the three laptops
const SEGUNDOS_POR_DIA = 8;           // "Play week": one day every ~8 s
const SENALES_REACCION = 5;

const app = {
  datos: null,            // last state received from the backend
  red: null,              // last network state
  conexion: true,         // does Laptop 1 respond?
  zona: null,             // selected body-map zone
  zonaElegida: false,     // true if the person chose it (it does not change by itself)
  indicador: "sueno_h",   // indicator of the trend chart
  informesAbiertos: new Set(),
  temporizadores: new Map(),   // key -> end time (ms)
  nivelAnterior: null,
  firmaRed: null,
  reproduccion: null,
  ocupado: false,
  diaFormulario: null,
};
const cache = {};   // last HTML painted per container: only what changes is repainted
const $ = (id) => document.getElementById(id);

// ---------------------------------------------------------------------------
// Backend communication (relative routes: works on any IP in the router)
// ---------------------------------------------------------------------------
async function pedir(ruta, cuerpo) {
  const opciones = cuerpo === undefined ? {} : {
    method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(cuerpo),
  };
  const respuesta = await fetch(ruta, opciones);
  let datos = null;
  try { datos = await respuesta.json(); } catch { /* response without body */ }
  if (!respuesta.ok) {
    const detalle = datos && datos.detail ? datos.detail : `The server responded ${respuesta.status}.`;
    throw new Error(typeof detalle === "string" ? detalle : "The data is not valid.");
  }
  return datos;
}

async function cargarEstado() {
  if (app.ocupado) return;
  try {
    app.datos = await pedir("api/estado");
    app.conexion = true;
  } catch {
    app.conexion = false;
  }
  pintar();
}

async function cargarRed() {
  try {
    app.red = await pedir("api/red");
    const firma = JSON.stringify([app.red.laptop3.ok, app.red.laptop2.ok, app.red.modelo_solar.ok]);
    // If a laptop went down or came back, ask for a new evaluation to reflect it.
    if (app.firmaRed !== null && app.firmaRed !== firma && !app.ocupado) {
      try { app.datos = await pedir("api/reevaluar", {}); } catch { /* retried next cycle */ }
    }
    app.firmaRed = firma;
    app.conexion = true;
  } catch {
    app.red = null;
    app.conexion = false;
  }
  pintar();
}

/** Runs an action that returns the new state; shows the error in 'salida' if it fails. */
async function accion(ruta, cuerpo, salida) {
  app.ocupado = true;
  if (salida) salida.textContent = "";
  try {
    const datos = await pedir(ruta, cuerpo ?? {});
    if (datos && datos.resultado) app.datos = datos;
    app.conexion = true;
    return datos;
  } catch (error) {
    const texto = error instanceof TypeError
      ? "No connection to Laptop 1. Check the network and try again." : traducirError(error.message);
    if (salida) salida.textContent = texto;
    return null;
  } finally {
    app.ocupado = false;
    pintar();
  }
}

// ---------------------------------------------------------------------------
// Rendering
// ---------------------------------------------------------------------------
function poner(id, html) {
  if (cache[id] === html) return;
  cache[id] = html;
  const contenedor = $(id);
  // If focus was inside, it is returned to the same control after repainting (keyboard and screen readers).
  const activo = contenedor.contains(document.activeElement) ? document.activeElement : null;
  let selector = null;
  if (activo) {
    const d = activo.dataset;
    if (activo.id) selector = `#${activo.id}`;
    else if (d.paso) selector = `[data-alerta="${d.alerta}"][data-paso="${d.paso}"]`;
    else if (d.zona) selector = `${activo.tagName.toLowerCase()}[data-zona="${d.zona}"]`;
    else if (d.animo) selector = `[data-animo="${d.animo}"]`;
    else if (d.clave) selector = `[data-clave="${d.clave}"]`;
  }
  contenedor.innerHTML = html;
  if (selector) {
    const nuevo = contenedor.querySelector(selector);
    if (nuevo) nuevo.focus({ preventScroll: true });
  }
}

function luz(nombre, ok, detalle) {
  return `<span class="luz ${ok ? "luz-ok" : "luz-mal"}">${icono(ok ? "verde" : "rojo")}
    <span><b>${esc(nombre)}</b> ${esc(detalle)}</span></span>`;
}

function pintarRed() {
  const red = app.red;
  if (!app.conexion || !red) {
    poner("red", luz("Laptop 1", false, "offline"));
    return;
  }
  const guardadas = red.respuestas_guardadas;
  const l2 = red.laptop2;
  const detalleL2 = l2.ok ? (guardadas ? "saved answers" : "online")
    : (l2.simulada ? "simulated dropout" : "no response");
  const modelos = Object.entries(l2.modelos || {}).filter(([, m]) => !m.ok).map(([n]) => NOMBRES_ESPECIALISTA[n] || n);
  poner("red", [
    luz("Laptop 1", true, "online"),
    luz("Laptop 2", l2.ok && !modelos.length, modelos.length && l2.ok ? `missing ${modelos.join(", ")}` : detalleL2),
    luz("Laptop 3", red.laptop3.ok, red.laptop3.ok ? "online" : "no response"),
    luz("Solar model", red.modelo_solar.ok, red.modelo_solar.ok ? (guardadas ? "saved answers" : "online") : "no response"),
  ].join(""));
}

function pintarAvisos() {
  const avisos = [];
  if (!app.conexion) {
    avisos.push(`<div class="aviso-sistema sin-conexion">${icono("rojo")}<p><b>No connection to Laptop 1.</b>
      Showing the last data received. Retrying every few seconds.</p></div>`);
  }
  const r = app.datos && app.datos.resultado;
  if (r && r.origen === "respaldo-local") {
    avisos.push(`<div class="aviso-sistema">${icono("naranja")}<p><b>Degraded mode: Laptop 3 (orchestrator) is not responding.</b>
      Laptop 1 keeps watching with the same rules, without the specialist board.</p></div>`);
  } else if (r && r.modo === "degradado") {
    const nombres = r.especialistas_no_disponibles.map((n) => NOMBRES_ESPECIALISTA[n] || n).join(", ");
    avisos.push(`<div class="aviso-sistema">${icono("naranja")}<p><b>Degraded mode.</b> Unavailable: ${esc(nombres)}.
      The system keeps running on the rules and the local solar model.</p></div>`);
  }
  if (r && r.respuestas_guardadas) {
    avisos.push(`<div class="aviso-sistema guardadas">${icono("reloj")}<p><b>Single-machine demo.</b>
      Model answers are saved results from real runs; they are not computed now.</p></div>`);
  }
  poner("avisos-sistema", avisos.join(""));
}

function pintarControles(e) {
  // Demo panel
  const deslizador = $("demo-deslizador");
  deslizador.max = String(e.dias_totales);
  if (document.activeElement !== deslizador) deslizador.value = String(e.dia_actual);
  $("demo-dia-texto").textContent = `${deslizador.value} of ${e.dias_totales}`;
  const solar = $("demo-solar");
  solar.setAttribute("aria-pressed", String(e.evento_solar.activo_hoy));
  solar.textContent = e.evento_solar.activo_hoy ? "End solar event" : "Solar event";
  const reproducir = $("demo-reproducir");
  reproducir.setAttribute("aria-pressed", String(Boolean(app.reproduccion)));
  reproducir.textContent = app.reproduccion ? "Pause" : "Play week";
  if (app.red) $("demo-caida").checked = Boolean(app.red.laptop2.simulada);
  for (const boton of document.querySelectorAll("#sec-demo button")) boton.disabled = app.ocupado;

  // One-tap mood
  const animo = e.indicadores.animo;
  poner("animo-botones", ANIMOS.map((texto, i) => `
    <button type="button" class="opcion" data-animo="${i + 1}" aria-pressed="${animo === i + 1}">
      <b>${i + 1}</b><small>${texto}</small></button>`).join(""));

  // Manual form: filled when the day changes, not while typing.
  const formulario = $("form-manual");
  if (app.diaFormulario !== e.dia_actual && !formulario.contains(document.activeElement)) {
    app.diaFormulario = e.dia_actual;
    $("manual-campos").innerHTML = Object.entries(e.catalogo).filter(([, f]) => f.editable).map(([clave, f]) => `
      <label class="campo">${esc(nombreIndicador(clave))} (${esc(unidadIndicador(clave) || f.unidad)})
        <input type="number" inputmode="decimal" name="${clave}" min="${f.minimo}" max="${f.maximo}" step="${f.paso}"
          value="${typeof e.indicadores[clave] === "number" ? e.indicadores[clave] : ""}" placeholder="no data">
      </label>`).join("");
  }
}

function pintar() {
  pintarRed();
  pintarAvisos();
  const e = app.datos;
  if (!e) {
    $("quien").textContent = app.conexion ? "Connecting to the station…" : "No connection to Laptop 1.";
    return;
  }
  if (!app.zonaElegida) app.zona = zonaPorDefecto(e);
  $("quien").textContent = `${traducirNombre(e.astronauta.nombre)}, day ${e.dia_actual} of ${e.dias_totales}`;
  const nivel = e.resultado.nivel_global;
  poner("estado-global", vistaEstado(e, app.nivelAnterior));
  app.nivelAnterior = nivel;
  poner("tablero", vistaTablero(e));
  poner("cuerpo", vistaCuerpo(e, app.zona));
  poner("alertas", vistaAlertas(e));
  poner("junta", vistaJunta(e));
  poner("tendencia", vistaTendencia(e, app.indicador));
  poner("informe", vistaInforme(e, app.informesAbiertos));
  pintarControles(e);
  pintarTemporizadores();
}

// ---------------------------------------------------------------------------
// Protocol timers ("measure again in 15 min")
// ---------------------------------------------------------------------------
function pintarTemporizadores() {
  const ahora = Date.now();
  for (const elemento of document.querySelectorAll("[data-temporizador]")) {
    const fin = app.temporizadores.get(elemento.dataset.temporizador);
    if (!fin) { elemento.textContent = ""; continue; }
    const resto = Math.max(0, Math.round((fin - ahora) / 1000));
    if (resto === 0) {
      elemento.textContent = "Time's up";
      elemento.classList.add("listo");
    } else {
      const minutos = String(Math.floor(resto / 60)).padStart(2, "0");
      elemento.textContent = `${minutos}:${String(resto % 60).padStart(2, "0")}`;
      elemento.classList.remove("listo");
    }
  }
}

// ---------------------------------------------------------------------------
// Reaction test (short vigilance check)
// ---------------------------------------------------------------------------
const reaccion = { tiempos: [], inicio: 0, espera: null };

function estadoReaccion(estado, texto) {
  const zona = $("reaccion-zona");
  zona.dataset.estado = estado;
  zona.textContent = texto;
}

function siguienteSenal() {
  estadoReaccion("espera", `Wait for the signal… (${reaccion.tiempos.length + 1} of ${SENALES_REACCION})`);
  reaccion.espera = setTimeout(() => {
    reaccion.inicio = performance.now();
    estadoReaccion("ya", "Tap now!");
  }, 1500 + Math.random() * 2500);
}

async function tocarReaccion() {
  const estado = $("reaccion-zona").dataset.estado;
  if (estado === "inicio") {
    reaccion.tiempos = [];
    $("reaccion-resultado").textContent = "";
    siguienteSenal();
  } else if (estado === "espera") {
    clearTimeout(reaccion.espera);          // early tap: does not count
    estadoReaccion("espera", "Too soon. Wait for the signal…");
    reaccion.espera = setTimeout(siguienteSenal, 900);
  } else if (estado === "ya") {
    reaccion.tiempos.push(Math.round(performance.now() - reaccion.inicio));
    if (reaccion.tiempos.length < SENALES_REACCION) {
      siguienteSenal();
      return;
    }
    estadoReaccion("inicio", "Repeat test");
    const salida = $("reaccion-resultado");
    const datos = await accion("api/checkin/reaccion", { tiempos_ms: reaccion.tiempos }, salida);
    if (datos) {
      const r = datos.checkins.reaccion;
      salida.textContent = `Saved. Your typical reaction time was ${r.mediana_ms} ms` +
        (r.lapsos ? ` with ${r.lapsos} very slow reaction${r.lapsos === 1 ? "" : "s"}.` : ".");
    }
  }
}

// ---------------------------------------------------------------------------
// Demo panel
// ---------------------------------------------------------------------------
function detenerReproduccion() {
  clearInterval(app.reproduccion);
  app.reproduccion = null;
}

async function reproducir() {
  if (app.reproduccion) { detenerReproduccion(); pintar(); return; }
  const mensaje = $("demo-mensaje");
  // If it is already on the last day, the story starts again from day 1.
  if (app.datos && app.datos.dia_actual >= app.datos.dias_totales) {
    await accion("api/demo/dia", { dia: 1 }, mensaje);
  }
  app.reproduccion = setInterval(async () => {
    const e = app.datos;
    if (!e || e.dia_actual >= e.dias_totales) { detenerReproduccion(); pintar(); return; }
    await accion("api/demo/dia", { dia: e.dia_actual + 1 }, mensaje);
    if (app.datos.dia_actual >= app.datos.dias_totales) { detenerReproduccion(); pintar(); }
  }, SEGUNDOS_POR_DIA * 1000);
  pintar();
}

// ---------------------------------------------------------------------------
// Events
// ---------------------------------------------------------------------------
function elegirZona(id) {
  app.zona = id;
  app.zonaElegida = true;
  pintar();
}

function prepararEventos() {
  document.addEventListener("click", async (evento) => {
    const zona = evento.target.closest("[data-zona]");
    if (zona) { elegirZona(zona.dataset.zona); return; }

    const temporizador = evento.target.closest('[data-accion="temporizador"]');
    if (temporizador) {
      app.temporizadores.set(temporizador.dataset.clave, Date.now() + Number(temporizador.dataset.min) * 60000);
      pintarTemporizadores();
      return;
    }

    const animo = evento.target.closest("[data-animo]");
    if (animo) { await accion("api/checkin/animo", { valor: Number(animo.dataset.animo) }); }
  });

  // Body-map zones with the keyboard (Enter or space).
  document.addEventListener("keydown", (evento) => {
    if (evento.key !== "Enter" && evento.key !== " ") return;
    const zona = evento.target.closest && evento.target.closest("g[data-zona]");
    if (zona) { evento.preventDefault(); elegirZona(zona.dataset.zona); }
  });

  document.addEventListener("change", async (evento) => {
    const objetivo = evento.target;
    if (objetivo.dataset.accion === "paso") {
      try {
        const datos = await pedir("api/protocolo/paso", {
          alerta_id: objetivo.dataset.alerta, paso_id: objetivo.dataset.paso, hecho: objetivo.checked,
        });
        if (app.datos) app.datos.pasos_hechos = datos.pasos_hechos;
        // The pending report shows the actions taken: refresh the whole state.
        cargarEstado();
      } catch {
        objetivo.checked = !objetivo.checked;   // not saved: undo the check
      }
      pintar();
    } else if (objetivo.id === "tendencia-indicador") {
      app.indicador = objetivo.value;
      pintar();
      const selector = $("tendencia-indicador");
      if (selector) selector.focus();
    }
  });

  // Remember which reports are open so they do not close when repainting.
  document.addEventListener("toggle", (evento) => {
    const informe = evento.target.closest && evento.target.closest("[data-informe]");
    if (!informe) return;
    if (informe.open) app.informesAbiertos.add(informe.dataset.informe);
    else app.informesAbiertos.delete(informe.dataset.informe);
  }, true);

  // Reaction test: pointerdown measures better than click; the keyboard works too.
  const zonaReaccion = $("reaccion-zona");
  zonaReaccion.addEventListener("pointerdown", (evento) => { evento.preventDefault(); tocarReaccion(); });
  zonaReaccion.addEventListener("keydown", (evento) => {
    if (evento.key === "Enter" || evento.key === " ") { evento.preventDefault(); tocarReaccion(); }
  });

  // Weekly team survey
  $("encuesta-preguntas").innerHTML = PREGUNTAS_EQUIPO.map((p) => `
    <fieldset class="pregunta">
      <legend>${esc(p.texto)}</legend>
      <div class="fila-botones">${[1, 2, 3, 4, 5].map((n) => `
        <label class="opcion"><input type="radio" name="${p.clave}" value="${n}" required><b>${n}</b></label>`).join("")}
      </div>
    </fieldset>`).join("");
  $("encuesta-equipo").addEventListener("submit", async (evento) => {
    evento.preventDefault();
    const formulario = new FormData(evento.target);
    const cuerpo = Object.fromEntries(PREGUNTAS_EQUIPO.map((p) => [p.clave, Number(formulario.get(p.clave))]));
    const salida = $("encuesta-resultado");
    const datos = await accion("api/checkin/equipo", cuerpo, salida);
    if (datos) salida.textContent = `Saved. Team cohesion: ${datos.checkins.equipo.cohesion} of 5.`;
  });

  // Manual log
  $("form-manual").addEventListener("submit", async (evento) => {
    evento.preventDefault();
    const indicadores = {};
    for (const campo of evento.target.querySelectorAll("input[name]")) {
      if (campo.value !== "") indicadores[campo.name] = Number(campo.value);
    }
    const salida = $("manual-resultado");
    const datos = await accion("api/registro", { indicadores }, salida);
    if (datos) { salida.textContent = "Today's data saved and evaluated."; app.diaFormulario = null; pintar(); }
  });

  // Demo panel
  const mensaje = $("demo-mensaje");
  const deslizador = $("demo-deslizador");
  deslizador.addEventListener("input", () => {
    $("demo-dia-texto").textContent = `${deslizador.value} of ${deslizador.max}`;
  });
  deslizador.addEventListener("change", async () => {
    detenerReproduccion();
    app.zonaElegida = false;
    await accion("api/demo/dia", { dia: Number(deslizador.value) }, mensaje);
  });
  $("demo-reproducir").addEventListener("click", reproducir);
  $("demo-solar").addEventListener("click", async () => {
    const activo = !(app.datos && app.datos.evento_solar.activo_hoy);
    app.zonaElegida = false;
    const datos = await accion("api/demo/evento-solar", { activo }, mensaje);
    if (datos) mensaje.textContent = activo ? "Solar event simulated on the current day." : "Solar event ended.";
  });
  $("demo-enlace").addEventListener("click", async () => {
    const datos = await accion("api/demo/enlace-tierra", {}, mensaje);
    if (datos) {
      const n = datos.ultimo_enlace.enviados;
      mensaje.textContent = n
        ? `Simulated link: ${n} report${n === 1 ? "" : "s"} sent. Earth's reply would take about ${2 * datos.retraso_enlace_min} minutes.`
        : "Simulated link: there were no reports waiting.";
    }
  });
  $("demo-caida").addEventListener("change", async (evento) => {
    const activa = evento.target.checked;
    const datos = await accion("api/demo/caida-laptop2", { activa }, mensaje);
    if (!datos) { evento.target.checked = !activa; return; }
    mensaje.textContent = activa ? "Laptop 2 offline (simulated)." : "Laptop 2 back online.";
    cargarRed();
  });
  $("demo-reiniciar").addEventListener("click", async () => {
    detenerReproduccion();
    app.zonaElegida = false;
    app.temporizadores.clear();
    app.informesAbiertos.clear();
    app.diaFormulario = null;
    const datos = await accion("api/demo/reiniciar", {}, mensaje);
    if (datos) mensaje.textContent = "Demo reset to day 1.";
    cargarRed();
  });
}

// ---------------------------------------------------------------------------
// Startup
// ---------------------------------------------------------------------------
prepararEventos();
cargarEstado();
cargarRed();
setInterval(cargarEstado, INTERVALO_ESTADO_MS);
setInterval(cargarRed, INTERVALO_RED_MS);
setInterval(pintarTemporizadores, 500);
