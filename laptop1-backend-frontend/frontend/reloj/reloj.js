// Simulated smart watch for one astronaut.
//
// It is a web screen, not a native app and not a real device: all data is
// simulated. It polls a compact state every 5 s, queues readings offline and
// sends protocol steps. No frameworks, no CDN, no service worker.
//
// The pure queue logic lives in cola.js and is tested with `node --test`.

import { esc, icono, insignia, TEXTO_NIVEL, formato } from "../js/util.js";
import {
  nombreIndicador, unidadIndicador, tituloAlerta, traducirCausa, pasoProtocolo,
  explicacionGlobal, traducirError, avisoSensor, traducirRol,
} from "../js/i18n.js";
import {
  MAX_COLA, agregar, deserializar, enRevision, marcarPendiente, marcarRevisar,
  pendientes, puedeReintentar, quitar, reemplazarLectura, serializar, siguienteEspera,
} from "./cola.js";

const INTERVALO_SONDEO_MS = 5000;
const RECORDATORIO_MIN = 15;
const CLAVE_ASTRONAUTA = "argonaut.reloj.astronauta";
const CLAVE_ESTADO = "argonaut.reloj.estado.";
const CLAVE_COLA = "argonaut.reloj.cola.";
const VERSION_RELOJ = "0.1.0-demo";

const TEXTOS = {
  today: "Today", measure: "Measure", alert: "Alert", trend: "Trend", watch: "My watch",
  whatNow: "What to do now", suggested: "Suggested action",
  done: "Done", seeAll: "See all", measureNow: "Measure now", send: "Send",
  sending: "Sending…", sent: "Sent.", saved: "Saved on watch",
  allClear: "All clear", noAlerts: "No alerts. Keep to your routine and log your data tomorrow.",
  remind: "Remind me in 15 min", reminded: "Reminder set",
  allDone: "All protocol steps are done.",
  projectionTitle: "If this continues…", projectionNote: "Heuristic projection from the last days. Not a diagnosis.",
  notEnough: "Not enough data to project.",
  connection: "Station online", offline: "Offline", degraded: "Degraded",
  savedOnWatch: "saved on watch", queue: "Readings in queue", sync: "Sync now",
  openDashboard: "Open full dashboard", paired: "Paired astronaut",
  battery: "Battery", signal: "Signal", lastSync: "Last sync", never: "not yet",
  simulation: "Simulated watch. Not a medical device.", version: "Version",
  measureHint: "Values are simulated around your baseline. You can edit every field before sending.",
  measureError: "Enter at least one value before sending.",
  simulated: "simulated", retry: "Retry", discard: "Discard", edit: "Edit",
  needsReview: "Needs review", pending: "Pending", noQueue: "No saved readings.",
  reviewHint: "The server rejected this reading. Edit it or discard it.",
  offlineHint: "No connection. Readings are saved on the watch and retried automatically.",
  synced: "Synced.", syncFailed: "Could not sync yet. It will retry automatically.",
  newAlert: "New alert", stepSaved: "Step saved.", stepError: "The step could not be saved.",
  noDataHint: "No data yet. Wait for the station or take a simulated measurement.",
  noData: "No data",
  noDataToday: "No data logged today for this astronaut.",
  goMeasure: "Go to Measure",
  trendSleep: "Sleep", trendPulse: "Resting pulse", trendHrv: "HRV",
  since: "since", queued: "queued",
};

const $ = (id) => document.getElementById(id);
const IDS_VALIDOS = ["AST-01", "AST-02", "AST-03", "AST-04", "AST-05", "AST-06"];

const S = {
  astronautaId: (() => {
    const guardado = leerLocal(CLAVE_ASTRONAUTA);
    return IDS_VALIDOS.includes(guardado) ? guardado : "AST-01";
  })(),
  estado: null,
  conectado: navigator.onLine !== false,
  pantalla: "today",
  mediciones: {},
  simulados: new Set(),
  mensaje: "",
  mensajeTipo: "",
  enviando: false,
  procesando: false,
  recordatorio: null,
  cola: [],
  ultimaSync: null,
  ultimaAlerta: null,
  editando: null,
  sondeo: null,
  reloj: null,
};

// ---------------------------------------------------------------------------
// Storage helpers (localStorage can be unavailable; the watch must not break)
// ---------------------------------------------------------------------------
function leerLocal(clave) {
  try { return window.localStorage.getItem(clave); } catch { return null; }
}

function guardarLocal(clave, valor) {
  try { window.localStorage.setItem(clave, valor); } catch { /* private mode */ }
}

function eliminarLocal(clave) {
  try { window.localStorage.removeItem(clave); } catch { /* private mode */ }
}

function cargarCola() {
  return deserializar(leerLocal(CLAVE_COLA + S.astronautaId));
}

function guardarCola() {
  guardarLocal(CLAVE_COLA + S.astronautaId, serializar(S.cola));
}

function cargarCache() {
  try {
    const datos = JSON.parse(leerLocal(CLAVE_ESTADO + S.astronautaId) || "null");
    return datos && datos.estado ? datos : null;
  } catch {
    return null;
  }
}

function guardarCache() {
  if (!S.estado) return;
  guardarLocal(CLAVE_ESTADO + S.astronautaId,
    JSON.stringify({ estado: S.estado, momento: new Date().toISOString() }));
}

// ---------------------------------------------------------------------------
// Backend
// ---------------------------------------------------------------------------
async function pedir(ruta, opciones = {}) {
  const respuesta = await fetch(ruta, { cache: "no-store", ...opciones });
  let datos = null;
  try { datos = await respuesta.json(); } catch { /* empty body */ }
  if (!respuesta.ok) {
    const detalle = datos && datos.detail ? datos.detail : `The server responded ${respuesta.status}.`;
    const error = new Error(typeof detalle === "string" ? detalle : "The data is not valid.");
    error.status = respuesta.status;
    throw error;
  }
  return datos;
}

async function cargarEstado() {
  try {
    S.estado = await pedir(`../api/reloj/estado?astronauta_id=${encodeURIComponent(S.astronautaId)}`);
    S.conectado = true;
    S.ultimaSync = new Date();
    guardarCache();
    anunciarAlerta();
    pintar();
  } catch {
    S.conectado = false;
    if (!S.estado) {
      const cache = cargarCache();
      if (cache) { S.estado = cache.estado; S.ultimaSync = new Date(cache.momento); }
    }
    pintar();
  }
}

function anunciarAlerta() {
  const principal = S.estado && S.estado.alerta_principal;
  const id = principal ? principal.id : null;
  if (!id) { S.ultimaAlerta = null; return; }
  if (id !== S.ultimaAlerta) {
    const salida = $("reloj-anuncio");
    if (salida) salida.textContent = `${TEXTOS.newAlert}: ${tituloAlerta(principal)}`;
    S.ultimaAlerta = id;
  }
}

// ---------------------------------------------------------------------------
// Rendering helpers
// ---------------------------------------------------------------------------
function nivelTexto(nivel) {
  return TEXTO_NIVEL[nivel] || "No data";
}

function textoConexion() {
  const guardadas = S.cola.length;
  if (!S.conectado || navigator.onLine === false) {
    return `${TEXTOS.offline} · ${guardadas} ${TEXTOS.savedOnWatch}`;
  }
  if (S.estado && S.estado.conexion && S.estado.conexion.modo === "degradado") {
    return `${TEXTOS.degraded} · ${TEXTOS.connection}`;
  }
  return TEXTOS.connection;
}

function textoExplicacion() {
  if (!S.estado) return "";
  if (S.estado.sin_datos) return TEXTOS.noDataToday;
  return explicacionGlobal({
    alertas: S.estado.alertas || [],
    modo: S.estado.conexion ? S.estado.conexion.modo : "completo",
    sensores_sospechosos: S.estado.datos_sospechosos || [],
  });
}

function sparkline(valores, etiqueta) {
  const numeros = (valores || []).map((v) => (typeof v === "number" ? v : null));
  const validos = numeros.filter((v) => v !== null);
  if (!validos.length) return `<span class="reloj-sin-dato">${TEXTOS.notEnough}</span>`;
  const ANCHO = 100, ALTO = 28, PAD = 2;
  let min = Math.min(...validos), max = Math.max(...validos);
  if (max - min < 1e-9) { min -= 1; max += 1; }
  const x = (i) => PAD + (i * (ANCHO - 2 * PAD)) / Math.max(1, numeros.length - 1);
  const y = (v) => ALTO - PAD - ((v - min) / (max - min)) * (ALTO - 2 * PAD);
  const tramos = [];
  let actual = [];
  numeros.forEach((v, i) => {
    if (v === null) {
      if (actual.length) { tramos.push(actual); actual = []; }
    } else {
      actual.push(`${x(i).toFixed(1)},${y(v).toFixed(1)}`);
    }
  });
  if (actual.length) tramos.push(actual);
  return `<svg class="reloj-spark" viewBox="0 0 ${ANCHO} ${ALTO}" role="img" aria-label="${esc(etiqueta)}">
    ${tramos.map((t) => `<polyline points="${t.join(" ")}"/>`).join("")}</svg>`;
}

function direccionTexto(direccion) {
  return { sube: "rising", baja: "falling", estable: "steady", sin_dato: "no data" }[direccion] || "no data";
}

function avisoSensores() {
  const lista = (S.estado && S.estado.datos_sospechosos) || [];
  return lista.map((s) => `<p class="reloj-sensor">${icono("sospechoso")}<span>${esc(avisoSensor(s))}</span></p>`).join("");
}

// ---------------------------------------------------------------------------
// Screens
// ---------------------------------------------------------------------------
function pantallaHoy() {
  const e = S.estado;
  if (!e) return `<div class="reloj-vacio"><b>${TEXTOS.noDataHint}</b></div>`;
  const quien = `<div class="reloj-quien"><b>${esc(e.astronauta.nombre)}</b><small>${esc(traducirRol(e.astronauta.rol))} · Day ${e.dia_mision}</small></div>`;
  if (e.sin_datos) {
    return `${quien}
      <div class="reloj-nivel nivel-sin_dato" role="status">${icono("sin_dato")}<span>${TEXTOS.noData}</span></div>
      <p class="reloj-texto">${esc(TEXTOS.noDataToday)}</p>
      <button type="button" class="reloj-boton" data-accion="ir" data-pantalla="medir">${TEXTOS.goMeasure}</button>`;
  }
  const principal = e.alerta_principal;
  const paso = principal && principal.siguiente_paso;
  const accion = principal
    ? `<div class="reloj-accion">
        <small>${TEXTOS.whatNow}</small>
        <p>${esc(paso ? paso.texto : TEXTOS.allDone)}</p>
        <div class="reloj-botones">
          ${paso ? `<button type="button" class="reloj-boton" data-accion="hecho"
            data-alerta="${esc(principal.id)}" data-paso="${esc(paso.id)}">${icono("verde")}${TEXTOS.done}</button>` : ""}
          <button type="button" class="reloj-boton reloj-boton-sec" data-accion="ir" data-pantalla="alerta">${TEXTOS.seeAll}</button>
        </div>
      </div>`
    : `<div class="reloj-accion"><small>${TEXTOS.suggested}</small><p>${TEXTOS.allClear}.</p>
        <button type="button" class="reloj-boton reloj-boton-sec" data-accion="ir" data-pantalla="alerta">${TEXTOS.seeAll}</button></div>`;
  return `
    ${quien}
    <div class="reloj-nivel nivel-${e.nivel_global}" role="status">
      ${icono(e.nivel_global)}<span>${nivelTexto(e.nivel_global)}</span><b>${e.riesgo_pct} %</b>
    </div>
    <p class="reloj-texto">${esc(textoExplicacion())}</p>
    ${avisoSensores()}
    ${accion}
    <p class="reloj-mensaje reloj-${S.mensajeTipo}" role="status" aria-live="polite">${esc(S.mensaje)}</p>`;
}

function campoMedida(campo) {
  const valor = Object.prototype.hasOwnProperty.call(S.mediciones, campo.clave)
    ? S.mediciones[campo.clave]
    : (S.estado && S.estado.indicadores ? S.estado.indicadores[campo.clave] : null);
  const nombre = nombreIndicador(campo.clave) || campo.nombre;
  const unidad = unidadIndicador(campo.clave) || campo.unidad;
  const simulado = S.simulados.has(campo.clave)
    ? `<span class="reloj-simulado">${TEXTOS.simulated}</span>` : "";
  return `
    <label class="reloj-campo">
      <span class="reloj-campo-nombre">${esc(nombre)} ${simulado}</span>
      <span class="reloj-campo-fila">
        <input type="number" inputmode="decimal" data-campo="${esc(campo.clave)}"
          min="${campo.minimo}" max="${campo.maximo}" step="${campo.paso}"
          value="${typeof valor === "number" ? valor : ""}" placeholder="no data"
          aria-label="${esc(nombre)} (${esc(unidad)})">
        <small>${esc(unidad)} · ${campo.minimo}–${campo.maximo} · step ${campo.paso}</small>
      </span>
    </label>`;
}

function pantallaMedir() {
  const e = S.estado;
  if (!e) return `<div class="reloj-vacio"><b>${TEXTOS.noDataHint}</b></div>`;
  const campos = e.campos || [];
  const diarios = ["sueno_h", "animo", "estres", "ejercicio_min", "ingesta_pct"];
  const vitales = ["fc_reposo", "hrv", "spo2", "temperatura"];
  const grupo = (titulo, claves) => `
    <fieldset class="reloj-grupo"><legend>${titulo}</legend>
      ${campos.filter((c) => claves.includes(c.clave)).map(campoMedida).join("")}
    </fieldset>`;
  const enCola = pendientes(S.cola).length + enRevision(S.cola).length;
  return `
    <div class="reloj-cabecera-pantalla"><b>${TEXTOS.measure}</b><small>Day ${e.dia_mision} · ${esc(e.astronauta.nombre)}</small></div>
    <p class="reloj-ayuda">${esc(TEXTOS.measureHint)}</p>
    ${avisoSensores()}
    ${grupo("Daily check-in", diarios)}
    ${grupo("Vitals", vitales)}
    <div class="reloj-botones">
      <button type="button" class="reloj-boton reloj-boton-sec" data-accion="medir">${icono("pulso")}${TEXTOS.measureNow}</button>
      <button type="button" class="reloj-boton" data-accion="enviar" ${S.enviando ? "disabled" : ""}>
        ${S.enviando ? TEXTOS.sending : TEXTOS.send}</button>
    </div>
    <p class="reloj-mensaje reloj-${S.mensajeTipo}" role="status" aria-live="polite">${esc(S.mensaje)}</p>
    ${enCola ? `<button type="button" class="reloj-enlace" data-accion="ir" data-pantalla="reloj">${enCola} ${TEXTOS.queued} · ${TEXTOS.watch}</button>` : ""}`;
}

function pantallaAlerta() {
  const e = S.estado;
  if (!e) return `<div class="reloj-vacio"><b>${TEXTOS.noDataHint}</b></div>`;
  if (e.sin_datos) {
    return `<div class="reloj-cabecera-pantalla"><b>${TEXTOS.alert}</b></div>
      <div class="reloj-vacio"><b>${TEXTOS.noData}.</b>${esc(TEXTOS.noDataToday)}</div>`;
  }
  const alertas = e.alertas || [];
  if (!alertas.length) {
    return `<div class="reloj-cabecera-pantalla"><b>${TEXTOS.alert}</b></div>
      <div class="reloj-vacio"><b>${TEXTOS.allClear}.</b>${esc(textoExplicacion() || TEXTOS.noAlerts)}</div>`;
  }
  const bloques = alertas.map((alerta) => {
    const pasos = (alerta.pasos || []).map((paso) => `
      <li class="reloj-paso${paso.hecho ? " hecho" : ""}">
        <label><input type="checkbox" data-accion="paso" data-alerta="${esc(alerta.id)}"
          data-paso="${esc(paso.id)}" ${paso.hecho ? "checked" : ""}>
          <span>${esc(pasoProtocolo(alerta.protocolo_id, paso))}</span></label>
      </li>`).join("");
    return `
      <article class="reloj-alerta nivel-${alerta.nivel}">
        <div class="reloj-alerta-cabecera">${insignia(alerta.nivel)}<b>${esc(tituloAlerta(alerta))}</b></div>
        <p>${esc(traducirCausa(alerta.causa, alerta.id))}</p>
        ${pasos ? `<ol class="reloj-pasos">${pasos}</ol>` : ""}
      </article>`;
  }).join("");
  return `
    <div class="reloj-cabecera-pantalla"><b>${TEXTOS.alert}</b>
      <button type="button" class="reloj-boton reloj-boton-sec reloj-boton-mini" data-accion="recordar">${icono("reloj")}${TEXTOS.remind}</button>
    </div>
    <p class="reloj-recordatorio" id="reloj-recordatorio" aria-live="off">${textoRecordatorio()}</p>
    ${bloques}
    <p class="reloj-mensaje reloj-${S.mensajeTipo}" role="status" aria-live="polite">${esc(S.mensaje)}</p>`;
}

function textoRecordatorio() {
  if (!S.recordatorio) return "";
  const resto = Math.max(0, Math.round((S.recordatorio - Date.now()) / 1000));
  if (resto === 0) return `${TEXTOS.reminded}: 00:00`;
  return `${TEXTOS.reminded}: ${String(Math.floor(resto / 60)).padStart(2, "0")}:${String(resto % 60).padStart(2, "0")}`;
}

function pantallaTendencia() {
  const e = S.estado;
  if (!e) return `<div class="reloj-vacio"><b>${TEXTOS.noDataHint}</b></div>`;
  const claves = [["sueno_h", TEXTOS.trendSleep], ["fc_reposo", TEXTOS.trendPulse], ["hrv", TEXTOS.trendHrv]];
  const graficas = claves.map(([clave, titulo]) => `
    <div class="reloj-mini">
      <span>${esc(nombreIndicador(clave) || titulo)}</span>
      ${sparkline((e.tendencia || {})[clave], `${titulo} trend`)}
    </div>`).join("");
  const proyecciones = (e.proyeccion || []).map((p) => {
    const unidad = unidadIndicador(p.indicador) || "";
    const cuerpo = p.valor_24h === null
      ? `<span class="reloj-sin-dato">${TEXTOS.notEnough}</span>`
      : `<b>${formato(p.valor_24h, (S.estado && S.estado.campos || []).find((c) => c.clave === p.indicador)?.decimales || 0)} ${esc(unidad)}</b>
         <span>${direccionTexto(p.direccion)}${p.dias_para_base !== null ? ` · ${p.dias_para_base} d` : ""}</span>`;
    return `<div class="reloj-proyeccion"><span>${esc(nombreIndicador(p.indicador))}</span>${cuerpo}</div>`;
  }).join("");
  return `
    <div class="reloj-cabecera-pantalla"><b>${TEXTOS.trend}</b><small>${TEXTOS.projectionTitle}</small></div>
    <div class="reloj-minis">${graficas}</div>
    <div class="reloj-proyecciones">${proyecciones}</div>
    <p class="reloj-aviso">${esc(TEXTOS.projectionNote)}</p>`;
}

function pantallaReloj() {
  const e = S.estado;
  const revisar = enRevision(S.cola);
  const pend = pendientes(S.cola);
  const filas = S.cola.length ? S.cola.map((item) => `
    <li class="reloj-cola-item ${item.estado}">
      <span>${esc(item.lectura.lectura_id.slice(0, 8))} · ${item.estado === "revisar" ? TEXTOS.needsReview : TEXTOS.pending}</span>
      ${item.error ? `<small>${esc(traducirError(item.error))}</small>` : ""}
      <span class="reloj-cola-acciones">
        ${item.estado === "revisar"
          ? `<button type="button" class="reloj-boton reloj-boton-mini" data-accion="editar" data-id="${esc(item.lectura.lectura_id)}">${TEXTOS.edit}</button>`
          : `<button type="button" class="reloj-boton reloj-boton-mini" data-accion="reintentar" data-id="${esc(item.lectura.lectura_id)}">${TEXTOS.retry}</button>`}
        <button type="button" class="reloj-boton reloj-boton-mini reloj-boton-sec" data-accion="descartar" data-id="${esc(item.lectura.lectura_id)}">${TEXTOS.discard}</button>
      </span>
    </li>`).join("") : `<li class="reloj-vacio">${TEXTOS.noQueue}</li>`;
  const opciones = (e && e.roster ? e.roster : []).map((a) =>
    `<option value="${esc(a.id)}" ${a.id === S.astronautaId ? "selected" : ""}>${esc(a.nombre)} · ${esc(traducirRol(a.rol))}</option>`).join("");
  return `
    <div class="reloj-cabecera-pantalla"><b>${TEXTOS.watch}</b><small>${TEXTOS.simulation}</small></div>
    <label class="reloj-campo"><span class="reloj-campo-nombre">${TEXTOS.paired}</span>
      <select id="reloj-astronauta" aria-label="${TEXTOS.paired}">${opciones}</select></label>
    <div class="reloj-estado-reloj">
      <span>${TEXTOS.battery} <b>87 %</b></span>
      <span>${TEXTOS.signal} <b>strong</b></span>
      <span>${TEXTOS.lastSync} <b>${S.ultimaSync ? S.ultimaSync.toLocaleTimeString() : TEXTOS.never}</b></span>
    </div>
    <p class="reloj-ayuda">${revisar.length ? TEXTOS.reviewHint : TEXTOS.offlineHint}</p>
    <div class="reloj-cola-cabecera"><b>${TEXTOS.queue} (${S.cola.length})</b>
      <button type="button" class="reloj-boton reloj-boton-mini" data-accion="sincronizar">${TEXTOS.sync}</button></div>
    <ul class="reloj-cola">${filas}</ul>
    <p class="reloj-mensaje reloj-${S.mensajeTipo}" role="status" aria-live="polite">${esc(S.mensaje)}</p>
    <a class="reloj-boton reloj-boton-sec" href="../">${TEXTOS.openDashboard}</a>
    <p class="reloj-aviso">${TEXTOS.simulation} · ${TEXTOS.version} ${VERSION_RELOJ}</p>`;
}

function pintarNav() {
  for (const boton of document.querySelectorAll("[data-pantalla-nav]")) {
    const activo = boton.dataset.pantallaNav === S.pantalla;
    boton.setAttribute("aria-current", activo ? "page" : "false");
    boton.setAttribute("aria-pressed", String(activo));
  }
}

function pintar() {
  // Do not repaint while the person is typing in a Measure field: it would lose focus.
  const activo = document.activeElement;
  if (S.pantalla === "medir" && activo && activo.dataset && activo.dataset.campo) return;
  const pantallas = {
    today: pantallaHoy, medir: pantallaMedir, alerta: pantallaAlerta,
    tendencia: pantallaTendencia, reloj: pantallaReloj,
  };
  const contenido = (pantallas[S.pantalla] || pantallaHoy)();
  $("reloj-pantalla").innerHTML = contenido;
  $("reloj-conexion").textContent = textoConexion();
  $("reloj-conexion").dataset.estado = S.conectado ? (S.cola.length ? "cola" : "ok") : "off";
  pintarNav();
  pintarHora();
}

function pintarHora() {
  const ahora = new Date();
  $("reloj-hora").textContent = ahora.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
  const recordatorio = $("reloj-recordatorio");
  if (recordatorio) recordatorio.textContent = textoRecordatorio();
}

// ---------------------------------------------------------------------------
// Actions
// ---------------------------------------------------------------------------
function hash(texto) {
  let h = 2166136261;
  for (let i = 0; i < texto.length; i += 1) {
    h ^= texto.charCodeAt(i);
    h = Math.imul(h, 16777619);
  }
  return h >>> 0;
}

function pseudoAleatorio(semilla) {
  const x = Math.sin(semilla) * 10000;
  return x - Math.floor(x);
}

function redondear(valor, decimales) {
  const factor = 10 ** decimales;
  return Math.round(valor * factor) / factor;
}

function medirAhora() {
  if (!S.estado) return;
  const base = S.estado.linea_base || {};
  const amplitudes = { fc_reposo: 3, hrv: 4, spo2: 0.8, temperatura: 0.2 };
  const campos = (S.estado.campos || []).filter((c) => c.clave in amplitudes);
  for (const campo of campos) {
    const semilla = hash(`${S.astronautaId}-${S.estado.dia_mision}-${campo.clave}`);
    const centro = typeof base[campo.clave] === "number" ? base[campo.clave]
      : (typeof S.estado.indicadores[campo.clave] === "number" ? S.estado.indicadores[campo.clave]
        : (campo.minimo + campo.maximo) / 2);
    const ruido = (pseudoAleatorio(semilla) - 0.5) * 2 * amplitudes[campo.clave];
    let valor = redondear(centro + ruido, campo.decimales);
    valor = Math.min(campo.maximo, Math.max(campo.minimo, valor));
    S.mediciones[campo.clave] = valor;
    S.simulados.add(campo.clave);
  }
  S.mensaje = "Simulated reading added around your baseline. You can edit it.";
  S.mensajeTipo = "info";
  pintar();
}

function nuevaLectura() {
  const indicadores = {};
  for (const [clave, valor] of Object.entries(S.mediciones)) {
    if (typeof valor === "number" && Number.isFinite(valor)) indicadores[clave] = valor;
  }
  // Si no se tocó ningún campo, se envía lo que se ve en pantalla. Así "Send"
  // después de abrir Measure no falla por no haber editado nada.
  if (!Object.keys(indicadores).length) {
    for (const entrada of document.querySelectorAll("[data-campo]")) {
      if (entrada.value === "") continue;
      const valor = Number(entrada.value);
      if (Number.isFinite(valor)) indicadores[entrada.dataset.campo] = valor;
    }
  }
  if (!Object.keys(indicadores).length) return null;
  return {
    lectura_id: S.editando || (crypto.randomUUID ? crypto.randomUUID() : `w-${Date.now()}-${Math.random().toString(16).slice(2)}`),
    astronauta_id: S.astronautaId,
    capturado_en: new Date().toISOString(),
    origen: "reloj-simulado",
    indicadores,
  };
}

function limpiarMediciones() {
  S.mediciones = {};
  S.simulados.clear();
  S.editando = null;
}

async function enviar() {
  if (S.enviando) return;
  const lectura = nuevaLectura();
  if (!lectura) { S.mensaje = TEXTOS.measureError; S.mensajeTipo = "error"; pintar(); return; }
  if (!S.conectado || navigator.onLine === false) {
    S.cola = agregar(S.cola, lectura, MAX_COLA);
    guardarCola();
    limpiarMediciones();
    S.mensaje = `${TEXTOS.saved}. ${TEXTOS.offlineHint}`;
    S.mensajeTipo = "ok";
    pintar();
    programarReintento();
    return;
  }
  S.enviando = true;
  S.mensaje = TEXTOS.sending;
  S.mensajeTipo = "info";
  pintar();
  try {
    const respuesta = await pedir("../api/reloj/lectura", {
      method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(lectura),
    });
    S.estado = respuesta.estado_reloj;
    S.ultimaSync = new Date();
    S.conectado = true;
    guardarCache();
    anunciarAlerta();
    if (S.editando) S.cola = quitar(S.cola, S.editando);
    guardarCola();
    limpiarMediciones();
    S.mensaje = TEXTOS.sent;
    S.mensajeTipo = "ok";
    if (pendientes(S.cola).length) procesarCola();
  } catch (error) {
    if (error.status && error.status >= 400 && error.status < 500) {
      if (S.editando) {
        S.cola = marcarRevisar(S.cola, S.editando, error.message);
        guardarCola();
      }
      S.mensaje = traducirError(error.message);
      S.mensajeTipo = "error";
    } else {
      S.cola = agregar(S.cola, lectura, MAX_COLA);
      guardarCola();
      limpiarMediciones();
      S.mensaje = `${TEXTOS.saved}. ${TEXTOS.offlineHint}`;
      S.mensajeTipo = "ok";
      S.conectado = false;
      programarReintento();
    }
  } finally {
    S.enviando = false;
    pintar();
  }
}

async function marcarPaso(alertaId, pasoId, hecho) {
  try {
    await pedir("../api/protocolo/paso", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ alerta_id: alertaId, paso_id: pasoId, hecho, astronauta_id: S.astronautaId }),
    });
    if (S.estado) {
      for (const alerta of S.estado.alertas || []) {
        if (alerta.id !== alertaId) continue;
        for (const paso of alerta.pasos || []) if (paso.id === pasoId) paso.hecho = hecho;
        alerta.siguiente_paso = (alerta.pasos || []).find((p) => !p.hecho) || null;
      }
      if (S.estado.alerta_principal && S.estado.alerta_principal.id === alertaId) {
        S.estado.alerta_principal.siguiente_paso =
          (S.estado.alerta_principal.pasos || []).find((p) => !p.hecho) || null;
      }
    }
    S.mensaje = TEXTOS.stepSaved;
    S.mensajeTipo = "ok";
    pintar();
    return true;
  } catch (error) {
    S.mensaje = `${TEXTOS.stepError} ${traducirError(error.message)}`;
    S.mensajeTipo = "error";
    pintar();
    return false;
  }
}

async function procesarCola(forzar = false) {
  if (S.procesando) return;
  S.procesando = true;
  let cambiado = false;
  for (const item of [...S.cola]) {
    if (item.estado !== "pendiente") continue;
    if (!forzar && !puedeReintentar(item)) continue;
    try {
      const respuesta = await pedir("../api/reloj/lectura", {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify(item.lectura),
      });
      S.estado = respuesta.estado_reloj;
      S.ultimaSync = new Date();
      S.conectado = true;
      S.cola = quitar(S.cola, item.lectura.lectura_id);
      S.mensaje = TEXTOS.synced;
      S.mensajeTipo = "ok";
      cambiado = true;
      guardarCache();
      anunciarAlerta();
    } catch (error) {
      if (error.status && error.status >= 400 && error.status < 500) {
        S.cola = marcarRevisar(S.cola, item.lectura.lectura_id, error.message);
      } else {
        const intentos = (item.intentos || 0) + 1;
        S.cola = marcarPendiente(S.cola, item.lectura.lectura_id, intentos,
          Date.now() + siguienteEspera(intentos));
        S.conectado = false;
      }
      cambiado = true;
    }
  }
  S.procesando = false;
  if (cambiado) {
    guardarCola();
    pintar();
    if (pendientes(S.cola).length) programarReintento();
  }
}

function programarReintento() {
  const esperas = pendientes(S.cola).map((i) => Number(i.siguiente || 0) - Date.now());
  if (!esperas.length) return;
  const espera = Math.max(1000, Math.min(...esperas));
  window.setTimeout(() => procesarCola(), espera);
}

function recordar() {
  S.recordatorio = Date.now() + RECORDATORIO_MIN * 60000;
  S.mensaje = `${TEXTOS.reminded}.`;
  S.mensajeTipo = "ok";
  pintar();
}

function editarEnCola(lecturaId) {
  const item = S.cola.find((i) => i.lectura.lectura_id === lecturaId);
  if (!item) return;
  S.mediciones = { ...item.lectura.indicadores };
  S.simulados.clear();
  S.editando = lecturaId;
  S.pantalla = "medir";
  S.mensaje = TEXTOS.reviewHint;
  S.mensajeTipo = "info";
  pintar();
}

function cambiarAstronauta(id) {
  if (!IDS_VALIDOS.includes(id)) return;
  S.astronautaId = id;
  guardarLocal(CLAVE_ASTRONAUTA, id);
  S.estado = null;
  S.mediciones = {};
  S.simulados.clear();
  S.editando = null;
  S.cola = cargarCola();
  S.ultimaAlerta = null;
  S.recordatorio = null;
  S.ultimaSync = null;
  S.mensaje = "";
  const cache = cargarCache();
  if (cache) { S.estado = cache.estado; S.ultimaSync = new Date(cache.momento); }
  S.pantalla = "today";
  pintar();
  cargarEstado();
  procesarCola();
}

// ---------------------------------------------------------------------------
// Events and startup
// ---------------------------------------------------------------------------
function prepararEventos() {
  document.addEventListener("click", async (evento) => {
    const nav = evento.target.closest("[data-pantalla-nav]");
    if (nav) { S.pantalla = nav.dataset.pantallaNav; pintar(); return; }

    const boton = evento.target.closest("[data-accion]");
    if (!boton) return;
    const accion = boton.dataset.accion;
    if (accion === "ir") { S.pantalla = boton.dataset.pantalla || "today"; pintar(); return; }
    if (accion === "medir") { medirAhora(); return; }
    if (accion === "enviar") { await enviar(); return; }
    if (accion === "recordar") { recordar(); return; }
    if (accion === "sincronizar") { await procesarCola(true); await cargarEstado(); return; }
    if (accion === "reintentar") { await procesarCola(true); return; }
    if (accion === "descartar") {
      S.cola = quitar(S.cola, boton.dataset.id);
      guardarCola();
      if (S.editando === boton.dataset.id) limpiarMediciones();
      S.mensaje = "Reading discarded.";
      S.mensajeTipo = "ok";
      pintar();
      return;
    }
    if (accion === "editar") { editarEnCola(boton.dataset.id); return; }
    if (accion === "hecho") {
      await marcarPaso(boton.dataset.alerta, boton.dataset.paso, true);
    }
  });

  document.addEventListener("change", async (evento) => {
    const objetivo = evento.target;
    if (objetivo.id === "reloj-astronauta") { cambiarAstronauta(objetivo.value); return; }
    if (objetivo.dataset.accion === "paso") {
      const guardado = await marcarPaso(objetivo.dataset.alerta, objetivo.dataset.paso, objetivo.checked);
      if (!guardado) objetivo.checked = !objetivo.checked;   // no se guardó: deshacer
    }
  });

  document.addEventListener("input", (evento) => {
    const campo = evento.target.dataset && evento.target.dataset.campo;
    if (!campo) return;
    const valor = evento.target.value === "" ? null : Number(evento.target.value);
    if (valor === null || Number.isFinite(valor)) S.mediciones[campo] = valor;
    S.simulados.delete(campo);
  });

  window.addEventListener("online", () => {
    S.conectado = true;
    cargarEstado();
    procesarCola(true);
  });
  window.addEventListener("offline", () => {
    S.conectado = false;
    pintar();
  });
  document.addEventListener("visibilitychange", () => {
    if (document.visibilityState === "visible") {
      cargarEstado();
      procesarCola();
    }
  });
}

function iniciarSondeo() {
  window.clearInterval(S.sondeo);
  S.sondeo = window.setInterval(() => {
    if (document.visibilityState === "visible") cargarEstado();
  }, INTERVALO_SONDEO_MS);
}

function iniciar() {
  S.cola = cargarCola();
  const cache = cargarCache();
  if (cache) { S.estado = cache.estado; S.ultimaSync = new Date(cache.momento); }
  prepararEventos();
  pintar();
  cargarEstado();
  procesarCola();
  iniciarSondeo();
  window.setInterval(pintarHora, 1000);
}

iniciar();
