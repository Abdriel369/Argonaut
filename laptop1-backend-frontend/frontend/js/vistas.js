// Views: pure functions that take the backend state and return HTML.
// If a value is missing it shows "No data"; none of this should break the screen.

import { esc, icono, insignia, formato, nivelMaximo, TEXTO_NIVEL, NOMBRES_ESPECIALISTA } from "./util.js";
import { ZONAS, INMUNE } from "./contenido.js";
import {
  nombreIndicador, unidadIndicador, tituloAlerta, tituloProtocolo, pasoProtocolo,
  traducirMotivo, traducirCausa, traducirPaso, explicacionGlobal, opinionJunta,
  explicacionCorta, notaDia, MUSCULO, MODULOS, NOTA_INFORME, ESCALAMIENTO, ETIQUETAS,
  avisoSensor, MOTIVO_SENSOR, OPINION_LIMITADA,
} from "./i18n.js";

const semaforo = (e) => (e.resultado && e.resultado.semaforo_indicadores) || {};

/** Today's readings set aside because the sensor seems to be failing.
 *  The orchestrator's list carries the affected rules; the backend's own list is the fallback. */
export function sensoresSospechosos(e) {
  const delResultado = (e.resultado && e.resultado.sensores_sospechosos) || [];
  return delResultado.length ? delResultado : (e.sensores_sospechosos || []);
}
const sospecha = (e, clave) => sensoresSospechosos(e).find((s) => s.indicador === clave);

// ---------------------------------------------------------------------------
// Overall status + mission week
// ---------------------------------------------------------------------------
export function vistaEstado(e, nivelAnterior) {
  const r = e.resultado;
  const nivel = r.nivel_global;
  const dias = [];
  for (let d = 1; d <= e.dias_totales; d += 1) {
    const hecho = e.historial.find((h) => h.dia === d);
    const clases = ["semana-dia", d === e.dia_actual ? "hoy" : "", hecho ? "" : "futuro"].join(" ");
    const marca = hecho
      ? `<span class="nivel nivel-${hecho.nivel_global}">${icono(hecho.nivel_global)}<span class="solo-lectores">${TEXTO_NIVEL[hecho.nivel_global]}</span></span>`
      : `<span aria-hidden="true">${icono("sin_dato")}</span><span class="solo-lectores">Not yet</span>`;
    dias.push(`<div class="${clases}"><span>Day</span><b>${d}</b>${marca}</div>`);
  }
  const cambio = nivelAnterior && nivelAnterior !== nivel ? " cambio" : "";
  const nota = notaDia(e.nota_dia);
  return `
    <div class="estado-global">
      <div class="estado-principal nivel-${nivel}">
        <div class="estado-insignia${cambio}">${icono(nivel)}</div>
        <div>
          <p class="estado-nivel">${TEXTO_NIVEL[nivel]}</p>
          <p class="estado-texto">${esc(explicacionGlobal(r))}</p>
          <p class="estado-accion"><b>What's next:</b> ${esc(ESCALAMIENTO[nivel] || "")}</p>
        </div>
      </div>
      <div>
        <p class="semana-titulo">Mission week${nota ? `. Today: ${esc(nota.toLowerCase())}` : ""}</p>
        <div class="semana">${dias.join("")}</div>
      </div>
    </div>`;
}

// ---------------------------------------------------------------------------
// Indicator board
// ---------------------------------------------------------------------------
function tarjeta(e, clave, extra = "") {
  const ficha = e.catalogo[clave] || { nombre: clave, unidad: "", decimales: 0, icono: "sin_dato" };
  const estado = semaforo(e)[clave];
  const valor = e.indicadores[clave];
  const hayDato = typeof valor === "number";
  const dudoso = sospecha(e, clave);
  const nivel = dudoso ? "sospechoso" : (!hayDato ? "sin_dato" : (estado ? estado.nivel : "verde"));
  const unidad = unidadIndicador(clave) || ficha.unidad;
  let pie = "";
  if (dudoso) {
    // The value is shown struck through, only so the person can see what the sensor read.
    return `
    <article class="tarjeta nivel-sospechoso">
      <p class="tarjeta-nombre">${icono(ficha.icono)}<span>${esc(nombreIndicador(clave))}</span></p>
      <p class="tarjeta-valor"><s class="leido">${formato(dudoso.valor_leido, ficha.decimales)}</s><small>${esc(unidad)}</small></p>
      ${insignia("sospechoso")}
      <p class="tarjeta-pie"><span>Sensor reading not used: ${esc(MOTIVO_SENSOR[dudoso.motivo] || "unreliable value")}. Check the equipment.</span></p>
      ${extra}
    </article>`;
  }
  if (hayDato && estado && typeof estado.desviacion === "number") {
    const signo = estado.desviacion > 0 ? "+" : estado.desviacion < 0 ? "−" : "";
    const contra = clave === "ejercicio_min" ? "vs the plan" : "vs your normal";
    const palabra = { sube: "Up", baja: "Down", estable: "Steady" }[estado.tendencia] || "";
    // "of 5" or "% of plan" are not useful for a difference: talk about points.
    const unidadDiferencia = /^(of |%)/.test(unidad) ? "points" : unidad;
    pie = `<p class="tarjeta-pie">${estado.tendencia && estado.tendencia !== "sin_dato" ? icono(estado.tendencia) : ""}
      <span>${palabra ? palabra + ", " : ""}${signo}${formato(Math.abs(estado.desviacion), ficha.decimales)} ${esc(unidadDiferencia)} ${contra}</span></p>`;
  }
  const manual = (e.datos_manuales || []).includes(clave) ? '<span class="etiqueta-manual">Entered by hand</span>' : "";
  return `
    <article class="tarjeta nivel-${nivel}">
      <p class="tarjeta-nombre">${icono(ficha.icono)}<span>${esc(nombreIndicador(clave))}</span></p>
      <p class="tarjeta-valor">${hayDato ? formato(valor, ficha.decimales) : "No data"}${hayDato ? `<small>${esc(unidad)}</small>` : ""}</p>
      ${insignia(nivel)}
      ${pie}${extra}${manual}
    </article>`;
}

export function vistaTablero(e) {
  const principales = Object.keys(e.catalogo).filter((c) => e.catalogo[c].principal);
  const dosis = e.indicadores.dosis_acumulada_msv;
  const extraRadiacion = `<p class="tarjeta-pie">Mission total: ${formato(dosis, 1)} mSv</p>`;
  const externos = e.modulos_externos || {};
  const presion = externos.presion && typeof externos.presion.sistolica === "number"
    ? `<span>${formato(externos.presion.sistolica)}/${formato(externos.presion.diastolica)} <small>mmHg, blood pressure</small></span>` : "";
  const glucosa = typeof externos.glucosa === "number"
    ? `<span>${formato(externos.glucosa)} <small>mg/dL, glucose</small></span>` : "";
  return `
    <div class="tarjetas">${principales.map((c) => tarjeta(e, c)).join("")}</div>
    <h3 class="subtitulo">Other indicators</h3>
    <div class="tarjetas chicas">
      ${tarjeta(e, "spo2")}${tarjeta(e, "temperatura")}${tarjeta(e, "ingesta_pct")}
      ${tarjeta(e, "tasa_dosis_usv_h", extraRadiacion)}
    </div>
    ${presion || glucosa ? `
    <div class="externos">
      <h3>Optional external modules</h3>
      <div class="externos-valores">${presion}${glucosa}</div>
      <p class="ayuda">${esc(MODULOS)}</p>
    </div>` : ""}`;
}

// ---------------------------------------------------------------------------
// Body map
// ---------------------------------------------------------------------------
function nivelZona(e, zona) {
  const niveles = zona.indicadores.map((c) => (semaforo(e)[c] || {}).nivel);
  for (const alerta of e.resultado.alertas) {
    if (zona.alertas.includes(alerta.id)) niveles.push(alerta.nivel);
  }
  if (zona.estimado && e.musculo_hueso) niveles.push(e.musculo_hueso.nivel);
  return nivelMaximo(niveles);
}

export function zonaPorDefecto(e) {
  const orden = ["rojo", "naranja", "amarillo"];
  for (const nivel of orden) {
    const zona = ZONAS.find((z) => nivelZona(e, z) === nivel);
    if (zona) return zona.id;
  }
  return "cabeza";
}

export function vistaCuerpo(e, zonaActiva) {
  const niveles = Object.fromEntries(ZONAS.map((z) => [z.id, nivelZona(e, z)]));
  const zona = (id, contenido) => {
    const z = ZONAS.find((x) => x.id === id);
    return `<g class="zona nivel-${niveles[id]}${zonaActiva === id ? " activa" : ""}" data-zona="${id}" tabindex="0"
      role="button" aria-pressed="${zonaActiva === id}" aria-label="${esc(z.nombre)}: ${TEXTO_NIVEL[niveles[id]]}">${contenido}</g>`;
  };
  const figura = `
    <svg viewBox="-4 -4 208 438" role="group" aria-label="Body silhouette. Each zone can be tapped.">
      ${zona("radiacion", `
        <ellipse class="aro" cx="100" cy="215" rx="97" ry="210"/>
        <ellipse cx="100" cy="215" rx="97" ry="210" fill="none" stroke="transparent" stroke-width="24" pointer-events="stroke"/>`)}
      <g aria-hidden="true">
        <path class="silueta-borde" stroke-width="24" d="M54 100 36 204M146 100l18 104"/>
        <path class="silueta-borde" stroke-width="32" d="M84 226 79 394M116 226l5 168"/>
        <rect class="silueta" x="56" y="80" width="88" height="152" rx="28"/>
        <rect class="silueta" x="90" y="62" width="20" height="24" rx="6"/>
        <circle class="silueta" cx="100" cy="42" r="27"/>
        <path class="silueta-linea" stroke-width="20" d="M54 100 36 204M146 100l18 104"/>
        <path class="silueta-linea" stroke-width="28" d="M84 226 79 394M116 226l5 168"/>
        <rect x="58" y="82" width="84" height="148" rx="26" fill="#1a2f5e"/>
      </g>
      ${zona("musculo", `
        <path class="trazo" d="M100 168v48M84 244 80 384M116 244l4 140"/>
        <path d="M100 168v48M84 244 80 384M116 244l4 140" fill="none" stroke="transparent" stroke-width="30" stroke-linecap="round" pointer-events="stroke"/>`)}
      ${zona("pulmones", `
        <ellipse class="relleno" cx="80" cy="124" rx="13" ry="23"/>
        <ellipse class="relleno" cx="120" cy="124" rx="13" ry="23"/>`)}
      ${zona("corazon", `
        <path class="relleno" d="M102 150s-12-7.4-12-15.8a6.8 6.8 0 0 1 12-4.2 6.8 6.8 0 0 1 12 4.2c0 8.4-12 15.8-12 15.8Z"/>
        <circle class="zona-toque" cx="102" cy="138" r="16"/>`)}
      ${zona("cabeza", '<circle class="relleno" cx="100" cy="42" r="21"/>')}
    </svg>`;

  const lista = ZONAS.map((z) => `
    <button type="button" class="zona-boton" data-zona="${z.id}" aria-pressed="${zonaActiva === z.id}">
      <span>${esc(z.corto)}</span>${insignia(niveles[z.id])}
    </button>`).join("");

  const z = ZONAS.find((x) => x.id === zonaActiva) || ZONAS[0];
  const lineas = z.indicadores.map((clave) => {
    const ficha = e.catalogo[clave] || { nombre: clave, unidad: "", decimales: 0 };
    const valor = e.indicadores[clave];
    const unidad = unidadIndicador(clave) || ficha.unidad;
    const dudoso = sospecha(e, clave);
    const texto = dudoso
      ? `Suspicious data (the sensor read ${formato(dudoso.valor_leido, ficha.decimales)} ${esc(unidad)}; not used)`
      : (typeof valor === "number" ? `${formato(valor, ficha.decimales)} ${esc(unidad)}` : "No data");
    return `<li>${esc(nombreIndicador(clave))}: <b>${texto}</b></li>`;
  });
  if (z.id === "radiacion") {
    lineas.push(`<li>Mission total: <b>${formato(e.indicadores.dosis_acumulada_msv, 1)} mSv</b></li>`);
    if (e.evento_solar && e.evento_solar.activo_hoy) lineas.push("<li><b>A solar storm is underway.</b></li>");
  }
  if (z.estimado && e.musculo_hueso) {
    const m = e.musculo_hueso;
    const diasMision = `${m.dias_mision} mission day${m.dias_mision === 1 ? "" : "s"}`;
    const diasSin = `${formato(m.dias_equivalentes_sin_ejercicio, 1)} day${m.dias_equivalentes_sin_ejercicio === 1 ? "" : "s"}`;
    lineas.push(`<li>Estimated exposure: <b>${esc(MUSCULO[m.nivel] || "")}</b>. Over ${diasMision} that equals
      ${diasSin} without exercise. It is an estimate, not a measurement.</li>`);
  }
  const detalle = `
    <div class="zona-detalle" aria-live="polite">
      <div class="alerta-cabecera"><h3>${esc(z.nombre)}</h3>${insignia(niveles[z.id])}</div>
      <dl>
        <div><dt>How it is</dt><dd><ul style="margin:0;padding-left:1.1rem">${lineas.join("")}</ul></dd></div>
        <div><dt>What causes it in space</dt><dd>${esc(z.causa)}</dd></div>
        <div><dt>What to do</dt><dd>${esc(z.hacer)}</dd></div>
      </dl>
    </div>`;

  return `
    <div class="cuerpo">
      <div class="cuerpo-figura">${figura}</div>
      <div class="zonas-lista">
        ${lista}
        ${detalle}
        <div class="zona-detalle futura"><h3>${esc(INMUNE.titulo)}</h3><p>${esc(INMUNE.texto)}</p></div>
      </div>
    </div>`;
}

// ---------------------------------------------------------------------------
// Alerts with a step-by-step protocol
// ---------------------------------------------------------------------------
export function claveTemporizador(dia, alertaId, pasoId) {
  return `${dia}|${alertaId}|${pasoId}`;
}

export function vistaAlertas(e) {
  const r = e.resultado;
  if (!r.alertas.length) {
    return `<div class="vacio"><b>No alerts.</b>Nothing to do right now; keep to your routine and log your data tomorrow.</div>`;
  }
  return r.alertas.map((alerta) => {
    const protocolo = (r.protocolos || {})[alerta.protocolo_id];
    const hechos = (e.pasos_hechos || {})[alerta.id] || [];
    const pasos = protocolo ? protocolo.pasos.map((paso) => {
      const hecho = hechos.includes(paso.id);
      const clave = claveTemporizador(e.dia_actual, alerta.id, paso.id);
      const texto = pasoProtocolo(alerta.protocolo_id, paso);
      const reloj = paso.temporizador_min ? `
        <div class="paso-extra">
          <button type="button" class="boton boton-chico" data-accion="temporizador" data-clave="${esc(clave)}" data-min="${paso.temporizador_min}">
            ${icono("reloj")}Start ${paso.temporizador_min} min</button>
          <span class="temporizador" data-temporizador="${esc(clave)}" aria-live="off"></span>
        </div>` : "";
      return `
        <li class="paso${hecho ? " hecho" : ""}">
          <label>
            <input type="checkbox" data-accion="paso" data-alerta="${esc(alerta.id)}" data-paso="${esc(paso.id)}" ${hecho ? "checked" : ""}
              aria-label="Done: ${esc(texto)}">
            <span class="paso-texto">${esc(texto)}</span>
          </label>
          ${reloj}
        </li>`;
    }).join("") : "";
    const elevada = (alerta.elevada_por || []).length
      ? ` Raised one level by: ${alerta.elevada_por.map((n) => esc(NOMBRES_ESPECIALISTA[n] || n)).join(", ")}.` : "";
    const opinion = opinionJunta(alerta, r);
    return `
      <article class="alerta nivel-${alerta.nivel}">
        <div class="alerta-cabecera">${insignia(alerta.nivel)}<h3>${esc(tituloAlerta(alerta))}</h3></div>
        <p>${esc(traducirCausa(alerta.causa_en_lenguaje_simple, alerta.id))}</p>
        ${opinion || elevada ? `<p class="junta-dice">${esc(opinion)}${elevada}</p>` : ""}
        ${protocolo ? `
        <div class="protocolo">
          <h4>${esc(tituloProtocolo(alerta.protocolo_id))}. Check each step as you do it (${hechos.length} of ${protocolo.pasos.length}).</h4>
          <ol>${pasos}</ol>
        </div>` : ""}
      </article>`;
  }).join("");
}

// ---------------------------------------------------------------------------
// Medical board
// ---------------------------------------------------------------------------
const TEXTO_ESTADO = { respondio: "Answered", no_disponible: "Unavailable", no_convocado: "Not consulted" };
const ICONO_ESTADO = { respondio: "verde", no_disponible: "rojo", no_convocado: "pausa" };

function datosEntrenamiento(valor) {
  return valor === "sintéticos" ? "synthetic" : (valor || "synthetic");
}

export function vistaJunta(e) {
  const r = e.resultado;
  const miembros = (r.junta || []).map((m) => {
    const resp = m.respuesta;
    let cuerpo = `<p class="ayuda">${esc(traducirMotivo(m.motivo))}</p>`;
    if (resp) {
      const factores = (resp.factores || []).filter((f) => Math.abs(f.aporte) > 0.05).map((f) => `
        <li>${icono(f.aporte > 0 ? "sube" : "baja")}<span>${esc(ETIQUETAS[f.indicador] || "a personal factor")}${
          f.aporte > 0 ? " (raises risk)" : " (lowers risk)"}</span></li>`).join("");
      cuerpo = `
        <div class="riesgo nivel-${resp.nivel}">
          <span class="riesgo-cifra">${Math.round(resp.riesgo * 100)} %</span>
          <span class="riesgo-barra" role="img" aria-label="Estimated risk ${Math.round(resp.riesgo * 100)} percent"><i style="width:${Math.round(resp.riesgo * 100)}%"></i></span>
          ${insignia(resp.nivel)}
        </div>
        <p>${esc(explicacionCorta(resp))}</p>
        ${factores ? `<ul class="factores">${factores}</ul>` : ""}
        ${m.opinion_limitada ? `<p class="opinion-limitada">${icono("sospechoso")}<span>${esc(OPINION_LIMITADA)}</span></p>` : ""}
        <p class="ficha">Why it was consulted: ${esc(traducirMotivo(m.motivo) || "board round")}.</p>
        <p class="ficha">Model v${esc(resp.version_modelo)}, trained on ${esc(datosEntrenamiento(resp.datos_entrenamiento))} data.
          Confidence ${Math.round(resp.confianza * 100)} %.${resp.dispositivo ? ` Runs on ${esc(resp.dispositivo.toUpperCase())}.` : ""}${
          resp.respuesta_guardada ? " <b>Saved answer from a real run.</b>" : ""}</p>`;
    }
    return `
      <article class="miembro ${m.estado}">
        <div class="miembro-cabecera">
          <h3>${esc(NOMBRES_ESPECIALISTA[m.especialista] || m.especialista)} <span class="miembro-lugar">lives on the ${esc(m.laptop)}</span></h3>
          <span class="estado-miembro ${m.estado}">${icono(ICONO_ESTADO[m.estado])}${TEXTO_ESTADO[m.estado]}</span>
        </div>
        ${cuerpo}
      </article>`;
  }).join("");
  const degradado = r.modo === "degradado";
  const reglas = (r.reglas_activadas || []).length
    ? r.reglas_activadas.map((id) => tituloAlerta(id)).join(", ") : "none";
  return `
    <div class="junta">
      ${miembros}
      <div class="resultado-final">
        <h3>Final result</h3>
        <div class="alerta-cabecera">${insignia(r.nivel_global)}
          <span class="modo ${r.modo}">${icono(degradado ? "naranja" : "verde")}${degradado ? "Degraded" : "Full"} mode</span></div>
        <p>${esc(explicacionGlobal(r))}</p>
        <p class="ficha">The rules set the level. A specialist can raise it one step, never lower it.
          Rules activated today: ${esc(reglas)}.</p>
      </div>
    </div>`;
}

// ---------------------------------------------------------------------------
// Trend chart (custom SVG, no libraries)
// ---------------------------------------------------------------------------
export const INDICADORES_TENDENCIA = [
  "sueno_h", "animo", "estres", "ejercicio_min", "fc_reposo", "hrv", "spo2", "temperatura",
  "ingesta_pct", "tasa_dosis_usv_h", "dosis_acumulada_msv", "tiempo_reaccion_ms", "cohesion_equipo",
];

export function vistaTendencia(e, clave) {
  const ficha = e.catalogo[clave] || { nombre: clave, unidad: "", decimales: 0 };
  const unidad = unidadIndicador(clave) || ficha.unidad;
  const serie = e.tendencias_7d[clave] || [];
  const dias = e.dias_tendencia || [];
  const estado = semaforo(e)[clave] || {};
  const base = typeof estado.referencia === "number" ? estado.referencia
    : (typeof e.linea_base[clave] === "number" ? e.linea_base[clave] : null);
  const umbral = typeof estado.umbral_amarillo === "number" ? estado.umbral_amarillo : null;

  const opciones = INDICADORES_TENDENCIA.filter((c) => e.catalogo[c]).map((c) =>
    `<option value="${c}" ${c === clave ? "selected" : ""}>${esc(nombreIndicador(c))}</option>`).join("");
  const selector = `
    <div class="selector">
      <label for="tendencia-indicador">Indicator</label>
      <select id="tendencia-indicador">${opciones}</select>
    </div>`;

  const validos = serie.filter((v) => typeof v === "number");
  if (!validos.length) {
    return `${selector}<div class="vacio"><b>No data.</b>There are no records for this indicator yet.</div>`;
  }

  const ANCHO = 640, ALTO = 270, IZQ = 50, DER = 20, ARR = 26, ABA = 36;
  const referencia = [...validos];
  let banda = null;
  if (base !== null) {
    referencia.push(base);
    if (umbral !== null) {
      const delta = Math.abs(umbral - base);
      banda = [base - delta, base + delta];
      referencia.push(umbral);
    }
  } else if (umbral !== null) {
    referencia.push(umbral);
  }
  let min = Math.min(...referencia), max = Math.max(...referencia);
  if (max - min < 1e-9) { min -= 1; max += 1; }
  const margen = (max - min) * 0.14;
  min -= margen; max += margen;
  const x = (i) => (serie.length === 1 ? (IZQ + ANCHO - DER) / 2 : IZQ + (i * (ANCHO - IZQ - DER)) / (serie.length - 1));
  const y = (v) => ARR + (1 - (v - min) / (max - min)) * (ALTO - ARR - ABA);
  const recortar = (v) => Math.min(Math.max(v, min), max);

  // Line by segments: a day without data breaks the line instead of inventing a value.
  const tramos = [];
  let actual = [];
  serie.forEach((v, i) => {
    if (typeof v === "number") actual.push(`${x(i).toFixed(1)},${y(v).toFixed(1)}`);
    else if (actual.length) { tramos.push(actual); actual = []; }
  });
  if (actual.length) tramos.push(actual);

  const marcas = [min + margen, (min + max) / 2, max - margen].map((v) => `
    <line class="eje" x1="${IZQ}" x2="${ANCHO - DER}" y1="${y(v).toFixed(1)}" y2="${y(v).toFixed(1)}"/>
    <text x="${IZQ - 8}" y="${(y(v) + 4).toFixed(1)}" text-anchor="end">${formato(v, ficha.decimales)}</text>`).join("");
  const puntos = serie.map((v, i) => {
    const etiquetaDia = `<text x="${x(i).toFixed(1)}" y="${ALTO - 12}" text-anchor="middle">Day ${dias[i] ?? i + 1}</text>`;
    if (typeof v !== "number") {
      return `${etiquetaDia}<text x="${x(i).toFixed(1)}" y="${(ALTO - ABA - 8)}" text-anchor="middle">no data</text>`;
    }
    const hoy = i === serie.length - 1;
    return `${etiquetaDia}
      <circle class="punto${hoy ? " hoy" : ""}" cx="${x(i).toFixed(1)}" cy="${y(v).toFixed(1)}" r="${hoy ? 7 : 5.5}"/>
      <text class="valor" x="${x(i).toFixed(1)}" y="${(y(v) - 13).toFixed(1)}" text-anchor="middle">${formato(v, ficha.decimales)}</text>`;
  }).join("");

  const resumen = `${nombreIndicador(clave)}, last ${serie.length} days: ` +
    serie.map((v, i) => `day ${dias[i] ?? i + 1}, ${typeof v === "number" ? formato(v, ficha.decimales) : "no data"}`).join("; ") +
    (base !== null ? `. Baseline ${formato(base, ficha.decimales)}.` : ".");

  return `
    ${selector}
    <div class="grafica">
      <svg viewBox="0 0 ${ANCHO} ${ALTO}" role="img" aria-label="${esc(resumen)}">
        ${banda ? `<rect class="banda" x="${IZQ}" width="${ANCHO - IZQ - DER}" y="${y(recortar(banda[1])).toFixed(1)}"
          height="${Math.max(0, y(recortar(banda[0])) - y(recortar(banda[1]))).toFixed(1)}"/>` : ""}
        ${marcas}
        ${base !== null ? `<line class="base" x1="${IZQ}" x2="${ANCHO - DER}" y1="${y(base).toFixed(1)}" y2="${y(base).toFixed(1)}"/>` : ""}
        ${umbral !== null ? `<line class="umbral" x1="${IZQ}" x2="${ANCHO - DER}" y1="${y(umbral).toFixed(1)}" y2="${y(umbral).toFixed(1)}"/>` : ""}
        ${tramos.map((t) => `<polyline class="linea" points="${t.join(" ")}"/>`).join("")}
        ${puntos}
      </svg>
    </div>
    <div class="leyenda">
      <span><i class="l-dato"></i>${esc(nombreIndicador(clave))} (${esc(unidad)})</span>
      ${base !== null ? `<span><i></i>${clave === "ejercicio_min" ? "Plan" : "Your baseline"}: ${formato(base, ficha.decimales)}</span>` : ""}
      ${banda ? '<span><i class="l-banda"></i>Your usual range</span>' : ""}
      ${umbral !== null ? `<span><i class="l-umbral"></i>Warns from here: ${formato(umbral, ficha.decimales)}</span>` : ""}
    </div>
    <p style="margin-top:.9rem"><a class="boton boton-secundario" href="api/exportar.csv" download>Export history (CSV)</a></p>`;
}

// ---------------------------------------------------------------------------
// Flight surgeon report
// ---------------------------------------------------------------------------
export function vistaInforme(e, abiertos) {
  const informes = e.informes || [];
  const enlace = e.ultimo_enlace
    ? `<p class="ayuda">Last simulated link with Earth: ${e.ultimo_enlace.enviados} report${e.ultimo_enlace.enviados === 1 ? "" : "s"} sent.</p>` : "";
  if (!informes.length) {
    return `<div class="vacio"><b>No reports.</b>One is prepared automatically when the level reaches Alert or Critical,
      and it waits for the next link with Earth (about ${e.retraso_enlace_min} minutes each way).</div>${enlace}`;
  }
  const lista = informes.map((inf) => {
    const c = inf.contenido;
    const pendiente = inf.estado === "pendiente";
    const filas = (c.indicadores || []).map((i) => `
      <tr><td>${esc(nombreIndicador(i.indicador) || i.nombre)}</td>
        <td class="num">${typeof i.valor === "number" ? i.valor : (i.nivel === "sospechoso" ? "not used" : "no data")} ${esc(unidadIndicador(i.indicador) || i.unidad)}</td>
        <td class="num">${typeof i.linea_base === "number" ? Math.round(i.linea_base * 10) / 10 : "–"}</td>
        <td>${insignia(i.nivel)}</td></tr>`).join("");
    const tomadas = (c.acciones_tomadas || []).length
      ? `<ul>${c.acciones_tomadas.map((a) => `<li>${esc(traducirPaso(a.paso) || "Protocol step completed.")}</li>`).join("")}</ul>`
      : '<p class="ayuda">No protocol step has been checked yet.</p>';
    const consultados = (c.especialistas_consultados || []).length
      ? `<ul>${c.especialistas_consultados.map((s) => `<li>${esc(NOMBRES_ESPECIALISTA[s.especialista] || s.especialista)} (${esc(s.laptop)}):
          risk ${Math.round(s.riesgo * 100)} %, ${TEXTO_NIVEL[s.nivel].toLowerCase()}, model v${esc(s.version_modelo)} with ${esc(datosEntrenamiento(s.datos_entrenamiento))} data</li>`).join("")}</ul>`
      : '<p class="ayuda">No specialist answered; the report is based on the rules.</p>';
    const reglas = (c.reglas_activadas || []).length
      ? c.reglas_activadas.map((id) => tituloAlerta(id)).join(", ") : "None";
    const dudosos = (c.sensores_sospechosos || []).length
      ? `<div><h4>Suspicious sensor data (not used)</h4><ul>${c.sensores_sospechosos.map((s) =>
        `<li>${esc(avisoSensor(s))}</li>`).join("")}</ul></div>` : "";
    return `
      <details class="informe" data-informe="${esc(inf.id)}" ${abiertos.has(inf.id) ? "open" : ""}>
        <summary><span>Day ${inf.dia} report</span> ${insignia(c.nivel_global)}
          <span class="cola ${inf.estado}">${icono(pendiente ? "reloj" : "verde")}${pendiente ? "Pending to send" : "Sent to Earth"}</span>
        </summary>
        <div class="informe-cuerpo">
          <div><h4>Summary</h4><ul>${(c.resumen || []).map((a) => `<li><b>${esc(tituloAlerta(a.alerta))}.</b> ${esc(traducirCausa(a.causa, a.alerta))}</li>`).join("")}</ul></div>
          <div><h4>Indicators of the day</h4>
            <div class="tabla-envoltura"><table>
              <thead><tr><th>Indicator</th><th>Value</th><th>Baseline</th><th>Status</th></tr></thead>
              <tbody>${filas}</tbody></table></div></div>
          ${dudosos}
          <div><h4>Rules activated</h4><p>${esc(reglas)}</p></div>
          <div><h4>Specialists consulted</h4>${consultados}
            ${(c.especialistas_no_disponibles || []).length ? `<p class="ayuda">Unavailable: ${c.especialistas_no_disponibles.map((n) => esc(NOMBRES_ESPECIALISTA[n] || n)).join(", ")}.</p>` : ""}</div>
          <div><h4>Actions taken by the astronaut</h4>${tomadas}</div>
          <p class="ficha">${esc(NOTA_INFORME)} Includes the 7-day trend for each indicator.</p>
        </div>
      </details>`;
  }).join("");
  const pendientes = informes.filter((i) => i.estado === "pendiente").length;
  return `${lista}
    <p class="ayuda" style="margin-top:.7rem">${pendientes
      ? `${pendientes} report${pendientes === 1 ? "" : "s"} waiting. They are sent when you press "Simulate link with Earth" in the demo panel.`
      : "No reports waiting."}</p>${enlace}`;
}
