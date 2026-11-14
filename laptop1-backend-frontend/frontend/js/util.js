// Utilidades compartidas por la interfaz: iconos locales, textos de nivel y formato.
// Todo es código propio: sin librerías ni recursos remotos.

/** Escapa texto antes de insertarlo como HTML. */
export function esc(texto) {
  return String(texto ?? "").replace(/[&<>"']/g, (c) => (
    { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]
  ));
}

// Trazos SVG (24x24). Cada nivel tiene una FORMA distinta, no solo un color.
const TRAZOS = {
  verde: '<circle cx="12" cy="12" r="9"/><path d="m8 12.5 3 3 5-6"/>',
  amarillo: '<path d="M12 3.5 2.8 19.5h18.4L12 3.5Z"/><path d="M12 10v4.5M12 17.2v.3"/>',
  naranja: '<path d="M12 2.5 21.5 12 12 21.5 2.5 12 12 2.5Z"/><path d="M12 8v5M12 15.8v.3"/>',
  rojo: '<path d="M8.2 3h7.6L21 8.2v7.6L15.8 21H8.2L3 15.8V8.2L8.2 3Z"/><path d="m9 9 6 6M15 9l-6 6"/>',
  sin_dato: '<circle cx="12" cy="12" r="9" stroke-dasharray="3 3.5"/><path d="M8.5 12h7"/>',
  sube: '<path d="M12 19V5M6 11l6-6 6 6"/>',
  baja: '<path d="M12 5v14M6 13l6 6 6-6"/>',
  estable: '<path d="M5 12h14M13 6l6 6-6 6"/>',
  luna: '<path d="M20 14.5A8 8 0 1 1 9.5 4a6.5 6.5 0 0 0 10.5 10.5Z"/>',
  cara: '<circle cx="12" cy="12" r="9"/><path d="M8.5 14.5a4.5 4.5 0 0 0 7 0M9 9.5v.5M15 9.5v.5"/>',
  onda: '<path d="M3 12c2-6 4-6 6 0s4 6 6 0 4-6 6 0"/>',
  pesa: '<path d="M4 9v6M7 6.5v11M17 6.5v11M20 9v6M7 12h10"/>',
  corazon: '<path d="M12 20s-7.5-4.6-7.5-10A4.5 4.5 0 0 1 12 7.5 4.5 4.5 0 0 1 19.5 10c0 5.4-7.5 10-7.5 10Z"/>',
  pulso: '<path d="M3 12h4l2.5-6 4 12 2.5-6h5"/>',
  gota: '<path d="M12 3.5s6 6.3 6 10.5a6 6 0 0 1-12 0c0-4.2 6-10.5 6-10.5Z"/>',
  termometro: '<path d="M10 14V5a2 2 0 1 1 4 0v9a4 4 0 1 1-4 0Z"/>',
  plato: '<circle cx="12" cy="12" r="8.5"/><circle cx="12" cy="12" r="4"/>',
  radiacion: '<circle cx="12" cy="12" r="2.5"/><path d="M12 3v4M12 17v4M3 12h4M17 12h4M5.6 5.6l2.8 2.8M15.6 15.6l2.8 2.8M18.4 5.6l-2.8 2.8M8.4 15.6l-2.8 2.8"/>',
  reloj: '<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/>',
  pausa: '<circle cx="12" cy="12" r="9"/><path d="M10 9v6M14 9v6"/>',
};

export function icono(nombre) {
  return `<svg class="icono" viewBox="0 0 24 24" aria-hidden="true">${TRAZOS[nombre] || TRAZOS.sin_dato}</svg>`;
}

export const TEXTO_NIVEL = {
  verde: "Normal", amarillo: "Atención", naranja: "Alerta", rojo: "Crítico", sin_dato: "Sin dato",
};
const ORDEN = ["sin_dato", "verde", "amarillo", "naranja", "rojo"];

/** Insignia de nivel: icono + texto + color (nunca solo color). */
export function insignia(nivel) {
  const n = TEXTO_NIVEL[nivel] ? nivel : "sin_dato";
  return `<span class="nivel nivel-${n}">${icono(n)}${TEXTO_NIVEL[n]}</span>`;
}

/** El nivel más grave de una lista (ignora los vacíos). */
export function nivelMaximo(niveles) {
  return niveles.filter(Boolean).reduce((a, b) => (ORDEN.indexOf(b) > ORDEN.indexOf(a) ? b : a), "sin_dato");
}

/** Número con los decimales del catálogo, o "Sin dato". */
export function formato(valor, decimales = 0) {
  if (typeof valor !== "number" || Number.isNaN(valor)) return "Sin dato";
  return valor.toFixed(decimales);
}

export const NOMBRES_ESPECIALISTA = {
  "sueno": "Sueño", "fatiga-bienestar": "Fatiga y bienestar",
  "cardiovascular": "Cardiovascular", "riesgo-solar": "Riesgo solar",
};
