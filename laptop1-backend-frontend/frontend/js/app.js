// Médico de estación · aplicación de la interfaz.
// Pide el estado al backend (Laptop 1), lo pinta y envía las acciones del usuario.
// Si algo falla, se muestra un aviso y la pantalla sigue funcionando con lo último recibido.

import { esc, icono, NOMBRES_ESPECIALISTA } from "./util.js";
import { ANIMOS, PREGUNTAS_EQUIPO } from "./contenido.js";
import {
  vistaEstado, vistaTablero, vistaCuerpo, vistaAlertas, vistaJunta, vistaTendencia, vistaInforme,
  zonaPorDefecto,
} from "./vistas.js";

const INTERVALO_ESTADO_MS = 4000;     // sincroniza celular y laptop
const INTERVALO_RED_MS = 5000;        // healthchecks de las tres laptops
const SEGUNDOS_POR_DIA = 8;           // "Reproducir semana": un día cada ~8 s
const SENALES_REACCION = 5;

const app = {
  datos: null,            // último estado recibido del backend
  red: null,              // último estado de la red
  conexion: true,         // ¿responde la Laptop 1?
  zona: null,             // zona del mapa corporal seleccionada
  zonaElegida: false,     // true si la eligió la persona (no se cambia sola)
  indicador: "sueno_h",   // indicador de la gráfica de tendencia
  informesAbiertos: new Set(),
  temporizadores: new Map(),   // clave -> momento de fin (ms)
  nivelAnterior: null,
  firmaRed: null,
  reproduccion: null,
  ocupado: false,
  diaFormulario: null,
};
const cache = {};   // último HTML pintado por contenedor: solo se repinta lo que cambia
const $ = (id) => document.getElementById(id);

// ---------------------------------------------------------------------------
// Comunicación con el backend (rutas relativas: sirve en cualquier IP del router)
// ---------------------------------------------------------------------------
async function pedir(ruta, cuerpo) {
  const opciones = cuerpo === undefined ? {} : {
    method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(cuerpo),
  };
  const respuesta = await fetch(ruta, opciones);
  let datos = null;
  try { datos = await respuesta.json(); } catch { /* respuesta sin cuerpo */ }
  if (!respuesta.ok) {
    const detalle = datos && datos.detail ? datos.detail : `El servidor respondió ${respuesta.status}.`;
    throw new Error(typeof detalle === "string" ? detalle : "El dato no es válido.");
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
    // Si una laptop se cayó o volvió, se pide una evaluación nueva para reflejarlo.
    if (app.firmaRed !== null && app.firmaRed !== firma && !app.ocupado) {
      try { app.datos = await pedir("api/reevaluar", {}); } catch { /* se reintenta en el siguiente ciclo */ }
    }
    app.firmaRed = firma;
    app.conexion = true;
  } catch {
    app.red = null;
    app.conexion = false;
  }
  pintar();
}

/** Ejecuta una acción que devuelve el estado nuevo; muestra el error en 'salida' si falla. */
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
      ? "No hay conexión con la Laptop 1. Revisa la red e inténtalo de nuevo." : error.message;
    if (salida) salida.textContent = texto;
    return null;
  } finally {
    app.ocupado = false;
    pintar();
  }
}

// ---------------------------------------------------------------------------
// Pintado
// ---------------------------------------------------------------------------
function poner(id, html) {
  if (cache[id] === html) return;
  cache[id] = html;
  const contenedor = $(id);
  // Si el foco estaba dentro, se devuelve al mismo control tras repintar (teclado y lectores).
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
    poner("red", luz("Laptop 1", false, "sin conexión"));
    return;
  }
  const guardadas = red.respuestas_guardadas;
  const l2 = red.laptop2;
  const detalleL2 = l2.ok ? (guardadas ? "respuestas guardadas" : "en línea")
    : (l2.simulada ? "caída simulada" : "sin respuesta");
  const modelos = Object.entries(l2.modelos || {}).filter(([, m]) => !m.ok).map(([n]) => NOMBRES_ESPECIALISTA[n] || n);
  poner("red", [
    luz("Laptop 1", true, "en línea"),
    luz("Laptop 2", l2.ok && !modelos.length, modelos.length && l2.ok ? `sin ${modelos.join(", ")}` : detalleL2),
    luz("Laptop 3", red.laptop3.ok, red.laptop3.ok ? "en línea" : "sin respuesta"),
    luz("Modelo solar", red.modelo_solar.ok, red.modelo_solar.ok ? (guardadas ? "respuestas guardadas" : "en línea") : "sin respuesta"),
  ].join(""));
}

function pintarAvisos() {
  const avisos = [];
  if (!app.conexion) {
    avisos.push(`<div class="aviso-sistema sin-conexion">${icono("rojo")}<p><b>Sin conexión con la Laptop 1.</b>
      Se muestran los últimos datos recibidos. Reintentando cada pocos segundos.</p></div>`);
  }
  const r = app.datos && app.datos.resultado;
  if (r && r.origen === "respaldo-local") {
    avisos.push(`<div class="aviso-sistema">${icono("naranja")}<p><b>Modo degradado: la Laptop 3 (orquestador) no responde.</b>
      La Laptop 1 sigue vigilando con las mismas reglas, sin la junta de especialistas.</p></div>`);
  } else if (r && r.modo === "degradado") {
    const nombres = r.especialistas_no_disponibles.map((n) => NOMBRES_ESPECIALISTA[n] || n).join(", ");
    avisos.push(`<div class="aviso-sistema">${icono("naranja")}<p><b>Modo degradado.</b> No disponibles: ${esc(nombres)}.
      El sistema sigue funcionando con las reglas y el modelo solar local.</p></div>`);
  }
  if (r && r.respuestas_guardadas) {
    avisos.push(`<div class="aviso-sistema guardadas">${icono("reloj")}<p><b>Demo en una sola máquina.</b>
      Las respuestas de los modelos son resultados guardados de ejecuciones reales, no se calculan ahora.</p></div>`);
  }
  poner("avisos-sistema", avisos.join(""));
}

function pintarControles(e) {
  // Panel de demo
  const deslizador = $("demo-deslizador");
  deslizador.max = String(e.dias_totales);
  if (document.activeElement !== deslizador) deslizador.value = String(e.dia_actual);
  $("demo-dia-texto").textContent = `${deslizador.value} de ${e.dias_totales}`;
  const solar = $("demo-solar");
  solar.setAttribute("aria-pressed", String(e.evento_solar.activo_hoy));
  solar.textContent = e.evento_solar.activo_hoy ? "Terminar evento solar" : "Evento solar";
  const reproducir = $("demo-reproducir");
  reproducir.setAttribute("aria-pressed", String(Boolean(app.reproduccion)));
  reproducir.textContent = app.reproduccion ? "Pausar" : "Reproducir semana";
  if (app.red) $("demo-caida").checked = Boolean(app.red.laptop2.simulada);
  for (const boton of document.querySelectorAll("#sec-demo button")) boton.disabled = app.ocupado;

  // Ánimo de 1 toque
  const animo = e.indicadores.animo;
  poner("animo-botones", ANIMOS.map((texto, i) => `
    <button type="button" class="opcion" data-animo="${i + 1}" aria-pressed="${animo === i + 1}">
      <b>${i + 1}</b><small>${texto}</small></button>`).join(""));

  // Formulario manual: se rellena al cambiar de día, no mientras se escribe.
  const formulario = $("form-manual");
  if (app.diaFormulario !== e.dia_actual && !formulario.contains(document.activeElement)) {
    app.diaFormulario = e.dia_actual;
    $("manual-campos").innerHTML = Object.entries(e.catalogo).filter(([, f]) => f.editable).map(([clave, f]) => `
      <label class="campo">${esc(f.nombre)} (${esc(f.unidad)})
        <input type="number" inputmode="decimal" name="${clave}" min="${f.minimo}" max="${f.maximo}" step="${f.paso}"
          value="${typeof e.indicadores[clave] === "number" ? e.indicadores[clave] : ""}" placeholder="sin dato">
      </label>`).join("");
  }
}

function pintar() {
  pintarRed();
  pintarAvisos();
  const e = app.datos;
  if (!e) {
    $("quien").textContent = app.conexion ? "Conectando con la estación…" : "Sin conexión con la Laptop 1.";
    return;
  }
  if (!app.zonaElegida) app.zona = zonaPorDefecto(e);
  $("quien").textContent = `${e.astronauta.nombre}, día ${e.dia_actual} de ${e.dias_totales}`;
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
// Temporizadores de los protocolos ("vuelve a medir en 15 min")
// ---------------------------------------------------------------------------
function pintarTemporizadores() {
  const ahora = Date.now();
  for (const elemento of document.querySelectorAll("[data-temporizador]")) {
    const fin = app.temporizadores.get(elemento.dataset.temporizador);
    if (!fin) { elemento.textContent = ""; continue; }
    const resto = Math.max(0, Math.round((fin - ahora) / 1000));
    if (resto === 0) {
      elemento.textContent = "Tiempo cumplido";
      elemento.classList.add("listo");
    } else {
      const minutos = String(Math.floor(resto / 60)).padStart(2, "0");
      elemento.textContent = `${minutos}:${String(resto % 60).padStart(2, "0")}`;
      elemento.classList.remove("listo");
    }
  }
}

// ---------------------------------------------------------------------------
// Prueba de reacción (vigilancia corta)
// ---------------------------------------------------------------------------
const reaccion = { tiempos: [], inicio: 0, espera: null };

function estadoReaccion(estado, texto) {
  const zona = $("reaccion-zona");
  zona.dataset.estado = estado;
  zona.textContent = texto;
}

function siguienteSenal() {
  estadoReaccion("espera", `Espera la señal… (${reaccion.tiempos.length + 1} de ${SENALES_REACCION})`);
  reaccion.espera = setTimeout(() => {
    reaccion.inicio = performance.now();
    estadoReaccion("ya", "¡Toca ahora!");
  }, 1500 + Math.random() * 2500);
}

async function tocarReaccion() {
  const estado = $("reaccion-zona").dataset.estado;
  if (estado === "inicio") {
    reaccion.tiempos = [];
    $("reaccion-resultado").textContent = "";
    siguienteSenal();
  } else if (estado === "espera") {
    clearTimeout(reaccion.espera);          // toque adelantado: no cuenta
    estadoReaccion("espera", "Demasiado pronto. Espera la señal…");
    reaccion.espera = setTimeout(siguienteSenal, 900);
  } else if (estado === "ya") {
    reaccion.tiempos.push(Math.round(performance.now() - reaccion.inicio));
    if (reaccion.tiempos.length < SENALES_REACCION) {
      siguienteSenal();
      return;
    }
    estadoReaccion("inicio", "Repetir prueba");
    const salida = $("reaccion-resultado");
    const datos = await accion("api/checkin/reaccion", { tiempos_ms: reaccion.tiempos }, salida);
    if (datos) {
      const r = datos.checkins.reaccion;
      salida.textContent = `Guardado. Tu tiempo de reacción típico fue de ${r.mediana_ms} ms` +
        (r.lapsos ? ` con ${r.lapsos} reacción${r.lapsos === 1 ? "" : "es"} muy lenta${r.lapsos === 1 ? "" : "s"}.` : ".");
    }
  }
}

// ---------------------------------------------------------------------------
// Panel de demo
// ---------------------------------------------------------------------------
function detenerReproduccion() {
  clearInterval(app.reproduccion);
  app.reproduccion = null;
}

async function reproducir() {
  if (app.reproduccion) { detenerReproduccion(); pintar(); return; }
  const mensaje = $("demo-mensaje");
  // Si ya está en el último día, la historia empieza de nuevo desde el día 1.
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
// Eventos
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

  // Zonas del mapa con teclado (Enter o barra espaciadora).
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
        // El informe pendiente muestra las acciones tomadas: se refresca el estado completo.
        cargarEstado();
      } catch {
        objetivo.checked = !objetivo.checked;   // no se guardó: se deshace la marca
      }
      pintar();
    } else if (objetivo.id === "tendencia-indicador") {
      app.indicador = objetivo.value;
      pintar();
      const selector = $("tendencia-indicador");
      if (selector) selector.focus();
    }
  });

  // Recordar qué informes están abiertos para que no se cierren al repintar.
  document.addEventListener("toggle", (evento) => {
    const informe = evento.target.closest && evento.target.closest("[data-informe]");
    if (!informe) return;
    if (informe.open) app.informesAbiertos.add(informe.dataset.informe);
    else app.informesAbiertos.delete(informe.dataset.informe);
  }, true);

  // Prueba de reacción: pointerdown mide mejor que click; el teclado también vale.
  const zonaReaccion = $("reaccion-zona");
  zonaReaccion.addEventListener("pointerdown", (evento) => { evento.preventDefault(); tocarReaccion(); });
  zonaReaccion.addEventListener("keydown", (evento) => {
    if (evento.key === "Enter" || evento.key === " ") { evento.preventDefault(); tocarReaccion(); }
  });

  // Encuesta semanal del equipo
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
    if (datos) salida.textContent = `Guardado. Cohesión del equipo: ${datos.checkins.equipo.cohesion} de 5.`;
  });

  // Registro manual
  $("form-manual").addEventListener("submit", async (evento) => {
    evento.preventDefault();
    const indicadores = {};
    for (const campo of evento.target.querySelectorAll("input[name]")) {
      if (campo.value !== "") indicadores[campo.name] = Number(campo.value);
    }
    const salida = $("manual-resultado");
    const datos = await accion("api/registro", { indicadores }, salida);
    if (datos) { salida.textContent = "Datos de hoy guardados y evaluados."; app.diaFormulario = null; pintar(); }
  });

  // Panel de demo
  const mensaje = $("demo-mensaje");
  const deslizador = $("demo-deslizador");
  deslizador.addEventListener("input", () => {
    $("demo-dia-texto").textContent = `${deslizador.value} de ${deslizador.max}`;
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
    if (datos) mensaje.textContent = activo ? "Evento solar simulado en el día actual." : "Evento solar terminado.";
  });
  $("demo-enlace").addEventListener("click", async () => {
    const datos = await accion("api/demo/enlace-tierra", {}, mensaje);
    if (datos) {
      const n = datos.ultimo_enlace.enviados;
      mensaje.textContent = n
        ? `Enlace simulado: ${n} informe${n === 1 ? "" : "s"} enviado${n === 1 ? "" : "s"}. La respuesta de la Tierra tardaría unos ${2 * datos.retraso_enlace_min} minutos.`
        : "Enlace simulado: no había informes en espera.";
    }
  });
  $("demo-caida").addEventListener("change", async (evento) => {
    const activa = evento.target.checked;
    const datos = await accion("api/demo/caida-laptop2", { activa }, mensaje);
    if (!datos) { evento.target.checked = !activa; return; }
    mensaje.textContent = activa ? "Laptop 2 fuera de línea (simulado)." : "Laptop 2 de nuevo en línea.";
    cargarRed();
  });
  $("demo-reiniciar").addEventListener("click", async () => {
    detenerReproduccion();
    app.zonaElegida = false;
    app.temporizadores.clear();
    app.informesAbiertos.clear();
    app.diaFormulario = null;
    const datos = await accion("api/demo/reiniciar", {}, mensaje);
    if (datos) mensaje.textContent = "Demo reiniciada en el día 1.";
    cargarRed();
  });
}

// ---------------------------------------------------------------------------
// Arranque
// ---------------------------------------------------------------------------
prepararEventos();
cargarEstado();
cargarRed();
setInterval(cargarEstado, INTERVALO_ESTADO_MS);
setInterval(cargarRed, INTERVALO_RED_MS);
setInterval(pintarTemporizadores, 500);
