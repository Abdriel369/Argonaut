// Vistas: funciones puras que reciben el estado del backend y devuelven HTML.
// Si falta un dato se muestra "Sin dato"; nada de esto debe romper la pantalla.

import { esc, icono, insignia, formato, nivelMaximo, TEXTO_NIVEL, NOMBRES_ESPECIALISTA } from "./util.js";
import { ZONAS, INMUNE } from "./contenido.js";

const semaforo = (e) => (e.resultado && e.resultado.semaforo_indicadores) || {};

// ---------------------------------------------------------------------------
// Estado general + semana de misión
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
      : `<span aria-hidden="true">${icono("sin_dato")}</span><span class="solo-lectores">Aún no llega</span>`;
    dias.push(`<div class="${clases}"><span>Día</span><b>${d}</b>${marca}</div>`);
  }
  const cambio = nivelAnterior && nivelAnterior !== nivel ? " cambio" : "";
  return `
    <div class="estado-global">
      <div class="estado-principal nivel-${nivel}">
        <div class="estado-insignia${cambio}">${icono(nivel)}</div>
        <div>
          <p class="estado-nivel">${TEXTO_NIVEL[nivel]}</p>
          <p class="estado-texto">${esc(r.explicacion_global)}</p>
          <p class="estado-accion"><b>Qué sigue:</b> ${esc(r.escalamiento.accion)}</p>
        </div>
      </div>
      <div>
        <p class="semana-titulo">Semana de misión${e.nota_dia ? `. Hoy: ${esc(e.nota_dia.toLowerCase())}` : ""}</p>
        <div class="semana">${dias.join("")}</div>
      </div>
    </div>`;
}

// ---------------------------------------------------------------------------
// Tablero de indicadores
// ---------------------------------------------------------------------------
function tarjeta(e, clave, extra = "") {
  const ficha = e.catalogo[clave] || { nombre: clave, unidad: "", decimales: 0, icono: "sin_dato" };
  const estado = semaforo(e)[clave];
  const valor = e.indicadores[clave];
  const hayDato = typeof valor === "number";
  const nivel = !hayDato ? "sin_dato" : (estado ? estado.nivel : "verde");
  let pie = "";
  if (hayDato && estado && typeof estado.desviacion === "number") {
    const signo = estado.desviacion > 0 ? "+" : estado.desviacion < 0 ? "−" : "";
    const contra = clave === "ejercicio_min" ? "frente al plan" : "frente a tu normal";
    const palabra = { sube: "Sube", baja: "Baja", estable: "Estable" }[estado.tendencia] || "";
    // "de 5" o "% del plan" no sirven para decir una diferencia: se habla de puntos.
    const unidad = /^(de |%)/.test(ficha.unidad) ? "puntos" : ficha.unidad;
    pie = `<p class="tarjeta-pie">${estado.tendencia && estado.tendencia !== "sin_dato" ? icono(estado.tendencia) : ""}
      <span>${palabra ? palabra + ", " : ""}${signo}${formato(Math.abs(estado.desviacion), ficha.decimales)} ${esc(unidad)} ${contra}</span></p>`;
  }
  const manual = (e.datos_manuales || []).includes(clave) ? '<span class="etiqueta-manual">Ingresado a mano</span>' : "";
  return `
    <article class="tarjeta nivel-${nivel}">
      <p class="tarjeta-nombre">${icono(ficha.icono)}<span>${esc(ficha.nombre)}</span></p>
      <p class="tarjeta-valor">${hayDato ? formato(valor, ficha.decimales) : "Sin dato"}${hayDato ? `<small>${esc(ficha.unidad)}</small>` : ""}</p>
      ${insignia(nivel)}
      ${pie}${extra}${manual}
    </article>`;
}

export function vistaTablero(e) {
  const principales = Object.keys(e.catalogo).filter((c) => e.catalogo[c].principal);
  const dosis = e.indicadores.dosis_acumulada_msv;
  const extraRadiacion = `<p class="tarjeta-pie">Acumulada en la misión: ${formato(dosis, 1)} mSv</p>`;
  const externos = e.modulos_externos || {};
  const presion = externos.presion && typeof externos.presion.sistolica === "number"
    ? `<span>${formato(externos.presion.sistolica)}/${formato(externos.presion.diastolica)} <small>mmHg, presión arterial</small></span>` : "";
  const glucosa = typeof externos.glucosa === "number"
    ? `<span>${formato(externos.glucosa)} <small>mg/dL, glucosa</small></span>` : "";
  return `
    <div class="tarjetas">${principales.map((c) => tarjeta(e, c)).join("")}</div>
    <h3 class="subtitulo">Otros indicadores</h3>
    <div class="tarjetas chicas">
      ${tarjeta(e, "spo2")}${tarjeta(e, "temperatura")}${tarjeta(e, "ingesta_pct")}
      ${tarjeta(e, "tasa_dosis_usv_h", extraRadiacion)}
    </div>
    ${presion || glucosa ? `
    <div class="externos">
      <h3>Módulos externos opcionales</h3>
      <div class="externos-valores">${presion}${glucosa}</div>
      <p class="ayuda">${esc(externos.etiqueta || "")}</p>
    </div>` : ""}`;
}

// ---------------------------------------------------------------------------
// Mapa corporal
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
    <svg viewBox="-4 -4 208 438" role="group" aria-label="Silueta del cuerpo. Cada zona se puede tocar.">
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
    const texto = typeof valor === "number" ? `${formato(valor, ficha.decimales)} ${esc(ficha.unidad)}` : "Sin dato";
    return `<li>${esc(ficha.nombre)}: <b>${texto}</b></li>`;
  });
  if (z.id === "radiacion") {
    lineas.push(`<li>Acumulada en la misión: <b>${formato(e.indicadores.dosis_acumulada_msv, 1)} mSv</b></li>`);
    if (e.evento_solar && e.evento_solar.activo_hoy) lineas.push("<li><b>Hay una tormenta solar en curso.</b></li>");
  }
  if (z.estimado && e.musculo_hueso) {
    const m = e.musculo_hueso;
    lineas.push(`<li>Exposición estimada: <b>${esc(m.texto)}</b>. En ${m.dias_mision} día${m.dias_mision === 1 ? "" : "s"} de misión
      equivale a ${formato(m.dias_equivalentes_sin_ejercicio, 1)} día${m.dias_equivalentes_sin_ejercicio === 1 ? "" : "s"} sin ejercicio.
      Es una estimación, no una medición.</li>`);
  }
  const detalle = `
    <div class="zona-detalle" aria-live="polite">
      <div class="alerta-cabecera"><h3>${esc(z.nombre)}</h3>${insignia(niveles[z.id])}</div>
      <dl>
        <div><dt>Cómo está</dt><dd><ul style="margin:0;padding-left:1.1rem">${lineas.join("")}</ul></dd></div>
        <div><dt>Qué lo causa en el espacio</dt><dd>${esc(z.causa)}</dd></div>
        <div><dt>Qué hacer</dt><dd>${esc(z.hacer)}</dd></div>
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
// Alertas con protocolo paso a paso
// ---------------------------------------------------------------------------
export function claveTemporizador(dia, alertaId, pasoId) {
  return `${dia}|${alertaId}|${pasoId}`;
}

export function vistaAlertas(e) {
  const r = e.resultado;
  if (!r.alertas.length) {
    return `<div class="vacio"><b>Sin alertas.</b>No hay nada que hacer ahora; sigue con tu rutina y registra tus datos mañana.</div>`;
  }
  return r.alertas.map((alerta) => {
    const protocolo = (r.protocolos || {})[alerta.protocolo_id];
    const hechos = (e.pasos_hechos || {})[alerta.id] || [];
    const pasos = protocolo ? protocolo.pasos.map((paso) => {
      const hecho = hechos.includes(paso.id);
      const clave = claveTemporizador(e.dia_actual, alerta.id, paso.id);
      const reloj = paso.temporizador_min ? `
        <div class="paso-extra">
          <button type="button" class="boton boton-chico" data-accion="temporizador" data-clave="${esc(clave)}" data-min="${paso.temporizador_min}">
            ${icono("reloj")}Iniciar ${paso.temporizador_min} min</button>
          <span class="temporizador" data-temporizador="${esc(clave)}" aria-live="off"></span>
        </div>` : "";
      return `
        <li class="paso${hecho ? " hecho" : ""}">
          <label>
            <input type="checkbox" data-accion="paso" data-alerta="${esc(alerta.id)}" data-paso="${esc(paso.id)}" ${hecho ? "checked" : ""}
              aria-label="Ya lo hice: ${esc(paso.texto)}">
            <span class="paso-texto">${esc(paso.texto)}</span>
          </label>
          ${reloj}
        </li>`;
    }).join("") : "";
    const elevada = (alerta.elevada_por || []).length
      ? ` Subió un nivel por la opinión de: ${alerta.elevada_por.map((n) => esc(NOMBRES_ESPECIALISTA[n] || n)).join(", ")}.` : "";
    return `
      <article class="alerta nivel-${alerta.nivel}">
        <div class="alerta-cabecera">${insignia(alerta.nivel)}<h3>${esc(alerta.titulo)}</h3></div>
        <p>${esc(alerta.causa_en_lenguaje_simple)}</p>
        ${alerta.opinion_junta || elevada ? `<p class="junta-dice">${esc(alerta.opinion_junta || "")}${elevada}</p>` : ""}
        ${protocolo ? `
        <div class="protocolo">
          <h4>${esc(protocolo.titulo)}. Marca cada paso cuando lo hagas (${hechos.length} de ${protocolo.pasos.length}).</h4>
          <ol>${pasos}</ol>
        </div>` : ""}
      </article>`;
  }).join("");
}

// ---------------------------------------------------------------------------
// Junta médica
// ---------------------------------------------------------------------------
const TEXTO_ESTADO = { respondio: "Respondió", no_disponible: "No disponible", no_convocado: "No se le consultó" };
const ICONO_ESTADO = { respondio: "verde", no_disponible: "rojo", no_convocado: "pausa" };

export function vistaJunta(e) {
  const r = e.resultado;
  const miembros = (r.junta || []).map((m) => {
    const resp = m.respuesta;
    let cuerpo = `<p class="ayuda">${esc(m.motivo || "")}</p>`;
    if (resp) {
      const factores = (resp.factores || []).filter((f) => Math.abs(f.aporte) > 0.05).map((f) => `
        <li>${icono(f.aporte > 0 ? "sube" : "baja")}<span>${esc(f.etiqueta || f.indicador)}${
          f.aporte > 0 ? " (sube el riesgo)" : " (baja el riesgo)"}</span></li>`).join("");
      cuerpo = `
        <div class="riesgo nivel-${resp.nivel}">
          <span class="riesgo-cifra">${Math.round(resp.riesgo * 100)} %</span>
          <span class="riesgo-barra" role="img" aria-label="Riesgo estimado ${Math.round(resp.riesgo * 100)} por ciento"><i style="width:${Math.round(resp.riesgo * 100)}%"></i></span>
          ${insignia(resp.nivel)}
        </div>
        <p>${esc(resp.explicacion_corta)}</p>
        ${factores ? `<ul class="factores">${factores}</ul>` : ""}
        <p class="ficha">Por qué se le consultó: ${esc(m.motivo || "ronda de la junta")}.</p>
        <p class="ficha">Modelo v${esc(resp.version_modelo)}, entrenado con datos ${esc(resp.datos_entrenamiento)}.
          Confianza ${Math.round(resp.confianza * 100)} %.${resp.dispositivo ? ` Corre en ${esc(resp.dispositivo.toUpperCase())}.` : ""}${
          resp.respuesta_guardada ? " <b>Respuesta guardada de una ejecución real.</b>" : ""}</p>`;
    }
    return `
      <article class="miembro ${m.estado}">
        <div class="miembro-cabecera">
          <h3>${esc(m.titulo || m.especialista)} <span class="miembro-lugar">vive en la ${esc(m.laptop)}</span></h3>
          <span class="estado-miembro ${m.estado}">${icono(ICONO_ESTADO[m.estado])}${TEXTO_ESTADO[m.estado]}</span>
        </div>
        ${cuerpo}
      </article>`;
  }).join("");
  const degradado = r.modo === "degradado";
  return `
    <div class="junta">
      ${miembros}
      <div class="resultado-final">
        <h3>Resultado final</h3>
        <div class="alerta-cabecera">${insignia(r.nivel_global)}
          <span class="modo ${r.modo}">${icono(degradado ? "naranja" : "verde")}Modo ${degradado ? "degradado" : "completo"}</span></div>
        <p>${esc(r.explicacion_global)}</p>
        <p class="ficha">Las reglas deciden el nivel. Un especialista puede subirlo un escalón, nunca bajarlo.
          Reglas activadas hoy: ${r.reglas_activadas && r.reglas_activadas.length ? esc(r.reglas_activadas.join(", ")) : "ninguna"}.</p>
      </div>
    </div>`;
}

// ---------------------------------------------------------------------------
// Gráfica de tendencia (SVG propio, sin librerías)
// ---------------------------------------------------------------------------
export const INDICADORES_TENDENCIA = [
  "sueno_h", "animo", "estres", "ejercicio_min", "fc_reposo", "hrv", "spo2", "temperatura",
  "ingesta_pct", "tasa_dosis_usv_h", "dosis_acumulada_msv", "tiempo_reaccion_ms", "cohesion_equipo",
];

export function vistaTendencia(e, clave) {
  const ficha = e.catalogo[clave] || { nombre: clave, unidad: "", decimales: 0 };
  const serie = e.tendencias_7d[clave] || [];
  const dias = e.dias_tendencia || [];
  const estado = semaforo(e)[clave] || {};
  const base = typeof estado.referencia === "number" ? estado.referencia
    : (typeof e.linea_base[clave] === "number" ? e.linea_base[clave] : null);
  const umbral = typeof estado.umbral_amarillo === "number" ? estado.umbral_amarillo : null;

  const opciones = INDICADORES_TENDENCIA.filter((c) => e.catalogo[c]).map((c) =>
    `<option value="${c}" ${c === clave ? "selected" : ""}>${esc(e.catalogo[c].nombre)}</option>`).join("");
  const selector = `
    <div class="selector">
      <label for="tendencia-indicador">Indicador</label>
      <select id="tendencia-indicador">${opciones}</select>
    </div>`;

  const validos = serie.filter((v) => typeof v === "number");
  if (!validos.length) {
    return `${selector}<div class="vacio"><b>Sin dato.</b>Todavía no hay registros de este indicador.</div>`;
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

  // Línea por tramos: un día sin dato corta la línea en lugar de inventar un valor.
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
    const etiquetaDia = `<text x="${x(i).toFixed(1)}" y="${ALTO - 12}" text-anchor="middle">Día ${dias[i] ?? i + 1}</text>`;
    if (typeof v !== "number") {
      return `${etiquetaDia}<text x="${x(i).toFixed(1)}" y="${(ALTO - ABA - 8)}" text-anchor="middle">sin dato</text>`;
    }
    const hoy = i === serie.length - 1;
    return `${etiquetaDia}
      <circle class="punto${hoy ? " hoy" : ""}" cx="${x(i).toFixed(1)}" cy="${y(v).toFixed(1)}" r="${hoy ? 7 : 5.5}"/>
      <text class="valor" x="${x(i).toFixed(1)}" y="${(y(v) - 13).toFixed(1)}" text-anchor="middle">${formato(v, ficha.decimales)}</text>`;
  }).join("");

  const resumen = `${ficha.nombre}, últimos ${serie.length} días: ` +
    serie.map((v, i) => `día ${dias[i] ?? i + 1}, ${typeof v === "number" ? formato(v, ficha.decimales) : "sin dato"}`).join("; ") +
    (base !== null ? `. Línea base ${formato(base, ficha.decimales)}.` : ".");

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
      <span><i class="l-dato"></i>${esc(ficha.nombre)} (${esc(ficha.unidad)})</span>
      ${base !== null ? `<span><i></i>${clave === "ejercicio_min" ? "Plan" : "Tu línea base"}: ${formato(base, ficha.decimales)}</span>` : ""}
      ${banda ? '<span><i class="l-banda"></i>Tu rango habitual</span>' : ""}
      ${umbral !== null ? `<span><i class="l-umbral"></i>Desde aquí avisa: ${formato(umbral, ficha.decimales)}</span>` : ""}
    </div>
    <p style="margin-top:.9rem"><a class="boton boton-secundario" href="api/exportar.csv" download>Exportar historial (CSV)</a></p>`;
}

// ---------------------------------------------------------------------------
// Informe para el cirujano de vuelo
// ---------------------------------------------------------------------------
export function vistaInforme(e, abiertos) {
  const informes = e.informes || [];
  const enlace = e.ultimo_enlace
    ? `<p class="ayuda">Último enlace simulado con la Tierra: ${e.ultimo_enlace.enviados} informe${e.ultimo_enlace.enviados === 1 ? "" : "s"} enviado${e.ultimo_enlace.enviados === 1 ? "" : "s"}.</p>` : "";
  if (!informes.length) {
    return `<div class="vacio"><b>No hay informes.</b>Se prepara uno automáticamente cuando el nivel llega a Alerta o Crítico,
      y queda en espera del próximo enlace con la Tierra (unos ${e.retraso_enlace_min} minutos por sentido).</div>${enlace}`;
  }
  const lista = informes.map((inf) => {
    const c = inf.contenido;
    const pendiente = inf.estado === "pendiente";
    const filas = (c.indicadores || []).map((i) => `
      <tr><td>${esc(i.nombre)}</td>
        <td class="num">${typeof i.valor === "number" ? i.valor : "sin dato"} ${esc(i.unidad)}</td>
        <td class="num">${typeof i.linea_base === "number" ? Math.round(i.linea_base * 10) / 10 : "–"}</td>
        <td>${insignia(i.nivel)}</td></tr>`).join("");
    const tomadas = (c.acciones_tomadas || []).length
      ? `<ul>${c.acciones_tomadas.map((a) => `<li>${esc(a.paso)}</li>`).join("")}</ul>`
      : '<p class="ayuda">Aún no se marcó ningún paso del protocolo.</p>';
    const consultados = (c.especialistas_consultados || []).length
      ? `<ul>${c.especialistas_consultados.map((s) => `<li>${esc(NOMBRES_ESPECIALISTA[s.especialista] || s.especialista)} (${esc(s.laptop)}):
          riesgo ${Math.round(s.riesgo * 100)} %, ${TEXTO_NIVEL[s.nivel].toLowerCase()}, modelo v${esc(s.version_modelo)} con datos ${esc(s.datos_entrenamiento)}</li>`).join("")}</ul>`
      : '<p class="ayuda">Ningún especialista respondió; el informe se basa en las reglas.</p>';
    return `
      <details class="informe" data-informe="${esc(inf.id)}" ${abiertos.has(inf.id) ? "open" : ""}>
        <summary><span>Informe del día ${inf.dia}</span> ${insignia(c.nivel_global)}
          <span class="cola ${inf.estado}">${icono(pendiente ? "reloj" : "verde")}${pendiente ? "Pendiente de enviar" : "Enviado a la Tierra"}</span>
        </summary>
        <div class="informe-cuerpo">
          <div><h4>Resumen</h4><ul>${(c.resumen || []).map((a) => `<li><b>${esc(a.titulo)}.</b> ${esc(a.causa)}</li>`).join("")}</ul></div>
          <div><h4>Indicadores del día</h4>
            <div class="tabla-envoltura"><table>
              <thead><tr><th>Indicador</th><th>Valor</th><th>Línea base</th><th>Estado</th></tr></thead>
              <tbody>${filas}</tbody></table></div></div>
          <div><h4>Reglas activadas</h4><p>${esc((c.reglas_activadas || []).join(", ") || "Ninguna")}</p></div>
          <div><h4>Especialistas consultados</h4>${consultados}
            ${(c.especialistas_no_disponibles || []).length ? `<p class="ayuda">No disponibles: ${c.especialistas_no_disponibles.map((n) => esc(NOMBRES_ESPECIALISTA[n] || n)).join(", ")}.</p>` : ""}</div>
          <div><h4>Acciones tomadas por la astronauta</h4>${tomadas}</div>
          <p class="ficha">${esc(c.nota || "")} Incluye la tendencia de 7 días de cada indicador.</p>
        </div>
      </details>`;
  }).join("");
  const pendientes = informes.filter((i) => i.estado === "pendiente").length;
  return `${lista}
    <p class="ayuda" style="margin-top:.7rem">${pendientes
      ? `${pendientes} informe${pendientes === 1 ? "" : "s"} en espera. Se envía${pendientes === 1 ? "" : "n"} al pulsar “Simular enlace con la Tierra” en el panel de demo.`
      : "No hay informes en espera."}</p>${enlace}`;
}
